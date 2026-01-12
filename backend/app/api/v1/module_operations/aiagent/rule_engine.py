# -*- coding: utf-8 -*-
"""
规则引擎
用于判断操作是否需要确认，以及是否符合安全规则
"""

import logging
from typing import Dict, Any, Tuple, List
from datetime import datetime, time

from app.api.v1.module_system.auth.schema import AuthSchema
from app.api.v1.module_system.user.model import UserModel

from .crud import AIAgentCRUD
from .models import RuleType

logger = logging.getLogger(__name__)


class RuleEngine:
    """规则引擎"""
    
    def __init__(self, auth: AuthSchema):
        """
        初始化规则引擎
        
        Args:
            auth: 认证信息
        """
        self.auth = auth
        self.crud = AIAgentCRUD(auth)
        self._rules_cache: List[Dict[str, Any]] = []
        self._cache_time: datetime = datetime.now()
    
    async def _load_rules(self, force_reload: bool = False) -> List[Dict[str, Any]]:
        """
        加载规则（带缓存）
        
        Args:
            force_reload: 是否强制重新加载
            
        Returns:
            规则列表
        """
        # 缓存5分钟
        if not force_reload and self._rules_cache and \
           (datetime.now() - self._cache_time).seconds < 300:
            return self._rules_cache
        
        # 从数据库加载启用的规则
        rules = await self.crud.get_enabled_rules()
        
        # 按优先级排序（优先级越高越先检查）
        rules.sort(key=lambda r: r.priority, reverse=True)
        
        self._rules_cache = [
            {
                "id": rule.id,
                "name": rule.rule_name,
                "type": rule.rule_type,
                "config": rule.rule_config,
                "priority": rule.priority
            }
            for rule in rules
        ]
        self._cache_time = datetime.now()
        
        return self._rules_cache
    
    async def check_operation(
        self,
        operation_type: str,
        params: Dict[str, Any],
        user: UserModel
    ) -> Tuple[bool, str]:
        """
        检查操作是否需要确认
        
        Args:
            operation_type: 操作类型（如 delete_servers, execute_task）
            params: 操作参数
            user: 执行用户
            
        Returns:
            (need_confirm, reason) - 是否需要确认，原因说明
        """
        rules = await self._load_rules()
        
        for rule in rules:
            need_confirm, reason = await self._check_single_rule(
                rule, operation_type, params, user
            )
            if need_confirm:
                return True, reason
        
        return False, ""
    
    async def _check_single_rule(
        self,
        rule: Dict[str, Any],
        operation_type: str,
        params: Dict[str, Any],
        user: UserModel
    ) -> Tuple[bool, str]:
        """
        检查单个规则
        
        Args:
            rule: 规则配置
            operation_type: 操作类型
            params: 操作参数
            user: 执行用户
            
        Returns:
            (need_confirm, reason)
        """
        rule_type = rule["type"]
        config = rule["config"]
        
        if rule_type == RuleType.PERMISSION:
            return await self._check_permission_rule(config, operation_type, params, user)
        
        elif rule_type == RuleType.ENVIRONMENT:
            return await self._check_environment_rule(config, operation_type, params)
        
        elif rule_type == RuleType.BATCH:
            return await self._check_batch_rule(config, operation_type, params)
        
        elif rule_type == RuleType.TIME:
            return await self._check_time_rule(config, operation_type, params)
        
        elif rule_type == RuleType.DEPENDENCY:
            return await self._check_dependency_rule(config, operation_type, params)
        
        return False, ""
    
    async def _check_permission_rule(
        self,
        config: Dict[str, Any],
        operation_type: str,
        params: Dict[str, Any],
        user: UserModel
    ) -> Tuple[bool, str]:
        """
        检查权限规则
        
        配置示例：
        {
            "allowed_operations": ["list_servers", "get_server"],
            "denied_operations": ["delete_servers"]
        }
        """
        # 检查是否在拒绝列表中
        denied_ops = config.get("denied_operations", [])
        if operation_type in denied_ops:
            return True, f"操作 {operation_type} 需要特殊权限，请管理员确认"
        
        # 检查是否在允许列表中（如果配置了允许列表）
        allowed_ops = config.get("allowed_operations")
        if allowed_ops and operation_type not in allowed_ops:
            return True, f"操作 {operation_type} 不在允许范围内，需要确认"
        
        return False, ""
    
    async def _check_environment_rule(
        self,
        config: Dict[str, Any],
        operation_type: str,
        params: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        检查环境规则
        
        配置示例：
        {
            "operations": ["delete", "restart", "deploy"],
            "environments": ["production", "prod"],
            "need_confirm": true
        }
        """
        # 检查操作类型
        operations = config.get("operations", [])
        if operations:
            # 模糊匹配操作类型
            matched = any(op in operation_type.lower() for op in operations)
            if matched and config.get("need_confirm"):
                return True, f"敏感操作（{operation_type}）需要确认"
        
        # 检查环境
        environments = config.get("environments", [])
        if environments:
            # 从参数中提取环境信息
            env = params.get("environment") or params.get("project", "").lower()
            if any(e.lower() in env for e in environments):
                if config.get("need_confirm"):
                    return True, f"生产环境操作需要确认（环境：{env}）"
        
        return False, ""
    
    async def _check_batch_rule(
        self,
        config: Dict[str, Any],
        operation_type: str,
        params: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        检查批量操作规则
        
        配置示例：
        {
            "max_count": 10,
            "need_confirm_threshold": 5
        }
        """
        # 检查批量操作数量
        ids = params.get("ids", [])
        operator_metas = params.get("operator_metas", [])
        
        count = len(ids) if ids else len(operator_metas)
        
        if count == 0:
            return False, ""
        
        # 检查是否超过最大数量
        max_count = config.get("max_count")
        if max_count and count > max_count:
            return True, f"批量操作数量（{count}）超过限制（{max_count}），需要确认"
        
        # 检查是否超过确认阈值
        threshold = config.get("need_confirm_threshold")
        if threshold and count >= threshold:
            return True, f"批量操作涉及 {count} 个资源，需要确认"
        
        return False, ""
    
    async def _check_time_rule(
        self,
        config: Dict[str, Any],
        operation_type: str,
        params: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        检查时间窗口规则
        
        配置示例：
        {
            "allowed_time_ranges": [
                {"start": "09:00", "end": "18:00"}
            ],
            "blocked_days": ["Saturday", "Sunday"]
        }
        """
        now = datetime.now()
        
        # 检查星期
        blocked_days = config.get("blocked_days", [])
        if blocked_days:
            current_day = now.strftime("%A")  # 如 "Monday"
            if current_day in blocked_days:
                return True, f"当前时间（{current_day}）不允许执行该操作"
        
        # 检查时间范围
        allowed_ranges = config.get("allowed_time_ranges", [])
        if allowed_ranges:
            current_time = now.time()
            in_range = False
            
            for time_range in allowed_ranges:
                start = datetime.strptime(time_range["start"], "%H:%M").time()
                end = datetime.strptime(time_range["end"], "%H:%M").time()
                
                if start <= current_time <= end:
                    in_range = True
                    break
            
            if not in_range:
                return True, f"当前时间（{now.strftime('%H:%M')}）不在允许的操作时间窗口内"
        
        return False, ""
    
    async def _check_dependency_rule(
        self,
        config: Dict[str, Any],
        operation_type: str,
        params: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        检查依赖规则
        
        配置示例：
        {
            "operation": "restart",
            "pre_checks": ["health_check", "backup_check"]
        }
        """
        # 检查操作类型是否匹配
        if config.get("operation") and config["operation"] not in operation_type:
            return False, ""
        
        # 检查前置条件
        pre_checks = config.get("pre_checks", [])
        if pre_checks:
            return True, f"操作 {operation_type} 需要先执行前置检查：{', '.join(pre_checks)}"
        
        return False, ""
    
    async def validate_operation_params(
        self,
        operation_type: str,
        params: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        验证操作参数是否合法
        
        Args:
            operation_type: 操作类型
            params: 操作参数
            
        Returns:
            (is_valid, error_message)
        """
        # 通用参数验证
        if not params:
            return False, "操作参数不能为空"
        
        # 针对不同操作类型的特殊验证
        if "delete" in operation_type.lower():
            ids = params.get("ids", [])
            if not ids or len(ids) == 0:
                return False, "删除操作必须指定目标ID"
        
        elif "create" in operation_type.lower():
            # 检查必填字段
            required_fields = params.get("_required_fields", [])
            for field in required_fields:
                if field not in params:
                    return False, f"缺少必填字段: {field}"
        
        return True, ""

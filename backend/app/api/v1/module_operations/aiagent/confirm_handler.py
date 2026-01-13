# -*- coding: utf-8 -*-
"""
确认处理器
处理需要用户确认的敏感操作
使用 LangChain MCP Adapters 统一 MCP 客户端
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from app.api.v1.module_system.auth.schema import AuthSchema
from langchain_mcp_adapters.client import MultiServerMCPClient

from .crud import AIAgentCRUD
from .models import OperationStatus
from app.config.setting import settings

logger = logging.getLogger(__name__)


class ConfirmTimeout(Exception):
    """确认超时异常"""
    pass


class ConfirmHandler:
    """确认处理器"""
    
    def __init__(self, auth: AuthSchema):
        """
        初始化确认处理器
        
        Args:
            auth: 认证信息
        """
        self.auth = auth
        self.crud = AIAgentCRUD(auth)
        
        # MCP 适配器客户端（统一使用 MultiServerMCPClient）
        self.mcp_client: Optional[MultiServerMCPClient] = None
        
        # 待确认操作的Future字典 {operation_id: Future}
        self._pending_confirms: Dict[int, asyncio.Future] = {}
    
    async def _init_mcp_client(self):
        """初始化 MCP 客户端"""
        if self.mcp_client is None:
            # 配置 MCP 服务器
            mcp_servers_config = {
                "operations-tools": {
                    "url": settings.MCP_SERVER_URL,
                    "transport": "streamable_http"
                }
            }
            
            # 创建 MCP 适配器客户端
            self.mcp_client = MultiServerMCPClient(mcp_servers_config)
            logger.info("ConfirmHandler: 已初始化 MultiServerMCPClient")
    
    async def request_confirm(
        self,
        operation_id: int,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        请求用户确认操作
        
        Args:
            operation_id: 操作日志ID
            timeout: 超时时间（秒）
            
        Returns:
            确认结果
            
        Raises:
            ConfirmTimeout: 确认超时
        """
        # 创建Future用于等待确认
        future = asyncio.get_event_loop().create_future()
        self._pending_confirms[operation_id] = future
        
        try:
            # 等待确认（带超时）
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        
        except asyncio.TimeoutError:
            # 超时，自动拒绝
            logger.warning(f"操作确认超时: operation_id={operation_id}")
            
            await self.crud.update_operation_log(
                operation_id,
                status=OperationStatus.REJECTED,
                error_message="确认超时，操作已自动拒绝",
                confirmed_at=datetime.now()
            )
            
            raise ConfirmTimeout(f"操作确认超时（{timeout}秒）")
        
        finally:
            # 清理
            if operation_id in self._pending_confirms:
                del self._pending_confirms[operation_id]
    
    async def confirm_operation(
        self,
        operation_id: int,
        confirmed: bool,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        确认或拒绝操作
        
        Args:
            operation_id: 操作日志ID
            confirmed: 是否确认
            comment: 确认备注
            
        Returns:
            操作执行结果
        """
        # 获取操作日志
        operation_log = await self.crud.get_operation_log(operation_id)
        if not operation_log:
            raise ValueError(f"操作日志不存在: {operation_id}")
        
        # 检查状态
        if operation_log.status != OperationStatus.PENDING:
            raise ValueError(f"操作状态不正确: {operation_log.status}")
        
        # 更新确认状态
        if confirmed:
            # 用户确认，执行操作
            await self.crud.update_operation_log(
                operation_id,
                status=OperationStatus.CONFIRMED,
                confirmed_by=self.auth.user.id,
                confirmed_at=datetime.now()
            )
            
            # 执行 MCP 工具调用（使用 MultiServerMCPClient）
            result = await self._execute_confirmed_operation(operation_log)
            
            # 通知等待的Future
            if operation_id in self._pending_confirms:
                self._pending_confirms[operation_id].set_result(result)
            
            return result
        
        else:
            # 用户拒绝
            await self.crud.update_operation_log(
                operation_id,
                status=OperationStatus.REJECTED,
                confirmed_by=self.auth.user.id,
                confirmed_at=datetime.now(),
                error_message=f"用户拒绝执行。备注：{comment or '无'}"
            )
            
            result = {
                "success": False,
                "message": "操作已被拒绝",
                "comment": comment
            }
            
            # 通知等待的Future
            if operation_id in self._pending_confirms:
                self._pending_confirms[operation_id].set_result(result)
            
            return result
    
    async def _execute_confirmed_operation(
        self,
        operation_log
    ) -> Dict[str, Any]:
        """
        执行已确认的操作（使用 MultiServerMCPClient）
        
        Args:
            operation_log: 操作日志对象
            
        Returns:
            执行结果
        """
        try:
            # 初始化 MCP 客户端
            await self._init_mcp_client()
            
            # 获取工具
            tools = await self.mcp_client.get_tools()
            
            # 查找对应的工具
            tool = None
            for t in tools:
                if t.name == operation_log.tool_name:
                    tool = t
                    break
            
            if not tool:
                raise ValueError(f"工具不存在: {operation_log.tool_name}")
            
            # 调用工具
            result = await tool.ainvoke(operation_log.params)
            
            # 更新操作日志
            if isinstance(result, dict) and result.get("success"):
                await self.crud.update_operation_log(
                    operation_log.id,
                    status=OperationStatus.SUCCESS,
                    result=result,
                    executed_at=datetime.now()
                )
            else:
                await self.crud.update_operation_log(
                    operation_log.id,
                    status=OperationStatus.FAILED,
                    error_message=str(result) if not isinstance(result, dict) else result.get("error", "未知错误"),
                    executed_at=datetime.now()
                )
            
            return {
                "success": True,
                "result": result
            }
        
        except Exception as e:
            logger.error(f"执行确认操作失败: {str(e)}")
            
            await self.crud.update_operation_log(
                operation_log.id,
                status=OperationStatus.FAILED,
                error_message=str(e),
                executed_at=datetime.now()
            )
            
            return {
                "success": False,
                "error": str(e)
            }
    
    async def cancel_operation(self, operation_id: int) -> Dict[str, Any]:
        """
        取消待确认的操作
        
        Args:
            operation_id: 操作日志ID
            
        Returns:
            取消结果
        """
        # 更新状态为已取消
        await self.crud.update_operation_log(
            operation_id,
            status=OperationStatus.CANCELLED,
            confirmed_at=datetime.now()
        )
        
        # 通知等待的Future
        if operation_id in self._pending_confirms:
            self._pending_confirms[operation_id].set_result({
                "success": False,
                "message": "操作已取消"
            })
        
        return {"success": True, "message": "操作已取消"}
    
    async def get_pending_operations(
        self,
        session_id: Optional[int] = None
    ) -> list:
        """
        获取待确认的操作列表
        
        Args:
            session_id: 会话ID（可选）
            
        Returns:
            待确认操作列表
        """
        return await self.crud.get_pending_operations(session_id)
    
    async def close(self):
        """清理资源"""
        if self.mcp_client:
            try:
                await self.mcp_client.close()
                logger.info("ConfirmHandler: 已关闭 MultiServerMCPClient")
            except Exception as e:
                logger.error(f"关闭 MCP 客户端失败: {str(e)}")
            finally:
                self.mcp_client = None
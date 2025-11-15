# -*- coding: utf-8 -*-
"""
任务执行器
负责任务的实际执行逻辑和日志写入
"""

import asyncio
import random
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Any

import aiofiles

from app.config.setting import settings
from app.core.database import AsyncSessionLocal
from app.core.logger import logger
from app.api.v1.module_system.auth.schema import AuthSchema
from .crud import TaskCRUD


class TaskExecutor:
    """任务执行器，负责任务的实际执行逻辑和日志写入"""

    LOG_DIR = settings.BASE_DIR.joinpath("logs", "operations_task")
    LOG_CONFIG_KEY = "operations_task_log_keep_days"

    @classmethod
    def ensure_log_dir(cls) -> None:
        """确保日志目录存在"""
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def build_log_path(cls, task_type: str, node_ip: str) -> Path:
        """构建日志文件路径"""
        cls.ensure_log_dir()
        safe_ip = node_ip.replace(":", "-").replace(".", "-")
        filename = f"{task_type}_{safe_ip}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}.log"
        return cls.LOG_DIR.joinpath(filename)

    @classmethod
    async def write_log(cls, log_path: Path, message: str) -> None:
        """
        写入日志到文件
        
        Args:
            log_path: 日志文件路径
            message: 日志消息
        """
        cls.ensure_log_dir()
        async with aiofiles.open(log_path, "a", encoding="utf-8") as log_file:
            await log_file.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")

    @classmethod
    async def execute_batch_task(
        cls,
        *,
        base_auth: AuthSchema,
        task_id: int,
        log_path: Path,
        nodes: List[Any],
        task_type: str,
        operator_metas: Optional[List[dict]] = None,
    ) -> None:
        """
        执行批次任务（多个节点）
        
        Args:
            base_auth: 基础认证信息
            task_id: 任务ID
            log_path: 日志文件路径
            nodes: 节点列表
            task_type: 任务类型 (deploy/restart)
            operator_metas: 操作元数据（可选），格式: [{"service_id": 1, "nodes": [node_obj, ...]}, ...]
        """
        # 获取任务步骤
        if task_type == "deploy":
            steps = [
                "检查节点状态",
                "备份当前版本",
                "下载新版本文件",
                "停止旧服务",
                "部署新版本",
                "启动新服务",
                "验证服务状态",
            ]
        else:  # restart
            steps = [
                "检查节点状态",
                "停止服务",
                "清理临时文件",
                "启动服务",
                "验证服务状态",
            ]
        
        total_nodes = len(nodes)
        success_count = 0
        failed_count = 0
        failure_rate = 0.15 if task_type == "deploy" else 0.10
        
        async with AsyncSessionLocal() as new_db:
            new_auth = AuthSchema(db=new_db, user=base_auth.user, check_data_scope=False)
            new_task_crud = TaskCRUD(new_auth)
            
            try:
                await cls.write_log(log_path, f"批次任务创建成功，共 {total_nodes} 个节点")
                
                # 如果提供了 operator_metas，按服务分组显示
                if operator_metas:
                    for idx, meta in enumerate(operator_metas, 1):
                        service_id = meta.get("service_id")
                        service_nodes = meta.get("nodes", [])
                        # 获取服务名称（从第一个节点获取）
                        service_name = None
                        if service_nodes:
                            first_node = service_nodes[0]
                            if hasattr(first_node, 'services'):
                                for svc in (first_node.services or []):
                                    if svc.id == service_id:
                                        service_name = svc.name
                                        break
                            if not service_name and hasattr(first_node, 'service'):
                                if first_node.service and first_node.service.id == service_id:
                                    service_name = first_node.service.name
                        
                        service_display = f"{service_name}(ID:{service_id})" if service_name else f"服务ID:{service_id}"
                        await cls.write_log(log_path, f"{idx}. {service_display} - {len(service_nodes)} 个节点")
                        for node in service_nodes:
                            await cls.write_log(log_path, f"   - {node.ip}:{node.port or 22}")
                else:
                    # 如果没有 operator_metas，直接列出所有节点
                    for idx, node in enumerate(nodes, 1):
                        await cls.write_log(log_path, f"{idx}. {node.ip}:{node.port or 22}")
                
                await cls.write_log(log_path, f"\n开始执行批次{'部署' if task_type == 'deploy' else '重启'}任务")
                await cls.write_log(log_path, f"共 {total_nodes} 个节点需要处理")
                await cls.write_log(log_path, "="*60)
                
                # 逐个处理节点
                for idx, node in enumerate(nodes, 1):
                    await cls.write_log(log_path, f"\n{node.ip}:{node.port or 22}")
                    await cls.write_log(log_path, "-"*60)
                    
                    node_success = True
                    
                    # 执行各个步骤
                    for step_idx, step in enumerate(steps, 1):
                        # 计算总进度
                        progress = int((idx - 1) / total_nodes * 100 + (step_idx / len(steps)) * (100 / total_nodes))
                        await new_task_crud.update(
                            id=task_id,
                            data={"progress": min(progress, 99)}
                        )
                        await new_db.commit()
                        
                        await cls.write_log(log_path, f"[{step_idx}/{len(steps)}] {step}...")
                        await asyncio.sleep(random.uniform(0.3, 0.8))
                        
                        # 模拟随机失败
                        if random.random() < failure_rate:
                            node_success = False
                            error_msg = f"执行 {step} 失败"
                            await cls.write_log(log_path, f"[ERROR] {error_msg}")
                            failed_count += 1
                            break
                        
                        await cls.write_log(log_path, f"[✓] {step} 完成")
                    
                    if node_success:
                        success_count += 1
                        await cls.write_log(log_path, f"[SUCCESS] 节点 {node.ip} 处理成功")
                    else:
                        await cls.write_log(log_path, f"[FAILED] 节点 {node.ip} 处理失败")
                
                # 任务完成，更新最终状态
                await cls.write_log(log_path, "="*60)
                await cls.write_log(log_path, f"\n批次任务完成")
                await cls.write_log(log_path, f"成功: {success_count}/{total_nodes}")
                await cls.write_log(log_path, f"失败: {failed_count}/{total_nodes}")
                
                # 根据结果确定任务状态
                if failed_count == 0:
                    final_status = "success"
                    await cls.write_log(log_path, "任务执行状态: 全部成功")
                elif success_count == 0:
                    final_status = "failed"
                    await cls.write_log(log_path, "任务执行状态: 全部失败")
                else:
                    final_status = "partial_success"
                    await cls.write_log(log_path, "任务执行状态: 部分成功")
                
                # 更新任务最终状态
                await new_task_crud.update(
                    id=task_id,
                    data={
                        "task_status": final_status,
                        "progress": 100,
                        "error_message": f"成功{success_count}个，失败{failed_count}个" if failed_count > 0 else None,
                    }
                )
                await new_db.commit()
                
            except asyncio.CancelledError:
                await new_db.rollback()
                await cls.write_log(log_path, "批次任务被取消")
                await new_task_crud.update(
                    id=task_id,
                    data={
                        "task_status": "failed",
                        "error_message": "任务被取消",
                        "progress": 100,
                    },
                )
                await new_db.commit()
                raise
            except Exception as exc:
                await new_db.rollback()
                await cls.write_log(log_path, f"批次任务执行异常: {exc}")
                await new_task_crud.update(
                    id=task_id,
                    data={
                        "task_status": "failed",
                        "error_message": str(exc),
                        "progress": 100,
                    },
                )
                await new_db.commit()
                logger.error(f"批次任务执行失败: {exc}")


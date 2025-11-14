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
from typing import Optional

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
    async def execute_task(
        cls,
        *,
        base_auth: AuthSchema,
        task_id: int,
        log_path: Path,
        task_type: str,
    ) -> None:
        """
        执行任务
        
        Args:
            base_auth: 基础认证信息
            task_id: 任务ID
            log_path: 日志文件路径
            task_type: 任务类型 (deploy/restart)
        """
        # 模拟任务执行步骤
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

        failure_rate = 0.2 if task_type == "deploy" else 0.15

        async with AsyncSessionLocal() as new_db:
            new_auth = AuthSchema(db=new_db, user=base_auth.user, check_data_scope=False)
            new_task_crud = TaskCRUD(new_auth)

            try:
                await cls.write_log(log_path, f"开始执行{'部署' if task_type == 'deploy' else '重启'}任务")
                total_steps = len(steps)
                for index, step in enumerate(steps, start=1):
                    await asyncio.sleep(random.uniform(0.6, 1.2))
                    await cls.write_log(log_path, step)
                    progress = min(int(index / (total_steps + 1) * 100), 95)
                    await new_task_crud.update(id=task_id, data={"progress": progress})
                    await new_db.commit()

                await asyncio.sleep(random.uniform(0.8, 1.5))
                success = random.random() > failure_rate
                if success:
                    await cls.write_log(log_path, "任务执行成功")
                    update_data = {"task_status": "success", "progress": 100, "error_message": None}
                else:
                    await cls.write_log(log_path, "任务执行失败")
                    update_data = {
                        "task_status": "failed",
                        "progress": 100,
                        "error_message": "模拟执行失败，请检查日志",
                    }
                await new_task_crud.update(id=task_id, data=update_data)
                await new_db.commit()
            except asyncio.CancelledError:
                await new_db.rollback()
                await cls.write_log(log_path, "任务被取消")
                await new_task_crud.update(
                    id=task_id,
                    data={"task_status": "failed", "error_message": "任务被取消", "progress": 100},
                )
                await new_db.commit()
                raise
            except Exception as exc:
                await new_db.rollback()
                await cls.write_log(log_path, f"任务执行异常: {exc}")
                await new_task_crud.update(
                    id=task_id,
                    data={"task_status": "failed", "error_message": str(exc), "progress": 100},
                )
                await new_db.commit()
                logger.error(f"任务执行失败: {exc}")


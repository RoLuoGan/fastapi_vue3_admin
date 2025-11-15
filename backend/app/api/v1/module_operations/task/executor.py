# -*- coding: utf-8 -*-
"""
任务执行器
负责任务的实际执行逻辑和日志写入
"""

import asyncio
import random
import uuid
import subprocess
import sys
import os
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Any, Dict

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
    def _build_operator_metas_for_script(cls, operator_metas: List[dict]) -> List[Dict]:
        """
        构建传递给脚本的 operator_metas 格式
        
        Args:
            operator_metas: 操作元数据列表，格式: [{"service_id": 1, "nodes": [node_obj, ...]}, ...]
        
        Returns:
            List[Dict]: 格式化的操作元数据列表
        """
        result = []
        for meta in operator_metas:
            service_id = meta.get("service_id")
            service_nodes = meta.get("nodes", [])
            
            # 获取服务名称
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
            
            # 构建节点列表
            node_list = []
            for node in service_nodes:
                node_dict = {
                    "id": node.id,
                    "ip": node.ip,
                    "port": node.port or 22,
                    "service_id": service_id,
                }
                node_list.append(node_dict)
            
            result.append({
                "service_id": service_id,
                "service_name": service_name,
                "nodes": node_list,
            })
        
        return result

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
        执行批次任务（多个节点）- 使用 subprocess 执行外部脚本
        
        Args:
            base_auth: 基础认证信息
            task_id: 任务ID
            log_path: 日志文件路径
            nodes: 节点列表
            task_type: 任务类型 (deploy/restart)
            operator_metas: 操作元数据（可选），格式: [{"service_id": 1, "nodes": [node_obj, ...]}, ...]
        """
        async with AsyncSessionLocal() as new_db:
            new_auth = AuthSchema(db=new_db, user=base_auth.user, check_data_scope=False)
            new_task_crud = TaskCRUD(new_auth)
            
            try:
                # 构建脚本参数
                script_path = settings.BASE_DIR.joinpath("app", "scripts", "execute_batch_task.py")
                if not script_path.exists():
                    raise FileNotFoundError(f"脚本文件不存在: {script_path}")
                
                # 构建 operator_metas（如果提供）
                script_operator_metas = None
                if operator_metas:
                    script_operator_metas = cls._build_operator_metas_for_script(operator_metas)
                else:
                    # 如果没有提供 operator_metas，从 nodes 构建
                    # 按 service_id 分组
                    nodes_by_service = {}
                    for node in nodes:
                        service_id = node.service_id or 0
                        if service_id not in nodes_by_service:
                            nodes_by_service[service_id] = []
                        nodes_by_service[service_id].append(node)
                    
                    script_operator_metas = []
                    for service_id, service_nodes in nodes_by_service.items():
                        service_name = None
                        if service_nodes:
                            first_node = service_nodes[0]
                            if hasattr(first_node, 'service') and first_node.service:
                                service_name = first_node.service.name
                        
                        node_list = []
                        for node in service_nodes:
                            node_list.append({
                                "id": node.id,
                                "ip": node.ip,
                                "port": node.port or 22,
                                "service_id": service_id,
                            })
                        
                        script_operator_metas.append({
                            "service_id": service_id,
                            "service_name": service_name,
                            "nodes": node_list,
                        })
                
                # 构建参数字典
                params_dict = {
                    "log_path": str(log_path),
                    "task_id": task_id,
                    "task_type": task_type,
                    "operator_metas": script_operator_metas,
                }
                params_json = json.dumps(params_dict, ensure_ascii=False)
                
                # 构建命令（使用环境变量传递参数，避免命令行参数中的 JSON 解析问题）
                python_exe = sys.executable
                cmd = [
                    python_exe,
                    str(script_path),
                ]
                
                # 设置环境变量（主要方式，避免 Windows 命令行参数解析问题）
                env = os.environ.copy()
                env["TASK_LOG_PATH"] = str(log_path)
                env["TASK_ID"] = str(task_id)
                env["TASK_TYPE"] = task_type
                env["OPERATOR_METAS"] = json.dumps(script_operator_metas, ensure_ascii=False)
                env["TASK_PARAMS_JSON"] = params_json
                
                logger.info(f"执行命令: {' '.join(cmd)}")
                logger.info(f"脚本路径: {script_path}")
                logger.info(f"Python可执行文件: {python_exe}")
                logger.info(f"工作目录: {settings.BASE_DIR}")
                
                # 启动子进程（Windows 兼容）
                if sys.platform == 'win32':
                    # Windows 使用 shell=True 和字符串命令
                    cmd_str = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in cmd)
                    process = await asyncio.to_thread(
                        subprocess.Popen,
                        cmd_str,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        env=env,
                        cwd=str(settings.BASE_DIR),
                        shell=True,
                        encoding='utf-8',
                        errors='replace',
                    )
                else:
                    # Linux/Mac 使用列表命令
                    process = await asyncio.to_thread(
                        subprocess.Popen,
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        env=env,
                        cwd=str(settings.BASE_DIR),
                        encoding='utf-8',
                        errors='replace',
                    )
                
                await cls.write_log(log_path, f"脚本进程已启动，PID: {process.pid}")
                
                # 进度解析正则表达式
                progress_pattern = re.compile(r'PROGRESS:\s*(\d+)\s*-\s*(.+)')
                
                # 实时读取输出
                last_progress = 0
                
                async def read_output(stream, is_stderr=False):
                    """异步读取输出流"""
                    nonlocal last_progress
                    while True:
                        line = await asyncio.to_thread(stream.readline)
                        if not line:
                            break
                        
                        line = line.rstrip('\n\r')
                        if not line:
                            continue
                        
                        # 直接写入日志文件（脚本输出已包含时间戳，不再重复添加）
                        cls.ensure_log_dir()
                        async with aiofiles.open(log_path, "a", encoding="utf-8", errors='replace') as log_file:
                            await log_file.write(line + "\n")
                        
                        # 解析进度
                        match = progress_pattern.search(line)
                        if match:
                            progress = int(match.group(1))
                            message = match.group(2)
                            if progress != last_progress:
                                last_progress = progress
                                await new_task_crud.update(
                                    id=task_id,
                                    data={"progress": min(progress, 99)}
                                )
                                await new_db.commit()
                                logger.debug(f"任务进度更新: {progress}% - {message}")
                
                # 同时读取 stdout 和 stderr
                await asyncio.gather(
                    read_output(process.stdout, is_stderr=False),
                    read_output(process.stderr, is_stderr=True),
                )
                
                # 等待进程结束
                return_code = await asyncio.to_thread(process.wait)
                
                # 根据返回码确定任务状态
                if return_code == 0:
                    final_status = "success"
                    error_message = None
                else:
                    # 检查是否有部分成功的情况（需要脚本输出特定格式）
                    final_status = "failed"
                    error_message = f"脚本执行失败，返回码: {return_code}"
                
                # 更新任务最终状态
                await new_task_crud.update(
                    id=task_id,
                    data={
                        "task_status": final_status,
                        "progress": 100,
                        "error_message": error_message,
                    }
                )
                await new_db.commit()
                
                await cls.write_log(log_path, f"脚本执行完成，返回码: {return_code}, 状态: {final_status}")
                logger.info(f"批次任务执行完成: task_id={task_id}, return_code={return_code}, status={final_status}")
                
            except asyncio.CancelledError:
                await new_db.rollback()
                if 'process' in locals():
                    def terminate_process():
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                    await asyncio.to_thread(terminate_process)
                
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
                if 'process' in locals():
                    def terminate_process():
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                    await asyncio.to_thread(terminate_process)
                
                error_msg = f"批次任务执行异常: {exc}"
                await cls.write_log(log_path, f"[ERROR] {error_msg}")
                import traceback
                error_traceback = traceback.format_exc()
                await cls.write_log(log_path, f"[ERROR] 异常堆栈:\n{error_traceback}")
                
                await new_task_crud.update(
                    id=task_id,
                    data={
                        "task_status": "failed",
                        "error_message": str(exc),
                        "progress": 100,
                    },
                )
                await new_db.commit()
                logger.error(f"批次任务执行失败: {exc}\n{error_traceback}")


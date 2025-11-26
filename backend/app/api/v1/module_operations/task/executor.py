# -*- coding: utf-8 -*-
"""
任务执行器
负责任务的实际执行逻辑和日志写入
"""

import asyncio
import time
import uuid
import sys
from importlib import import_module
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Any, Dict, Tuple

import aiofiles
from redis.asyncio.client import Redis

from app.config.setting import settings
from app.core.database import AsyncSessionLocal
from app.core.logger import logger
from app.core.exceptions import CustomException
from app.api.v1.module_system.auth.schema import AuthSchema
from .crud import TaskCRUD
from .log_crud import TaskLogCRUD
from .redis_stream import TaskLogRedisStream


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
        写入日志到文件（保留兼容性）
        
        Args:
            log_path: 日志文件路径
            message: 日志消息
        """
        cls.ensure_log_dir()
        async with aiofiles.open(log_path, "a", encoding="utf-8", errors="replace") as log_file:
            await log_file.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    
    @classmethod
    async def write_log_to_storage(
        cls,
        task_id: int,
        seq: int,
        content: str,
        timestamp: Optional[int] = None,
        redis: Optional[Redis] = None,
        log_crud: Optional[TaskLogCRUD] = None,
    ) -> None:
        """
        将日志写入 MySQL 和 Redis Stream
        
        Args:
            task_id: 任务ID
            seq: 全局序号
            content: 日志内容
            timestamp: Unix时间戳（秒）
            redis: Redis 连接（可选）
            log_crud: TaskLogCRUD 实例（可选）
        """
        if timestamp is None:
            timestamp = int(datetime.now().timestamp())
        
        logger.debug(f"[Executor] write_log_to_storage 开始 task_id={task_id}, seq={seq}, content_length={len(content)}, line_count={content.count(chr(10)) + 1}, timestamp={timestamp}")
        
        # 写入 MySQL（如果提供了 log_crud）
        if log_crud:
            try:
                # 支持分段归档：每 1000 行一条记录
                # 这里 content 可能包含多行，需要计算行数
                line_count = content.count('\n') + (1 if content else 0)
                
                logger.debug(f"[Executor] 写入 MySQL task_id={task_id}, seq={seq}, line_count={line_count}")
                await log_crud.add_log_crud(
                    task_id=task_id,
                    seq=seq,
                    content=content,
                    line_count=line_count,
                    timestamp=timestamp,
                )
                logger.debug(f"[Executor] MySQL 写入完成 task_id={task_id}, seq={seq}")
            except Exception as e:
                logger.error(f"[Executor] 写入 MySQL 日志失败 task_id={task_id}, seq={seq}: {e}", exc_info=True)
        else:
            logger.debug(f"[Executor] log_crud 未提供，跳过 MySQL 写入 task_id={task_id}, seq={seq}")
        
        # 写入 Redis Stream（如果提供了 redis）
        if redis:
            try:
                logger.debug(f"[Executor] 写入 Redis Stream task_id={task_id}, seq={seq}, content_length={len(content)}")
                entry_id = await TaskLogRedisStream.add_log(
                    redis=redis,
                    task_id=task_id,
                    seq=seq,
                    content=content,
                    timestamp=timestamp,
                )
                logger.debug(f"[Executor] Redis Stream 写入完成 task_id={task_id}, seq={seq}, entry_id={entry_id}")
            except Exception as e:
                logger.error(f"[Executor] 写入 Redis Stream 日志失败 task_id={task_id}, seq={seq}: {e}", exc_info=True)
        else:
            logger.warning(f"[Executor] Redis 未提供，跳过 Redis Stream 写入 task_id={task_id}, seq={seq}")

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
        task_type: str,
        operator_type: str,
        operator_metas: Optional[List[dict]] = None,
        redis: Optional[Redis] = None,
    ) -> None:
        """
        执行批次任务（多个节点）- 通过 import_module 调用脚本逻辑
        
        Args:
            base_auth: 基础认证信息
            task_id: 任务ID
            log_path: 日志文件路径
            task_type: 任务类型 (node_operator, server_operator 等)
            operator_type: 操作类型 (deploy, restart, init 等)
            operator_metas: 操作元数据（任意结构，直接透传）
            redis: 复用的 Redis 连接（可选，通过依赖注入获取）
        """
        async with AsyncSessionLocal() as new_db:
            new_auth = AuthSchema(db=new_db, user=base_auth.user, check_data_scope=False)
            new_task_crud = TaskCRUD(new_auth)
            new_log_crud = TaskLogCRUD(new_auth)
            
            if settings.REDIS_ENABLE and redis is None:
                logger.warning("[Executor] 未提供 Redis 连接，将跳过 Redis Stream 写入")
            
            # 初始化 seq 计数器（从 MySQL 获取最大 seq）
            current_seq = await new_log_crud.get_max_seq_crud(task_id=task_id)
            seq_lock = asyncio.Lock()
            
            # 日志缓冲区（用于分段归档）
            log_buffer: List[str] = []
            BUFFER_SIZE = 1000  # 每 1000 行一条记录
            BUFFER_FLUSH_INTERVAL = 1.0  # 每 1 秒强制刷新一次缓冲区（确保实时性）
            last_flush_time = time.time()
            
            async def flush_log_buffer():
                """刷新日志缓冲区到存储（使用独立的数据库会话）"""
                if not log_buffer:
                    return
                
                async with seq_lock:
                    nonlocal current_seq
                    current_seq += 1
                    seq = current_seq
                
                content = '\n'.join(log_buffer)
                buffer_size = len(log_buffer)
                logger.debug(f"[Executor] 刷新日志缓冲区 task_id={task_id}, seq={seq}, buffer_size={buffer_size}, content_length={len(content)}")
                
                # 使用独立的数据库会话，避免会话关闭问题
                async with AsyncSessionLocal() as log_db:
                    log_auth = AuthSchema(db=log_db, user=base_auth.user, check_data_scope=False)
                    log_crud = TaskLogCRUD(log_auth)
                    try:
                        logger.debug(f"[Executor] 开始写入日志到存储 task_id={task_id}, seq={seq}")
                        await cls.write_log_to_storage(
                            task_id=task_id,
                            seq=seq,
                            content=content,
                            redis=redis,
                            log_crud=log_crud,
                        )
                        await log_db.commit()
                        logger.debug(f"[Executor] 日志写入完成 task_id={task_id}, seq={seq}, 已写入 MySQL 和 Redis Stream")
                        log_buffer.clear()
                    except Exception as e:
                        await log_db.rollback()
                        logger.error(f"[Executor] 刷新日志缓冲区失败 task_id={task_id}, seq={seq}: {e}", exc_info=True)
                        # 即使失败也清空缓冲区，避免重复写入
                        log_buffer.clear()
            
            try:
                # 直接使用 operator_metas，不做加工（只转换为可序列化格式）
                script_operator_metas = operator_metas or []
                
                # 根据 task_type 确定脚本模块名
                # 脚本命名规则: task_{task_type}.py
                script_module_name = f"task_{task_type}"
                logger.info(f"导入批次任务脚本模块: {script_module_name}")
                
                # 通过 import_module 导入脚本模块
                # 添加当前工作scripts目录
                sys.path.append(str(Path.cwd().joinpath("scripts")))
                
                def load_module_sync():
                    try:
                        return import_module(script_module_name)
                    except ModuleNotFoundError:
                        raise CustomException(f"未找到任务类型脚本: {script_module_name}")

                # 将模块导入放入线程池执行，防止 import 阻塞事件循环
                module = await asyncio.to_thread(load_module_sync)
                
                loop = asyncio.get_running_loop()
                log_queue: asyncio.Queue[str] = asyncio.Queue()
                progress_queue: asyncio.Queue[Optional[Tuple[int, str]]] = asyncio.Queue()
                
                def log_handler(message: str):
                    loop.call_soon_threadsafe(log_queue.put_nowait, message)
                
                def progress_handler(progress: int, message: str):
                    loop.call_soon_threadsafe(progress_queue.put_nowait, (progress, message))
                
                async def log_consumer():
                    """日志消费者：同时写入文件、MySQL 和 Redis Stream"""
                    nonlocal last_flush_time
                    line_count = 0
                    while True:
                        try:
                            # 计算超时时间
                            current_time = time.time()
                            time_since_last_flush = current_time - last_flush_time
                            timeout = max(0.1, BUFFER_FLUSH_INTERVAL - time_since_last_flush)
                            
                            # 如果缓冲区有数据，设置超时时间；否则一直等待
                            if log_buffer:
                                line = await asyncio.wait_for(log_queue.get(), timeout=timeout)
                            else:
                                line = await log_queue.get()
                        except asyncio.TimeoutError:
                            # 超时，刷新缓冲区
                            if log_buffer:
                                await flush_log_buffer()
                                last_flush_time = time.time()
                            continue

                        if line is None:
                            # 刷新剩余的缓冲区
                            logger.debug(f"[Executor] 日志队列结束，刷新剩余缓冲区 task_id={task_id}, total_lines={line_count}")
                            await flush_log_buffer()
                            break
                        
                        line_count += 1
                        logger.debug(f"[Executor] 收到日志行 #{line_count} task_id={task_id}, line_preview={line[:50]}")
                        
                        # 写入文件（保留兼容性）
                        cls.ensure_log_dir()
                        async with aiofiles.open(log_path, "a", encoding="utf-8", errors="replace") as log_file:
                            await log_file.write(line + "\n")
                        
                        # 添加到缓冲区
                        log_buffer.append(line)
                        
                        # 检查是否需要立即刷新（基于缓冲区大小）
                        if len(log_buffer) >= BUFFER_SIZE:
                            logger.debug(f"[Executor] 缓冲区达到阈值，触发刷新 task_id={task_id}, buffer_size={len(log_buffer)}")
                            await flush_log_buffer()
                            last_flush_time = time.time()
                
                async def progress_consumer():
                    """进度消费者：使用独立的数据库会话"""
                    last_progress = 0
                    while True:
                        item = await progress_queue.get()
                        if item is None:
                            break
                        progress, message = item
                        if progress != last_progress:
                            last_progress = progress
                            # 使用独立的数据库会话，避免会话关闭问题
                            async with AsyncSessionLocal() as progress_db:
                                progress_auth = AuthSchema(db=progress_db, user=base_auth.user, check_data_scope=False)
                                progress_task_crud = TaskCRUD(progress_auth)
                                try:
                                    await progress_task_crud.update(
                                        id=task_id,
                                        data={"progress": min(progress, 99)}
                                    )
                                    await progress_db.commit()
                                    logger.debug(f"任务进度更新: {progress}% - {message}")
                                except Exception as e:
                                    await progress_db.rollback()
                                    logger.error(f"更新任务进度失败: {e}")
                
                log_task = asyncio.create_task(log_consumer())
                progress_task = asyncio.create_task(progress_consumer())
                
                def run_module():
                    return module.execute_in_process(
                        log_path=log_path,
                        task_id=task_id,
                        task_type=operator_type,  # 传递 operator_type 给脚本
                        operator_metas=script_operator_metas,
                        log_handler=log_handler,
                        progress_handler=progress_handler,
                    )
                
                try:
                    return_code = await asyncio.to_thread(run_module)
                finally:
                    await log_queue.put(None)
                    await progress_queue.put(None)
                    await asyncio.gather(log_task, progress_task)
                
                # 根据返回码确定任务状态
                if return_code == 0:
                    final_status = "success"
                    error_message = None
                else:
                    # 检查是否有部分成功的情况（需要脚本输出特定格式）
                    final_status = "failed"
                    error_message = f"脚本执行失败，返回码: {return_code}"
                
                # 刷新剩余的日志缓冲区
                await flush_log_buffer()
                
                # 更新任务最终状态（使用独立的数据库会话）
                async with AsyncSessionLocal() as final_db:
                    final_auth = AuthSchema(db=final_db, user=base_auth.user, check_data_scope=False)
                    final_task_crud = TaskCRUD(final_auth)
                    try:
                        await final_task_crud.update(
                            id=task_id,
                            data={
                                "task_status": final_status,
                                "progress": 100,
                                "error_message": error_message,
                            }
                        )
                        await final_db.commit()
                    except Exception as e:
                        await final_db.rollback()
                        logger.error(f"更新任务最终状态失败: {e}")
                
                await cls.write_log(log_path, f"脚本执行完成，返回码: {return_code}, 状态: {final_status}")
                
                # 任务完成后，可以选择清理 Redis Stream（可选）
                # if redis:
                #     await TaskLogRedisStream.delete_stream(redis, task_id)
                
                logger.info(f"批次任务执行完成: task_id={task_id}, return_code={return_code}, status={final_status}")
                
            except asyncio.CancelledError:
                await cls.write_log(log_path, "批次任务被取消")
                await flush_log_buffer()  # 刷新缓冲区
                
                # 使用独立的数据库会话更新任务状态
                async with AsyncSessionLocal() as cancel_db:
                    cancel_auth = AuthSchema(db=cancel_db, user=base_auth.user, check_data_scope=False)
                    cancel_task_crud = TaskCRUD(cancel_auth)
                    try:
                        await cancel_task_crud.update(
                            id=task_id,
                            data={
                                "task_status": "failed",
                                "error_message": "任务被取消",
                                "progress": 100,
                            },
                        )
                        await cancel_db.commit()
                    except Exception as e:
                        await cancel_db.rollback()
                        logger.error(f"更新任务取消状态失败: {e}")
                raise
            except Exception as exc:
                error_msg = f"批次任务执行异常: {exc}"
                await cls.write_log(log_path, f"[ERROR] {error_msg}")
                import traceback
                error_traceback = traceback.format_exc()
                await cls.write_log(log_path, f"[ERROR] 异常堆栈:\n{error_traceback}")
                
                await flush_log_buffer()  # 刷新缓冲区
                
                # 使用独立的数据库会话更新任务状态
                async with AsyncSessionLocal() as error_db:
                    error_auth = AuthSchema(db=error_db, user=base_auth.user, check_data_scope=False)
                    error_task_crud = TaskCRUD(error_auth)
                    try:
                        await error_task_crud.update(
                            id=task_id,
                            data={
                                "task_status": "failed",
                                "error_message": str(exc),
                                "progress": 100,
                            },
                        )
                        await error_db.commit()
                    except Exception as e:
                        await error_db.rollback()
                        logger.error(f"更新任务错误状态失败: {e}")
                
                logger.error(f"批次任务执行失败: {exc}\n{error_traceback}")
            finally:
                # 注意: 这里不关闭 Redis 连接，因为 Redis 连接是复用的（如果是由依赖注入传入的）
                # 如果在这里关闭了，会影响其他请求
                pass
                # if redis:
                #     try:
                #         await redis.close()
                #     except Exception as e:
                #         logger.warning(f"关闭 Redis 连接失败: {e}")


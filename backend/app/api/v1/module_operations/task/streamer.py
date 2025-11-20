# -*- coding: utf-8 -*-
"""
任务日志流处理器
负责SSE日志流的生成和推送
按照规范文档实现，结构简单清晰
"""

import asyncio
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Optional, Dict, Any, Tuple

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


class TaskLogStreamer:
    """任务日志流处理器，负责SSE日志流的生成和推送"""

    @staticmethod
    def format_sse_event(
        event_type: str,
        payload: Dict[str, Any],
        *,
        event_id: Optional[str] = None,
        timestamp: Optional[int] = None,
        request_id: Optional[str] = None,
        retry: int = 3000,
    ) -> str:
        """
        标准化SSE事件格式生成函数
        统一处理所有SSE事件格式
        
        Args:
            event_type: 事件类型 (task_log, task_status, task_info, task_error, task_end)
            payload: 事件负载数据
            event_id: 事件ID，格式为 task_{task_id}_{line_number}
            timestamp: Unix时间戳（秒），默认使用当前时间
            request_id: 请求ID（UUID），用于追踪请求
            retry: 重试间隔（毫秒），默认 3000
        
        Returns:
            SSE格式的字符串
        """
        if timestamp is None:
            timestamp = int(datetime.now().timestamp())
        
        if request_id is None:
            request_id = str(uuid.uuid4())
        
        # 构建标准化的数据格式
        data = {
            "type": event_type,
            "payload": payload,
            "timestamp": timestamp,
            "requestId": request_id,
        }
        
        lines = []
        
        # id: task_123_42
        if event_id is not None:
            lines.append(f"id: {event_id}")
        
        # event: task_log
        lines.append(f"event: {event_type}")
        
        # retry: 3000
        lines.append(f"retry: {retry}")
        
        # data: JSON格式的数据（支持多行）
        payload_str = json.dumps(data, ensure_ascii=False)
        for chunk in payload_str.splitlines() or [""]:
            lines.append(f"data: {chunk}")
        
        lines.append("")  # 结尾空行分隔事件（SSE规范要求两个换行符）
        return "\n".join(lines) + "\n"  # 确保每个事件后有两个换行符

    @staticmethod
    def parse_log_line(line: str) -> Tuple[str, str]:
        """解析日志行，提取时间戳和消息内容"""
        raw = line.rstrip("\n")
        default_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if raw.startswith("[") and "]" in raw:
            end_index = raw.find("]")
            timestamp_candidate = raw[1:end_index].strip()
            message = raw[end_index + 1 :].lstrip()
            if timestamp_candidate:
                return timestamp_candidate, message or ""
        return default_timestamp, raw

    @staticmethod
    def parse_last_event_id(last_event_id: str, task_id: int) -> int:
        """
        解析 last_event_id，获取最后读取的 seq
        
        格式: task_{task_id}_{seq} 或 task_{task_id}_{line_number}（兼容旧格式）
        
        Returns:
            最后读取的 seq，如果没有则返回 0
        """
        if not last_event_id:
            return 0
        
        try:
            if last_event_id.startswith(f"task_{task_id}_"):
                seq_str = last_event_id.replace(f"task_{task_id}_", "")
                return max(int(seq_str), 0)
            else:
                # 兼容旧格式（纯数字）
                return max(int(float(last_event_id)), 0)
        except (ValueError, TypeError):
            return 0

    @classmethod
    async def stream_task_log(
        cls,
        auth: AuthSchema,
        task_id: int,
        last_event_id: Optional[str] = None,
        redis: Optional[Redis] = None,
    ) -> AsyncGenerator[str, None]:
        """
        生成任务日志SSE流（分布式版本）
        
        流程：
        1. 先从 MySQL 读取历史日志（根据 last_seq）
        2. 然后订阅 Redis Stream 实时日志
        3. 使用 seq 全局序号确保无重复、无缺失
        
        Args:
            auth: 认证信息
            task_id: 任务ID
            last_event_id: 最后事件ID，用于断点续传（格式: task_{task_id}_{seq}）
            redis: Redis 连接对象（可选，通过依赖注入传入）
        
        Yields:
            SSE格式的字符串
        """
        request_id = str(uuid.uuid4())
        logger.info(f"[SSE] 开始生成任务日志流 task_id={task_id}, request_id={request_id}")
        
        # Redis 连接已通过依赖注入传入
        try:
            # 获取任务信息
            task = await TaskCRUD(auth).get_by_id_crud(id=task_id)
            if not task:
                logger.warning(f"[SSE] 任务不存在 task_id={task_id}")
                event_str = cls.format_sse_event(
                    "task_error",
                    {
                        "taskId": f"task_{task_id}",
                        "message": "任务不存在",
                    },
                    event_id=f"task_{task_id}_0",
                    request_id=request_id,
                )
                yield event_str.encode("utf-8")
                await asyncio.sleep(0)
                return

            # 解析 last_event_id，获取最后读取的 seq
            last_seq = cls.parse_last_event_id(last_event_id or "", task_id)
            logger.info(f"[SSE] 任务日志流 task_id={task_id}, last_seq={last_seq}")

            # 初始化 last_seq（用于异常处理）
            current_seq = last_seq

            # 发送初始连接确认事件
            logger.info(f"[SSE] 发送初始连接确认事件 task_id={task_id}")
            event_str = cls.format_sse_event(
                "task_info",
                {
                    "taskId": f"task_{task_id}",
                    "seq": 0,
                    "content": "日志流连接已建立",
                },
                event_id=f"task_{task_id}_0",
                timestamp=int(datetime.now().timestamp()),
                request_id=request_id,
            )
            yield event_str.encode("utf-8")
            await asyncio.sleep(0)

            # 步骤1: 从 MySQL 读取历史日志（last_seq 之后的所有日志）
            log_crud = TaskLogCRUD(auth)
            logger.debug(f"[SSE] 开始从 MySQL 读取历史日志 task_id={task_id}, last_seq={last_seq}")
            mysql_logs = await log_crud.get_logs_after_seq_crud(
                task_id=task_id,
                last_seq=last_seq,
                limit=None,  # 读取所有历史日志
            )
            
            logger.info(f"[SSE] 从 MySQL 读取到 {len(mysql_logs)} 条历史日志记录")
            
            # 发送历史日志
            total_lines_sent = 0
            for log_record in mysql_logs:
                # 将日志内容按行分割
                lines = log_record.content.split('\n')
                logger.debug(f"[SSE] MySQL 日志记录 seq={log_record.seq}, 包含 {len(lines)} 行")
                
                for line_idx, line in enumerate(lines):
                    if not line.strip():
                        continue
                    
                    # 为每一行生成唯一的 event_id，避免去重问题
                    event_id = f"task_{task_id}_{log_record.seq}_{line_idx}"
                    
                    event_str = cls.format_sse_event(
                        "task_log",
                        {
                            "taskId": f"task_{task_id}",
                            "seq": log_record.seq,
                            "content": line,
                        },
                        event_id=event_id,
                        timestamp=log_record.timestamp or int(datetime.now().timestamp()),
                        request_id=request_id,
                    )
                    
                    logger.debug(f"[SSE] 发送 MySQL 历史日志行 seq={log_record.seq}, line_idx={line_idx}, event_id={event_id}")
                    yield event_str.encode("utf-8")
                    total_lines_sent += 1
                    await asyncio.sleep(0)  # 让出控制权，确保立即发送
                
                # 更新 current_seq
                current_seq = log_record.seq
            
            logger.info(f"[SSE] MySQL 历史日志发送完成，共发送 {total_lines_sent} 行")

            # 步骤2: 订阅 Redis Stream 实时日志
            if redis:
                logger.info(f"[SSE] 开始订阅 Redis Stream 实时日志 task_id={task_id}, current_seq={current_seq}")
                
                # 先读取 Redis Stream 中可能已有的日志（在 MySQL 写入和 Redis 写入之间的日志）
                logger.debug(f"[SSE] 读取 Redis Stream 中已有的日志 task_id={task_id}, last_seq={current_seq}")
                redis_logs = await TaskLogRedisStream.read_logs(
                    redis=redis,
                    task_id=task_id,
                    last_seq=current_seq,
                )
                
                logger.info(f"[SSE] Redis Stream 中已有 {len(redis_logs)} 条日志记录")
                
                # 发送 Redis Stream 中已有的日志
                redis_lines_sent = 0
                for log_data in redis_logs:
                    lines = log_data["content"].split('\n')
                    logger.debug(f"[SSE] Redis Stream 日志记录 seq={log_data['seq']}, 包含 {len(lines)} 行")
                    
                    for line_idx, line in enumerate(lines):
                        if not line.strip():
                            continue
                        
                        # 为每一行生成唯一的 event_id，避免去重问题
                        event_id = f"task_{task_id}_{log_data['seq']}_{line_idx}"
                        
                        event_str = cls.format_sse_event(
                            "task_log",
                            {
                                "taskId": f"task_{task_id}",
                                "seq": log_data["seq"],
                                "content": line,
                            },
                            event_id=event_id,
                            timestamp=log_data["timestamp"],
                            request_id=request_id,
                        )
                        
                        logger.debug(f"[SSE] 发送 Redis Stream 已有日志行 seq={log_data['seq']}, line_idx={line_idx}, event_id={event_id}")
                        yield event_str.encode("utf-8")
                        redis_lines_sent += 1
                        await asyncio.sleep(0)  # 让出控制权，确保立即发送
                    
                    # 更新 current_seq
                    current_seq = log_data["seq"]
                
                logger.info(f"[SSE] Redis Stream 已有日志发送完成，共发送 {redis_lines_sent} 行")
                
                # 订阅新的实时日志
                logger.info(f"[SSE] 开始订阅 Redis Stream 新日志 task_id={task_id}, current_seq={current_seq}")
                realtime_lines_sent = 0
                last_status_check_time = time.time()
                STATUS_CHECK_INTERVAL = 2.0  # 每 2 秒检查一次任务状态
                task_finished = False
                
                # 定义任务状态检查函数
                async def check_task_status_func() -> bool:
                    """检查任务是否已完成"""
                    nonlocal task_finished, last_status_check_time
                    current_time = time.time()
                    if current_time - last_status_check_time >= STATUS_CHECK_INTERVAL:
                        last_status_check_time = current_time
                        try:
                            async with AsyncSessionLocal() as new_db:
                                new_auth = AuthSchema(db=new_db, user=auth.user, check_data_scope=False)
                                fresh_task = await TaskCRUD(new_auth).get_by_id_crud(id=task_id)
                            
                            if fresh_task and fresh_task.task_status in ("success", "failed", "partial_success"):
                                task_finished = True
                                return True
                        except Exception as e:
                            logger.warning(f"[SSE] 检查任务状态失败 task_id={task_id}: {e}")
                    return False
                
                try:
                    async for log_data in TaskLogRedisStream.subscribe_logs(
                        redis=redis,
                        task_id=task_id,
                        last_seq=current_seq,
                        check_task_status=check_task_status_func,
                    ):
                        logger.debug(f"[SSE] 收到 Redis Stream 实时日志 seq={log_data['seq']}, timestamp={log_data['timestamp']}")
                        
                        lines = log_data["content"].split('\n')
                        logger.debug(f"[SSE] Redis Stream 实时日志记录 seq={log_data['seq']}, 包含 {len(lines)} 行")
                        
                        for line_idx, line in enumerate(lines):
                            if not line.strip():
                                continue
                            
                            # 为每一行生成唯一的 event_id，避免去重问题
                            # 使用时间戳确保实时日志的唯一性
                            event_id = f"task_{task_id}_{log_data['seq']}_{line_idx}_{int(time.time() * 1000)}"
                            
                            event_str = cls.format_sse_event(
                                "task_log",
                                {
                                    "taskId": f"task_{task_id}",
                                    "seq": log_data["seq"],
                                    "content": line,
                                },
                                event_id=event_id,
                                timestamp=log_data["timestamp"],
                                request_id=request_id,
                            )
                            
                            logger.debug(f"[SSE] 立即发送实时日志行 seq={log_data['seq']}, line_idx={line_idx}, event_id={event_id}, content_preview={line[:50]}")
                            yield event_str.encode("utf-8")
                            realtime_lines_sent += 1
                            await asyncio.sleep(0)  # 让出控制权，确保立即发送
                            logger.debug(f"[SSE] 实时日志行已发送 seq={log_data['seq']}, line_idx={line_idx}")
                        
                        # 更新 current_seq
                        current_seq = log_data["seq"]
                        logger.debug(f"[SSE] 更新 current_seq={current_seq}")
                        
                        # 每次收到日志后都检查任务状态（因为任务可能在日志写入后立即完成）
                        current_time = time.time()
                        if current_time - last_status_check_time >= STATUS_CHECK_INTERVAL or current_seq % 10 == 0:
                            last_status_check_time = current_time
                            async with AsyncSessionLocal() as new_db:
                                new_auth = AuthSchema(db=new_db, user=auth.user, check_data_scope=False)
                                fresh_task = await TaskCRUD(new_auth).get_by_id_crud(id=task_id)
                            
                            if fresh_task and fresh_task.task_status in ("success", "failed", "partial_success"):
                                logger.info(f"[SSE] 检测到任务已完成 task_id={task_id}, status={fresh_task.task_status}")
                                task_finished = True
                                
                                # 发送任务状态更新事件
                                event_str = cls.format_sse_event(
                                    "task_status",
                                    {
                                        "taskId": f"task_{task_id}",
                                        "taskStatus": fresh_task.task_status,
                                        "progress": fresh_task.progress or 0,
                                        "errorMessage": fresh_task.error_message,
                                    },
                                    event_id=f"task_{task_id}_{current_seq + 1}",
                                    request_id=request_id,
                                )
                                yield event_str.encode("utf-8")
                                await asyncio.sleep(0)
                                
                                # 发送结束事件
                                status_text = "完成" if fresh_task.task_status == "success" else "失败"
                                event_str = cls.format_sse_event(
                                    "task_end",
                                    {
                                        "taskId": f"task_{task_id}",
                                        "seq": current_seq + 2,
                                        "content": f"任务已{status_text}",
                                    },
                                    event_id=f"task_{task_id}_{current_seq + 2}",
                                    request_id=request_id,
                                )
                                yield event_str.encode("utf-8")
                                await asyncio.sleep(0)
                                logger.info(f"[SSE] 任务已完成，中断 Redis Stream 订阅 task_id={task_id}")
                                break
                    
                    # 如果任务已完成（通过 check_task_status_func 检测），发送结束事件
                    if task_finished:
                        logger.info(f"[SSE] 任务已完成，退出 Redis Stream 订阅循环 task_id={task_id}")
                        # 再次确认任务状态并发送结束事件
                        async with AsyncSessionLocal() as new_db:
                            new_auth = AuthSchema(db=new_db, user=auth.user, check_data_scope=False)
                            fresh_task = await TaskCRUD(new_auth).get_by_id_crud(id=task_id)
                        
                        if fresh_task:
                            # 发送任务状态更新事件
                            event_str = cls.format_sse_event(
                                "task_status",
                                {
                                    "taskId": f"task_{task_id}",
                                    "taskStatus": fresh_task.task_status,
                                    "progress": fresh_task.progress or 0,
                                    "errorMessage": fresh_task.error_message,
                                },
                                event_id=f"task_{task_id}_{current_seq + 1}",
                                request_id=request_id,
                            )
                            yield event_str.encode("utf-8")
                            await asyncio.sleep(0)
                            
                            # 发送结束事件
                            status_text = "完成" if fresh_task.task_status == "success" else "失败"
                            event_str = cls.format_sse_event(
                                "task_end",
                                {
                                    "taskId": f"task_{task_id}",
                                    "seq": current_seq + 2,
                                    "content": f"任务已{status_text}",
                                },
                                event_id=f"task_{task_id}_{current_seq + 2}",
                                request_id=request_id,
                            )
                            yield event_str.encode("utf-8")
                            await asyncio.sleep(0)
                        
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"[SSE] 订阅 Redis Stream 失败 task_id={task_id}: {e}")
            else:
                # 如果没有 Redis，回退到文件读取模式（兼容旧逻辑）
                logger.warning(f"[SSE] Redis 未启用，回退到文件读取模式 task_id={task_id}")
                # 这里可以保留原有的文件读取逻辑作为降级方案
                event_str = cls.format_sse_event(
                    "task_info",
                    {
                        "taskId": f"task_{task_id}",
                        "seq": current_seq + 1,
                        "content": "Redis 未启用，无法获取实时日志",
                    },
                    event_id=f"task_{task_id}_{current_seq + 1}",
                    request_id=request_id,
                )
                yield event_str.encode("utf-8")
                await asyncio.sleep(0)
        
        except asyncio.CancelledError:
            logger.info(f"[SSE] 任务日志流被取消 task_id={task_id}")
            raise
        except Exception as exc:
            logger.error(f"[SSE] 推送任务日志失败 task_id={task_id}: {exc}", exc_info=True)
            try:
                current_seq_value = current_seq if 'current_seq' in locals() else 0
                event_str = cls.format_sse_event(
                    "task_error",
                    {
                        "taskId": f"task_{task_id}",
                        "seq": current_seq_value + 1,
                        "content": f"日志推送异常: {exc}",
                    },
                    event_id=f"task_{task_id}_{current_seq_value + 1}",
                    request_id=request_id,
                )
                yield event_str.encode("utf-8")
                await asyncio.sleep(0)
            except Exception as e:
                logger.error(f"[SSE] 发送错误事件失败: {e}")
        finally:
            logger.info(f"[SSE] 任务日志流结束 task_id={task_id}")


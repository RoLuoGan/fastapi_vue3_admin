# -*- coding: utf-8 -*-
"""
任务日志流处理器
负责SSE日志流的生成和推送
按照规范文档实现，结构简单清晰
"""

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Optional, Dict, Any, Tuple

import aiofiles

from app.core.database import AsyncSessionLocal
from app.core.logger import logger
from app.api.v1.module_system.auth.schema import AuthSchema
from .crud import TaskCRUD


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
    def parse_last_event_id(last_event_id: str, task_id: int) -> Tuple[int, int]:
        """
        解析 last_event_id，获取初始位置和行号
        
        格式: task_{task_id}_{line_number}
        """
        initial_position = 0
        initial_line_number = 0
        
        if not last_event_id:
            return initial_position, initial_line_number
        
        try:
            if last_event_id.startswith(f"task_{task_id}_"):
                line_number_str = last_event_id.replace(f"task_{task_id}_", "")
                initial_line_number = max(int(line_number_str), 0)
            else:
                # 兼容旧格式（纯数字位置）
                initial_position = max(int(float(last_event_id)), 0)
        except (ValueError, TypeError):
            initial_position = 0
            initial_line_number = 0
        
        return initial_position, initial_line_number

    @classmethod
    async def stream_task_log(
        cls,
        auth: AuthSchema,
        task_id: int,
        last_event_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        生成任务日志SSE流
        
        Args:
            auth: 认证信息
            task_id: 任务ID
            last_event_id: 最后事件ID，用于断点续传
        
        Yields:
            SSE格式的字符串
        """
        request_id = str(uuid.uuid4())
        logger.info(f"[SSE] 开始生成任务日志流 task_id={task_id}, request_id={request_id}")
        
        try:
            # 获取任务信息
            task = await TaskCRUD(auth).get_by_id_crud(id=task_id)
            if not task or not task.log_path:
                logger.warning(f"[SSE] 任务不存在或未生成日志 task_id={task_id}")
                event_str = cls.format_sse_event(
                    "task_error",
                    {
                        "taskId": f"task_{task_id}",
                        "message": "任务不存在或未生成日志",
                    },
                    event_id=f"task_{task_id}_0",
                    request_id=request_id,
                )
                yield event_str.encode("utf-8")
                await asyncio.sleep(0)
                return

            log_path = Path(task.log_path)
            initial_position, initial_line_number = cls.parse_last_event_id(last_event_id or "", task_id)
            logger.info(f"[SSE] 日志路径: {log_path}, 初始位置: {initial_position}, 初始行号: {initial_line_number}")
            
            # 如果使用行号定位，需要计算文件位置
            if initial_line_number > 0 and log_path.exists():
                async with aiofiles.open(log_path, "r", encoding="utf-8") as f:
                    for _ in range(initial_line_number):
                        await f.readline()
                    initial_position = await f.tell()

            # 发送初始连接确认事件
            logger.info(f"[SSE] 发送初始连接确认事件 task_id={task_id}")
            event_str = cls.format_sse_event(
                "task_info",
                {
                    "taskId": f"task_{task_id}",
                    "lineNumber": 0,
                    "content": "日志流连接已建立",
                },
                event_id=f"task_{task_id}_0",
                timestamp=int(datetime.now().timestamp()),
                request_id=request_id,
            )
            yield event_str.encode("utf-8")
            await asyncio.sleep(0)  # 让出控制权，确保立即发送

            file = None
            position = initial_position
            line_number = initial_line_number
            inactive_cycles = 0
            info_notified = False
            last_info_time = 0
            
            logger.info(f"[SSE] 进入主循环 task_id={task_id}")
            while True:
                # 读取日志文件
                if log_path.exists():
                    if file is None or file.closed:
                        current_size = log_path.stat().st_size
                        if position > current_size:
                            position = current_size
                        
                        # 如果position不在文件开头，确保从UTF-8字符边界开始读取
                        if position > 0:
                            with open(log_path, "rb") as bin_file:
                                bin_file.seek(position)
                                lookback = min(256, position)
                                bin_file.seek(max(0, position - lookback))
                                chunk = bin_file.read(lookback + 10)
                                last_newline = chunk.rfind(b"\n")
                                if last_newline >= 0:
                                    position = max(0, position - lookback + last_newline + 1)
                                    # 重新计算行号
                                    if position > 0:
                                        try:
                                            with open(log_path, "r", encoding="utf-8") as f:
                                                line_count = 0
                                                while True:
                                                    line = f.readline()
                                                    if not line:
                                                        break
                                                    line_count += 1
                                                    if f.tell() >= position:
                                                        break
                                                line_number = line_count
                                        except Exception:
                                            pass
                                else:
                                    position = max(0, position - lookback)
                        
                        file = open(log_path, "r", encoding="utf-8")
                        file.seek(position)
                    
                    # 逐行读取，每次只读取一行，立即推送
                    line = file.readline()
                    if line:
                        position = file.tell()
                        line_number += 1
                        inactive_cycles = 0
                        timestamp_str, message = cls.parse_log_line(line)
                        
                        # 转换时间戳为Unix时间戳（秒）
                        try:
                            dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                            timestamp = int(dt.timestamp())
                        except (ValueError, TypeError):
                            timestamp = int(datetime.now().timestamp())
                        
                        # 发送日志事件（立即推送，不等待）
                        event_str = cls.format_sse_event(
                            "task_log",
                            {
                                "taskId": f"task_{task_id}",
                                "lineNumber": line_number,
                                "content": message,
                            },
                            event_id=f"task_{task_id}_{line_number}",
                            timestamp=timestamp,
                            request_id=request_id,
                        )
                        yield event_str.encode("utf-8")
                        await asyncio.sleep(0)  # 让出控制权，确保立即发送
                        info_notified = True
                        # 继续读取下一行，不sleep，实现实时推送
                        continue
                    else:
                        # 没有新行，检查文件是否有新内容
                        current_file_size = log_path.stat().st_size
                        if position < current_file_size:
                            # 文件有新内容但还没有换行符，关闭文件等待下次读取
                            if file and not file.closed:
                                file.close()
                                file = None
                else:
                    # 日志文件不存在，定期发送提示信息（每10秒一次）
                    current_time = datetime.now().timestamp()
                    if not info_notified or (current_time - last_info_time) >= 10:
                        event_str = cls.format_sse_event(
                            "task_info",
                            {
                                "taskId": f"task_{task_id}",
                                "lineNumber": line_number + 1,
                                "content": "日志文件尚未生成，等待任务写入日志…",
                            },
                            event_id=f"task_{task_id}_{line_number + 1}",
                            timestamp=int(current_time),
                            request_id=request_id,
                        )
                        yield event_str.encode("utf-8")
                        await asyncio.sleep(0)  # 让出控制权，确保立即发送
                        info_notified = True
                        last_info_time = current_time
                
                # 没有新行时，短暂等待后继续检查（减少延迟，提高实时性）
                inactive_cycles += 1
                await asyncio.sleep(0.1)  # 从1秒改为0.1秒，提高实时性

                # 定期检查任务状态（每5秒检查一次，0.1秒 * 50 = 5秒）
                if inactive_cycles % 50 == 0:
                    async with AsyncSessionLocal() as new_db:
                        new_auth = AuthSchema(db=new_db, user=auth.user, check_data_scope=False)
                        fresh_task = await TaskCRUD(new_auth).get_by_id_crud(id=task_id)

                    if not fresh_task:
                        event_str = cls.format_sse_event(
                            "task_error",
                            {
                                "taskId": f"task_{task_id}",
                                "lineNumber": line_number + 1,
                                "content": "任务已删除",
                            },
                            event_id=f"task_{task_id}_{line_number + 1}",
                            request_id=request_id,
                        )
                        yield event_str.encode("utf-8")
                        await asyncio.sleep(0)
                        break

                    if fresh_task.task_status in ("success", "failed"):
                        # 发送任务状态更新事件
                        event_str = cls.format_sse_event(
                            "task_status",
                            {
                                "taskId": f"task_{task_id}",
                                "taskStatus": fresh_task.task_status,
                                "progress": fresh_task.progress or 0,
                                "errorMessage": fresh_task.error_message,
                            },
                            event_id=f"task_{task_id}_{line_number + 1}",
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
                                "lineNumber": line_number + 2,
                                "content": f"任务已{status_text}",
                            },
                            event_id=f"task_{task_id}_{line_number + 2}",
                            request_id=request_id,
                        )
                        yield event_str.encode("utf-8")
                        await asyncio.sleep(0)
                        break

                # 长时间无新日志，结束推送（0.1秒 * 600 = 60秒）
                if inactive_cycles > 600:
                    event_str = cls.format_sse_event(
                        "task_end",
                        {
                            "taskId": f"task_{task_id}",
                            "lineNumber": line_number + 1,
                            "content": "长时间无新日志，结束推送",
                        },
                        event_id=f"task_{task_id}_{line_number + 1}",
                        request_id=request_id,
                    )
                    yield event_str.encode("utf-8")
                    await asyncio.sleep(0)
                    break
                        
        except asyncio.CancelledError:
            logger.info(f"[SSE] 任务日志流被取消 task_id={task_id}")
            raise
        except Exception as exc:
            logger.error(f"[SSE] 推送任务日志失败 task_id={task_id}: {exc}", exc_info=True)
            try:
                event_str = cls.format_sse_event(
                    "task_error",
                    {
                        "taskId": f"task_{task_id}",
                        "lineNumber": line_number + 1,
                        "content": f"日志推送异常: {exc}",
                    },
                    event_id=f"task_{task_id}_{line_number + 1}",
                    request_id=request_id,
                )
                yield event_str.encode("utf-8")
                await asyncio.sleep(0)
            except Exception as e:
                logger.error(f"[SSE] 发送错误事件失败: {e}")
        finally:
            if file and not file.closed:
                file.close()
            logger.info(f"[SSE] 任务日志流结束 task_id={task_id}")


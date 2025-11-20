# -*- coding: utf-8 -*-
"""
Redis Stream 工具类
用于任务日志的实时缓存和分发
"""

import asyncio
import json
from typing import Optional, Dict, Any, AsyncGenerator, List, Callable
from datetime import datetime

from redis.asyncio.client import Redis
from app.core.logger import logger


class TaskLogRedisStream:
    """任务日志 Redis Stream 工具类"""
    
    # Stream key 前缀
    STREAM_KEY_PREFIX = "task_log_stream"
    
    # Stream 最大长度（保留最近 N 条，用于实时缓存）
    MAX_STREAM_LENGTH = 10000
    
    @classmethod
    def get_stream_key(cls, task_id: int) -> str:
        """获取任务日志 Stream key"""
        return f"{cls.STREAM_KEY_PREFIX}:{task_id}"
    
    @classmethod
    async def add_log(
        cls,
        redis: Redis,
        task_id: int,
        seq: int,
        content: str,
        timestamp: Optional[int] = None,
    ) -> str:
        """
        添加日志到 Redis Stream
        
        Args:
            redis: Redis 客户端
            task_id: 任务ID
            seq: 全局序号
            content: 日志内容
            timestamp: Unix时间戳（秒），默认使用当前时间
            
        Returns:
            Stream entry ID
        """
        if timestamp is None:
            timestamp = int(datetime.now().timestamp())
        
        stream_key = cls.get_stream_key(task_id)
        
        # 构建消息内容
        message = {
            "seq": str(seq),
            "content": content,
            "timestamp": str(timestamp),
        }
        
        try:
            # 使用 XADD 添加消息，自动生成 ID
            entry_id = await redis.xadd(
                stream_key,
                message,
                maxlen=cls.MAX_STREAM_LENGTH,
                approximate=True,  # 使用近似修剪，性能更好
            )
            
            logger.debug(f"[Redis Stream] 添加日志 task_id={task_id}, seq={seq}, entry_id={entry_id}")
            return entry_id
            
        except Exception as e:
            logger.error(f"[Redis Stream] 添加日志失败 task_id={task_id}, seq={seq}: {e}")
            raise
    
    @classmethod
    async def read_logs(
        cls,
        redis: Redis,
        task_id: int,
        last_seq: Optional[int] = None,
        count: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        从 Redis Stream 读取日志
        
        Args:
            redis: Redis 客户端
            task_id: 任务ID
            last_seq: 最后读取的 seq，从该 seq + 1 开始读取
            count: 读取数量限制
            
        Returns:
            日志列表，格式: [{"seq": int, "content": str, "timestamp": int, "entry_id": str}, ...]
        """
        stream_key = cls.get_stream_key(task_id)
        
        try:
            # 如果指定了 last_seq，从该 seq 之后开始读取
            if last_seq is not None:
                # 使用 XREAD 从指定位置读取
                # 需要找到大于 last_seq 的第一个 entry
                # 这里使用 XRANGE 先找到起始位置
                start_id = "0"  # 从开始读取
                if last_seq > 0:
                    # 尝试找到 seq >= last_seq + 1 的 entry
                    # 由于 Stream 的 ID 是时间戳+序号，我们需要遍历查找
                    # 简化处理：从 "-" 开始读取（最新位置），然后过滤
                    start_id = "-"
                
                # 使用 XREAD 读取新消息
                # BLOCK=0 表示非阻塞，立即返回
                streams = await redis.xread(
                    {stream_key: start_id},
                    count=count or 1000,
                    block=0,
                )
            else:
                # 读取所有消息
                streams = await redis.xread(
                    {stream_key: "0"},
                    count=count or 1000,
                    block=0,
                )
            
            result = []
            if streams:
                for stream_name, entries in streams:
                    for entry_id, data in entries:
                        try:
                            seq = int(data.get("seq", 0))
                            # 如果指定了 last_seq，只返回大于 last_seq 的日志
                            if last_seq is not None and seq <= last_seq:
                                continue
                            
                            result.append({
                                "seq": seq,
                                "content": data.get("content", ""),
                                "timestamp": int(data.get("timestamp", 0)),
                                "entry_id": entry_id.decode() if isinstance(entry_id, bytes) else entry_id,
                            })
                        except (ValueError, TypeError) as e:
                            logger.warning(f"[Redis Stream] 解析日志失败 entry_id={entry_id}: {e}")
                            continue
            
            # 按 seq 排序
            result.sort(key=lambda x: x["seq"])
            
            return result
            
        except Exception as e:
            logger.error(f"[Redis Stream] 读取日志失败 task_id={task_id}: {e}")
            return []
    
    @classmethod
    async def subscribe_logs(
        cls,
        redis: Redis,
        task_id: int,
        last_seq: Optional[int] = None,
        check_task_status: Optional[Callable[[], Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        订阅 Redis Stream 实时日志（阻塞读取）
        
        Args:
            redis: Redis 客户端
            task_id: 任务ID
            last_seq: 最后读取的 seq，从该 seq + 1 开始订阅
            
        Yields:
            日志字典，格式: {"seq": int, "content": str, "timestamp": int, "entry_id": str}
        """
        stream_key = cls.get_stream_key(task_id)
        logger.debug(f"[Redis Stream] 开始订阅实时日志 stream_key={stream_key}, task_id={task_id}, last_seq={last_seq}")
        
        # 确定起始位置
        start_id = "0"
        if last_seq is not None:
            # 从 last_seq + 1 开始订阅
            # 先读取一次，找到起始位置
            start_id = "$"  # 从最新位置开始（只读取新消息）
            logger.debug(f"[Redis Stream] 使用 start_id=$ 从最新位置开始订阅")
        else:
            logger.debug(f"[Redis Stream] 使用 start_id=0 从开始位置订阅")
        
        try:
            loop_count = 0
            while True:
                loop_count += 1
                try:
                    logger.debug(f"[Redis Stream] 第 {loop_count} 次 XREAD 调用 stream_key={stream_key}, start_id={start_id}, block=1000ms")
                    
                    # 使用 XREAD 阻塞读取（BLOCK=1000ms，超时后继续循环）
                    streams = await redis.xread(
                        {stream_key: start_id},
                        count=100,  # 每次最多读取 100 条
                        block=1000,  # 阻塞 1 秒
                    )
                    
                    logger.debug(f"[Redis Stream] XREAD 返回 streams={streams is not None}, entries_count={len(streams[0][1]) if streams and len(streams) > 0 else 0}")
                    
                    if streams:
                        for stream_name, entries in streams:
                            logger.debug(f"[Redis Stream] 处理 {len(entries)} 条 Stream 条目")
                            for entry_idx, (entry_id, data) in enumerate(entries):
                                try:
                                    seq = int(data.get("seq", 0))
                                    logger.debug(f"[Redis Stream] 处理条目 {entry_idx+1}/{len(entries)}, entry_id={entry_id}, seq={seq}, last_seq={last_seq}")
                                    
                                    # 如果指定了 last_seq，只返回大于 last_seq 的日志
                                    if last_seq is not None and seq <= last_seq:
                                        logger.debug(f"[Redis Stream] 跳过已处理的日志 seq={seq} <= last_seq={last_seq}")
                                        # 更新起始位置，跳过已处理的日志
                                        start_id = entry_id.decode() if isinstance(entry_id, bytes) else entry_id
                                        continue
                                    
                                    log_data = {
                                        "seq": seq,
                                        "content": data.get("content", ""),
                                        "timestamp": int(data.get("timestamp", 0)),
                                        "entry_id": entry_id.decode() if isinstance(entry_id, bytes) else entry_id,
                                    }
                                    
                                    logger.debug(f"[Redis Stream] 准备 yield 日志数据 seq={seq}, content_length={len(log_data['content'])}, timestamp={log_data['timestamp']}")
                                    
                                    # 更新起始位置
                                    start_id = entry_id.decode() if isinstance(entry_id, bytes) else entry_id
                                    
                                    yield log_data
                                    
                                    logger.debug(f"[Redis Stream] 已 yield 日志数据 seq={seq}")
                                    
                                except (ValueError, TypeError) as e:
                                    logger.warning(f"[Redis Stream] 解析日志失败 entry_id={entry_id}: {e}")
                                    continue
                    else:
                        # 没有新消息，检查任务状态（如果提供了检查函数）
                        if check_task_status:
                            try:
                                task_finished = await check_task_status()
                                if task_finished:
                                    logger.info(f"[Redis Stream] 任务已完成，中断订阅 task_id={task_id}")
                                    break
                            except Exception as e:
                                logger.warning(f"[Redis Stream] 检查任务状态失败 task_id={task_id}: {e}")
                        
                        # 没有新消息，继续等待
                        if loop_count % 10 == 0:  # 每10次循环记录一次
                            logger.debug(f"[Redis Stream] 没有新消息，继续等待 (循环 {loop_count} 次)")
                        await asyncio.sleep(0.1)
                        
                except asyncio.CancelledError:
                    logger.info(f"[Redis Stream] 订阅被取消 task_id={task_id}")
                    break
                except Exception as e:
                    logger.error(f"[Redis Stream] 订阅日志失败 task_id={task_id}: {e}", exc_info=True)
                    await asyncio.sleep(1)  # 出错后等待 1 秒再继续
                    
        except asyncio.CancelledError:
            logger.info(f"[Redis Stream] 订阅被取消 task_id={task_id}")
        except Exception as e:
            logger.error(f"[Redis Stream] 订阅异常 task_id={task_id}: {e}", exc_info=True)
    
    @classmethod
    async def get_max_seq(cls, redis: Redis, task_id: int) -> int:
        """
        获取任务日志的最大 seq
        
        Args:
            redis: Redis 客户端
            task_id: 任务ID
            
        Returns:
            最大 seq，如果 Stream 为空则返回 0
        """
        stream_key = cls.get_stream_key(task_id)
        
        try:
            # 使用 XREVRANGE 获取最后一条消息
            entries = await redis.xrevrange(stream_key, count=1)
            
            if entries:
                entry_id, data = entries[0]
                seq = int(data.get("seq", 0))
                return seq
            
            return 0
            
        except Exception as e:
            logger.error(f"[Redis Stream] 获取最大 seq 失败 task_id={task_id}: {e}")
            return 0
    
    @classmethod
    async def delete_stream(cls, redis: Redis, task_id: int) -> bool:
        """
        删除任务的 Redis Stream（任务完成后清理）
        
        Args:
            redis: Redis 客户端
            task_id: 任务ID
            
        Returns:
            是否删除成功
        """
        stream_key = cls.get_stream_key(task_id)
        
        try:
            await redis.delete(stream_key)
            logger.info(f"[Redis Stream] 删除 Stream task_id={task_id}")
            return True
        except Exception as e:
            logger.error(f"[Redis Stream] 删除 Stream 失败 task_id={task_id}: {e}")
            return False


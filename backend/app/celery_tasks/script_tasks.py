# -*- coding: utf-8 -*-
"""
脚本执行相关的 Celery 任务
调用 TaskExecutor.execute_batch_task 复用现有的任务执行框架
"""

import asyncio
from typing import Dict, Any, List
from pathlib import Path

from celery import shared_task

from app.core.logger import logger


@shared_task(bind=True, name="app.celery_tasks.script_tasks.execute_script_task")
def execute_script_task(
    self,
    task_id: int,
    log_path: str,
    task_type: str,
    operator_type: str,
    operator_metas: List[Dict[str, Any]],
    timeout: int = 3600,
) -> Dict[str, Any]:
    """
    执行脚本任务 - 调用 TaskExecutor.execute_batch_task
    
    Args:
        task_id: 任务记录ID（数据库中的任务ID）
        log_path: 日志文件路径
        task_type: 任务类型 (script_executor)
        operator_type: 操作类型 (run)
        operator_metas: 操作元数据列表
        timeout: 超时时间（秒）
    
    Returns:
        Dict: 执行结果
    """
    celery_task_id = self.request.id
    
    logger.info(f"[Celery Task {celery_task_id}] 开始执行脚本任务")
    logger.info(f"[Celery Task {celery_task_id}] task_id={task_id}, task_type={task_type}, operator_type={operator_type}")
    logger.info(f"[Celery Task {celery_task_id}] 脚本数量: {len(operator_metas)}")
    
    for idx, meta in enumerate(operator_metas, 1):
        logger.info(f"[Celery Task {celery_task_id}] 脚本 {idx}: {meta.get('script_name')} (ID: {meta.get('script_id')})")
    
    result = {
        "celery_task_id": celery_task_id,
        "task_id": task_id,
        "status": "running",
        "error": None,
    }
    
    try:
        # 在新的事件循环中执行异步任务
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(
                _execute_task_async(
                    task_id=task_id,
                    log_path=Path(log_path),
                    task_type=task_type,
                    operator_type=operator_type,
                    operator_metas=operator_metas,
                    timeout=timeout,
                )
            )
            result["status"] = "success"
            logger.info(f"[Celery Task {celery_task_id}] 任务执行完成")
        except asyncio.CancelledError as e:
            # 任务被取消（超时或手动取消），这是正常情况，不应该导致 Worker 崩溃
            result["status"] = "cancelled"
            result["error"] = str(e) if str(e) else "任务已被取消（超时或手动取消）"
            logger.warning(f"[Celery Task {celery_task_id}] 任务已取消: {result['error']}")
        except RuntimeError as e:
            # 捕获事件循环相关的错误（如 Event loop is closed）
            if "Event loop is closed" in str(e):
                result["status"] = "cancelled"
                result["error"] = "任务执行过程中事件循环已关闭（可能是超时导致）"
                logger.warning(f"[Celery Task {celery_task_id}] 事件循环已关闭: {e}")
            else:
                raise
        finally:
            # 快速清理事件循环，避免阻塞 Worker
            try:
                # 获取所有待处理的任务
                pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
                if pending:
                    logger.debug(f"[Celery Task {celery_task_id}] 发现 {len(pending)} 个待处理任务，开始取消")
                    # 直接取消所有待处理任务，不等待完成
                    for task in pending:
                        task.cancel()
                    
                    # 尝试快速等待取消完成，设置超时避免阻塞
                    try:
                        # 使用 asyncio.wait_for 设置超时（最多等待 2 秒）
                        async def cancel_all():
                            await asyncio.gather(*pending, return_exceptions=True)
                        
                        loop.run_until_complete(asyncio.wait_for(cancel_all(), timeout=2.0))
                        logger.debug(f"[Celery Task {celery_task_id}] 所有待处理任务已取消")
                    except asyncio.TimeoutError:
                        logger.warning(f"[Celery Task {celery_task_id}] 取消待处理任务超时，强制关闭事件循环")
                    except RuntimeError:
                        # 如果事件循环已经关闭，忽略错误
                        pass
                    except Exception as cancel_error:
                        logger.warning(f"[Celery Task {celery_task_id}] 取消待处理任务时出错: {cancel_error}")
            except Exception as cleanup_error:
                logger.warning(f"[Celery Task {celery_task_id}] 清理待处理任务时出错: {cleanup_error}")
            finally:
                # 强制关闭事件循环
                try:
                    # 再次尝试取消所有剩余任务
                    try:
                        remaining = [t for t in asyncio.all_tasks(loop) if not t.done()]
                        for task in remaining:
                            task.cancel()
                    except RuntimeError:
                        pass
                    
                    # 关闭事件循环
                    loop.close()
                    logger.debug(f"[Celery Task {celery_task_id}] 事件循环已关闭")
                except Exception as close_error:
                    logger.warning(f"[Celery Task {celery_task_id}] 关闭事件循环时出错: {close_error}")
            
    except Exception as e:
        # 捕获所有其他异常，避免 Worker 崩溃
        result["status"] = "failed"
        result["error"] = str(e)
        logger.error(f"[Celery Task {celery_task_id}] 任务执行失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    # 始终返回结果，确保 Celery Worker 不会因为异常而崩溃
    return result


async def _execute_task_async(
    task_id: int,
    log_path: Path,
    task_type: str,
    operator_type: str,
    operator_metas: List[Dict[str, Any]],
    timeout: int,
) -> None:
    """
    异步执行任务 - 调用 TaskExecutor.execute_batch_task
    """
    from redis.asyncio import Redis
    from app.core.database import AsyncSessionLocal
    from app.api.v1.module_system.auth.schema import AuthSchema
    from app.api.v1.module_operations.task.executor import TaskExecutor
    from app.config.setting import settings
    
    # 获取 Redis 连接（如果启用）
    redis = None
    if settings.REDIS_ENABLE:
        try:
            redis = await Redis.from_url(
                url=settings.REDIS_URI,
                encoding='utf-8',
                decode_responses=True,
            )
            logger.info(f"[Celery] Redis 连接成功")
        except Exception as e:
            logger.warning(f"[Celery] Redis 连接失败，将跳过 Redis Stream: {e}")
            redis = None
    
    try:
        # 创建数据库会话
        async with AsyncSessionLocal() as db:
            # 创建系统级别的 auth（无用户，但有数据库会话）
            auth = AuthSchema(db=db, user=None, check_data_scope=False)
            
            # 调用 TaskExecutor.execute_batch_task
            # 注意：如果任务超时，executor 会抛出 CancelledError
            try:
                await TaskExecutor.execute_batch_task(
                    base_auth=auth,
                    task_id=task_id,
                    log_path=log_path,
                    task_type=task_type,
                    operator_type=operator_type,
                    operator_metas=operator_metas,
                    timeout=timeout,
                    redis=redis,
                )
            except asyncio.CancelledError as ce:
                # 捕获 CancelledError，这是任务超时或取消的正常情况
                logger.warning(f"[Celery] 任务 {task_id} 执行过程中被取消: {ce}")
                # executor 内部已经更新了任务状态，这里不需要额外处理
                # 重新抛出，让外层处理，但确保快速退出
                raise
    except asyncio.CancelledError:
        # 捕获 CancelledError，这是正常情况，不应该导致 Worker 崩溃
        # 重新抛出，让外层函数处理
        logger.warning(f"[Celery] 任务 {task_id} 执行过程中被取消")
        raise
    except Exception as e:
        # 捕获其他异常，避免未处理的异常导致 Worker 崩溃
        logger.error(f"[Celery] 任务 {task_id} 执行异常: {e}", exc_info=True)
        raise
    finally:
        # 快速关闭 Redis 连接，不阻塞
        if redis:
            try:
                # 使用 asyncio.wait_for 设置超时，避免阻塞
                await asyncio.wait_for(redis.close(), timeout=1.0)
            except (asyncio.TimeoutError, Exception):
                # 如果关闭超时或出错，直接忽略，避免阻塞
                pass

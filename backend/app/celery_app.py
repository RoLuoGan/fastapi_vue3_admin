# -*- coding: utf-8 -*-
"""
Celery 应用配置
"""

import os
from celery import Celery
from celery.signals import worker_ready, worker_shutdown

# 确保环境变量已设置
env = os.environ.get("ENVIRONMENT", "dev")
os.environ["ENVIRONMENT"] = env

# 导入配置
from app.config.setting import settings

# 创建 Celery 应用
celery_app = Celery(
    "fastapi_vue3_admin",
    broker=settings.REDIS_URI,
    backend=settings.REDIS_URI,
)

# Celery 配置
celery_app.conf.update(
    # 任务序列化
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # 时区
    timezone="Asia/Shanghai",
    enable_utc=True,
    
    # 任务配置
    task_track_started=True,
    task_time_limit=86400,  # 任务最大执行时间 24小时
    task_soft_time_limit=82800,  # 软超时 23小时
    
    # 结果配置
    result_expires=3600,  # 结果过期时间 1小时
    
    # Worker 配置
    worker_prefetch_multiplier=1,  # 每个 worker 预取的任务数
    worker_max_tasks_per_child=100,  # 每个 worker 执行的最大任务数后重启
    
    # 默认队列（任务会通过 apply_async(queue=xxx) 动态指定队列）
    task_default_queue="scripts",
)

# 自动发现任务
celery_app.autodiscover_tasks(["app.celery_tasks"])

# 配置任务失败处理，避免 Worker 崩溃
from celery.signals import task_failure

@task_failure.connect
def on_task_failure(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwargs):
    """任务失败时的处理，避免 Worker 崩溃"""
    import asyncio
    from app.core.logger import logger
    
    # 如果是 CancelledError，这是正常情况（任务超时或取消），不应该导致 Worker 崩溃
    if isinstance(exception, (asyncio.CancelledError, RuntimeError)):
        if isinstance(exception, RuntimeError) and "Event loop is closed" in str(exception):
            logger.warning(f"[Celery] 任务 {task_id} 失败（事件循环已关闭，可能是超时导致）: {exception}")
            return  # 不记录为严重错误
        elif isinstance(exception, asyncio.CancelledError):
            logger.warning(f"[Celery] 任务 {task_id} 失败（任务已取消）: {exception}")
            return  # 不记录为严重错误
    
    # 其他异常正常记录
    logger.error(f"[Celery] 任务 {task_id} 执行失败: {exception}", exc_info=einfo)


@worker_ready.connect
def on_worker_ready(sender, **kwargs):
    """Worker 启动时自动注册到管理系统"""
    import asyncio
    from app.core.logger import logger
    
    register_enabled = os.environ.get("CELERY_WORKER_REGISTER", "1") == "1"
    if not register_enabled:
        logger.info("Worker 自动注册已禁用")
        return
    
    worker_ip = os.environ.get("CELERY_WORKER_IP", "127.0.0.1")
    worker_hostname = os.environ.get("CELERY_WORKER_HOSTNAME", sender.hostname)
    queue_code = os.environ.get("CELERY_WORKER_QUEUE", "default")
    
    # 从队列编码生成队列名称
    queue_name_map = {
        "scripts": "脚本执行",
        "default": "默认队列",
    }
    queue_name = queue_name_map.get(queue_code, queue_code)
    
    logger.info(f"Worker 准备注册: {queue_code}@{worker_ip}")
    
    async def register():
        from app.core.database import AsyncSessionLocal
        from app.api.v1.module_system.auth.schema import AuthSchema
        from app.api.v1.module_operations.celery_worker.service import CeleryWorkerService
        
        try:
            async with AsyncSessionLocal() as db:
                # 创建一个系统级别的 auth（无用户）
                auth = AuthSchema(db=db, user=None, check_data_scope=False)
                await CeleryWorkerService.register_service(
                    auth=auth,
                    queue_name=queue_name,
                    queue_code=queue_code,
                    node_ip=worker_ip,
                    node_hostname=worker_hostname
                )
                # 显式提交事务（Celery Worker 中需要手动提交）
                await db.commit()
                logger.info(f"Worker 注册成功: {queue_code}@{worker_ip}")
        except Exception as e:
            logger.error(f"Worker 注册失败: {e}", exc_info=True)
    
    # 在新的事件循环中执行异步注册
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(register())
        loop.close()
    except Exception as e:
        from app.core.logger import logger
        logger.error(f"Worker 注册异常: {e}")


@worker_shutdown.connect
def on_worker_shutdown(sender, **kwargs):
    """Worker 关闭时更新状态"""
    import asyncio
    from app.core.logger import logger
    
    worker_ip = os.environ.get("CELERY_WORKER_IP", "127.0.0.1")
    queue_code = os.environ.get("CELERY_WORKER_QUEUE", "default")
    
    logger.info(f"Worker 正在关闭: {queue_code}@{worker_ip}")
    
    async def update_status():
        from app.core.database import AsyncSessionLocal
        from app.api.v1.module_operations.celery_worker.crud import CeleryWorkerCRUD
        from app.api.v1.module_system.auth.schema import AuthSchema
        
        try:
            async with AsyncSessionLocal() as db:
                auth = AuthSchema(db=db, user=None, check_data_scope=False)
                crud = CeleryWorkerCRUD(auth)
                worker = await crud.get_by_queue_and_ip_crud(queue_code, worker_ip)
                if worker:
                    worker.status = False
                    # 显式提交事务（Celery Worker 中需要手动提交）
                    await db.commit()
                    logger.info(f"Worker 状态已更新为离线: {queue_code}@{worker_ip}")
        except Exception as e:
            logger.error(f"更新 Worker 状态失败: {e}", exc_info=True)
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(update_status())
        loop.close()
    except Exception as e:
        logger.error(f"Worker 关闭异常: {e}")


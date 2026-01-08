# -*- coding: utf-8 -*-
"""
脚本管理业务逻辑
"""

import json
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

from redis.asyncio.client import Redis

from app.core.exceptions import CustomException
from app.core.logger import logger
from app.api.v1.module_system.auth.schema import AuthSchema

from .crud import ScriptCRUD
from .schema import ScriptCreateSchema, ScriptUpdateSchema, ScriptOutSchema, ScriptRunSchema
from ..task.crud import TaskCRUD
from ..task.executor import TaskExecutor
from ..task.schema import TaskStatus


class ScriptService:
    """脚本管理服务层"""

    @classmethod
    async def get_list_service(
        cls,
        auth: AuthSchema,
        search: Optional[Dict] = None,
    ) -> List[Dict]:
        scripts = await ScriptCRUD(auth).get_list_crud(
            search=search,
            order_by=[{"created_at": "desc"}]
        )
        return [ScriptOutSchema.model_validate(s).model_dump() for s in scripts]

    @classmethod
    async def get_page_service(
        cls,
        auth: AuthSchema,
        page_no: int,
        page_size: int,
        search,
        order_by,
    ) -> Dict:
        page_no = page_no or 1
        page_size = page_size or 10
        offset = (page_no - 1) * page_size
        search_dict = search.__dict__ if hasattr(search, "__dict__") else search
        order = order_by or [{"created_at": "desc"}]
        return await ScriptCRUD(auth).page_crud(
            offset=offset,
            limit=page_size,
            order_by=order,
            search=search_dict,
            out_schema=ScriptOutSchema,
        )

    @classmethod
    async def get_detail_service(cls, auth: AuthSchema, id: int) -> Dict:
        script = await ScriptCRUD(auth).get_by_id_crud(id=id)
        if not script:
            raise CustomException(msg="脚本不存在")
        return ScriptOutSchema.model_validate(script).model_dump()

    @classmethod
    async def create_service(cls, auth: AuthSchema, data: ScriptCreateSchema) -> Dict:
        crud = ScriptCRUD(auth)
        
        # 检查名称是否已存在
        existing = await crud.get_by_name_crud(data.name)
        if existing:
            raise CustomException(msg=f"脚本名称 {data.name} 已存在")
        
        # 创建脚本（事务由依赖注入层自动管理，不需要显式 commit）
        script = await crud.create_script_crud(data)
        return ScriptOutSchema.model_validate(script).model_dump()

    @classmethod
    async def update_service(cls, auth: AuthSchema, id: int, data: ScriptUpdateSchema) -> Dict:
        crud = ScriptCRUD(auth)
        
        script = await crud.get_by_id_crud(id=id)
        if not script:
            raise CustomException(msg="脚本不存在")
        
        # 检查名称唯一性（如果有名称字段）
        if hasattr(data, 'name') and data.name:
            existing = await crud.get_by_name_crud(data.name)
            if existing and existing.id != id:
                raise CustomException(msg=f"脚本名称 {data.name} 已存在")
        
        # 更新脚本（事务由依赖注入层自动管理，不需要显式 commit）
        script = await crud.update_script_crud(id=id, data=data)
        return ScriptOutSchema.model_validate(script).model_dump()

    @classmethod
    async def delete_service(cls, auth: AuthSchema, ids: List[int]) -> None:
        if len(ids) < 1:
            raise CustomException(msg="删除对象不能为空")
        # 删除脚本（事务由依赖注入层自动管理，不需要显式 commit）
        await ScriptCRUD(auth).delete_crud(ids=ids)

    @classmethod
    async def run_script_service(
        cls,
        auth: AuthSchema,
        data: ScriptRunSchema,
        redis: Optional[Redis] = None,
    ) -> Dict:
        """
        运行脚本 - 发送到 Celery Worker 队列执行
        
        流程：
        1. 验证脚本和参数
        2. 创建任务记录
        3. 发送 Celery 任务到指定队列
        4. 返回 task_id
        """
        crud = ScriptCRUD(auth)
        
        # 获取脚本信息
        script = await crud.get_by_id_crud(id=data.script_id)
        if not script:
            raise CustomException(msg="脚本不存在")
        
        if not script.status:
            raise CustomException(msg="脚本已禁用")
        
        # 验证参数
        script_data = ScriptOutSchema.model_validate(script).model_dump()
        params_schema = script_data.get("params_schema") or []
        run_params = data.params or {}
        
        # 检查必填参数
        for param_def in params_schema:
            param_name = param_def.get("name")
            required = param_def.get("required", True)
            default = param_def.get("default")
            
            if required and param_name not in run_params:
                if default is not None:
                    run_params[param_name] = default
                else:
                    raise CustomException(msg=f"缺少必填参数: {param_name}")
        
        # 构建 operator_metas
        timeout = data.timeout or script.default_timeout
        queue_code = script.queue_code or "scripts"
        
        operator_metas = [{
            "script_id": script.id,
            "script_name": script.name,
            "script_type": script.script_type,
            "content_type": script.content_type,
            "content": script.content,
            "queue_code": queue_code,
            "params": run_params,
            "target_nodes": data.target_nodes,
        }]
        
        # 构建任务参数
        task_type = "script_executor"
        operator_type = "run"
        params_dict = {
            "task_type": task_type,
            "operator_type": operator_type,
            "operator_metas": operator_metas,
        }
        
        # 创建任务记录
        task_crud = TaskCRUD(auth)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = TaskExecutor.build_log_path(task_type=operator_type, node_ip=f"script_{timestamp}")
        
        task_data = {
            "task_type": operator_type,
            "task_status": TaskStatus.RUNNING,
            "progress": 0,
            "log_path": str(log_path),
            "params": json.dumps(params_dict, ensure_ascii=False),
        }
        
        # 创建任务记录（create 方法已经调用了 flush 和 refresh）
        task = await task_crud.create(data=task_data)
        # 需要立即提交以便 Celery 任务可以看到任务记录
        await auth.db.commit()
        
        logger.debug(
            f"[脚本执行] 任务记录已创建: task_id={task.id}, script_id={script.id}, "
            f"script_name={script.name}, queue={queue_code}, timeout={timeout}"
        )
        
        # 检查 Celery 和 Redis 配置
        from app.config.setting import settings
        from app.celery_app import celery_app
        
        # 获取 Celery broker 和 backend（使用正确的方式）
        try:
            broker_url = getattr(celery_app.conf, 'broker_url', None) or settings.REDIS_URI
            backend_url = getattr(celery_app.conf, 'result_backend', None) or settings.REDIS_URI
        except Exception as e:
            logger.warning(f"[脚本执行] 获取Celery配置失败: {e}, 使用settings.REDIS_URI")
            broker_url = settings.REDIS_URI
            backend_url = settings.REDIS_URI
        
        logger.debug(
            f"[脚本执行] Celery配置检查: "
            f"broker={broker_url}, "
            f"backend={backend_url}, "
            f"queue={queue_code}"
        )
        
        # 检查 Redis 连接
        redis_host = None
        redis_port = None
        redis_db = None
        try:
            import redis
            redis_uri = settings.REDIS_URI
            logger.debug(f"[脚本执行] Redis URI: {redis_uri}")
            
            # 解析 Redis URI
            from urllib.parse import urlparse
            parsed = urlparse(redis_uri)
            redis_host = parsed.hostname or "127.0.0.1"
            redis_port = parsed.port or 6379
            redis_db = int(parsed.path.lstrip('/')) if parsed.path else 0
            
            logger.debug(
                f"[脚本执行] Redis连接参数: host={redis_host}, port={redis_port}, db={redis_db}"
            )
            
            # 尝试连接 Redis
            test_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                socket_connect_timeout=2,
                decode_responses=False
            )
            test_client.ping()
            logger.debug(f"[脚本执行] Redis连接测试成功")
            test_client.close()
        except Exception as redis_error:
            error_details = f"host={redis_host}, port={redis_port}, db={redis_db}" if redis_host else "无法解析Redis URI"
            logger.error(
                f"[脚本执行] Redis连接测试失败: {redis_error}, "
                f"请检查Redis服务是否启动 ({error_details})",
                exc_info=True
            )
            raise CustomException(
                msg=f"Redis连接失败: {redis_error}. 请检查Redis服务是否启动"
            )
        
        # 发送 Celery 任务到指定队列
        from app.celery_tasks.script_tasks import execute_script_task
        
        logger.debug(
            f"[脚本执行] 准备发送Celery任务: task_id={task.id}, "
            f"queue={queue_code}, kwargs={len(str(operator_metas))} chars"
        )
        
        try:
            celery_task = execute_script_task.apply_async(
                kwargs={
                    "task_id": task.id,
                    "log_path": str(log_path),
                    "task_type": task_type,
                    "operator_type": operator_type,
                    "operator_metas": operator_metas,
                    "timeout": timeout,
                },
                queue=queue_code,
            )
            
            logger.info(
                f"[脚本执行] 任务已发送到队列: script_id={script.id}, script_name={script.name}, "
                f"task_id={task.id}, celery_task_id={celery_task.id}, queue={queue_code}"
            )
            
            return {
                "message": "任务已发送到执行队列",
                "task_id": task.id,
                "celery_task_id": celery_task.id,
                "task_type": task_type,
                "operator_type": operator_type,
                "queue": queue_code,
            }
        except Exception as celery_error:
            logger.error(
                f"[脚本执行] Celery任务发送失败: task_id={task.id}, queue={queue_code}, "
                f"error={type(celery_error).__name__}: {celery_error}",
                exc_info=True
            )
            
            # 更新任务状态为失败
            try:
                task.task_status = TaskStatus.FAILED
                task.error_message = f"任务发送失败: {str(celery_error)}"
                await auth.db.commit()
            except Exception as update_error:
                logger.error(f"[脚本执行] 更新任务状态失败: {update_error}")
            
            raise CustomException(
                msg=f"任务发送到Celery队列失败: {str(celery_error)}. "
                f"请检查Redis连接和Celery Worker是否正常运行"
            )



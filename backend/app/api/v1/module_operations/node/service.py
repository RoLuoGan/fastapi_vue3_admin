# -*- coding: utf-8 -*-

from typing import List, Dict, Optional
import asyncio

from app.core.exceptions import CustomException
from app.core.logger import logger
from ...module_system.auth.schema import AuthSchema
from .crud import ServiceCRUD, NodeCRUD, TaskCRUD
from .param import ServiceQueryParam, NodeQueryParam
from .schema import (
    ServiceCreateSchema,
    ServiceUpdateSchema,
    ServiceOutSchema,
    NodeCreateSchema,
    NodeUpdateSchema,
    NodeOutSchema,
    TaskOutSchema
)


class ServiceService:
    """服务模块管理服务层"""

    @classmethod
    async def get_service_tree_service(cls, auth: AuthSchema, search: Optional[ServiceQueryParam] = None, order_by: Optional[List[Dict]] = None) -> List[Dict]:
        """获取服务模块树形列表（包含节点）"""
        service_list = await ServiceCRUD(auth).get_list_crud(search=search.__dict__ if search else None, order_by=order_by)
        result = []
        for service in service_list:
            service_dict = ServiceOutSchema.model_validate(service).model_dump()
            # 获取该服务下的节点列表
            nodes = []
            for node in service.nodes:
                node_dict = NodeOutSchema.model_validate(node).model_dump()
                node_dict['service_name'] = service.name
                nodes.append(node_dict)
            service_dict['nodes'] = nodes
            result.append(service_dict)
        return result

    @classmethod
    async def get_service_detail_service(cls, auth: AuthSchema, id: int) -> Dict:
        """获取服务模块详情"""
        service = await ServiceCRUD(auth).get_by_id_crud(id=id)
        if not service:
            raise CustomException(msg='服务模块不存在')
        service_dict = ServiceOutSchema.model_validate(service).model_dump()
        # 包含节点信息
        nodes = []
        for node in service.nodes:
            node_dict = NodeOutSchema.model_validate(node).model_dump()
            node_dict['service_name'] = service.name
            nodes.append(node_dict)
        service_dict['nodes'] = nodes
        return service_dict

    @classmethod
    async def create_service_service(cls, auth: AuthSchema, data: ServiceCreateSchema) -> Dict:
        """创建服务模块"""
        service = await ServiceCRUD(auth).get(name=data.name)
        if service:
            raise CustomException(msg='创建失败，该服务模块已存在')
        service = await ServiceCRUD(auth).create(data=data)
        return ServiceOutSchema.model_validate(service).model_dump()

    @classmethod
    async def update_service_service(cls, auth: AuthSchema, id: int, data: ServiceUpdateSchema) -> Dict:
        """更新服务模块"""
        service = await ServiceCRUD(auth).get_by_id_crud(id=id)
        if not service:
            raise CustomException(msg='更新失败，该服务模块不存在')
        exist_service = await ServiceCRUD(auth).get(name=data.name)
        if exist_service and exist_service.id != id:
            raise CustomException(msg='更新失败，服务模块名称重复')
        service = await ServiceCRUD(auth).update(id=id, data=data)
        return ServiceOutSchema.model_validate(service).model_dump()

    @classmethod
    async def delete_service_service(cls, auth: AuthSchema, ids: list[int]) -> None:
        """删除服务模块"""
        if len(ids) < 1:
            raise CustomException(msg='删除失败，删除对象不能为空')
        for id in ids:
            service = await ServiceCRUD(auth).get_by_id_crud(id=id, preload=["nodes"])
            if not service:
                raise CustomException(msg='删除失败，该服务模块不存在')
            # 检查是否有节点，如果有节点则不允许删除
            if service.nodes and len(service.nodes) > 0:
                raise CustomException(msg=f'删除失败，服务模块"{service.name}"下存在节点，请先删除节点')
        await ServiceCRUD(auth).delete(ids=ids)


class NodeService:
    """节点管理服务层"""

    @classmethod
    async def get_node_detail_service(cls, auth: AuthSchema, id: int) -> Dict:
        """获取节点详情"""
        node = await NodeCRUD(auth).get_by_id_crud(id=id)
        if not node:
            raise CustomException(msg='节点不存在')
        node_dict = NodeOutSchema.model_validate(node).model_dump()
        node_dict['service_name'] = node.service.name if node.service else None
        return node_dict

    @classmethod
    async def create_node_service(cls, auth: AuthSchema, data: NodeCreateSchema) -> Dict:
        """创建节点"""
        # 验证服务模块是否存在
        service = await ServiceCRUD(auth).get_by_id_crud(id=data.service_id)
        if not service:
            raise CustomException(msg='创建失败，服务模块不存在')
        
        # 检查同模块下是否已存在相同的IP:PORT
        port = data.port or 22  # 默认端口22
        existing_nodes = await NodeCRUD(auth).get_list_crud(
            search={'service_id': data.service_id, 'ip': data.ip, 'port': port}
        )
        if existing_nodes:
            raise CustomException(msg=f'创建失败，服务模块下已存在IP {data.ip}:{port} 的节点')
        
        node = await NodeCRUD(auth).create(data=data)
        node_dict = NodeOutSchema.model_validate(node).model_dump()
        node_dict['service_name'] = service.name
        return node_dict

    @classmethod
    async def update_node_service(cls, auth: AuthSchema, id: int, data: NodeUpdateSchema) -> Dict:
        """更新节点"""
        node = await NodeCRUD(auth).get_by_id_crud(id=id)
        if not node:
            raise CustomException(msg='更新失败，该节点不存在')
        # 验证服务模块是否存在
        service = await ServiceCRUD(auth).get_by_id_crud(id=data.service_id)
        if not service:
            raise CustomException(msg='更新失败，服务模块不存在')
        
        # 检查同模块下是否已存在相同的IP:PORT（排除当前节点）
        port = data.port or 22  # 默认端口22
        existing_nodes = await NodeCRUD(auth).get_list_crud(
            search={'service_id': data.service_id, 'ip': data.ip, 'port': port}
        )
        # 过滤掉当前节点
        existing_nodes = [n for n in existing_nodes if n.id != id]
        if existing_nodes:
            raise CustomException(msg=f'更新失败，服务模块下已存在IP {data.ip}:{port} 的节点')
        
        node = await NodeCRUD(auth).update(id=id, data=data)
        node_dict = NodeOutSchema.model_validate(node).model_dump()
        node_dict['service_name'] = service.name
        return node_dict

    @classmethod
    async def delete_node_service(cls, auth: AuthSchema, ids: list[int]) -> None:
        """删除节点"""
        if len(ids) < 1:
            raise CustomException(msg='删除失败，删除对象不能为空')
        for id in ids:
            node = await NodeCRUD(auth).get_by_id_crud(id=id)
            if not node:
                raise CustomException(msg='删除失败，该节点不存在')
        await NodeCRUD(auth).delete(ids=ids)


class TaskService:
    """任务管理服务层"""

    @classmethod
    async def get_recent_tasks_service(cls, auth: AuthSchema, limit: int = 20) -> List[Dict]:
        """获取最近的任务列表"""
        tasks = await TaskCRUD(auth).get_recent_tasks_crud(limit=limit)
        return [TaskOutSchema.model_validate(task).model_dump() for task in tasks]

    @classmethod
    async def deploy_service(cls, auth: AuthSchema, node_ids: list[int]) -> Dict:
        """部署服务（体现模拟）"""
        # 获取节点信息
        nodes = []
        for node_id in node_ids:
            node = await NodeCRUD(auth).get_by_id_crud(id=node_id)
            if not node:
                raise CustomException(msg=f'节点ID {node_id} 不存在')
            nodes.append(node)

        # 创建任务记录（模拟异步执行）
        task_crud = TaskCRUD(auth)
        task_records = []
        for node in nodes:
            task_data = {
                'node_id': node.id,
                'ip': node.ip,
                'task_type': 'deploy',
                'task_status': 'running',
            }
            task = await task_crud.create(data=task_data)
            task_records.append(task)

        # 确保事务提交，释放数据库锁定
        await auth.db.commit()

        # 模拟异步任务执行（实际应该使用后台任务队列）
        async def simulate_task(task_record_id: int):
            # 使用独立的数据库会话，避免与主事务冲突
            from app.core.database import AsyncSessionLocal
            from ...module_system.auth.schema import AuthSchema
            from app.core.dependencies import get_current_user
            
            async with AsyncSessionLocal() as new_db:
                try:
                    # 获取当前用户信息（如果需要的话）
                    current_user = auth.user
                    new_auth = AuthSchema(db=new_db, user=current_user, check_data_scope=False)
                    new_task_crud = TaskCRUD(new_auth)
                    
                    await asyncio.sleep(2)  # 模拟执行时间
                    # 随机模拟成功或失败
                    import random
                    task_status = 'success' if random.random() > 0.2 else 'failed'
                    error_message = '模拟部署失败' if task_status == 'failed' else None
                    
                    # 更新任务状态
                    await new_task_crud.update(id=task_record_id, data={'task_status': task_status, 'error_message': error_message})
                    await new_db.commit()
                except Exception as e:
                    await new_db.rollback()
                    logger.error(f"更新任务状态失败 {task_record_id}: {str(e)}")

        # 在后台执行任务（这里只是示例，实际应该使用任务队列）
        for task_record in task_records:
            asyncio.create_task(simulate_task(task_record.id))

        return {"message": "部署任务已启动", "task_count": len(task_records)}

    @classmethod
    async def restart_service(cls, auth: AuthSchema, node_ids: list[int]) -> Dict:
        """重启服务（模拟实现）"""
        # 获取节点信息
        nodes = []
        for node_id in node_ids:
            node = await NodeCRUD(auth).get_by_id_crud(id=node_id)
            if not node:
                raise CustomException(msg=f'节点ID {node_id} 不存在')
            nodes.append(node)

        # 创建任务记录
        task_crud = TaskCRUD(auth)
        task_records = []
        for node in nodes:
            task_data = {
                'node_id': node.id,
                'ip': node.ip,
                'task_type': 'restart',
                'task_status': 'running',
            }
            task = await task_crud.create(data=task_data)
            task_records.append(task)

        # 确保事务提交，释放数据库锁定
        await auth.db.commit()

        # 模拟异步任务执行
        async def simulate_task(task_record_id: int):
            # 使用独立的数据库会话，避免与主事务冲突
            from app.core.database import AsyncSessionLocal
            from ...module_system.auth.schema import AuthSchema
            
            async with AsyncSessionLocal() as new_db:
                try:
                    # 获取当前用户信息（如果需要的话）
                    current_user = auth.user
                    new_auth = AuthSchema(db=new_db, user=current_user, check_data_scope=False)
                    new_task_crud = TaskCRUD(new_auth)
                    
                    await asyncio.sleep(1.5)  # 模拟执行时间
                    import random
                    task_status = 'success' if random.random() > 0.15 else 'failed'
                    error_message = '模拟重启失败' if task_status == 'failed' else None
                    
                    # 更新任务状态
                    await new_task_crud.update(id=task_record_id, data={'task_status': task_status, 'error_message': error_message})
                    await new_db.commit()
                except Exception as e:
                    await new_db.rollback()
                    logger.error(f"更新任务状态失败 {task_record_id}: {str(e)}")

        for task_record in task_records:
            asyncio.create_task(simulate_task(task_record.id))

        return {"message": "重启任务已启动", "task_count": len(task_records)}


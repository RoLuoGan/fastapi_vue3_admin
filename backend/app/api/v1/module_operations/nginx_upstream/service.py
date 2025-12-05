# -*- coding: utf-8 -*-
"""
Nginx Upstream领域服务
"""

from typing import List, Dict, Optional
import json
import time
from jinja2 import Template, TemplateError

from app.core.exceptions import CustomException
from app.api.v1.module_system.auth.schema import AuthSchema

from .crud import NginxUpstreamCRUD
from .schema import (
    NginxUpstreamCreateSchema,
    NginxUpstreamUpdateSchema,
    NginxUpstreamOutSchema,
    ProxyTargetSchema,
    HealthCheckSchema,
    SyncUpstreamSchema,
    PreviewTemplateSchema,
)
from ..server.schema import NodeOutSchema
from ..server.crud import ServerCRUD
from ..service_module.crud import ServiceCRUD


class NginxUpstreamService:
    """Nginx Upstream业务逻辑"""

    @classmethod
    async def get_upstream_page_service(
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
        search_dict = search.__dict__ if hasattr(search, "__dict__") else (search or {})
        order = order_by or [{"created_at": "desc"}]
        return await NginxUpstreamCRUD(auth).page_crud(
            offset=offset,
            limit=page_size,
            order_by=order,
            search=search_dict,
            out_schema=NginxUpstreamOutSchema,
            preload=["nginx_node"],
        )

    @classmethod
    async def get_upstream_detail_service(cls, auth: AuthSchema, id: int) -> Dict:
        upstream = await NginxUpstreamCRUD(auth).get_by_id_crud(id=id, preload=["nginx_node"])
        if not upstream:
            raise CustomException(msg="Nginx Upstream不存在")
        return NginxUpstreamOutSchema.model_validate(upstream).model_dump()

    @classmethod
    async def create_upstream_service(cls, auth: AuthSchema, data: NginxUpstreamCreateSchema) -> Dict:
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"[NginxUpstream] 开始创建upstream: {data.upstream}, nginx_node_id: {data.nginx_node_id}")
        logger.debug(f"[NginxUpstream] 创建数据: {data.model_dump()}")
        
        # 检查upstream名称+nginx_node_id组合是否已存在
        exist = await NginxUpstreamCRUD(auth).get(upstream=data.upstream, nginx_node_id=data.nginx_node_id)
        if exist:
            logger.warning(f"[NginxUpstream] upstream已存在: upstream={data.upstream}, nginx_node_id={data.nginx_node_id}, exist_id={exist.id}")
            raise CustomException(msg=f"创建失败，该upstream名称在该Nginx节点上已存在（ID: {exist.id}）")

        # 检查nginx节点是否存在
        logger.debug(f"[NginxUpstream] 检查nginx节点: {data.nginx_node_id}")
        nginx_node = await ServerCRUD(auth).get_by_id_crud(id=data.nginx_node_id, preload=["services"])
        if not nginx_node:
            logger.error(f"[NginxUpstream] Nginx节点不存在: {data.nginx_node_id}")
            raise CustomException(msg="创建失败，Nginx节点不存在")

        logger.debug(f"[NginxUpstream] 节点信息: id={nginx_node.id}, ip={nginx_node.ip}, services={len(nginx_node.services) if nginx_node.services else 0}")

        # 检查nginx节点是否配置了nginx服务模块（通过services关联的module_group判断）
        has_nginx_service = False
        if nginx_node.services:
            for service in nginx_node.services:
                if service.module_group and "nginx" in service.module_group.lower():
                    has_nginx_service = True
                    logger.debug(f"[NginxUpstream] 找到nginx服务模块: {service.name}, module_group={service.module_group}")
                    break
        
        if not has_nginx_service:
            logger.warning(f"[NginxUpstream] 节点未配置nginx服务模块: {data.nginx_node_id}")
            raise CustomException(msg="创建失败，该节点未配置nginx服务模块")

        # 转换proxy_targets为JSON字符串
        proxy_targets_json = json.dumps([target.model_dump() for target in data.proxy_targets], ensure_ascii=False)
        logger.debug(f"[NginxUpstream] proxy_targets JSON长度: {len(proxy_targets_json)}")

        # 准备创建数据
        data_dict = data.model_dump(exclude={'proxy_targets'})
        data_dict['proxy_targets'] = proxy_targets_json

        logger.info(f"[NginxUpstream] 准备创建upstream记录: upstream={data.upstream}, nginx_node_id={data.nginx_node_id}")
        upstream = await NginxUpstreamCRUD(auth).create(data=data_dict)
        logger.info(f"[NginxUpstream] upstream创建成功: id={upstream.id}, upstream={upstream.upstream}, nginx_node_id={upstream.nginx_node_id}")
        
        return NginxUpstreamOutSchema.model_validate(upstream).model_dump()

    @classmethod
    async def update_upstream_service(cls, auth: AuthSchema, id: int, data: NginxUpstreamUpdateSchema) -> Dict:
        upstream = await NginxUpstreamCRUD(auth).get_by_id_crud(id=id)
        if not upstream:
            raise CustomException(msg="更新失败，该upstream不存在")

        # 检查upstream名称是否重复
        if data.upstream and data.upstream != upstream.upstream:
            exist = await NginxUpstreamCRUD(auth).get(upstream=data.upstream)
            if exist:
                raise CustomException(msg="更新失败，该upstream名称已存在")

        # 检查nginx节点是否存在
        if data.nginx_node_id and data.nginx_node_id != upstream.nginx_node_id:
            nginx_node = await ServerCRUD(auth).get_by_id_crud(id=data.nginx_node_id)
            if not nginx_node:
                raise CustomException(msg="更新失败，Nginx节点不存在")

        # 转换proxy_targets为JSON字符串
        proxy_targets_json = json.dumps([target.model_dump() for target in data.proxy_targets], ensure_ascii=False)

        # 准备更新数据
        data_dict = data.model_dump(exclude={'proxy_targets'}, exclude_unset=True)
        data_dict['proxy_targets'] = proxy_targets_json

        upstream = await NginxUpstreamCRUD(auth).update(id=id, data=data_dict)
        return NginxUpstreamOutSchema.model_validate(upstream).model_dump()

    @classmethod
    async def delete_upstream_service(cls, auth: AuthSchema, ids: List[int]) -> None:
        if len(ids) < 1:
            raise CustomException(msg="删除失败，删除对象不能为空")
        await NginxUpstreamCRUD(auth).delete(ids=ids)


    @classmethod
    async def sync_upstream_service(cls, auth: AuthSchema, upstream_ids: List[int]) -> Dict:
        """同步upstream配置到nginx节点（支持多个节点）"""
        import logging
        logger = logging.getLogger(__name__)
        
        if not upstream_ids:
            raise CustomException(msg="同步失败，upstream ID列表不能为空")

        logger.info(f"[NginxUpstream] 开始同步upstream: {upstream_ids}")
        
        # 获取所有upstream信息
        upstreams = []
        for upstream_id in upstream_ids:
            upstream = await NginxUpstreamCRUD(auth).get_by_id_crud(id=upstream_id, preload=["nginx_node"])
            if not upstream:
                logger.error(f"[NginxUpstream] upstream不存在: {upstream_id}")
                raise CustomException(msg=f"同步失败，upstream ID {upstream_id} 不存在")
            upstreams.append(upstream)
            logger.debug(f"[NginxUpstream] 获取到upstream: id={upstream.id}, name={upstream.upstream}, nginx_node_id={upstream.nginx_node_id}")

        # 按nginx节点分组
        node_upstreams: Dict[int, List] = {}
        for upstream in upstreams:
            node_id = upstream.nginx_node_id
            if node_id not in node_upstreams:
                node_upstreams[node_id] = []
            node_upstreams[node_id].append(upstream)

        logger.info(f"[NginxUpstream] 按节点分组完成: {len(node_upstreams)} 个节点")

        # 构建任务元数据（每个upstream+node组合生成一个operator_meta）
        operator_metas = []
        for node_id, node_upstream_list in node_upstreams.items():
            # 获取nginx节点信息
            nginx_node = await ServerCRUD(auth).get_by_id_crud(id=node_id)
            if not nginx_node:
                logger.warning(f"[NginxUpstream] nginx节点不存在: {node_id}")
                continue

            logger.info(f"[NginxUpstream] 处理节点: id={node_id}, ip={nginx_node.ip}, upstream数量={len(node_upstream_list)}")

            # 为每个upstream生成配置
            for upstream in node_upstream_list:
                # 解析proxy_targets
                proxy_targets = json.loads(upstream.proxy_targets) if isinstance(upstream.proxy_targets, str) else upstream.proxy_targets

                # 准备模板变量
                template_vars = {
                    "service_name": upstream.upstream.replace("_upstream", "").replace("-upstream", ""),
                    "hosts": proxy_targets,
                }

                operator_meta = {
                    "nginx_node_id": node_id,
                    "nginx_node_ip": nginx_node.ip,
                    "upstream_id": upstream.id,
                    "upstream_name": upstream.upstream,
                    "upstream_template": upstream.upstream_template,
                    "template_vars": template_vars,
                }
                
                operator_metas.append(operator_meta)
                logger.debug(f"[NginxUpstream] 添加operator_meta: upstream={upstream.upstream}, node={nginx_node.ip}")

        logger.info(f"[NginxUpstream] 生成operator_metas数量: {len(operator_metas)}")
        
        if not operator_metas:
            raise CustomException(msg="同步失败，没有可用的nginx节点")

        # 调用统一任务执行接口
        from ..task.service import TaskService
        result = await TaskService.execute_task_service(
            auth=auth,
            task_type="nginx_upstream_sync",
            operator_type="sync",
            operator_metas=operator_metas,
        )

        logger.info(f"[NginxUpstream] 同步任务创建成功")
        return result

    @classmethod
    async def preview_template_service(cls, data: PreviewTemplateSchema) -> Dict:
        """预览模板渲染结果"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.debug(f"[NginxUpstream] 预览模板: upstream={data.upstream}")
        
        try:
            # 准备模板变量
            template_vars = {
                "service_name": data.upstream.replace("_upstream", "").replace("-upstream", ""),
                "hosts": [target.model_dump() for target in data.proxy_targets],
            }
            
            logger.debug(f"[NginxUpstream] 模板变量: {template_vars}")
            
            # 渲染模板
            template = Template(data.upstream_template)
            rendered_content = template.render(**template_vars)
            
            logger.debug(f"[NginxUpstream] 渲染结果: {rendered_content}")
            
            return {
                "rendered_content": rendered_content,
                "template_vars": template_vars,
            }
        except TemplateError as e:
            logger.error(f"[NginxUpstream] 模板渲染错误: {str(e)}")
            raise CustomException(msg=f"模板渲染失败: {str(e)}")
        except Exception as e:
            logger.error(f"[NginxUpstream] 预览模板失败: {str(e)}")
            raise CustomException(msg=f"预览模板失败: {str(e)}")


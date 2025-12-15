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
        # 移除不支持的查询字段，防止报错
        if "nginx_node_id" in search_dict:
            # TODO: 支持按关联节点过滤
            search_dict.pop("nginx_node_id")
            
        order = order_by or [{"created_at": "desc"}]
        return await NginxUpstreamCRUD(auth).page_crud(
            offset=offset,
            limit=page_size,
            order_by=order,
            search=search_dict,
            out_schema=NginxUpstreamOutSchema,
            preload=["nginx_nodes"],
        )

    @classmethod
    async def get_upstream_detail_service(cls, auth: AuthSchema, id: int) -> Dict:
        upstream = await NginxUpstreamCRUD(auth).get_by_id_crud(id=id, preload=["nginx_nodes"])
        if not upstream:
            raise CustomException(msg="Nginx Upstream不存在")
        return NginxUpstreamOutSchema.model_validate(upstream).model_dump()

    @classmethod
    async def create_upstream_service(cls, auth: AuthSchema, data: NginxUpstreamCreateSchema) -> Dict:
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"[NginxUpstream] ========== 开始创建upstream ==========")
        logger.info(f"[NginxUpstream] upstream名称: {data.upstream}")
        logger.info(f"[NginxUpstream] nginx_node_ids: {data.nginx_node_ids}")
        logger.debug(f"[NginxUpstream] 完整请求数据: {data.model_dump()}")
        
        # 检查upstream名称是否已存在
        logger.debug(f"[NginxUpstream] 检查upstream名称是否已存在: {data.upstream}")
        exist = await NginxUpstreamCRUD(auth).get(upstream=data.upstream)
        if exist:
            logger.warning(f"[NginxUpstream] upstream名称已存在: {data.upstream}, exist_id={exist.id}")
            raise CustomException(msg=f"创建失败，upstream名称 '{data.upstream}' 已存在")

        # 检查nginx节点是否存在
        node_ids = list(set(data.nginx_node_ids))
        logger.debug(f"[NginxUpstream] 检查nginx节点: {node_ids}")
        nodes = await ServerCRUD(auth).get_list_crud(search={"id": ("in", node_ids)}, preload=["services"])
        logger.debug(f"[NginxUpstream] 找到的节点数量: {len(nodes)}, 期望数量: {len(node_ids)}")
        
        if len(nodes) != len(node_ids):
             found_ids = [n.id for n in nodes]
             missing_ids = set(node_ids) - set(found_ids)
             logger.error(f"[NginxUpstream] 部分节点不存在: 期望={node_ids}, 找到={found_ids}, 缺失={missing_ids}")
             raise CustomException(msg=f"创建失败，部分Nginx节点不存在: {missing_ids}")

        # 检查nginx节点是否配置了nginx服务模块
        logger.debug(f"[NginxUpstream] 检查节点nginx服务模块配置")
        for node in nodes:
            has_nginx_service = False
            if node.services:
                for service in node.services:
                    if service.module_group and "nginx" in service.module_group.lower():
                        has_nginx_service = True
                        logger.debug(f"[NginxUpstream] 节点 {node.ip} (ID:{node.id}) 已配置nginx服务: {service.name}")
                        break
            if not has_nginx_service:
                logger.error(f"[NginxUpstream] 节点 {node.ip} (ID:{node.id}) 未配置nginx服务模块")
                raise CustomException(msg=f"创建失败，节点 {node.ip} (ID:{node.id}) 未配置nginx服务模块")

        # 转换proxy_targets为JSON字符串
        logger.debug(f"[NginxUpstream] 转换proxy_targets为JSON")
        proxy_targets_json = json.dumps([target.model_dump() for target in data.proxy_targets], ensure_ascii=False)
        logger.debug(f"[NginxUpstream] proxy_targets JSON长度: {len(proxy_targets_json)}")

        # 准备创建数据
        logger.debug(f"[NginxUpstream] 准备创建数据字典")
        data_dict = data.model_dump(exclude={'proxy_targets', 'nginx_node_ids'})
        data_dict['proxy_targets'] = proxy_targets_json
        data_dict['nginx_nodes'] = nodes
        
        # 记录准备创建的数据（排除敏感信息）
        logger.debug(f"[NginxUpstream] 创建数据字典内容:")
        logger.debug(f"  - upstream: {data_dict.get('upstream')}")
        logger.debug(f"  - proxy_targets长度: {len(data_dict.get('proxy_targets', ''))}")
        logger.debug(f"  - upstream_template: {data_dict.get('upstream_template', '')[:50]}...")
        logger.debug(f"  - description: {data_dict.get('description', '')}")
        logger.debug(f"  - nginx_nodes数量: {len(data_dict.get('nginx_nodes', []))}")
        logger.debug(f"  - nginx_nodes IDs: {[n.id for n in data_dict.get('nginx_nodes', [])]}")
        logger.debug(f"  - data_dict keys: {list(data_dict.keys())}")
        logger.debug(f"  - 是否包含nginx_node_id: {'nginx_node_id' in data_dict}")
        logger.debug(f"  - 是否包含nginx_node_ids: {'nginx_node_ids' in data_dict}")

        logger.info(f"[NginxUpstream] 准备创建upstream记录: upstream={data.upstream}, 关联节点数={len(nodes)}")
        try:
            upstream = await NginxUpstreamCRUD(auth).create(data=data_dict)
            logger.info(f"[NginxUpstream] upstream创建成功: id={upstream.id}, upstream={upstream.upstream}")
            logger.debug(f"[NginxUpstream] 创建的upstream对象: id={upstream.id}, upstream={upstream.upstream}")
        except Exception as e:
            logger.error(f"[NginxUpstream] 创建失败，异常类型: {type(e).__name__}")
            logger.error(f"[NginxUpstream] 异常信息: {str(e)}")
            logger.error(f"[NginxUpstream] 创建数据字典: {data_dict}")
            # 检查是否是数据库结构问题
            if "nginx_node_id" in str(e) or "doesn't have a default value" in str(e):
                logger.error(f"[NginxUpstream] ========== 数据库结构错误 ==========")
                logger.error(f"[NginxUpstream] 错误提示: 数据库表 operations_nginx_upstream 仍然包含 nginx_node_id 字段")
                logger.error(f"[NginxUpstream] 解决方案: 请执行数据库迁移脚本: backend/sql/mysql/alter_nginx_upstream_to_many_to_many.sql")
                raise CustomException(
                    msg="创建失败：数据库表结构未更新。请执行数据库迁移脚本：backend/sql/mysql/alter_nginx_upstream_to_many_to_many.sql"
                )
            raise
        
        logger.info(f"[NginxUpstream] ========== 创建upstream完成 ==========")
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

        # 检查nginx节点
        if data.nginx_node_ids:
             node_ids = list(set(data.nginx_node_ids))
             nodes = await ServerCRUD(auth).get_list_crud(search={"id": ("in", node_ids)})
             if len(nodes) != len(node_ids):
                 raise CustomException(msg="更新失败，部分Nginx节点不存在")

        # 转换proxy_targets为JSON字符串
        proxy_targets_json = json.dumps([target.model_dump() for target in data.proxy_targets], ensure_ascii=False)

        # 准备更新数据
        data_dict = data.model_dump(exclude={'proxy_targets', 'nginx_node_ids'}, exclude_unset=True)
        data_dict['proxy_targets'] = proxy_targets_json
        if data.nginx_node_ids:
             data_dict['nginx_nodes'] = nodes

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
            upstream = await NginxUpstreamCRUD(auth).get_by_id_crud(id=upstream_id, preload=["nginx_nodes"])
            if not upstream:
                logger.error(f"[NginxUpstream] upstream不存在: {upstream_id}")
                raise CustomException(msg=f"同步失败，upstream ID {upstream_id} 不存在")
            upstreams.append(upstream)
            logger.debug(f"[NginxUpstream] 获取到upstream: id={upstream.id}, name={upstream.upstream}")

        # 按upstream分组，同一个upstream的所有节点合并处理
        # 构建任务元数据（每个upstream生成一个operator_meta，包含所有节点）
        operator_metas = []
        for upstream in upstreams:
            # 遍历该upstream关联的所有节点
            if not upstream.nginx_nodes:
                logger.warning(f"[NginxUpstream] upstream {upstream.upstream} 没有关联的nginx节点")
                continue
            
            # 解析proxy_targets（同一个upstream的所有节点使用相同的配置）
            proxy_targets = json.loads(upstream.proxy_targets) if isinstance(upstream.proxy_targets, str) else upstream.proxy_targets

            # 准备模板变量（同一个upstream的所有节点使用相同的模板变量）
            template_vars = {
                "service_name": upstream.upstream.replace("_upstream", "").replace("-upstream", ""),
                "hosts": proxy_targets,
            }

            logger.info(f"[NginxUpstream] 处理upstream: id={upstream.id}, name={upstream.upstream}, 节点数量={len(upstream.nginx_nodes)}")

            # 收集该upstream的所有节点信息
            nginx_node_ips = []
            for node in upstream.nginx_nodes:
                node_id = node.id
                # 获取nginx节点信息
                nginx_node = await ServerCRUD(auth).get_by_id_crud(id=node_id)
                if not nginx_node:
                    logger.warning(f"[NginxUpstream] nginx节点不存在: {node_id}")
                    continue

                nginx_node_ips.append({
                    "nginx_node_id": node_id,
                    "nginx_node_ip": nginx_node.ip,
                    "node_port": nginx_node.port or 22,
                })
                logger.debug(f"[NginxUpstream] 添加节点: upstream={upstream.upstream}, node={nginx_node.ip}")

            if not nginx_node_ips:
                logger.warning(f"[NginxUpstream] upstream {upstream.upstream} 没有有效的nginx节点")
                continue

            # 同一个upstream的所有节点合并到一个operator_meta中
            operator_meta = {
                "upstream_id": upstream.id,
                "upstream_name": upstream.upstream,
                "upstream_template": upstream.upstream_template,
                "template_vars": template_vars,
                "nginx_node_ips": nginx_node_ips,  # 使用数组存储多个节点
            }
            
            operator_metas.append(operator_meta)
            logger.info(f"[NginxUpstream] 添加operator_meta: upstream={upstream.upstream}, 节点数={len(nginx_node_ips)}")

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


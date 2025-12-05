# -*- coding: utf-8 -*-
"""
Nginx Upstream领域 Schema 定义
"""

from typing import Optional, List, Dict, Any, TYPE_CHECKING
import json

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.base_schema import BaseSchema

if TYPE_CHECKING:
    from ..server.schema import NodeOutSchema


class ProxyTargetSchema(BaseModel):
    """代理目标模型"""
    ip: str = Field(..., description="IP地址")
    port: int = Field(..., ge=1, le=65535, description="端口号")
    service_id: Optional[int] = Field(default=None, description="关联的服务模块ID（可选）")
    status: Optional[str] = Field(default="up", description="状态（up: 启用, down: 禁用）")
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, value: Optional[str]) -> str:
        """验证status字段"""
        if value is None:
            return "up"
        if value not in ["up", "down"]:
            raise ValueError("status必须是'up'或'down'")
        return value


class NginxUpstreamCreateSchema(BaseModel):
    """Nginx Upstream创建模型"""
    upstream: str = Field(..., max_length=100, description="upstream名称")
    proxy_targets: List[ProxyTargetSchema] = Field(..., min_length=1, description="代理目标列表")
    nginx_node_ids: List[int] = Field(..., min_length=1, description="Nginx节点ID列表")
    upstream_template: Optional[str] = Field(default=None, description="upstream模板（Jinja2格式）")
    description: Optional[str] = Field(default=None, max_length=255, description="描述")

    @field_validator("upstream")
    @classmethod
    def validate_upstream(cls, value: str) -> str:
        if not value or len(value.strip()) == 0:
            raise ValueError("upstream名称不能为空")
        import re
        if not re.match(r"^[A-Za-z][A-Za-z0-9_-]*$", value):
            raise ValueError("upstream名称必须以字母开头，且仅包含字母/数字/下划线/横线")
        return value.strip()

    @model_validator(mode="before")
    @classmethod
    def set_default_template(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """如果没有提供模板，设置默认模板"""
        if isinstance(values, dict):
            upstream_template = values.get("upstream_template")
            if not upstream_template or (isinstance(upstream_template, str) and upstream_template.strip() == ""):
                # 默认模板（支持status字段，down状态会添加down标记）
                values["upstream_template"] = """upstream {{ service_name }}_upstream {
{% for host in hosts %}
    server {{ host.ip }}:{{ host.port }}{% if host.status == 'down' %} down{% endif %};
{% endfor %}
}"""
        return values


class NginxUpstreamUpdateSchema(NginxUpstreamCreateSchema):
    """Nginx Upstream更新模型"""
    ...


class NginxUpstreamOutSchema(NginxUpstreamCreateSchema, BaseSchema):
    """Nginx Upstream响应模型"""
    model_config = {"from_attributes": True}

    nginx_nodes: Optional[List["NodeOutSchema"]] = Field(default=None, description="Nginx节点列表")
    # 覆盖 CreateSchema 中的 nginx_node_ids，使其在 OutSchema 中可选且允许空列表
    nginx_node_ids: Optional[List[int]] = Field(default=None, description="Nginx节点ID列表")

    @model_validator(mode="before")
    @classmethod
    def parse_proxy_targets(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """解析proxy_targets字段（从JSON字符串转换为列表）"""
        if values is None:
            return values

        # 如果是ORM对象，转换为字典
        if not isinstance(values, dict):
            obj = values
            attr_names = [
                "id", "upstream", "proxy_targets", "upstream_template",
                "description", "created_at", "updated_at"
            ]
            values = {name: getattr(obj, name, None) for name in attr_names}
            # 获取关联的nginx_nodes
            if hasattr(obj, "nginx_nodes"):
                from ..server.schema import NodeOutSchema
                nginx_nodes = getattr(obj, "nginx_nodes", None)
                values["nginx_nodes"] = [NodeOutSchema.model_validate(node).model_dump() for node in nginx_nodes] if nginx_nodes else []
                # 填充 nginx_node_ids 以匹配 CreateSchema
                values["nginx_node_ids"] = [node.id for node in nginx_nodes] if nginx_nodes else None
            else:
                values["nginx_node_ids"] = None

        # 解析 JSON 格式的 proxy_targets 字段
        proxy_targets = values.get("proxy_targets")
        if isinstance(proxy_targets, str) and proxy_targets:
            try:
                values["proxy_targets"] = json.loads(proxy_targets)
            except json.JSONDecodeError:
                values["proxy_targets"] = []
        elif proxy_targets is None:
            values["proxy_targets"] = []

        return values


from ..server.schema import NodeOutSchema  # noqa: E402

NginxUpstreamOutSchema.model_rebuild()


class SyncUpstreamSchema(BaseModel):
    """同步Upstream请求模型"""
    upstream_ids: List[int] = Field(..., min_length=1, description="Upstream ID列表")


class PreviewTemplateSchema(BaseModel):
    """预览模板请求模型"""
    upstream_template: str = Field(..., description="Upstream模板（Jinja2格式）")
    upstream: str = Field(..., description="upstream名称")
    proxy_targets: List[ProxyTargetSchema] = Field(..., min_length=1, description="代理目标列表")


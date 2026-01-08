# -*- coding: utf-8 -*-
"""
运维管理领域模型
"""

from typing import Optional, List
from sqlalchemy import Boolean, String, Integer, ForeignKey, Text, Table, Column, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.core.base_model import CreatorMixin

# 节点-服务模块关联表（多对多）
node_service_association = Table(
    'operations_node_service',
    CreatorMixin.metadata,
    Column('node_id', Integer, ForeignKey('operations_node.id', ondelete='CASCADE'), primary_key=True),
    Column('service_id', Integer, ForeignKey('operations_service.id', ondelete='CASCADE'), primary_key=True),
    extend_existing=True,
)

# Nginx Upstream与节点关联表（多对多）
nginx_upstream_node_association = Table(
    'operations_nginx_upstream_node',
    CreatorMixin.metadata,
    Column('nginx_upstream_id', Integer, ForeignKey('operations_nginx_upstream.id', ondelete='CASCADE'), primary_key=True),
    Column('node_id', Integer, ForeignKey('operations_node.id', ondelete='CASCADE'), primary_key=True),
    extend_existing=True,
)


class ServiceModel(CreatorMixin):
    """
    服务模块表 - 用于存储服务模块信息
    """
    __tablename__ = "operations_service"
    __table_args__ = (
        UniqueConstraint('project', 'module_group', 'name', name='uq_service_project_group_name'),
        {'comment': '服务模块表'}
    )
    __loader_options__ = ["creator", "nodes"]

    # 基础字段
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="服务模块名称")
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=True, comment="服务模块编码")
    status: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False, comment="是否启用(True:启用 False:禁用)")
    project: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="运维管理项目")
    module_group: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="模块分组")
    current_package_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="当前软件包版本号")
    endpoint_port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="服务端口号(用于Nginx代理)")
    
    # 关联关系（多对多）
    nodes: Mapped[List["NodeModel"]] = relationship(
        secondary=node_service_association,
        back_populates="services",
        lazy="selectin"
    )
    
    # 关联关系（一对多）
    packages: Mapped[List["ServicePackageModel"]] = relationship(
        "ServicePackageModel",
        back_populates="service",
        lazy="selectin",
        cascade="all, delete-orphan"
    )


class ServicePackageModel(CreatorMixin):
    """
    服务软件包表
    """
    __tablename__ = "operations_service_package"
    __table_args__ = ({'comment': '服务软件包表'})
    __loader_options__ = ["creator"]

    service_id: Mapped[int] = mapped_column(Integer, ForeignKey("operations_service.id", ondelete="CASCADE"), nullable=False, index=True, comment="服务模块ID")
    version: Mapped[str] = mapped_column(String(50), nullable=False, comment="版本号")
    package_path: Mapped[str] = mapped_column(String(255), nullable=False, comment="版本包路径")
    md5: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, comment="文件MD5（支持OSS ETag格式）")
    size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="文件大小(字节)")
    
    # 关联
    service: Mapped["ServiceModel"] = relationship("ServiceModel", back_populates="packages", lazy="selectin")


class NodeModel(CreatorMixin):
    """
    节点表 - 用于存储节点IP信息
    """
    __tablename__ = "operations_node"
    __table_args__ = (
        UniqueConstraint('ip', 'port', name='uq_node_ip_port'),
        {'comment': '节点表'}
    )
    __loader_options__ = ["creator", "services"]

    # 基础字段
    service_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("operations_service.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="主服务模块ID（保留用于兼容性）")
    ip: Mapped[str] = mapped_column(String(50), nullable=False, comment="节点IP地址")
    port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=22, comment="端口号")
    status: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False, comment="是否启用(True:启用 False:禁用)")
    project: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="运维管理项目")
    idc: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="机房")
    tags: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="服务器标签")
    operator_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="操作类型(deploy:部署, restart:重启, init:初始化 等)")
    
    # 关联关系（多对多）
    services: Mapped[List["ServiceModel"]] = relationship(
        secondary=node_service_association,
        back_populates="nodes",
        lazy="selectin"
    )
    
    # 保留旧的单一关系用于向后兼容
    service: Mapped[Optional["ServiceModel"]] = relationship(foreign_keys=[service_id], lazy="selectin")


class TaskModel(CreatorMixin):
    """
    任务表 - 用于存储任务进度信息（批次任务）
    """
    __tablename__ = "operations_task"
    __table_args__ = ({'comment': '任务表'})
    __loader_options__ = ["creator"]

    # 基础字段
    task_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="任务类型(deploy:部署, restart:重启)")
    task_status: Mapped[str] = mapped_column(String(20), nullable=False, default="running", comment="任务状态(running:执行中, success:完成, failed:失败, partial_success:部分成功)")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="任务进度百分比")
    log_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="任务日志文件路径")
    params: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="构建参数JSON")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="错误信息")
    
    # 通用字段（用于筛选）
    project: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="运维管理项目")
    idc: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="机房")
    module_group: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="模块分组")


class TaskLogModel(CreatorMixin):
    """
    任务日志表 - 用于存储任务日志（支持分布式）
    使用 seq 全局序号避免重复/缺失日志
    """
    __tablename__ = "operations_task_log"
    __table_args__ = ({'comment': '任务日志表'})
    __loader_options__ = ["creator"]

    # 关联字段
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("operations_task.id", ondelete="CASCADE"), nullable=False, index=True, comment="任务ID")
    
    # 日志字段
    seq: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="全局序号，用于避免重复/缺失日志")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="日志内容（支持多行，每1000行一条记录）")
    line_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="本条记录包含的行数")
    timestamp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True, comment="Unix时间戳（秒）")


class NginxUpstreamModel(CreatorMixin):
    """
    Nginx Upstream表 - 用于存储Nginx Upstream配置
    """
    __tablename__ = "operations_nginx_upstream"
    __table_args__ = (
        UniqueConstraint('upstream', name='uq_nginx_upstream_name'),
        {'comment': 'Nginx Upstream表'}
    )
    __loader_options__ = ["creator", "nginx_nodes"]

    # 基础字段
    upstream: Mapped[str] = mapped_column(String(100), nullable=False, comment="upstream名称")
    proxy_targets: Mapped[str] = mapped_column(Text, nullable=False, comment="代理目标列表(JSON格式)")
    upstream_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="upstream模板（Jinja2格式）")
    
    # 关联关系
    nginx_nodes: Mapped[List["NodeModel"]] = relationship(
        "NodeModel",
        secondary=nginx_upstream_node_association,
        lazy="selectin"
    )


class CeleryWorkerModel(CreatorMixin):
    """
    Celery Worker节点表 - 用于存储Celery执行队列节点信息
    """
    __tablename__ = "operations_celery_worker"
    __table_args__ = (
        UniqueConstraint('queue_code', 'node_ip', name='uq_celery_worker_queue_ip'),
        {'comment': 'Celery Worker节点表'}
    )
    __loader_options__ = ["creator"]

    # 基础字段
    queue_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="执行队列名称")
    queue_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="执行队列编码")
    node_ip: Mapped[str] = mapped_column(String(50), nullable=False, comment="节点IP")
    node_hostname: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="节点主机名")
    status: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False, comment="是否在线(True:在线 False:离线)")
    last_heartbeat: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="最后心跳时间戳")


class ScriptModel(CreatorMixin):
    """
    脚本管理表 - 用于存储通用脚本信息
    """
    __tablename__ = "operations_script"
    __table_args__ = (
        UniqueConstraint('name', name='uq_script_name'),
        {'comment': '脚本管理表'}
    )
    __loader_options__ = ["creator"]

    # 基础字段
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="脚本名称")
    script_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="脚本类型(python/shell)")
    content_type: Mapped[str] = mapped_column(String(20), nullable=False, default="text", comment="脚本内容类型(text/local_path)")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="脚本内容或本地路径")
    default_timeout: Mapped[int] = mapped_column(Integer, nullable=False, default=3600, comment="默认超时时间(秒)")
    queue_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="执行队列编码")
    params_schema: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="脚本参数JSON Schema")
    status: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False, comment="是否启用(True:启用 False:禁用)")

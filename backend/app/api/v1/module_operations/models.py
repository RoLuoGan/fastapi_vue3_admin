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
    
    # 关联关系（多对多）
    nodes: Mapped[List["NodeModel"]] = relationship(
        secondary=node_service_association,
        back_populates="services",
        lazy="selectin"
    )


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
    
    # 统计字段
    total_nodes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="总节点数")
    success_nodes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="成功节点数")
    failed_nodes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="失败节点数")
    
    # 保留字段用于向后兼容和统计
    service_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("operations_service.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="主服务模块ID（保留）")
    node_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("operations_node.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="主节点ID（保留）")
    ip: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="主IP地址（保留）")
    project: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="运维管理项目")
    idc: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="机房")
    module_group: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="模块分组")

    # 关联关系
    node: Mapped[Optional["NodeModel"]] = relationship(lazy="selectin")
    service: Mapped[Optional["ServiceModel"]] = relationship(lazy="selectin")


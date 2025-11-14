# -*- coding: utf-8 -*-
"""
运维管理领域模型
"""

from typing import Optional, List
from sqlalchemy import Boolean, String, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.core.base_model import CreatorMixin


class ServiceModel(CreatorMixin):
    """
    服务模块表 - 用于存储服务模块信息
    """
    __tablename__ = "operations_service"
    __table_args__ = ({'comment': '服务模块表'})
    __loader_options__ = ["creator", "nodes"]

    # 基础字段
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, comment="服务模块名称")
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=True, comment="服务模块编码")
    status: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False, comment="是否启用(True:启用 False:禁用)")
    project: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="运维管理项目")
    module_group: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="模块分组")
    
    # 关联关系
    nodes: Mapped[List["NodeModel"]] = relationship(back_populates="service", lazy="selectin", cascade="all, delete-orphan")


class NodeModel(CreatorMixin):
    """
    节点表 - 用于存储节点IP信息
    """
    __tablename__ = "operations_node"
    __table_args__ = ({'comment': '节点表'})
    __loader_options__ = ["creator", "service"]

    # 基础字段
    service_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("operations_service.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="服务模块ID")
    ip: Mapped[str] = mapped_column(String(50), nullable=False, comment="节点IP地址")
    port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=22, comment="端口号")
    status: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False, comment="是否启用(True:启用 False:禁用)")
    project: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="运维管理项目")
    idc: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="机房")
    tags: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="服务器标签")
    
    # 关联关系
    service: Mapped[Optional["ServiceModel"]] = relationship(back_populates="nodes", lazy="selectin")


class TaskModel(CreatorMixin):
    """
    任务表 - 用于存储任务进度信息
    """
    __tablename__ = "operations_task"
    __table_args__ = ({'comment': '任务表'})
    __loader_options__ = ["creator", "node", "service"]

    # 基础字段
    service_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("operations_service.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="服务模块ID")
    node_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("operations_node.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="节点ID")
    ip: Mapped[str] = mapped_column(String(50), nullable=False, comment="任务IP地址")
    task_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="任务类型(deploy:部署, restart:重启)")
    task_status: Mapped[str] = mapped_column(String(20), nullable=False, default="running", comment="任务状态(running:执行中, success:完成, failed:失败)")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="任务进度百分比")
    log_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="任务日志文件路径")
    params: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="构建参数JSON")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="错误信息")
    project: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="运维管理项目")
    idc: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="机房")
    module_group: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="模块分组")

    # 关联关系
    node: Mapped[Optional["NodeModel"]] = relationship(lazy="selectin")
    service: Mapped[Optional["ServiceModel"]] = relationship(lazy="selectin")


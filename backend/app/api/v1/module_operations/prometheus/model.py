# -*- coding: utf-8 -*-
"""
Prometheus 配置模型（运维模块）
"""

from typing import List, Optional
from sqlalchemy import String, Boolean, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import CreatorMixin


class PrometheusJobModel(CreatorMixin):
    """
    Prometheus Job 配置
    """

    __tablename__ = "monitor_prometheus_job"
    __table_args__ = (
        UniqueConstraint("job_name", name="uq_prometheus_job_name"),
        {"comment": "Prometheus Job 配置"},
    )
    __loader_options__ = ["creator", "endpoints", "labels"]

    job_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="Job 名称")
    description: Mapped[Optional[str]] = mapped_column(String(255), comment="描述")
    is_enabled: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False, comment="是否启用")

    endpoints: Mapped[List["PrometheusEndpointModel"]] = relationship(
        "PrometheusEndpointModel",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PrometheusEndpointModel(CreatorMixin):
    """
    Prometheus Endpoint 配置
    """

    __tablename__ = "monitor_prometheus_endpoint"
    __table_args__ = (
        UniqueConstraint("job_id", "endpoint", name="uq_prometheus_job_endpoint"),
        {"comment": "Prometheus Endpoint 配置"},
    )
    __loader_options__ = ["creator", "job", "labels"]

    job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("monitor_prometheus_job.id", ondelete="CASCADE"), nullable=False, index=True
    )
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False, comment="Endpoint/Target，如 10.0.0.1:9100")
    is_enabled: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False, comment="是否启用")
    scheme: Mapped[str] = mapped_column(String(10), default="http", nullable=False, comment="协议")

    job: Mapped["PrometheusJobModel"] = relationship(back_populates="endpoints", lazy="selectin")
    labels: Mapped[List["PrometheusLabelModel"]] = relationship(
        "PrometheusLabelModel",
        back_populates="endpoint",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PrometheusLabelModel(CreatorMixin):
    """
    Prometheus Label 配置
    """

    __tablename__ = "monitor_prometheus_label"
    __table_args__ = (
        UniqueConstraint("endpoint_id", "label_key", name="uq_prometheus_endpoint_label"),
        {"comment": "Prometheus Label 配置"},
    )
    __loader_options__ = ["creator", "endpoint"]

    endpoint_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("monitor_prometheus_endpoint.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label_key: Mapped[str] = mapped_column(String(64), nullable=False, comment="标签键")
    label_value: Mapped[str] = mapped_column(String(255), nullable=False, comment="标签值")

    endpoint: Mapped["PrometheusEndpointModel"] = relationship(back_populates="labels", lazy="selectin")



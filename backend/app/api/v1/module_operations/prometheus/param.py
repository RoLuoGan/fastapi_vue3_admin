# -*- coding: utf-8 -*-
"""
Prometheus 查询参数（运维模块）
"""

from typing import Optional
from pydantic import BaseModel, Field


class PrometheusJobQueryParam(BaseModel):
    """Job 查询参数"""

    job_name: Optional[str] = Field(default=None, description="Job 名称")
    is_enabled: Optional[bool] = Field(default=None, description="是否启用")


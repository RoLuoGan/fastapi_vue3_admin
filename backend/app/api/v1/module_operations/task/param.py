# -*- coding: utf-8 -*-
"""
任务查询参数
"""

from typing import Optional
from fastapi import Query

from app.core.validator import DateTimeStr


class TaskQueryParam:
    """任务查询参数"""

    def __init__(
        self,
        task_type: Optional[str] = Query(None, description="任务类型"),
        task_status: Optional[str] = Query(None, description="任务状态"),
        project: Optional[str] = Query(None, description="运维管理项目"),
        idc: Optional[str] = Query(None, description="机房"),
        module_group: Optional[str] = Query(None, description="模块分组"),
        start_time: Optional[DateTimeStr] = Query(None, description="开始时间", example="2025-01-01 00:00:00"),
        end_time: Optional[DateTimeStr] = Query(None, description="结束时间", example="2025-12-31 23:59:59"),
    ) -> None:

        self.task_type = task_type
        self.task_status = task_status
        self.project = project
        self.idc = idc
        self.module_group = module_group

        if start_time and end_time:
            self.created_at = ("between", (start_time, end_time))


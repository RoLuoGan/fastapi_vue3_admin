# -*- coding: utf-8 -*-
"""
服务器（节点）查询参数
"""

from typing import Optional
from fastapi import Query

from app.core.validator import DateTimeStr


class ServerQueryParam:
    """服务器节点查询参数"""

    def __init__(
        self,
        service_id: Optional[int] = Query(None, description="服务模块ID"),
        ip: Optional[str] = Query(None, description="节点IP地址"),
        status: Optional[bool] = Query(None, description="节点状态(True正常 False停用)"),
        project: Optional[str] = Query(None, description="运维管理项目"),
        idc: Optional[str] = Query(None, description="机房"),
        tags: Optional[str] = Query(None, description="服务器标签"),
        start_time: Optional[DateTimeStr] = Query(None, description="开始时间", example="2025-01-01 00:00:00"),
        end_time: Optional[DateTimeStr] = Query(None, description="结束时间", example="2025-12-31 23:59:59"),
    ) -> None:

        self.service_id = service_id
        self.status = status
        self.ip = ("like", ip)
        self.project = project
        self.idc = idc
        self.tags = ("like", tags)

        if start_time and end_time:
            self.created_at = ("between", (start_time, end_time))


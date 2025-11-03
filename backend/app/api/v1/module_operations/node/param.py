# -*- coding: utf-8 -*-
"""
服务节点管理查询参数模块
"""

from typing import Optional
from fastapi import Query

from app.core.validator import DateTimeStr


class ServiceQueryParam:
    """服务模块查询参数"""

    def __init__(
            self,
            name: Optional[str] = Query(None, description="服务模块名称"),
            code: Optional[str] = Query(None, description="服务模块编码"),
            status: Optional[bool] = Query(None, description="服务模块状态(True正常 False停用)"),
            start_time: Optional[DateTimeStr] = Query(None, description="开始时间", example="2025-01-01 00:00:00"),
            end_time: Optional[DateTimeStr] = Query(None, description="结束时间", example="2025-12-31 23:59:59"),
    ) -> None:
        
        # 模糊查询字段
        self.name = ("like", name)
        self.code = ("like", code)

        # 精确查询字段
        self.status = status

        # 时间范围查询
        if start_time and end_time:
            self.created_at = ("between", (start_time, end_time))


class NodeQueryParam:
    """节点查询参数"""

    def __init__(
            self,
            service_id: Optional[int] = Query(None, description="服务模块ID"),
            ip: Optional[str] = Query(None, description="节点IP地址"),
            status: Optional[bool] = Query(None, description="节点状态(True正常 False停用)"),
            start_time: Optional[DateTimeStr] = Query(None, description="开始时间", example="2025-01-01 00:00:00"),
            end_time: Optional[DateTimeStr] = Query(None, description="结束时间", example="2025-12-31 23:59:59"),
    ) -> None:
        
        # 精确查询字段
        self.service_id = service_id
        self.status = status

        # 模糊查询字段
        self.ip = ("like", ip)

        # 时间范围查询
        if start_time and end_time:
            self.created_at = ("between", (start_time, end_time))


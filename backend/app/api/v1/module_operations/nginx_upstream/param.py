# -*- coding: utf-8 -*-
"""
Nginx Upstream查询参数
"""

from typing import Optional
from fastapi import Query

from app.core.validator import DateTimeStr


class NginxUpstreamQueryParam:
    """Nginx Upstream查询参数"""

    def __init__(
        self,
        upstream: Optional[str] = Query(None, description="upstream名称"),
        nginx_node_id: Optional[int] = Query(None, description="Nginx节点ID"),
        start_time: Optional[DateTimeStr] = Query(None, description="开始时间", example="2025-01-01 00:00:00"),
        end_time: Optional[DateTimeStr] = Query(None, description="结束时间", example="2025-12-31 23:59:59"),
    ) -> None:

        # 模糊查询字段
        self.upstream = ("like", upstream)

        # 精确查询字段
        self.nginx_node_id = nginx_node_id

        # 时间范围查询
        if start_time and end_time:
            self.created_at = ("between", (start_time, end_time))


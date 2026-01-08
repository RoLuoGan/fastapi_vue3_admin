# -*- coding: utf-8 -*-
"""
Celery Worker 节点查询参数
"""

from typing import Optional
from fastapi import Query


class CeleryWorkerQueryParam:
    """Celery Worker节点查询参数"""

    def __init__(
        self,
        queue_name: Optional[str] = Query(None, description="执行队列名称"),
        queue_code: Optional[str] = Query(None, description="执行队列编码"),
        node_ip: Optional[str] = Query(None, description="节点IP"),
        status: Optional[bool] = Query(None, description="是否在线"),
    ):
        self.queue_name__contains = queue_name
        self.queue_code = queue_code
        self.node_ip__contains = node_ip
        self.status = status



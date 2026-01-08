# -*- coding: utf-8 -*-
"""
脚本管理查询参数
"""

from typing import Optional
from fastapi import Query


class ScriptQueryParam:
    """脚本查询参数"""

    def __init__(
        self,
        name: Optional[str] = Query(None, description="脚本名称"),
        script_type: Optional[str] = Query(None, description="脚本类型"),
        content_type: Optional[str] = Query(None, description="脚本内容类型"),
        queue_code: Optional[str] = Query(None, description="执行队列编码"),
        status: Optional[bool] = Query(None, description="是否启用"),
    ):
        self.name__contains = name
        self.script_type = script_type
        self.content_type = content_type
        self.queue_code = queue_code
        self.status = status



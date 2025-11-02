# -*- coding: utf-8 -*-

from typing import Optional
from fastapi import Query


class GenTableQueryParam:
    """代码生成业务表查询参数
    - 支持按`table_name`、`table_comment`进行模糊检索（由CRUD层实现like）。
    - 空值将被忽略，不参与过滤。
    """

    def __init__(
        self,
        table_name: Optional[str] = Query(None, description="表名称"),
        table_comment: Optional[str] = Query(None, description="表注释"),
    ) -> None:
        # 模糊查询字段
        self.table_name = table_name
        self.table_comment = table_comment


class GenTableColumnQueryParam:
    """代码生成业务表字段查询参数
    - `column_name`按like规则模糊查询（透传到CRUD层）。
    """

    def __init__(
        self,
        column_name: Optional[str] = Query(None, description="列名称"),
    ) -> None:
        # 模糊查询字段：约定("like", 值)格式，便于CRUD解析
        self.column_name = ("like", column_name)

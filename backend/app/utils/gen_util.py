# -*- coding: utf-8 -*-

import re
from typing import List

from app.common.constant import GenConstant
from app.config.setting import settings
from app.utils.string_util import StringUtil
from app.api.v1.module_generator.gencode.schema import GenTableSchema, GenTableColumnSchema


class GenUtils:
    """代码生成器工具类"""

    @classmethod
    def init_table(cls, gen_table: GenTableSchema) -> None:
        """
        初始化表信息

        参数:
        - gen_table (GenTableSchema): 业务表对象。

        返回:
        - None
        """
        # 只有当字段为None时才设置默认值
        if gen_table.class_name is None:
            gen_table.class_name = cls.convert_class_name(gen_table.table_name or "")
        if gen_table.package_name is None:
            gen_table.package_name = cls.get_package_name(gen_table.table_name or "")
        if gen_table.module_name is None:
            gen_table.module_name = cls.get_module_name(settings.package_name or "")
        if gen_table.business_name is None:
            gen_table.business_name = cls.get_business_name(gen_table.table_name or "")
        if gen_table.function_name is None:
            gen_table.function_name = cls.replace_text(gen_table.table_comment or "")
        if gen_table.function_author is None:
            gen_table.function_author = settings.author

    @classmethod
    def init_column_field(cls, column: GenTableColumnSchema, table: GenTableSchema) -> None:
        """
        初始化列属性字段

        参数:
        - column (GenTableColumnSchema): 业务表字段对象。
        - table (GenTableSchema): 业务表对象。

        返回:
        - None
        """
        data_type = cls.get_db_type(column.column_type or "")
        column_name = column.column_name or ""
        # 只有当table_id为None时才设置
        if column.table_id is None:
            column.table_id = table.table_id
        # 只有当python_field为None时才设置
        if column.python_field is None:
            column.python_field = column_name
        # 只有当python_type为None时才设置默认类型
        if column.python_type is None:
            # 根据数据库类型映射到Python类型（统一使用大写键以兼容MySQL）
            column.python_type = GenConstant.DB_TO_PYTHON.get(data_type.upper(), "Any")
        # 查询类型：优先根据字段语义（如以name结尾走LIKE），否则默认EQ
        if column.query_type is None:
            column.query_type = GenConstant.QUERY_LIKE if column_name.lower().endswith("name") else GenConstant.QUERY_EQ

        # HTML类型：根据数据库类型设置基础控件，再根据字段语义进行覆写
        if column.html_type is None:
            if cls.arrays_contains(GenConstant.COLUMNTYPE_STR, data_type) or cls.arrays_contains(
                GenConstant.COLUMNTYPE_TEXT, data_type
            ):
                # 字符串长度超过500设置为文本域
                column_length = cls.get_column_length(column.column_type or "")
                html_type = (
                    GenConstant.HTML_TEXTAREA
                    if column_length >= 500 or cls.arrays_contains(GenConstant.COLUMNTYPE_TEXT, data_type)
                    else GenConstant.HTML_INPUT
                )
                column.html_type = html_type
            elif cls.arrays_contains(GenConstant.COLUMNTYPE_TIME, data_type):
                column.html_type = GenConstant.HTML_DATETIME
            elif cls.arrays_contains(GenConstant.COLUMNTYPE_NUMBER, data_type):
                column.html_type = GenConstant.HTML_INPUT
            else:
                column.html_type = GenConstant.HTML_INPUT

        # 基于字段命名语义的控件类型覆写（若已设为通用input/textarea则按语义更精确的控件替换）
        # 这些覆写通常比类型映射更贴近业务含义
        if column_name.lower().endswith("status"):
            column.html_type = GenConstant.HTML_RADIO
        elif column_name.lower().endswith("type") or column_name.lower().endswith("sex"):
            column.html_type = GenConstant.HTML_SELECT
        elif column_name.lower().endswith("image"):
            column.html_type = GenConstant.HTML_IMAGE_UPLOAD
        elif column_name.lower().endswith("file"):
            column.html_type = GenConstant.HTML_FILE_UPLOAD
        elif column_name.lower().endswith("content"):
            column.html_type = GenConstant.HTML_EDITOR

        # 只有当is_insert为None时才设置插入字段（默认所有字段都需要插入）
        if column.is_insert is None:
            column.is_insert = GenConstant.REQUIRE

        # 只有当is_edit为None时才设置编辑字段
        if column.is_edit is None and not cls.arrays_contains(GenConstant.COLUMNNAME_NOT_EDIT, column_name) and not column.is_pk == '1':
            column.is_edit = GenConstant.REQUIRE
        # 只有当is_list为None时才设置列表字段
        if column.is_list is None and not cls.arrays_contains(GenConstant.COLUMNNAME_NOT_LIST, column_name) and not column.is_pk == '1':
            column.is_list = GenConstant.REQUIRE
        # 只有当is_query为None时才设置查询字段
        if column.is_query is None and not cls.arrays_contains(GenConstant.COLUMNNAME_NOT_QUERY, column_name) and not column.is_pk == '1':
            column.is_query = GenConstant.REQUIRE

        # 只有当query_type为None时才设置查询字段类型
        if column.query_type is None:
            if column_name.lower().endswith('name'):
                column.query_type = GenConstant.QUERY_LIKE

        # 只有当html_type为None时才设置HTML类型（重复设置）
        if column.html_type is None:
            # 状态字段设置单选框
            if column_name.lower().endswith('status'):
                column.html_type = GenConstant.HTML_RADIO
            # 类型&性别字段设置下拉框
            elif column_name.lower().endswith('type') or column_name.lower().endswith('sex'):
                column.html_type = GenConstant.HTML_SELECT
            # 图片字段设置图片上传控件
            elif column_name.lower().endswith('image'):
                column.html_type = GenConstant.HTML_IMAGE_UPLOAD
            # 文件字段设置文件上传控件
            elif column_name.lower().endswith('file'):
                column.html_type = GenConstant.HTML_FILE_UPLOAD
            # 内容字段设置富文本控件
            elif column_name.lower().endswith('content'):
                column.html_type = GenConstant.HTML_EDITOR
            else:
                column.html_type = GenConstant.HTML_INPUT

    @classmethod
    def arrays_contains(cls, arr: List[str], target_value: str) -> bool:
        """
        校验数组是否包含指定值（忽略大小写）

        参数:
        - arr (List[str]): 数组。
        - target_value (str): 需要校验的值。

        返回:
        - bool: 校验结果。
        """
        if target_value is None:
            return False
        return any(item.lower() == target_value.lower() for item in arr)

    @classmethod
    def get_module_name(cls, package_name: str) -> str:
        """
        获取模块名

        参数:
        - package_name (str): 包名。

        返回:
        - str: 模块名。
        """
        return package_name.split('.')[-1]

    @classmethod
    def get_package_name(cls, table_name: str) -> str:
        """
        获取包名

        参数:
        - table_name (str): 业务表名。

        返回:
        - str: 包名。
        """
        return settings.package_name  # 可配置的包名
        
    @classmethod
    def get_business_name(cls, table_name: str) -> str:
        """
        获取业务名

        参数:
        - table_name (str): 业务表名。

        返回:
        - str: 业务名。
        """
        return table_name.split('_')[-1]

    @classmethod
    def convert_class_name(cls, table_name: str) -> str:
        """
        表名转换成 Python 类名

        参数:
        - table_name (str): 业务表名。

        返回:
        - str: Python 类名。
        """
        auto_remove_pre = settings.auto_remove_pre
        table_prefix = settings.table_prefix
        if auto_remove_pre and table_prefix:
            search_list = table_prefix.split(',')
            table_name = cls.replace_first(table_name, search_list)
        return StringUtil.convert_to_camel_case(table_name)

    @classmethod
    def replace_first(cls, replacement: str, search_list: List[str]) -> str:
        """
        批量替换前缀

        参数:
        - replacement (str): 需要被替换的字符串。
        - search_list (List[str]): 可替换的字符串列表。

        返回:
        - str: 替换后的字符串。
        """
        for search_string in search_list:
            if replacement.startswith(search_string):
                return replacement.replace(search_string, '', 1)
        return replacement

    @classmethod
    def replace_text(cls, text: str) -> str:
        """
        关键字替换

        参数:
        - text (str): 需要被替换的字符串。

        返回:
        - str: 替换后的字符串。
        """
        return re.sub(r'(?:表|测试)', '', text)

    @classmethod
    def get_db_type(cls, column_type: str) -> str:
        """
        获取数据库类型字段

        参数:
        - column_type (str): 字段类型。

        返回:
        - str: 数据库类型。
        """
        if '(' in column_type:
            return column_type.split('(')[0]
        return column_type

    @classmethod
    def get_column_length(cls, column_type: str) -> int:
        """
        获取字段长度

        参数:
        - column_type (str): 字段类型，例如 'varchar(255)' 或 'decimal(10,2)'

        返回:
        - int: 字段长度（优先取第一个长度值，无法解析时返回0）。
        """
        if '(' in column_type and ')' in column_type:
            try:
                inner = column_type.split('(')[1].split(')')[0]
                first = inner.split(',')[0].strip()
                return int(first)
            except Exception:
                return 0
        return 0

    @classmethod
    def split_column_type(cls, column_type: str) -> List[str]:
        """
        拆分列类型

        参数:
        - column_type (str): 字段类型。

        返回:
        - List[str]: 拆分结果。
        """
        if '(' in column_type and ')' in column_type:
            return column_type.split('(')[1].split(')')[0].split(',')
        return []

    @classmethod
    def to_camel_case(cls, text: str) -> str:
        """
        将字符串转换为驼峰命名

        参数:
        - text (str): 需要转换的字符串。

        返回:
        - str: 驼峰命名。
        """
        parts = text.split('_')
        return parts[0] + ''.join(word.capitalize() for word in parts[1:])

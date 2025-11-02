# -*- coding:utf-8 -*-

from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.common.constant import GenConstant
from app.core.base_schema import BaseSchema


class GenTableOptionSchema(BaseModel):
    """代码生成表的附加选项（存入`options`字段的JSON）。
    - parent_menu_id：菜单归属；树模板依赖。
    - tree_*：树形结构必需的编码/父编码/名称字段。
    """

    model_config = ConfigDict(from_attributes=True)

    parent_menu_id: Optional[int] = Field(default=None, description='所属父级分类')
    tree_code: Optional[str] = Field(default=None, description='tree_code')
    tree_name: Optional[str] = Field(default=None, description='tree_name')
    tree_parent_code: Optional[str] = Field(default=None, description='tree_parent_code')


class GenDBTableSchema(BaseModel):
    """数据库中的表信息（跨方言统一结构）。
    - 供“导入表结构”与“同步结构”环节使用。
    """

    model_config = ConfigDict(from_attributes=True)

    database_name: Optional[str] = Field(default=None, description='数据库名称')
    table_name: Optional[str] = Field(default=None, description='表名称')
    table_type: Optional[str] = Field(default=None, description='表类型')
    table_comment: Optional[str] = Field(default=None, description='表描述')


class GenTableBaseSchema(BaseModel):
    """代码生成业务表基础模型（创建/更新共享字段）。
    - 说明：`params`为前端结构体，后端持久化为`options`的JSON。
    - 模板：`tpl_category` 区分 CRUD/Tree/Sub；`tpl_web_type` 区分 element-plus 等。
    """
    model_config = ConfigDict(from_attributes=True)

    table_id: Optional[int] =  Field(default=None, description='编号')
    table_name: Optional[str] = Field(default=None, description='表名称')
    table_comment: Optional[str] = Field(default=None, description='表描述')
    sub_table_name: Optional[str] = Field(default=None, description='关联子表的表名')
    sub_table_fk_name: Optional[str] = Field(default=None, description='子表关联的外键名')
    class_name: Optional[str] = Field(default=None, description='实体类名称')
    tpl_category: Optional[str] = Field(default=None, description='使用的模板（crud单表操作 tree树表操作）')
    tpl_web_type: Optional[str] = Field(default=None, description='前端模板类型（element-ui模版 element-plus模版）')
    package_name: Optional[str] = Field(default=None, description='生成包路径')
    module_name: Optional[str] = Field(default=None, description='生成模块名')
    business_name: Optional[str] = Field(default=None, description='生成业务名')
    function_name: Optional[str] = Field(default=None, description='生成功能名')
    function_author: Optional[str] = Field(default=None, description='生成功能作者')
    gen_type: Optional[Literal['0', '1']] = Field(default=None, description='生成代码方式（0zip压缩包 1自定义路径）')
    gen_path: Optional[str] = Field(default=None, description='生成路径（不填默认项目路径）')
    options: Optional[str] = Field(default=None, description='其它生成选项')
    description: Optional[str] = Field(default=None, description='功能描述')

    params: Optional[GenTableOptionSchema] = Field(default=None, description='前端传递过来的表附加信息，转换成json字符串后放到options')


class GenTableSchema(GenTableBaseSchema):
    """代码生成业务表更新模型（扩展聚合字段）。
    - 聚合：`columns`字段包含字段列表；`pk_column`主键字段；子表结构`sub_table`。
    - 便捷：`sub/tree/crud`基于`tpl_category`自动推导布尔标记。
    """

    pk_column: Optional['GenTableColumnOutSchema'] = Field(default=None, description='主键信息')
    sub_table: Optional['GenTableSchema'] = Field(default=None, description='子表信息')
    columns: Optional[List['GenTableColumnOutSchema']] = Field(default=None, description='表列信息')
    tree_code: Optional[str] = Field(default=None, description='树编码字段tree_code')
    tree_parent_code: Optional[str] = Field(default=None, description='树父编码字段')
    tree_name: Optional[str] = Field(default=None, description='树名称字段ree_name')
    parent_menu_id: Optional[int] = Field(default=None, description='上级菜单ID字段')
    parent_menu_name: Optional[str] = Field(default=None, description='上级菜单名称字段')
    sub: Optional[bool] = Field(default=None, description='是否为子表')
    tree: Optional[bool] = Field(default=None, description='是否为树表')
    crud: Optional[bool] = Field(default=None, description='是否为单表')

    @model_validator(mode='after')
    def check_some_is(self) -> 'GenTableSchema':
        self.sub = True if self.tpl_category and self.tpl_category == GenConstant.TPL_SUB else False
        self.tree = True if self.tpl_category and self.tpl_category == GenConstant.TPL_TREE else False
        self.crud = True if self.tpl_category and self.tpl_category == GenConstant.TPL_CRUD else False
        return self


class GenTableOutSchema(GenTableSchema, BaseSchema):
    """业务表输出模型（面向控制器/前端）。
    - 清洗：统一处理None值，保证`columns`为列表；文本字段为空字符串。
    - 兼容：既支持传入ORM对象，也支持字典输入。
    """
    model_config = ConfigDict(from_attributes=True)
    
    # 添加数据验证和转换的root_validator
    @model_validator(mode='before')
    def handle_null_values(cls, values):
        """将关键字段的None转换为安全默认值，避免前端渲染异常。"""
        # 处理None值，转换为空字符串或适当的默认值
        # 检查values是否为对象而非字典
        if hasattr(values, '__dict__'):
            # 如果是对象，获取其字典表示
            values_dict = values.__dict__
            for key in ['table_name', 'table_comment', 'class_name', 'columns']:
                if key in values_dict and values_dict[key] is None:
                    if key != 'columns':
                        setattr(values, key, '')
                    else:
                        setattr(values, key, [])
            return values
        elif isinstance(values, dict):
            # 如果是字典，执行原来的逻辑
            for key, value in values.items():
                if value is None:
                    if key in ['table_name', 'table_comment', 'class_name', 'columns']:
                        values[key] = '' if key != 'columns' else []
            return values
        return values


class GenTableColumnSchema(BaseModel):
    """代码生成业务表字段创建模型（原始字段+生成配置）。
    - 原始：`column_name/column_type/column_comment` 等。
    - 生成：`python_type/html_type/query_type/dict_type` 等由工具初始化。
    - 标记：所有 is_* 字段默认使用字符串'1'表示启用，便于前端和模板处理。
    """
    model_config = ConfigDict(from_attributes=True)

    table_id: Optional[int] = Field(default=None, description='归属表编号')
    column_name: Optional[str] = Field(default=None, description='列名称')
    column_comment: Optional[str] = Field(default=None, description='列描述')
    column_type: Optional[str] = Field(default=None, description='列类型')
    python_type: Optional[str] = Field(default=None, description='python类型')
    python_field: Optional[str] = Field(default=None, description='python字段名')
    is_pk: Optional[str] = Field(default=None, description='是否主键（1是）')
    is_increment: Optional[str] = Field(default=None, description='是否自增（1是）')
    is_required: Optional[str] = Field(default=None, description='是否必填（1是）')
    is_unique: Optional[str] = Field(default=None, description='是否唯一（1是）')
    is_insert: Optional[str] = Field(default=None, description='是否为插入字段（1是）')
    is_edit: Optional[str] = Field(default=None, description='是否编辑字段（1是）')
    is_list: Optional[str] = Field(default=None, description='是否列表字段（1是）')
    is_query: Optional[str] = Field(default=None, description='是否查询字段（1是）')
    query_type: Optional[str] = Field(default=None, description='查询方式（等于、不等于、大于、小于、范围）')
    html_type: Optional[str] = Field(default=None, description='显示类型（文本框、文本域、下拉框、复选框、单选框、日期控件）')
    dict_type: Optional[str] = Field(default=None, description='字典类型')
    sort: Optional[int] = Field(default=None, description='排序')
    description: Optional[str] = Field(default=None, description='功能描述')


class GenTableColumnOutSchema(GenTableColumnSchema, BaseSchema):
    """业务表字段输出模型（布尔派生+便捷字段）。
    - 布尔：将字符串 is_* 转为布尔 `pk/increment/...`，供前端/模板快捷使用。
    - 便捷：`cap_python_field` 存放大驼峰字段名（模板场景常用）。
    """
    model_config = ConfigDict(from_attributes=True)

    cap_python_field: Optional[str] = Field(default=None, description='字段大写形式')
    pk: Optional[bool] = Field(default=None, description='是否主键')
    increment: Optional[bool] = Field(default=None, description='是否自增')
    required: Optional[bool] = Field(default=None, description='是否必填')
    unique: Optional[bool] = Field(default=None, description='是否唯一')
    insert: Optional[bool] = Field(default=None, description='是否为插入字段')
    edit: Optional[bool] = Field(default=None, description='是否编辑字段')
    list: Optional[bool] = Field(default=None, description='是否列表字段')
    query: Optional[bool] = Field(default=None, description='是否查询字段')
    super_column: Optional[bool] = Field(default=None, description='是否为基类字段')
    usable_column: Optional[bool] = Field(default=None, description='是否为基类字段白名单')


class GenTableColumnDeleteSchema(BaseModel):
    """删除代码生成业务表字段模型（批量）。
    - 说明：仅包含待删除的字段ID列表。
    """
    model_config = ConfigDict(from_attributes=True)

    column_ids: List[int] = Field(..., description='需要删除的代码生成业务表字段ID')
# -*- coding:utf-8 -*-

import json
from datetime import datetime
from jinja2.environment import Environment
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template
from typing import Dict, List, Any, Set

from app.common.constant import GenConstant
from app.config.setting import settings
from app.api.v1.module_generator.gencode.schema import GenTableOutSchema, GenTableColumnOutSchema
from app.utils.common_util import CamelCaseUtil, SnakeCaseUtil
from app.utils.string_util import StringUtil


class Jinja2TemplateInitializerUtil:
    """
    模板引擎初始化类
    """

    @classmethod
    def init_jinja2(cls):
        """
        初始化 Jinja2 模板引擎。
        
        参数:
        - 无
        
        返回:
        - Environment: Jinja2 环境对象。
        
        异常:
        - RuntimeError: 初始化失败时抛出。
        """
        try:
            # 修复模板路径，使用正确的相对路径

            env = Environment(
                loader=FileSystemLoader(settings.TEMPLATE_DIR),
                autoescape=select_autoescape(['html', 'xml', 'jinja']), # 自动转义HTML
                trim_blocks=True,   # 删除多余的空行
                lstrip_blocks=True,  # 删除行首空格
                keep_trailing_newline=True,  # 保留行尾换行符
                enable_async=True,  # 开启异步支持  
            )
            env.filters.update(
                {
                    'camel_to_snake': SnakeCaseUtil.camel_to_snake,
                    'snake_to_camel': CamelCaseUtil.snake_to_camel,
                    'get_sqlalchemy_type': Jinja2TemplateUtil.get_sqlalchemy_type,
                }
            )
            return env
        except Exception as e:
            raise RuntimeError(f'初始化Jinja2模板引擎失败: {e}')


class Jinja2TemplateUtil:
    """
    模板处理工具类
    """

    # 项目路径
    FRONTEND_PROJECT_PATH = 'frontend'
    BACKEND_PROJECT_PATH = 'backend'
    # 默认上级菜单，系统工具
    DEFAULT_PARENT_MENU_ID = "3"
    
    # 环境对象
    _env = None
    
    @classmethod
    def get_env(cls) -> Environment:
        """
        获取模板环境对象。
        
        参数:
        - 无
        
        返回:
        - Environment: Jinja2 环境对象。
        
        异常:
        - RuntimeError: 初始化失败时抛出。
        """
        if cls._env is None:
            cls._env = Jinja2TemplateInitializerUtil.init_jinja2()
        return cls._env
    
    @classmethod
    def get_template(cls, template_path: str) -> Template:
        """
        获取模板。
        
        参数:
        - template_path (str): 模板路径。
        
        返回:
        - Template: Jinja2 模板对象。
        
        异常:
        - TemplateNotFound: 模板未找到时抛出。
        """
        return cls.get_env().get_template(template_path)
    
    @classmethod
    def prepare_context(cls, gen_table: GenTableOutSchema)  -> dict[str, Any]:
        """
        准备模板变量。
        
        参数:
        - gen_table (GenTableOutSchema): 生成表的配置信息。
        
        返回:
        - Dict[str, Any]: 模板上下文字典。
        """
        # 处理options为None的情况
        options = gen_table.options or '{}'
        try:
            params_obj = json.loads(options)
        except json.JSONDecodeError:
            params_obj = {}
            
        class_name = gen_table.class_name or ''
        module_name = gen_table.module_name or ''
        business_name = gen_table.business_name or ''
        package_name = gen_table.package_name or ''
        tpl_category = gen_table.tpl_category or ''
        function_name = gen_table.function_name or ''
        
        context = {
            'tpl_category': tpl_category,
            'table_name': gen_table.table_name or '',
            'function_name': function_name if StringUtil.is_not_empty(function_name) else '【请填写功能名称】',
            'class_name': class_name,
            'className': class_name.capitalize() if class_name else '',
            'module_name': module_name,
            'business_name': business_name.capitalize() if business_name else '',
            'base_package': cls.get_package_prefix(package_name) if package_name else '',
            'package_name': package_name,
            'author': gen_table.function_author or '',
            'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'pk_column': gen_table.pk_column,
            'do_import_list': cls.get_do_import_list(gen_table),
            'vo_import_list': cls.get_vo_import_list(gen_table),
            'permission_prefix': cls.get_permission_prefix(module_name, business_name),
            'columns': gen_table.columns or [],
            'table': gen_table,
            'dicts': cls.get_dicts(gen_table),
            'db_type': settings.DATABASE_TYPE,
            'column_not_add_show': GenConstant.COLUMNNAME_NOT_ADD_SHOW,
            'column_not_edit_show': GenConstant.COLUMNNAME_NOT_EDIT_SHOW,
            'primary_key': gen_table.pk_column.python_field if gen_table.pk_column else ''
        }

        # 设置菜单、树形结构、子表的上下文
        cls.set_menu_context(context, gen_table)
        if tpl_category == GenConstant.TPL_TREE:
            cls.set_tree_context(context, gen_table)
        if tpl_category == GenConstant.TPL_SUB:
            cls.set_sub_context(context, gen_table)

        return context
    
    @classmethod
    def set_menu_context(cls, context: Dict, gen_table: GenTableOutSchema):
        """
        设置菜单上下文。
        
        参数:
        - context (Dict): 模板上下文字典。
        - gen_table (GenTableOutSchema): 生成表的配置信息。
        
        返回:
        - Dict: 更新后的模板上下文字典。
        """
        # 处理options为None的情况
        options = gen_table.options or '{}'
        try:
            params_obj = json.loads(options)
        except json.JSONDecodeError:
            params_obj = {}
        context['parent_menu_id'] = cls.get_parent_menu_id(params_obj)
    
    @classmethod
    def set_tree_context(cls, context: Dict, gen_table: GenTableOutSchema):
        """
        设置树形结构上下文。
        
        参数:
        - context (Dict): 模板上下文字典。
        - gen_table (GenTableOutSchema): 生成表的配置信息。
        
        返回:
        - Dict: 更新后的模板上下文字典。
        """
        # 处理options为None的情况
        options = gen_table.options or '{}'
        try:
            params_obj = json.loads(options)
        except json.JSONDecodeError:
            params_obj = {}
        context['tree_code'] = cls.get_tree_code(params_obj)
        context['tree_parent_code'] = cls.get_tree_parent_code(params_obj)
        context['tree_name'] = cls.get_tree_name(params_obj)
        context['expand_column'] = cls.get_expand_column(gen_table)
    
    @classmethod
    def set_sub_context(cls, context: Dict, gen_table: GenTableOutSchema):
        """
        设置子表上下文。
        """
        sub_table = gen_table.sub_table
        sub_table_name = gen_table.sub_table_name or ''
        sub_table_fk_name = gen_table.sub_table_fk_name or ''
        # 修复：避免重复的条件判断，清晰处理None
        sub_class_name = sub_table.class_name if sub_table else ''
        sub_table_fk_class_name = CamelCaseUtil.snake_to_camel(sub_table_fk_name) if sub_table_fk_name else ''
        context['sub_table'] = sub_table
        context['sub_table_name'] = sub_table_name
        context['sub_table_fk_name'] = sub_table_fk_name
        context['sub_table_fk_class_name'] = sub_table_fk_class_name
        context['sub_table_fk_class_name_lower'] = sub_table_fk_class_name.lower() if sub_table_fk_class_name else ''
        context['sub_class_name'] = sub_class_name
        context['sub_class_name_lower'] = sub_class_name.lower() if sub_class_name else ''

    @classmethod
    def get_template_list(cls, tpl_category: str, tpl_web_type: str):
        """
        获取模板列表。
        
        参数:
        - tpl_category (str): 生成模板类型。
        - tpl_web_type (str): 前端类型。
        
        返回:
        - List[str]: 模板路径列表。
        """
        use_web_type = 'vue'
        # 处理空值情况
        if tpl_web_type and tpl_web_type == 'element-plus':
            use_web_type = 'vue'
        # 处理空值情况
        category = tpl_category or GenConstant.TPL_CRUD
        templates = [
            'python/controller.py.j2',
            'python/service.py.j2',
            'python/crud.py.j2',
            'python/schema.py.j2',
            'python/param.py.j2',
            'python/model.py.j2',
            'sql/sql.sql.j2',
            'ts/api.ts.j2',
        ]
        if category == GenConstant.TPL_CRUD:
            templates.append(f'{use_web_type}/index.vue.j2')
        elif category == GenConstant.TPL_TREE:
            templates.append(f'{use_web_type}/index-tree.vue.j2')
        elif category == GenConstant.TPL_SUB:
            templates.append(f'{use_web_type}/index.vue.j2')
        return templates
    
    @classmethod
    def get_file_name(cls, template: str, gen_table: GenTableOutSchema):
        """
        根据模板生成文件名。

        参数:
        - template (str): 模板路径字符串。
        - gen_table (GenTableOutSchema): 生成表的配置信息。
        
        返回:
        - str: 模板生成的文件名。
        """
        package_name = gen_table.package_name or ''
        module_name = gen_table.module_name or ''
        business_name = gen_table.business_name or ''

        vue_path = cls.FRONTEND_PROJECT_PATH
        python_path = cls.BACKEND_PROJECT_PATH

        if 'controller.py.j2' in template:
            return f'{python_path}/app/api/v1/module_{module_name}/{business_name}/controller.py'
        elif 'crud.py.j2' in template:
            return f'{python_path}/app/api/v1/module_{module_name}/{business_name}/crud.py'
        elif 'model.py.j2' in template:
            return f'{python_path}/app/api/v1/module_{module_name}/{business_name}/model.py'
        elif 'service.py.j2' in template:
            return f'{python_path}/app/api/v1/module_{module_name}/{business_name}/service.py'
        elif 'param.py.j2' in template:
            return f'{python_path}/app/api/v1/module_{module_name}/{business_name}/param.py'
        elif 'schema.py.j2' in template:
            return f'{python_path}/app/api/v1/module_{module_name}/{business_name}/schema.py'
        elif 'sql.sql.j2' in template:
            return f'{python_path}/sql/module_{module_name}/{business_name}_menu.sql'
        elif 'api.ts.j2' in template:
            return f'{vue_path}/src/api/module_{module_name}/{business_name}.ts'
        elif 'index.vue.j2' in template:
            return f'{vue_path}/src/views/module_{module_name}/{business_name}/index.vue'
        elif 'index-tree.vue.j2' in template:
            # 修复：树形模板生成到专用文件名
            return f'{vue_path}/src/views/module_{module_name}/{business_name}/index-tree.vue'
        return ''

    @classmethod
    def get_package_prefix(cls, package_name: str) -> str:
        """
        获取包前缀。

        参数:
        - package_name (str): 包名。
        
        返回:
        - str: 包前缀。
        """
        # 修复：当包名中不存在'.'时，直接返回原包名
        return package_name[: package_name.rfind('.')] if '.' in package_name else package_name

    @classmethod
    def get_vo_import_list(cls, gen_table: GenTableOutSchema):
        """
        获取 VO 模板导入包列表。

        参数:
        - gen_table (GenTableOutSchema): 生成表的配置信息。
        
        返回:
        - List[str]: 导入包列表。
        """
        columns = gen_table.columns or []
        import_list = set()
        for column in columns:
            # 处理column_type为None的情况
            column_type = column.column_type or ''
            if column_type in GenConstant.TYPE_DATE:
                import_list.add(f'from datetime import {column_type}')
            elif column_type == GenConstant.TYPE_DECIMAL:
                import_list.add('from decimal import Decimal')
        if gen_table.sub and gen_table.sub_table:
            # 处理sub_table.columns为None的情况
            sub_columns = gen_table.sub_table.columns or []
            for sub_column in sub_columns:
                # 处理sub_column.column_type为None的情况
                sub_column_type = sub_column.column_type or ''
                if sub_column_type in GenConstant.TYPE_DATE:
                    import_list.add(f'from datetime import {sub_column_type}')
                elif sub_column_type == GenConstant.TYPE_DECIMAL:
                    import_list.add('from decimal import Decimal')
        return cls.merge_same_imports(list(import_list), 'from datetime import')
    
    @classmethod
    def get_do_import_list(cls, gen_table: GenTableOutSchema) -> List[str]:
        """
        获取 DO 模板导入包列表。

        参数:
        - gen_table (GenTableOutSchema): 生成表的配置信息。
        
        返回:
        - List[str]: 导入包列表。
        """
        columns = gen_table.columns or []
        import_list = set()
        import_list.add('from sqlalchemy import Column')
        for column in columns:
            # 处理column.column_type为None的情况
            column_type = column.column_type or ''
            data_type = cls.get_db_type(column_type)
            if data_type in GenConstant.COLUMNTYPE_GEOMETRY:
                import_list.add('from geoalchemy2 import Geometry')
            import_list.add(
                f'from sqlalchemy import {StringUtil.get_mapping_value_by_key_ignore_case(GenConstant.DB_TO_SQLALCHEMY, data_type)}'
            )
        if gen_table.sub and gen_table.sub_table:
            import_list.add('from sqlalchemy import ForeignKey')
            # 处理sub_table.columns为None的情况
            sub_columns = gen_table.sub_table.columns or []
            for sub_column in sub_columns:
                # 处理sub_column.column_type为None的情况
                sub_column_type = sub_column.column_type or ''
                data_type = cls.get_db_type(sub_column_type)
                import_list.add(
                    f'from sqlalchemy import {StringUtil.get_mapping_value_by_key_ignore_case(GenConstant.DB_TO_SQLALCHEMY, data_type)}'
                )
        return cls.merge_same_imports(list(import_list), 'from sqlalchemy import')

    @classmethod
    def get_db_type(cls, column_type: str) -> str:
        """
        获取数据库字段类型。

        参数:
        - column_type (str): 字段类型字符串。
        
        返回:
        - str: 数据库类型（去除长度等修饰）。
        """
        if '(' in column_type:
            return column_type.split('(')[0]
        return column_type
    
    @classmethod
    def merge_same_imports(cls, imports: List[str], import_start: str) -> List[str]:
        """
        合并相同的导入语句。

        参数:
        - imports (List[str]): 导入语句列表。
        - import_start (str): 导入语句的起始字符串。
        
        返回:
        - List[str]: 合并后的导入语句列表。
        """
        merged_imports = []
        _imports = []
        for import_stmt in imports:
            if import_stmt.startswith(import_start):
                imported_items = import_stmt.split('import')[1].strip()
                _imports.extend(imported_items.split(', '))
            else:
                merged_imports.append(import_stmt)

        if _imports:
            merged_datetime_import = f'{import_start} {", ".join(_imports)}'
            merged_imports.append(merged_datetime_import)

        return merged_imports
    
    @classmethod
    def get_dicts(cls, gen_table: GenTableOutSchema):
        """
        获取字典列表。

        参数:
        - gen_table (GenTableOutSchema): 生成表的配置信息。
        
        返回:
        - str: 以逗号分隔的字典类型字符串。
        """
        columns = gen_table.columns or []
        dicts = set()
        cls.add_dicts(dicts, columns)
        # 处理sub_table为None的情况
        if gen_table.sub_table is not None:
            # 处理sub_table.columns为None的情况
            sub_columns = gen_table.sub_table.columns or []
            cls.add_dicts(dicts, sub_columns)
        return ', '.join(dicts)

    @classmethod
    def add_dicts(cls, dicts: Set[str], columns: List[GenTableColumnOutSchema]):
        """
        添加字典类型到集合。

        参数:
        - dicts (Set[str]): 字典类型集合。
        - columns (List[GenTableColumnOutSchema]): 字段列表。
        
        返回:
        - Set[str]: 更新后的字典类型集合。
        """
        for column in columns:
            # 处理column.super_column, column.dict_type, column.html_type为None的情况
            super_column = column.super_column if column.super_column is not None else False
            dict_type = column.dict_type or ''
            html_type = column.html_type or ''
            
            if (
                not super_column
                and StringUtil.is_not_empty(dict_type)
                and StringUtil.equals_any_ignore_case(
                    html_type, [GenConstant.HTML_SELECT, GenConstant.HTML_RADIO, GenConstant.HTML_CHECKBOX]
                )
            ):
                dicts.add(f"'{dict_type}'")

    @classmethod
    def get_permission_prefix(cls, module_name: str | None, business_name: str | None) -> str:
        """
        获取权限前缀。

        参数:
        - module_name (str | None): 模块名。
        - business_name (str | None): 业务名。
        
        返回:
        - str: 权限前缀字符串。
        """
        return f'{module_name}:{business_name}'
    
    @classmethod
    def get_parent_menu_id(cls, params_obj: Dict):
        """
        获取上级菜单ID。

        参数:
        - params_obj (Dict): 菜单参数字典。
        
        返回:
        - str: 上级菜单ID。
        """
        if params_obj and params_obj.get(GenConstant.PARENT_MENU_ID):
            return params_obj.get(GenConstant.PARENT_MENU_ID)
        return cls.DEFAULT_PARENT_MENU_ID
    
    @classmethod
    def get_tree_code(cls, params_obj: Dict):
        """
        获取树编码。

        参数:
        - params_obj (Dict): 菜单参数字典。
        
        返回:
        - str: 树编码（驼峰格式）。
        """
        if GenConstant.TREE_CODE in params_obj:
            tree_code = params_obj.get(GenConstant.TREE_CODE)
            # 处理tree_code为None的情况
            if tree_code:
                return cls.to_camel_case(str(tree_code))
        return ''
    
    @classmethod
    def get_tree_parent_code(cls, params_obj: Dict):
        """
        获取树父编码。

        参数:
        - params_obj (Dict): 菜单参数字典。
        
        返回:
        - str: 树父编码（驼峰格式）。
        """
        if GenConstant.TREE_PARENT_CODE in params_obj:
            tree_parent_code = params_obj.get(GenConstant.TREE_PARENT_CODE)
            # 处理tree_parent_code为None的情况
            if tree_parent_code:
                return cls.to_camel_case(str(tree_parent_code))
        return ''
    
    @classmethod
    def get_tree_name(cls, params_obj: Dict):
        """
        获取树名称。

        参数:
        - params_obj (Dict): 菜单参数字典。
        
        返回:
        - str: 树名称（驼峰格式）。
        """
        if GenConstant.TREE_NAME in params_obj:
            tree_name = params_obj.get(GenConstant.TREE_NAME)
            # 处理tree_name为None的情况
            if tree_name:
                return cls.to_camel_case(str(tree_name))
        return ''
    
    @classmethod
    def get_expand_column(cls, gen_table: GenTableOutSchema):
        """
        获取展开列位置序号。

        参数:
        - gen_table (GenTableOutSchema): 生成表的配置信息。
        
        返回:
        - int: 展开列在列表中的序号（从 1 开始）。
        """
        # 处理options为None的情况
        options = gen_table.options or '{}'
        try:
            params_obj = json.loads(options)
        except json.JSONDecodeError:
            params_obj = {}
        tree_name = params_obj.get(GenConstant.TREE_NAME) or ''
        num = 0
        # 处理gen_table.columns为None的情况
        columns = gen_table.columns or []
        for column in columns:
            if column.list:
                num += 1
                if column.column_name == tree_name:
                    break
        return num
    
    @classmethod
    def to_camel_case(cls, text: str) -> str:
        """
        将字符串转换为驼峰命名。

        参数:
        - text (str): 待转换的字符串。
        
        返回:
        - str: 转换后的驼峰命名字符串。
        """
        parts = text.split('_')
        return parts[0] + ''.join(word.capitalize() for word in parts[1:])
    
    @classmethod
    def get_sqlalchemy_type(cls, column_type):
        """
        获取 SQLAlchemy 类型。

        参数:
        - column_type (Any): 列类型或包含 `column_type` 属性的对象。
        
        返回:
        - str: SQLAlchemy 类型字符串。
        """
        # 适配可能传入的是对象而非字符串的情况
        if hasattr(column_type, 'column_type'):
            column_type_value = column_type.column_type
        else:
            column_type_value = str(column_type)
            
        if '(' in column_type_value:
            column_type_list = column_type_value.split('(')
            if column_type_list[0] in GenConstant.COLUMNTYPE_STR:
                sqlalchemy_type = (
                    StringUtil.get_mapping_value_by_key_ignore_case(
                        GenConstant.DB_TO_SQLALCHEMY, column_type_list[0]
                    )
                    + '('
                    + column_type_list[1]
                )
            else:
                sqlalchemy_type = StringUtil.get_mapping_value_by_key_ignore_case(
                    GenConstant.DB_TO_SQLALCHEMY, column_type_list[0]
                )
        else:
            sqlalchemy_type = StringUtil.get_mapping_value_by_key_ignore_case(
                GenConstant.DB_TO_SQLALCHEMY, column_type_value
            )

        return sqlalchemy_type

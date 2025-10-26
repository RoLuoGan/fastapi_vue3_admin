# -*- coding:utf-8 -*-

from sqlalchemy.engine.row import Row
from sqlalchemy import and_, delete, select, text, update
from sqlalchemy.orm import selectinload
from sqlglot.expressions import Expression
from typing import List, Optional, Sequence, Dict, Union, Any

from app.core.logger import logger
from app.config.setting import settings
from app.core.base_crud import CRUDBase
from app.api.v1.module_system.auth.schema import AuthSchema
from .param import GenTableQueryParam, GenTableColumnQueryParam
from .model import GenTableModel, GenTableColumnModel
from .schema import (
    GenTableSchema,
    GenTableOutSchema,
    GenTableColumnSchema,
    GenTableColumnOutSchema,
    GenTableColumnDeleteSchema,
    GenDBTableSchema,
)


class GenTableCRUD(CRUDBase[GenTableModel, GenTableSchema, GenTableSchema]):
    """代码生成业务表模块数据库操作层"""

    def __init__(self, auth: AuthSchema) -> None:
        """
        初始化CRUD操作层

        参数:
        - auth (AuthSchema): 认证信息模型
        """
        super().__init__(model=GenTableModel, auth=auth)

    async def get_gen_table_by_id(self, table_id: int, preload: Optional[List[Union[str, Any]]] = None) -> Optional[GenTableModel]:
        """
        根据业务表ID获取需要生成的业务表信息。

        参数:
        - table_id (int): 业务表ID。
        - preload (Optional[List[Union[str, Any]]]): 预加载关系，未提供时使用模型默认项

        返回:
        - GenTableModel | None: 业务表信息对象。
        """
        gen_table = (
            (
                await self.db.execute(
                    select(GenTableModel)
                    .options(selectinload(GenTableModel.columns))
                    .where(GenTableModel.id == table_id)
                )
            )
            .scalars()
            .first()
        )

        return gen_table

    async def get_gen_table_by_name(self, table_name: str, preload: Optional[List[Union[str, Any]]] = None) -> Optional[GenTableModel]:
        """
        根据业务表名称获取需要生成的业务表信息。

        参数:
        - table_name (str): 业务表名称。
        - preload (Optional[List[Union[str, Any]]]): 预加载关系，未提供时使用模型默认项

        返回:
        - GenTableModel | None: 业务表信息对象。
        """
        gen_table = (
            (
                await self.db.execute(
                    select(GenTableModel)
                    .options(selectinload(GenTableModel.columns))
                    .where(GenTableModel.table_name == table_name)
                )
            )
            .scalars()
            .first()
        )

        return gen_table
    
    async def get_gen_table_all(self, preload: Optional[List[Union[str, Any]]] = None) -> Sequence[GenTableModel]:
        """
        获取所有业务表信息。

        参数:
        - preload (Optional[List[Union[str, Any]]]): 预加载关系，未提供时使用模型默认项

        返回:
        - Sequence[GenTableModel]: 所有业务表信息列表。
        """
        gen_table_all = (
            await self.db.execute(
                select(GenTableModel)
                .options(selectinload(GenTableModel.columns))
                )
            ).scalars().all()

        return gen_table_all

    async def get_gen_table_list(self, search: Optional[GenTableQueryParam] = None, preload: Optional[List[Union[str, Any]]] = None) -> Sequence[GenTableModel]:
        """
        根据查询参数获取代码生成业务表列表信息。

        参数:
        - search (GenTableQueryParam | None): 查询参数对象。
        - preload (Optional[List[Union[str, Any]]]): 预加载关系，未提供时使用模型默认项

        返回:
        - Sequence[GenTableModel]: 业务表列表信息。
        """
        # 获取所有数据
        result = await self.db.execute(
            select(GenTableModel)
            .options(selectinload(GenTableModel.columns))
            .where(
                GenTableModel.table_name.like(f"%{search.table_name}%") if search and search.table_name else GenTableModel.id.isnot(None),
                GenTableModel.table_comment.like(f"%{search.table_comment}%") if search and search.table_comment else GenTableModel.id.isnot(None),
            )
            .order_by(GenTableModel.created_at.desc())
            .distinct()
        )
        gen_table_all = result.scalars().all()

        return gen_table_all

    async def add_gen_table(self, add_model: GenTableSchema) -> GenTableModel:
        """
        新增业务表信息。

        参数:
        - add_model (GenTableSchema): 新增业务表信息模型。

        返回:
        - GenTableModel: 新增的业务表信息对象。
        """
        gen_table = GenTableModel(
            **add_model.model_dump(exclude_unset=True, exclude={"sub", "tree", "crud"})
        )
        self.db.add(gen_table)
        await self.db.flush()
        return gen_table
    
    async def edit_gen_table(self, table_id: int, edit_model: GenTableSchema) -> GenTableSchema:
        """
        修改业务表信息。

        参数:
        - table_id (int): 业务表ID。
        - edit_model (GenTableSchema): 修改业务表信息模型。

        返回:
        - GenTableSchema: 修改后的业务表信息模型。
        """
        edit_dict_data = edit_model.model_dump(exclude_unset=True)
        await self.db.execute(
            update(GenTableModel)
            .where(GenTableModel.id == table_id)
            .values(**edit_dict_data)
        )
        await self.db.flush()
        await self.db.commit()
        return edit_model

    async def delete_gen_table(self, ids: List[int]) -> None:
        """
        删除业务表信息。除了系统表。

        参数:
        - ids (List[int]): 业务表ID列表。
        """
        await self.db.execute(
            delete(GenTableModel)
            .where(GenTableModel.id.in_(ids))
        )
        await self.db.flush()

    async def get_db_table_list(self, search: Optional[GenTableQueryParam] = None) -> list[Dict]:
        """
        根据查询参数获取数据库表列表信息。

        参数:
        - search (GenTableQueryParam | None): 查询参数对象。

        返回:
        - list[Dict]: 数据库表列表信息（已转为可序列化字典）。
        """

        # 使用更健壮的方式检测数据库方言
        if settings.DATABASE_TYPE == "postgresql":
            query_sql = (
                select(
                    text("table_catalog as database_name"),
                    text("table_name as table_name"),
                    text("table_type as table_type"),
                    text("table_comment as table_comment"),
                )
                .select_from(text("information_schema.tables"))
                .where(
                    and_(
                        text("table_catalog = (select current_database())"),
                        text("is_insertable_into = 'YES'"),
                        text("table_schema = 'public'"),
                    )
                )
            )
        elif settings.DATABASE_TYPE == "mysql":
            query_sql = (
                select(
                    text("table_schema as database_name"),
                    text("table_name as table_name"),
                    text("table_type as table_type"),
                    text("table_comment as table_comment"),
                )
                .select_from(text("information_schema.tables"))
                .where(
                    and_(
                        text("table_schema = (select database())"),
                    )
                )
            )
        else:
            query_sql = (
                select(
                    text("'fastapiadmin' as database_name"),  # SQLite没有数据库名概念，设为空字符串
                    text("name as table_name"),
                    text("type as table_type"),
                    text("name as table_comment"),  # SQLite中使用name作为表名和注释
                )
                .select_from(text("sqlite_master"))
                .where(
                    and_(
                        text("type = 'table'"),
                    )   
                )
            )
        
        # 动态条件构造
        params = {}
        if search and search.table_name:
            if settings.DATABASE_TYPE == "sqlite":
                query_sql = query_sql.where(
                    text("lower(name) like lower(:table_name)")
                )
            else:
                query_sql = query_sql.where(
                    text("lower(table_name) like lower(:table_name)")
                )
            params['table_name'] = f"%{search.table_name}%"
        if search and search.table_comment:
            if settings.DATABASE_TYPE == "sqlite":
                query_sql = query_sql.where(
                    text("lower(name) like lower(:table_comment)")
                )
            else:
                query_sql = query_sql.where(
                    text("lower(table_comment) like lower(:table_comment)")
                )
            params['table_comment'] = f"%{search.table_comment}%"

        # 执行查询并绑定参数
        all_data = (await self.db.execute(query_sql, params)).fetchall()

        # 将Row对象转换为字典列表，解决JSON序列化问题
        dict_data = []
        for row in all_data:
            # 检查row是否为Row对象
            if isinstance(row, Row):
                # 使用._mapping获取字典
                dict_row = GenDBTableSchema(**dict(row._mapping)).model_dump()
                dict_data.append(dict_row)
            else:
                dict_row = GenDBTableSchema(**dict(row)).model_dump()
                dict_data.append(dict_row)
        return dict_data

    async def get_db_table_list_by_names(self, table_names: List[str]) -> list[GenDBTableSchema]:
        """
        根据业务表名称列表获取数据库表信息。

        参数:
        - table_names (List[str]): 业务表名称列表。

        返回:
        - list[GenDBTableSchema]: 数据库表信息对象列表。
        """
        # 使用更健壮的方式检测数据库方言
        if settings.DATABASE_TYPE == "postgresql":
            query_sql = (
                select(
                    text("table_catalog as database_name"),
                    text("table_name as table_name"),
                    text("table_type as table_type"),
                    text("table_comment as table_comment"),
                )
                .select_from(text("information_schema.tables"))
                .where(
                    and_(
                        text("table_catalog = (select current_database())"),
                        text("is_insertable_into = 'YES'"),
                        text("table_schema = 'public'"),
                    )
                )
            )
        elif settings.DATABASE_TYPE == "mysql":
            query_sql = (
                select(
                    text("table_schema as database_name"),
                    text("table_name as table_name"),
                    text("table_type as table_type"),
                    text("table_comment as table_comment"),
                )
                .select_from(text("information_schema.tables"))
                .where(
                    and_(
                        text("table_schema = (select database())"),
                    )
                )
            )
        else:
            query_sql = (
                select(
                    text("'fastapiadmin' as database_name"),  # SQLite没有数据库名概念，设为空字符串
                    text("name as table_name"),
                    text("type as table_type"),
                    text("name as table_comment"),  # SQLite中使用name作为表名和注释
                )
                .select_from(text("sqlite_master"))
                .where(
                    and_(
                        text("type = 'table'"),
                    )   
                )
            )
        
        table_names_str = "','".join(table_names)
        # 修复SQL查询中的参数绑定问题
        if table_names:
            if settings.DATABASE_TYPE == "sqlite":
                # 对于SQLite，我们直接在SQL中使用表名，因为参数绑定有问题
                query_sql = query_sql.where(
                    text(f"name IN ('{table_names_str}')")
                )
                gen_db_table_list = (await self.db.execute(query_sql)).fetchall()
            else:
                # MySQL和PostgreSQL使用:table_names占位符
                query_sql = query_sql.where(
                    text(f"table_name IN ('{table_names_str}')")
                )
                # 使用params方法正确绑定参数
                query_sql = query_sql.params(table_names=tuple(table_names))
                gen_db_table_list = (await self.db.execute(query_sql)).fetchall()
        else:
            gen_db_table_list = (await self.db.execute(query_sql)).fetchall()
        
        # 将Row对象转换为字典列表，解决JSON序列化问题
        dict_data = []
        for row in gen_db_table_list:
            # 检查row是否为Row对象
            if isinstance(row, Row):
                # 使用._mapping获取字典
                dict_row = GenDBTableSchema(**dict(row._mapping))
                dict_data.append(dict_row)
            else:
                dict_row = GenDBTableSchema(**dict(row))
                dict_data.append(dict_row)
        return dict_data

    async def create_table_by_sql(self, sql: str) -> bool:
        """
        根据SQL语句创建表结构。

        参数:
        - sql (str): 创建表的SQL语句。

        返回:
        - bool: 是否创建成功。
        """
        try:
            await self.db.execute(text(sql))
            # 提交事务
            await self.db.commit()
            await self.db.flush()
            return True
        except Exception as e:
            # 如果发生异常，回滚事务
            await self.db.rollback()
            logger.error(f"创建表时发生错误: {e}")
            return False


class GenTableColumnCRUD(CRUDBase[GenTableColumnModel, GenTableColumnSchema, GenTableColumnSchema]):
    """代码生成业务表字段模块数据库操作层"""

    def __init__(self, auth: AuthSchema) -> None:
        """
        初始化CRUD操作层

        参数:
        - auth (AuthSchema): 认证信息模型
        """
        super().__init__(model=GenTableColumnModel, auth=auth)

    async def get_gen_table_column_by_id(self, id: int, preload: Optional[List[Union[str, Any]]] = None) -> Optional[GenTableColumnModel]:
        """根据业务表字段ID获取业务表字段信息。

        参数:
        - id (int): 业务表字段ID。
        - preload (Optional[List[Union[str, Any]]]): 预加载关系，未提供时使用模型默认项

        返回:
        - Optional[GenTableColumnModel]: 业务表字段信息对象。
        """
        return await self.get(id=id, preload=preload)
    
    async def get_gen_table_column_list_by_table_id(self, table_id: int, preload: Optional[List[Union[str, Any]]] = None) -> Optional[GenTableColumnModel]:
        """根据业务表ID获取业务表字段列表信息。

        参数:
        - table_id (int): 业务表ID。
        - preload (Optional[List[Union[str, Any]]]): 预加载关系，未提供时使用模型默认项

        返回:
        - Optional[GenTableColumnModel]: 业务表字段列表信息对象。
        """
        return await self.get(table_id=table_id, preload=preload)
    
    async def list_gen_table_column_crud_by_table_id(self, table_id: int, order_by: Optional[List[Dict[str, str]]] = None, preload: Optional[List[Union[str, Any]]] = None) -> Sequence[GenTableColumnModel]:
        """根据业务表ID查询业务表字段列表。

        参数:
        - table_id (int): 业务表ID。
        - order_by (Optional[List[Dict[str, str]]]): 排序字段列表，每个元素为{"field": "字段名", "order": "asc" | "desc"}。
        - preload (Optional[List[Union[str, Any]]]): 预加载关系，未提供时使用模型默认项

        返回:
        - Sequence[GenTableColumnModel]: 业务表字段列表信息对象序列。
        """
        return await self.list(search={"table_id": table_id}, order_by=order_by, preload=preload)

    async def get_gen_db_table_columns_by_name(self, table_name: str | None) -> List[GenTableColumnOutSchema]:
        """
        根据业务表名称获取业务表字段列表信息。

        参数:
        - table_name (str | None): 业务表名称。

        返回:
        - List[GenTableColumnOutSchema]: 业务表字段列表信息对象。
        """
        # 检查表名是否为空
        if not table_name:
            raise ValueError("数据表名称不能为空")

        # 兼容SQLite和MySQL/PostgreSQL
        if settings.DATABASE_TYPE == "postgresql":
            query_sql = """
                SELECT
                    column_name,
                    (CASE WHEN (is_nullable = 'no' AND column_key != 'PRI') THEN '1' ELSE '0' END) AS is_required,
                    (CASE WHEN column_key = 'PRI' THEN '1' ELSE '0' END) AS is_pk,
                    ordinal_position AS sort,
                    column_comment,
                    (CASE WHEN extra = 'auto_increment' THEN '1' ELSE '0' END) AS is_increment,
                    column_type
                FROM 
                    information_schema.columns
                WHERE 
                    table_catalog = (select current_database())
                    AND table_schema = 'public'
                    AND table_name = :table_name
            """
        elif settings.DATABASE_TYPE == "mysql":
            query_sql = """
                SELECT
                    column_name,
                    (CASE WHEN (is_nullable = 'no' AND column_key != 'PRI') THEN '1' ELSE '0' END) AS is_required,
                    (CASE WHEN column_key = 'PRI' THEN '1' ELSE '0' END) AS is_pk,
                    ordinal_position AS sort,
                    column_comment,
                    (CASE WHEN extra = 'auto_increment' THEN '1' ELSE '0' end) AS is_increment,
                    column_type
                FROM 
                    information_schema.columns
                WHERE 
                    table_schema = (SELECT DATABASE())
                    AND table_name = :table_name
            """
        else:
            # 修复SQLite查询语句，使用PRAGMA获取表结构信息
            query_sql = """
                SELECT
                    name as column_name,
                    (CASE WHEN (type != '' AND pk != 1) THEN '1' ELSE '0' END) AS is_required,
                    (CASE WHEN pk = 1 THEN '1' ELSE '0' END) AS is_pk,
                    cid AS sort,
                    '' as column_comment,
                    (CASE WHEN type LIKE '%AUTOINCREMENT%' THEN '1' ELSE '0' END) AS is_increment,
                    type as column_type
                FROM 
                    pragma_table_info(:table_name)
            """
        
        query = text(query_sql).bindparams(table_name=table_name)
        rows = (
            await self.db.execute(query)
        ).fetchall()
        result = [
            GenTableColumnOutSchema(
                column_name=row[0],
                is_required=row[1],
                is_pk=row[2],
                sort=row[3],
                column_comment=row[4],
                is_increment=row[5],
                column_type=row[6]
            )
            for row in rows
        ]
        
        return result

    async def list_gen_table_column_crud(self, search: Optional[Dict] = None, order_by: Optional[List[Dict[str, str]]] = None, preload: Optional[List[Union[str, Any]]] = None) -> Sequence[GenTableColumnModel]:
        """根据业务表字段查询业务表字段列表。

        参数:
        - search (Optional[Dict]): 查询参数，例如{"table_id": 1}。
        - order_by (Optional[List[Dict[str, str]]]): 排序字段列表，每个元素为{"field": "字段名", "order": "asc" | "desc"}。
        - preload (Optional[List[Union[str, Any]]]): 预加载关系，未提供时使用模型默认项

        返回:
        - Sequence[GenTableColumnModel]: 业务表字段列表信息对象序列。
        """
        return await self.list(search=search, order_by=order_by, preload=preload)

    async def create_gen_table_column_crud(self, data: GenTableColumnSchema) -> Optional[GenTableColumnModel]:
        """创建业务表字段。

        参数:
        - data (GenTableColumnSchema): 业务表字段模型。

        返回:
        - Optional[GenTableColumnModel]: 业务表字段列表信息对象。
        """
        return await self.create(data=data)

    async def update_gen_table_column_crud(self, id: int, data: GenTableColumnSchema) -> Optional[GenTableColumnModel]:
        """更新业务表字段。

        参数:
        - id (int): 业务表字段ID。
        - data (GenTableColumnSchema): 业务表字段模型。

        返回:
        - Optional[GenTableColumnModel]: 业务表字段列表信息对象。
        """
        return await self.update(id=id, data=data)

    async def delete_gen_table_column_by_table_id_dao(self, table_ids: List[int]) -> None:
        """根据业务表ID批量删除业务表字段。

        参数:
        - table_ids (List[int]): 业务表ID列表。

        返回:
        - None
        """
        # 先查询出这些表ID对应的所有字段ID
        query = select(GenTableColumnModel.id).where(GenTableColumnModel.table_id.in_(table_ids))
        result = await self.db.execute(query)
        column_ids = [row[0] for row in result.fetchall()]
        
        # 如果有字段ID，则删除这些字段
        if column_ids:
            await self.delete(ids=column_ids)

    async def delete_gen_table_column_by_column_id_dao(self, data: GenTableColumnDeleteSchema) -> None:
        """根据业务表字段ID批量删除业务表字段。

        参数:
        - data (GenTableColumnDeleteSchema): 业务表字段删除模型。

        返回:
        - None
        """
        return await self.delete(ids=data.column_ids)

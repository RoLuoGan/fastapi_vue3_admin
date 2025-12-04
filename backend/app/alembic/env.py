import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool
from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
from app.core.base_model import MappedBase

# 导入所有模型，确保 Alembic 能够检测到它们
# 系统模块
from app.api.v1.module_system.user.model import UserModel, UserRolesModel, UserPositionsModel
from app.api.v1.module_system.role.model import RoleModel, RoleDeptsModel, RoleMenusModel
from app.api.v1.module_system.position.model import PositionModel
from app.api.v1.module_system.dept.model import DeptModel
from app.api.v1.module_system.menu.model import MenuModel
from app.api.v1.module_system.params.model import ParamsModel
from app.api.v1.module_system.dict.model import DictTypeModel, DictDataModel
from app.api.v1.module_system.notice.model import NoticeModel
from app.api.v1.module_system.log.model import OperationLogModel

# 运维模块
from app.api.v1.module_operations.models import (
    ServiceModel,
    ServicePackageModel,
    NodeModel,
    TaskModel,
    TaskLogModel,
    node_service_association
)
from app.api.v1.module_operations.prometheus.model import (
    PrometheusJobModel,
    PrometheusEndpointModel,
    PrometheusLabelModel
)

# 代码生成模块
from app.api.v1.module_generator.gencode.model import GenTableModel, GenTableColumnModel
from app.api.v1.module_generator.demo.model import DemoModel

# 应用模块
from app.api.v1.module_application.myapp.model import ApplicationModel
from app.api.v1.module_application.job.model import JobModel, JobLogModel
from app.api.v1.module_application.ai.model import McpModel

target_metadata = MappedBase.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.
from app.config.setting import settings
config.set_main_option("sqlalchemy.url", settings.ASYNC_DB_URI)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    # 确保URL不为None
    if url is None:
        raise ValueError("数据库URL未正确配置，请检查环境配置文件")
        
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    url = config.get_main_option("sqlalchemy.url")
    # 确保URL不为None
    if url is None:
        raise ValueError("数据库URL未正确配置，请检查环境配置文件")
        
    connectable = create_async_engine(url, poolclass=pool.NullPool)
    
    async def run_async_migrations():
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)

    def do_run_migrations(connection):
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
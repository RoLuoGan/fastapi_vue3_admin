# -*- coding: utf-8 -*-

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from uvicorn.config import LifespanType
from urllib.parse import quote_plus

from app.common.enums import EnvironmentEnum


def _resolve_env_file(env: str) -> Path:
    """
    获取环境配置文件路径，支持以下优先级：
    1. 显式指定 ENV_FILE（绝对或相对路径）
    2. 指定 ENV_DIR（目录） + .env.<env>
    3. 当前工作目录下的 env/.env.<env>
    4. 包内置目录 backend/env/.env.<env>
    """
    env_file_name = f".env.{env}"

    # 1) 完整路径
    explicit_env_file = os.getenv("ENV_FILE")
    if explicit_env_file:
        env_path = Path(explicit_env_file).expanduser().resolve()
        if env_path.exists():
            return env_path

    candidates = []

    # 2) 指定目录
    explicit_env_dir = os.getenv("ENV_DIR")
    if explicit_env_dir:
        candidates.append(Path(explicit_env_dir))

    # 3) 当前工作目录
    candidates.append(Path.cwd() / "env")

    # 4) 包内目录
    candidates.append(Path(__file__).parent.parent.parent / "env")

    for candidate in candidates:
        env_path = (candidate / env_file_name).expanduser().resolve()
        if env_path.exists():
            return env_path

    raise FileNotFoundError(f"环境配置文件不存在: {candidates[-1] / env_file_name}")


class Settings(BaseSettings):
    """系统配置类"""
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding="utf-8",
        extra='ignore',
        case_sensitive=True, # 区分大小写
    )

    ENVIRONMENT: EnvironmentEnum
    
    BANNER: ClassVar[str] = f"""
     ______        _                  _ 
    |  ____|      | |     /\         (_)
    | |__ __ _ ___| |_   /  \   _ __  _ 
    |  __/ _` / __| __| / /\ \ | '_ \| |
    | | | (_| \__ \ |_ / ____ \| |_) | |
    |_|  \__,_|___/\__/_/    \_\ .__/|_|
                               | |      
                               |_|
    """
    # ================================================= #
    # ******************* 项目配置 ****************** #
    # ================================================= #
    # 项目根目录
    BASE_DIR: Path = Path(__file__).parent.parent.parent

    # ================================================= #
    # ******************* 服务器配置 ****************** #
    # ================================================= #
    SERVER_HOST: str         # 允许访问的IP地址
    SERVER_PORT: int         # 服务端口
    RELOAD: bool             # 是否自动重启
    FACTORY: bool            # 是否使用异步模式
    LIFESPAN: LifespanType   # 生命周期模式
    WORKERS: int             # 启动进程数
    LIMIT_CONCURRENCY: int   # 最大并发连接数
    BACKLOG: int             # 等待队列最大连接数
    LIMIT_MAX_REQUESTS: int  # HTTP最大请求数
    TIMEOUT_KEEP_ALIVE: int  # 保持连接时间(秒)

    # ================================================= #
    # ******************* API文档配置 ****************** #
    # ================================================= #
    DEBUG: bool             # 调试模式
    TITLE: str              # 文档标题
    VERSION: str            # 版本号
    DESCRIPTION: str        # 文档描述
    SUMMARY: str            # 文档概述
    DOCS_URL: str           # Swagger UI路径
    REDOC_URL: str          # ReDoc路径
    ROOT_PATH: str          # API路由前缀

    # ================================================= #
    # ******************** 跨域配置 ******************** #
    # ================================================= #
    CORS_ORIGIN_ENABLE: bool = True    # 是否启用跨域
    ALLOW_ORIGINS: List[str] = ["*"]   # 允许的域名列表
    ALLOW_METHODS: List[str] = ["*"]   # 允许的HTTP方法
    ALLOW_HEADERS: List[str] = ["*"]   # 允许的请求头
    ALLOW_CREDENTIALS: bool = True     # 是否允许携带cookie
    CORS_EXPOSE_HEADERS: list[str] = ['X-Request-ID']

    # ================================================= #
    # ******************* 登录认证配置 ****************** #
    # ================================================= #
    SECRET_KEY: str = "vgb0tnl9d58+6n-6h-ea&u^1#s0ccp!794=krylxcjq75vzps$"  # JWT密钥
    ALGORITHM: str = "HS256"                                                # JWT算法
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 60 * 24 * 1                     # access_token过期时间(秒)1 天
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 60 * 24 * 7                    # refresh_token过期时间(秒)7 天
    TOKEN_TYPE: str = "bearer"                                              # token类型
    TOKEN_REQUEST_PATH_EXCLUDE: list[str] = [                               # JWT / RBAC 路由白名单
        'api/v1/auth/login',
    ]

    # ================================================= #
    # ******************** 数据库配置 ******************* #
    # ================================================= #
    SQL_DB_ENABLE: bool = True                             # 是否启用数据库
    DATABASE_ECHO: bool | Literal['debug'] = False         # 是否显示SQL日志
    ECHO_POOL: bool | Literal['debug'] = False             # 是否显示连接池日志
    POOL_SIZE: int = 20                                    # 连接池大小
    MAX_OVERFLOW: int = 10                                 # 最大溢出连接数
    POOL_TIMEOUT: int = 30                                 # 连接超时时间(秒)
    POOL_RECYCLE: int = 1800                               # 连接回收时间(秒)
    POOL_PRE_PING: bool = True                             # 是否开启连接预检
    FUTURE: bool = True                                    # 是否使用SQLAlchemy 2.0特性
    AUTOCOMMIT: bool = False                               # 是否自动提交
    AUTOFETCH: bool = False                                # 是否自动获取
    EXPIRE_ON_COMMIT: bool = False                         # 是否在提交时过期

    # 数据库类型
    DATABASE_TYPE: Literal['sqlite','mysql', 'postgresql']
    

    # MySQL/PostgreSQL/SQLite数据库连接
    DATABASE_HOST: str
    DATABASE_PORT: int
    DATABASE_USER: str
    DATABASE_PASSWORD: str
    DATABASE_NAME: str

    # ================================================= #
    # ******************** MongoDB配置 ******************* #
    # ================================================= #
    MONGO_DB_ENABLE: bool # 是否启用MongoDB
    MONGO_DB_USER: str
    MONGO_DB_PASSWORD: str
    MONGO_DB_HOST: str
    MONGO_DB_PORT: int
    MONGO_DB_NAME: str

    # ================================================= #
    # ******************** Redis配置 ******************* #
    # ================================================= #
    REDIS_ENABLE: bool  # 是否启用Redis
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB_NAME: int
    REDIS_USER: str
    REDIS_PASSWORD: str

    # ================================================= #
    # ******************** 验证码配置 ******************* #
    # ================================================= #
    CAPTCHA_ENABLE: bool = True                              # 是否启用验证码
    CAPTCHA_EXPIRE_SECONDS: int = 60 * 1                     # 验证码过期时间(秒) 1分钟
    CAPTCHA_FONT_SIZE: int = 40                              # 字体大小
    CAPTCHA_FONT_PATH: str = 'static/assets/font/Arial.ttf'  # 字体路径

    # ================================================= #
    # ********************* 日志配置 ******************* #
    # ================================================= #
    LOGGER_DIR: Path = BASE_DIR.joinpath('logs')
    LOGGER_FORMAT: str = '%(asctime)s - %(levelname)8s - [%(name)s:%(filename)s:%(funcName)s:%(lineno)d] %(message)s' # 日志格式
    LOGGER_LEVEL: str = 'INFO'                                                                      # 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    BACKUPCOUNT: int = 10                                                                           # 日志文件备份数
    WHEN: str = 'MIDNIGHT'                                                                          # 日志分割时间 (MIDNIGHT, H, D, W0-W6)
    INTERVAL: int = 1                                                                               # 日志分割间隔
    ENCODING: str = 'utf-8'                                                                         # 日志编码
    LOG_RETENTION_DAYS: int = 30                                                                    # 日志保留天数，超过此天数的日志文件将被自动清理
    OPERATION_LOG_RECORD: bool = True                                                               # 是否记录操作日志
    IGNORE_OPERATION_FUNCTION: List[str] = ["get_captcha_for_login"]                                # 忽略记录的函数
    OPERATION_RECORD_METHOD: List[str] = ["POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]      # 需要记录的请求方法

    # ================================================= #
    # ******************* Gzip压缩配置 ******************* #
    # ================================================= #
    GZIP_ENABLE: bool = True        # 是否启用Gzip
    GZIP_MIN_SIZE: int = 1000       # 最小压缩大小(字节)
    GZIP_COMPRESS_LEVEL: int = 9    # 压缩级别(1-9)

    # ================================================= #
    # ***************** 静态文件配置 ***************** #
    # ================================================= #
    STATIC_ENABLE: bool = True                            # 是否启用静态文件
    STATIC_URL: str = "/static"                           # 访问路由
    STATIC_DIR: str = "static"                            # 目录名
    STATIC_ROOT: Path = BASE_DIR.joinpath(STATIC_DIR)     # 绝对路径

    # ================================================= #
    # ***************** 模版文件配置 ***************** #
    # ================================================= #
    TEMPLATE: str = "templates"
    TEMPLATE_DIR: Path = BASE_DIR.joinpath(TEMPLATE) # 模版目录

    # ================================================= #
    # ***************** 动态文件配置 ***************** #
    # ================================================= #
    UPLOAD_FILE_PATH: Path = Path('static/upload')    # 上传目录
    UPLOAD_MACHINE: str = 'A'                                      # 上传机器标识
    ALLOWED_EXTENSIONS: list[str] = [                              # 允许的文件类型
        # 图片
        '.bmp', '.gif', '.jpg', '.jpeg', '.png', '.ico', '.svg',
        # 文档
        '.csv', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.html', '.htm', '.txt', '.pdf',
        # 压缩包
        '.rar', '.zip', '.gz', '.bz2',
        # 视频
        '.mp4', '.avi', '.rmvb'
    ]
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 最大文件大小(10MB)

    # ================================================= #
    # ***************** Swagger配置 ***************** #
    # ================================================= #
    SWAGGER_CSS_URL: str = "static/swagger/swagger-ui/swagger-ui.css"
    SWAGGER_JS_URL: str = "static/swagger/swagger-ui/swagger-ui-bundle.js"
    REDOC_JS_URL: str = "static/swagger/redoc/bundles/redoc.standalone.js"
    FAVICON_URL: str = "static/swagger/favicon.png"

    # ================================================= #
    # ******************* 初始化数据 ****************** #
    # ================================================= #
    SCRIPT_DIR: Path = BASE_DIR.joinpath('app/scripts/data')  # 管理员路由目录

    # ================================================= #
    # ******************* 代码生成配置 ****************** #
    # ================================================= #
    author: str = 'FastapiAdmin'                    # 作者
    package_name: str = 'module_generator.gencode'  # 默认生成包路径 system 需改成自己的模块名称 如 system monitor tool
    auto_remove_pre: bool = False                   # 自动去除表前缀，默认是True
    table_prefix: str = 'gen_'                      # 表前缀（生成类名不会包含表前缀，多个用逗号分隔）
    allow_overwrite: bool = False                   # 是否允许生成文件覆盖到本地（自定义路径），默认不允许

    GEN_PATH: Path = BASE_DIR.joinpath('app/api/v1/module_generator/gen_backend_code')


    # ================================================= #
    # ******************* AI大模型配置 ****************** #
    # ================================================= #
    # https://bailian.console.aliyun.com/?spm=5176.29619931.J_AHgvE-XDhTWrtotIBlDQQ.13.74cd521clrmQ7o&tab=api#/api/?type=model&url=https%3A%2F%2Fhelp.aliyun.com%2Fdocument_detail%2F2712576.html&renderType=iframe
    OPENAI_BASE_URL: str
    OPENAI_API_KEY: str
    OPENAI_MODEL: str

    # ================================================= #
    # ******************* MCP 服务配置 ****************** #
    # ================================================= #
    # MCP 服务端配置
    MCP_SERVER_ENABLE: bool = True                      # 是否启用 MCP 服务
    MCP_SERVER_NAME: str = "operations-tools"           # MCP 服务名称
    MCP_SERVER_HOST: str = "0.0.0.0"                    # MCP 服务监听地址
    MCP_SERVER_PORT: int = 8002                         # MCP 服务监听端口
    MCP_SERVER_LOG_LEVEL: str = "INFO"                  # MCP 服务日志级别
    MCP_API_TIMEOUT: int = 300                          # MCP API 调用超时时间（秒）
    MCP_MAX_BATCH_SIZE: int = 50                        # MCP 批量操作最大数量
    
    # MCP 客户端配置
    MCP_CLIENT_ENABLE: bool = True                      # 是否启用 MCP 客户端
    MCP_SERVER_URL: str = "http://127.0.0.1:8002/mcp"   # MCP 服务器完整 URL（客户端连接地址）

    # ================================================= #
    # ******************* 其他配置 ******************* #
    # ================================================= #
    @property
    def MIDDLEWARE_LIST(self) -> List[Optional[str]]:
        """获取项目根目录"""
        # 中间件列表
        MIDDLEWARES: List[Optional[str]] = [
            "app.core.middlewares.CustomCORSMiddleware" if self.CORS_ORIGIN_ENABLE else None,
            "app.core.middlewares.RequestLogMiddleware" if self.OPERATION_LOG_RECORD else None,
            "app.core.middlewares.CustomGZipMiddleware" if self.GZIP_ENABLE else None,
        ]
        return MIDDLEWARES

    @property
    def EVENT_LIST(self) -> List[Optional[str]]:
        """获取事件列表"""
        EVENTS: List[Optional[str]] = [
            "app.core.database.mongodb_connect" if self.MONGO_DB_ENABLE else None,
            "app.core.database.redis_connect" if self.REDIS_ENABLE else None,
        ]
        return EVENTS

    @property
    def ASYNC_DB_URI(self) -> str:
        """获取异步数据库连接"""
        if self.DATABASE_TYPE == "mysql":
            return f"mysql+asyncmy://{self.DATABASE_USER}:{quote_plus(self.DATABASE_PASSWORD)}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}?charset=utf8mb4"
        elif self.DATABASE_TYPE == "postgresql":
            return f"postgresql+asyncpg://{self.DATABASE_USER}:{quote_plus(self.DATABASE_PASSWORD)}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        elif self.DATABASE_TYPE == "sqlite":
            return f"sqlite+aiosqlite:///{self.BASE_DIR.joinpath(self.DATABASE_NAME + '.db')}?characterEncoding=UTF-8"
        else:
            raise ValueError(f"数据库驱动不支持: {self.DATABASE_TYPE}, 请选择 请选择 mysql、postgresql、sqlite")

    @property
    def DB_URI(self) -> str:
        """获取同步数据库连接"""
        if self.DATABASE_TYPE == "mysql":
            return f"mysql+pymysql://{self.DATABASE_USER}:{quote_plus(self.DATABASE_PASSWORD)}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}?charset=utf8mb4"
        elif self.DATABASE_TYPE == "postgresql":
            return f"postgresql+psycopg2://{self.DATABASE_USER}:{quote_plus(self.DATABASE_PASSWORD)}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        elif self.DATABASE_TYPE == "sqlite":
            return f"sqlite:///{self.BASE_DIR.joinpath(self.DATABASE_NAME + '.db')}?charset=utf8"
        else:
            raise ValueError(f"数据库驱动不支持: {self.DATABASE_TYPE}, 请选择 mysql、postgresql、sqlite")

    @property
    def MONGO_DB_URI(self) -> str:
        """获取MongoDB连接"""
        return f"mongodb://{settings.MONGO_DB_USER}:{settings.MONGO_DB_PASSWORD}@{settings.MONGO_DB_HOST}:{settings.MONGO_DB_PORT}/{settings.MONGO_DB_NAME}"
    
    @property
    def REDIS_URI(self) -> str:
        """获取Redis连接"""
        return f"redis://{settings.REDIS_USER}:{self.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB_NAME}"
    
    @property
    def FASTAPI_CONFIG(self) -> dict[str, Any]:
        """获取FastAPI应用属性"""
        return {
            "debug": self.DEBUG,
            "title": self.TITLE,
            "version": self.VERSION,
            "description": self.DESCRIPTION,
            "summary": self.SUMMARY,
            "docs_url": None,
            "redoc_url": None,
            "root_path": self.ROOT_PATH
        }

    @property
    def UVICORN_CONFIG(self) -> Dict[str, Any]:
        """获取Uvicorn配置"""
        return {
            "host": self.SERVER_HOST,
            "port": self.SERVER_PORT,
            "reload": self.RELOAD,
            "log_config": {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "default": {
                        "()": "uvicorn.logging.DefaultFormatter",
                        "fmt": self.LOGGER_FORMAT,
                        "use_colors": None,
                    },
                    "access": {
                        "()": "uvicorn.logging.AccessFormatter",
                        "fmt": self.LOGGER_FORMAT,
                    },
                },
                "handlers": {
                    "console": {
                        "formatter": "default",
                        "class": "logging.StreamHandler",
                        "stream": "ext://sys.stderr",
                    },
                    "access_console": {
                        "formatter": "access",
                        "class": "logging.StreamHandler",
                        "stream": "ext://sys.stdout",
                    },
                    "file": {
                        "formatter": "default",
                        "class": "app.core.logger.CustomTimedRotatingFileHandler",
                        "filename": self.LOGGER_DIR.joinpath("all.log"),
                        "when": self.WHEN,
                        "backupCount": self.BACKUPCOUNT,
                        "encoding": self.ENCODING,
                    },
                },
                "loggers": {
                    "uvicorn": {"handlers": ["file", "console"], "level": self.LOGGER_LEVEL, "propagate": False},
                    "uvicorn.error": {"handlers": ["file", "console"], "level": self.LOGGER_LEVEL, "propagate": False},
                    "uvicorn.access": {"handlers": ["file", "access_console"], "level": self.LOGGER_LEVEL, "propagate": False},
                },
            },
            "workers": self.WORKERS,
            "limit_concurrency": self.LIMIT_CONCURRENCY,
            "backlog": self.BACKLOG,
            "limit_max_requests": self.LIMIT_MAX_REQUESTS,
            "timeout_keep_alive": self.TIMEOUT_KEEP_ALIVE,
            "lifespan": self.LIFESPAN,
            "factory": self.FACTORY,
        }

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """获取配置实例"""
    env = os.getenv('ENVIRONMENT', EnvironmentEnum.DEV.value)
    if env not in [e.value for e in EnvironmentEnum]:
        raise ValueError(f"无效的环境配置: {env}")

    env_file = _resolve_env_file(env)

    return Settings(_env_file=env_file)

settings = get_settings()

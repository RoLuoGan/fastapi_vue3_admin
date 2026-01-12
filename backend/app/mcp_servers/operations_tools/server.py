# -*- coding: utf-8 -*-
"""
MCP运维工具服务器主文件
将现有运维API封装为MCP协议的工具，供AI Agent调用
"""

import sys
import os
from pathlib import Path

# 确保能够导入 app 模块
# 获取当前脚本所在目录
current_file = Path(__file__).resolve()
# 计算 backend 目录（当前文件的父目录的父目录的父目录的父目录）
backend_dir = current_file.parent.parent.parent.parent
# 将 backend 目录添加到 Python 路径
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import asyncio
import logging
from typing import Optional
import uvicorn

# 先配置基础日志（在导入其他模块之前）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)  # 输出到 stderr，确保能被 stdio_client 捕获
    ]
)
logger = logging.getLogger(__name__)

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    # 尝试导入 streamable-http 支持
    try:
        from mcp.server.streamable_http import create_streamable_http_app
        STREAMABLE_HTTP_AVAILABLE = True
        logger.info("streamable-http 支持可用")
    except ImportError:
        STREAMABLE_HTTP_AVAILABLE = False
        logger.warning("streamable-http 支持不可用，将使用 stdio 模式")
    logger.info("MCP模块导入成功")
except Exception as e:
    print(f"ERROR: 导入MCP模块失败: {str(e)}", file=sys.stderr, flush=True)
    import traceback
    traceback.print_exc(file=sys.stderr)
    raise

try:
    from app.config.setting import settings
    logger.info("settings模块导入成功")
except Exception as e:
    print(f"ERROR: 导入settings模块失败: {str(e)}", file=sys.stderr, flush=True)
    import traceback
    traceback.print_exc(file=sys.stderr)
    raise

try:
    from app.core.database import session_connect
    logger.info("database模块导入成功")
except Exception as e:
    print(f"ERROR: 导入database模块失败: {str(e)}", file=sys.stderr, flush=True)
    import traceback
    traceback.print_exc(file=sys.stderr)
    raise

try:
    from app.api.v1.module_system.auth.schema import AuthSchema
    from app.api.v1.module_system.user.crud import UserCRUD
    logger.info("auth和user模块导入成功")
except Exception as e:
    print(f"ERROR: 导入auth/user模块失败: {str(e)}", file=sys.stderr, flush=True)
    import traceback
    traceback.print_exc(file=sys.stderr)
    raise

try:
    from .config import mcp_config
    from .tools.server_tools import register_server_tools
    from .tools.task_tools import register_task_tools
    from .tools.query_tools import register_query_tools
    logger.info("MCP工具模块导入成功")
    
    # 更新日志级别（在导入 mcp_config 之后）
    logger.setLevel(getattr(logging, mcp_config.log_level))
except Exception as e:
    print(f"ERROR: 导入MCP工具模块失败: {str(e)}", file=sys.stderr, flush=True)
    import traceback
    traceback.print_exc(file=sys.stderr)
    raise


class OperationsMCPServer:
    """运维工具MCP服务器"""
    
    def __init__(
        self, 
        user_id: Optional[int] = None,
        log_level: str = "INFO",
        api_base_url: Optional[str] = None,
        api_timeout: int = 300
    ):
        """
        初始化MCP服务器
        
        Args:
            user_id: 用户ID，用于权限控制（可选，默认使用管理员）
            log_level: 日志级别
            api_base_url: API基础URL（可选）
            api_timeout: API调用超时时间（秒）
        """
        # 更新配置
        mcp_config.log_level = log_level.upper()
        if api_base_url:
            mcp_config.api_base_url = api_base_url
        mcp_config.api_timeout = api_timeout
        
        # 更新日志级别
        logger.setLevel(getattr(logging, mcp_config.log_level))
        
        self.mcp_server = Server(mcp_config.server_name)
        self.user_id = user_id
        self.auth: Optional[AuthSchema] = None
        
    async def _init_auth(self):
        """初始化认证上下文"""
        try:
            # 创建数据库会话
            self.db = session_connect()
            logger.info("数据库会话已创建")
            
            # 如果没有指定用户ID，使用管理员用户（ID=1）
            user_id = self.user_id or 1
            logger.info(f"正在获取用户信息，user_id={user_id}")
            
            # 获取用户信息
            user_crud = UserCRUD(None)
            user_crud.db = self.db
            user = await user_crud.get_by_id_crud(id=user_id)
            
            if not user:
                raise ValueError(f"用户不存在: user_id={user_id}")
            
            # 创建认证上下文
            self.auth = AuthSchema(
                db=self.db,
                current_user=user,
                user_id=user.id,
                username=user.username
            )
            
            logger.info(f"MCP服务器认证初始化完成，用户: {user.username}")
        except Exception as e:
            logger.error(f"初始化认证上下文失败: {str(e)}", exc_info=True)
            raise
    
    async def setup(self):
        """设置MCP服务器"""
        # 初始化认证
        await self._init_auth()
        
        # 注册所有工具
        logger.info("开始注册MCP工具...")
        
        register_server_tools(self.mcp_server, self.auth)
        logger.info("✓ 服务器管理工具已注册")
        
        register_task_tools(self.mcp_server, self.auth)
        logger.info("✓ 任务管理工具已注册")
        
        register_query_tools(self.mcp_server, self.auth)
        logger.info("✓ 查询统计工具已注册")
        
        logger.info(f"MCP服务器 '{mcp_config.server_name}' 初始化完成")
    
    async def run(self, transport: str = "stdio", log_level: str = "INFO"):
        """
        运行MCP服务器
        
        Args:
            transport: 传输模式，"stdio" 或 "streamable-http"
            log_level: 日志级别（仅用于 streamable-http 模式）
        """
        try:
            # 先完成所有初始化工作
            logger.info("开始设置MCP服务器...")
            await self.setup()
            logger.info("MCP服务器设置完成")
            
            if transport == "streamable-http":
                # 使用 streamable-http 传输
                if not STREAMABLE_HTTP_AVAILABLE:
                    raise RuntimeError("streamable-http 传输不可用，请检查 MCP SDK 版本")
                
                logger.info("启动 streamable-http 服务器...")
                from fastapi import FastAPI
                from fastapi.middleware.cors import CORSMiddleware
                import contextlib
                
                # 创建 streamable-http 应用
                # 使用 create_streamable_http_app，server_factory 返回已初始化的服务器
                # 注意：server_factory 会在每次请求时调用，但我们已经初始化了服务器
                def server_factory():
                    logger.debug("创建MCP服务器实例（使用已初始化的服务器）")
                    return self.mcp_server
                
                logger.info("创建 streamable-http 应用...")
                mcp_app = create_streamable_http_app(
                    server_factory=server_factory,
                    stateless_http=False
                )
                logger.info("streamable-http 应用创建成功")
                
                # 创建 FastAPI 应用并挂载 MCP 应用
                @contextlib.asynccontextmanager
                async def lifespan(app: FastAPI):
                    # MCP 服务器的生命周期管理
                    logger.info("MCP服务器生命周期开始")
                    yield
                    logger.info("MCP服务器生命周期结束")
                
                app = FastAPI(
                    title="MCP Operations Tools Server",
                    description="MCP 运维工具服务器（streamable-http 模式）",
                    version="1.0.0",
                    lifespan=lifespan
                )
                
                # 配置 CORS
                app.add_middleware(
                    CORSMiddleware,
                    allow_origins=["*"],
                    allow_credentials=True,
                    allow_methods=["*"],
                    allow_headers=["*"],
                )
                
                # 添加健康检查端点（在挂载之前）
                @app.get("/health")
                async def health_check():
                    return {"status": "ok", "service": "mcp-operations-tools", "transport": "streamable-http"}
                
                # 挂载 MCP 应用到 /mcp 路径
                # 客户端访问 http://host:port/mcp
                # 注意：create_streamable_http_app 返回的是 Starlette 应用，可以直接使用 app.mount
                logger.info("挂载 MCP 应用到 /mcp 路径")
                app.mount("/mcp", mcp_app)
                logger.info("MCP 应用挂载完成，端点: POST http://{host}:{port}/mcp".format(host=os.getenv("MCP_HOST", "0.0.0.0"), port=os.getenv("MCP_PORT", "8001")))
                
                # 启动服务器
                host = os.getenv("MCP_HOST", "0.0.0.0")
                port = int(os.getenv("MCP_PORT", "8001"))
                logger.info(f"启动 streamable-http 服务器: {host}:{port}")
                logger.info(f"MCP端点: POST http://{host}:{port}/mcp")
                logger.info(f"健康检查: GET http://{host}:{port}/health")
                
                # 打印所有路由用于调试
                logger.debug("FastAPI应用路由:")
                for route in app.routes:
                    logger.debug(f"  {route.path} - {route.methods if hasattr(route, 'methods') else 'N/A'}")
                
                config = uvicorn.Config(app, host=host, port=port, log_level=log_level.lower())
                server_instance = uvicorn.Server(config)
                await server_instance.serve()
            else:
                # 使用stdio传输运行服务器
                logger.info("启动 stdio_server...")
                async with stdio_server() as (read_stream, write_stream):
                    logger.info("stdio_server 已启动，开始运行MCP服务器...")
                    await self.mcp_server.run(
                        read_stream,
                        write_stream,
                        self.mcp_server.create_initialization_options()
                    )
        except Exception as e:
            logger.error(f"MCP服务器运行失败: {str(e)}", exc_info=True)
            # 确保错误被输出到 stderr，以便客户端能够捕获
            import sys
            print(f"ERROR: {str(e)}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc(file=sys.stderr)
            raise


async def main(
    user_id: Optional[int] = None,
    log_level: str = "INFO",
    api_base_url: Optional[str] = None,
    api_timeout: int = 300,
    transport: str = "stdio"
):
    """
    主函数
    
    Args:
        user_id: 用户ID，用于权限控制（可选，默认使用管理员）
        log_level: 日志级别
        api_base_url: API基础URL（可选）
        api_timeout: API调用超时时间（秒）
        transport: 传输模式，"stdio" 或 "streamable-http"
    """
    server = OperationsMCPServer(
        user_id=user_id,
        log_level=log_level,
        api_base_url=api_base_url,
        api_timeout=api_timeout
    )
    await server.run(transport=transport, log_level=log_level)


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Operations Tools Server")
    parser.add_argument("--user-id", type=int, help="用户ID（可选，默认使用管理员）")
    parser.add_argument("--log-level", default="INFO", help="日志级别")
    parser.add_argument("--api-base-url", help="API基础URL")
    parser.add_argument("--api-timeout", type=int, default=300, help="API调用超时时间（秒）")
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="streamable-http", help="传输模式")
    parser.add_argument("--host", default="0.0.0.0", help="streamable-http 模式监听地址")
    parser.add_argument("--port", type=int, default=8001, help="streamable-http 模式监听端口")
    
    args = parser.parse_args()
    
    # 设置环境变量（用于 streamable-http 模式）
    if args.transport == "streamable-http":
        os.environ["MCP_HOST"] = args.host
        os.environ["MCP_PORT"] = str(args.port)
    
    try:
        logger.info("MCP服务器启动中...")
        logger.info(f"传输模式: {args.transport}")
        logger.info(f"用户ID: {args.user_id}")
        if args.transport == "streamable-http":
            logger.info(f"监听地址: {args.host}:{args.port}")
        logger.info(f"Python路径: {sys.path[:3]}")
        asyncio.run(main(
            user_id=args.user_id,
            log_level=args.log_level,
            api_base_url=args.api_base_url,
            api_timeout=args.api_timeout,
            transport=args.transport
        ))
    except KeyboardInterrupt:
        logger.info("MCP服务器被用户中断")
        print("INFO: MCP服务器被用户中断", file=sys.stderr, flush=True)
        sys.exit(0)
    except Exception as e:
        error_msg = f"MCP服务器启动失败: {str(e)}"
        print(f"ERROR: {error_msg}", file=sys.stderr, flush=True)
        logger.error(error_msg, exc_info=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

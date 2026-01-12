# -*- coding: utf-8 -*-
"""
MCP运维工具服务器主文件
将现有运维API封装为MCP协议的工具，供AI Agent调用
仅支持 streamable-http 传输模式
"""

import sys
import os
from pathlib import Path

# 确保能够导入 app 模块
current_file = Path(__file__).resolve()
backend_dir = current_file.parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import asyncio
from typing import Optional
import uvicorn

from app.core.logger import logger
from mcp.server import Server
from mcp.server.streamable_http import StreamableHTTPServerTransport
from app.config.setting import settings
from app.core.database import session_connect
from app.api.v1.module_system.auth.schema import AuthSchema
from app.api.v1.module_system.user.crud import UserCRUD

from .config import mcp_config
from .tools.server_tools import register_server_tools
from .tools.task_tools import register_task_tools
from .tools.query_tools import register_query_tools


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
            
            # 先创建一个临时的认证上下文（不带用户信息，不检查数据权限）
            temp_auth = AuthSchema(
                db=self.db,
                user=None,
                check_data_scope=False
            )
            
            # 使用临时认证上下文获取用户信息
            user_crud = UserCRUD(temp_auth)
            user = await user_crud.get_by_id_crud(id=user_id)
            
            if not user:
                raise ValueError(f"用户不存在: user_id={user_id}")
            
            # 创建完整的认证上下文（带用户信息）
            self.auth = AuthSchema(
                db=self.db,
                user=user,
                check_data_scope=False  # MCP服务器不需要检查数据权限
            )
            
            logger.info(f"MCP服务器认证初始化完成，用户: {user.username}")
        except Exception as e:
            logger.error(f"初始化认证上下文失败: {str(e)}")
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
    
    async def run(self, log_level: str = "INFO"):
        """
        运行MCP服务器（streamable-http 模式）
        
        Args:
            log_level: 日志级别
        """
        try:
            # 先完成所有初始化工作
            logger.info("开始设置MCP服务器...")
            await self.setup()
            logger.info("MCP服务器设置完成")
            
            # 使用 streamable-http 传输
            logger.info("启动 streamable-http 服务器...")
            from starlette.applications import Starlette
            from starlette.routing import Route, Mount
            from starlette.middleware import Middleware
            from starlette.middleware.cors import CORSMiddleware
            from starlette.responses import JSONResponse
            import contextlib
            import uuid
            
            # 从配置获取，允许环境变量覆盖
            host = os.getenv("MCP_HOST") or settings.MCP_SERVER_HOST
            port = int(os.getenv("MCP_PORT") or settings.MCP_SERVER_PORT)
            
            # 存储活跃的会话
            active_sessions: dict[str, tuple[StreamableHTTPServerTransport, asyncio.Task]] = {}
            
            # 健康检查端点
            async def health_check(request):
                return JSONResponse({
                    "status": "ok",
                    "service": "mcp-operations-tools",
                    "transport": "streamable-http",
                    "active_sessions": len(active_sessions)
                })
            
            # MCP ASGI 应用
            async def mcp_asgi_app(scope, receive, send):
                """ASGI 应用，为每个新会话创建独立的 transport"""
                if scope["type"] != "http":
                    return
                
                # 从请求头获取会话ID
                headers = dict(scope.get("headers", []))
                session_id = headers.get(b"mcp-session-id", b"").decode() or None
                
                if session_id and session_id in active_sessions:
                    # 已存在的会话，使用现有 transport
                    transport, _ = active_sessions[session_id]
                    await transport.handle_request(scope, receive, send)
                    return
                
                # 新会话：创建新的 transport
                new_session_id = str(uuid.uuid4())
                logger.info(f"创建新的 MCP 会话: {new_session_id}")
                
                transport = StreamableHTTPServerTransport(
                    mcp_session_id=new_session_id,
                    is_json_response_enabled=False
                )
                
                # 启动 MCP 服务器处理该会话
                async def run_session():
                    try:
                        async with transport.connect() as (read_stream, write_stream):
                            logger.info(f"MCP 会话 {new_session_id} 已建立")
                            await self.mcp_server.run(
                                read_stream,
                                write_stream,
                                self.mcp_server.create_initialization_options()
                            )
                    except Exception as e:
                        logger.error(f"MCP 会话 {new_session_id} 错误: {e}")
                    finally:
                        # 会话结束，清理
                        if new_session_id in active_sessions:
                            del active_sessions[new_session_id]
                            logger.info(f"MCP 会话 {new_session_id} 已清理")
                
                # 启动会话任务
                session_task = asyncio.create_task(run_session())
                active_sessions[new_session_id] = (transport, session_task)
                
                # 等待一小段时间让 transport 准备好
                await asyncio.sleep(0.01)
                
                # 处理当前请求
                await transport.handle_request(scope, receive, send)
            
            # lifespan
            @contextlib.asynccontextmanager
            async def lifespan(app):
                logger.info("MCP 服务器生命周期开始")
                yield
                # 清理所有活跃会话
                logger.info("MCP 服务器生命周期结束，清理活跃会话...")
                for session_id, (transport, task) in list(active_sessions.items()):
                    await transport.terminate()
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                active_sessions.clear()
            
            # 创建 Starlette 应用
            app = Starlette(
                debug=True,
                lifespan=lifespan,
                routes=[
                    Route("/health", health_check, methods=["GET"]),
                    Mount("/mcp", app=mcp_asgi_app),
                ],
                middleware=[
                    Middleware(
                        CORSMiddleware,
                        allow_origins=["*"],
                        allow_credentials=True,
                        allow_methods=["*"],
                        allow_headers=["*"],
                    ),
                ],
            )
            
            logger.info(f"启动 streamable-http 服务器: {host}:{port}")
            logger.info(f"MCP端点: POST http://{host}:{port}/mcp")
            logger.info(f"健康检查: GET http://{host}:{port}/health")
            
            config = uvicorn.Config(app, host=host, port=port, log_level=log_level.lower())
            server_instance = uvicorn.Server(config)
            await server_instance.serve()
            
        except Exception as e:
            logger.error(f"MCP服务器运行失败: {str(e)}")
            raise


async def main(
    user_id: Optional[int] = None,
    log_level: str = "INFO",
    api_base_url: Optional[str] = None,
    api_timeout: int = 300
):
    """
    主函数
    
    Args:
        user_id: 用户ID，用于权限控制（可选，默认使用管理员）
        log_level: 日志级别
        api_base_url: API基础URL（可选）
        api_timeout: API调用超时时间（秒）
    """
    server = OperationsMCPServer(
        user_id=user_id,
        log_level=log_level,
        api_base_url=api_base_url,
        api_timeout=api_timeout
    )
    await server.run(log_level=log_level)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Operations Tools Server")
    parser.add_argument("--user-id", type=int, help="用户ID（可选，默认使用管理员）")
    parser.add_argument("--log-level", default="INFO", help="日志级别")
    parser.add_argument("--api-base-url", help="API基础URL")
    parser.add_argument("--api-timeout", type=int, default=300, help="API调用超时时间（秒）")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=8001, help="监听端口")
    
    args = parser.parse_args()
    
    # 设置环境变量
    os.environ["MCP_HOST"] = args.host
    os.environ["MCP_PORT"] = str(args.port)
    
    try:
        logger.info("MCP服务器启动中...")
        logger.info(f"用户ID: {args.user_id}")
        logger.info(f"监听地址: {args.host}:{args.port}")
        asyncio.run(main(
            user_id=args.user_id,
            log_level=args.log_level,
            api_base_url=args.api_base_url,
            api_timeout=args.api_timeout
        ))
    except KeyboardInterrupt:
        logger.info("MCP服务器被用户中断")
        sys.exit(0)
    except Exception as e:
        logger.error(f"MCP服务器启动失败: {str(e)}")
        sys.exit(1)

# -*- coding: utf-8 -*-

import os
import sys
import uvicorn
import typer
from fastapi import FastAPI
from alembic import command
from alembic.config import Config

from app.common.enums import EnvironmentEnum

shell_app = typer.Typer()

# 初始化 Alembic 配置
alembic_cfg = Config("alembic.ini")

def create_app() -> FastAPI:
    
    from app.config.setting import settings
    from app.plugin.init_app import (
        register_middlewares,
        register_exceptions,
        register_routers,
        register_files,
        reset_api_docs,
        lifespan
    )
    # 创建FastAPI应用
    app = FastAPI(**settings.FASTAPI_CONFIG, lifespan=lifespan)

    # 注册异常处理器
    register_exceptions(app)
    # 注册中间件
    register_middlewares(app)
    # 注册路由
    register_routers(app)
    # 注册静态文件
    register_files(app)
    # 重设API文档
    reset_api_docs(app)

    return app


@shell_app.command()
def run(env: EnvironmentEnum = typer.Option(EnvironmentEnum.DEV, "--env", help="运行环境 (dev, prod)")):
    typer.echo("项目启动中..")
    # 设置环境变量
    os.environ["ENVIRONMENT"] = env.value
    
    # 确保在设置环境变量后导入配置
    from app.config.setting import settings
    
    # 启动uvicorn服务
    uvicorn.run(
        app='main:create_app',
        **settings.UVICORN_CONFIG
    )

@shell_app.command()
def revision(message: str, env: EnvironmentEnum = typer.Option(EnvironmentEnum.DEV, "--env", help="运行环境 (dev, test, prod)")):
    """
    生成新的 Alembic 迁移脚本。
    """
    os.environ["ENVIRONMENT"] = env.value
    command.revision(alembic_cfg, message=message, autogenerate=True)
    typer.echo(f"迁移脚本已生成: {message}")

@shell_app.command()
def upgrade(env: EnvironmentEnum = typer.Option(EnvironmentEnum.DEV, "--env", help="运行环境 (dev, test, prod)")):
    """
    应用最新的 Alembic 迁移。
    """
    os.environ["ENVIRONMENT"] = env.value
    command.upgrade(alembic_cfg, "head")
    typer.echo("所有迁移已应用。")


@shell_app.command()
def celery_worker(
    env: EnvironmentEnum = typer.Option(EnvironmentEnum.DEV, "--env", help="运行环境 (dev, prod)"),
    queue: str = typer.Option("scripts", "--queue", "-q", help="执行队列名称"),
    concurrency: int = typer.Option(4, "--concurrency", "-c", help="并发数"),
    loglevel: str = typer.Option("info", "--loglevel", "-l", help="日志级别 (debug, info, warning, error)"),
    hostname: str = typer.Option(None, "--hostname", "-n", help="Worker主机名（可选，默认自动生成）"),
    register: bool = typer.Option(True, "--register/--no-register", help="是否自动注册到管理系统"),
    pool: str = typer.Option(None, "--pool", "-P", help="进程池类型 (prefork/solo/threads/gevent, Windows默认solo)"),
):
    """
    启动 Celery Worker 进程。
    """
    import subprocess
    import socket
    import platform
    
    typer.echo(f"启动 Celery Worker...")
    typer.echo(f"  环境: {env.value}")
    typer.echo(f"  队列: {queue}")
    typer.echo(f"  并发数: {concurrency}")
    typer.echo(f"  日志级别: {loglevel}")
    
    # 检测操作系统，Windows 不支持 prefork，需要使用 solo 或 threads
    is_windows = platform.system() == "Windows"
    if pool is None:
        if is_windows:
            pool = "solo"  # Windows 默认使用 solo（单进程）
            typer.echo(f"  检测到 Windows 系统，使用 solo 进程池")
        else:
            pool = "prefork"  # Linux/Mac 默认使用 prefork
    
    typer.echo(f"  进程池: {pool}")
    
    # 设置环境变量
    os.environ["ENVIRONMENT"] = env.value
    os.environ["CELERY_QUEUE"] = queue
    
    # 生成 hostname
    if not hostname:
        hostname = f"{queue}@{socket.gethostname()}"
    typer.echo(f"  主机名: {hostname}")
    
    # 获取本机IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "127.0.0.1"
    
    os.environ["CELERY_WORKER_IP"] = local_ip
    os.environ["CELERY_WORKER_HOSTNAME"] = hostname
    os.environ["CELERY_WORKER_QUEUE"] = queue
    os.environ["CELERY_WORKER_REGISTER"] = "1" if register else "0"
    
    typer.echo(f"  节点IP: {local_ip}")
    
    # 构建 Celery 启动命令
    celery_cmd = [
        "celery",
        "-A", "app.celery_app:celery_app",
        "worker",
        f"--queues={queue}",
        f"--pool={pool}",
        f"--loglevel={loglevel}",
        f"--hostname={hostname}",
    ]
    
    # solo 模式不支持并发数参数，其他模式需要设置并发数
    if pool != "solo":
        celery_cmd.append(f"--concurrency={concurrency}")
    elif concurrency != 1:
        typer.echo(f"  警告: solo 模式不支持并发数设置，已忽略 --concurrency={concurrency}")
    
    typer.echo(f"\n执行命令: {' '.join(celery_cmd)}\n")
    
    # 启动 Celery Worker
    try:
        subprocess.run(celery_cmd, check=True)
    except KeyboardInterrupt:
        typer.echo("\nCelery Worker 已停止")
    except subprocess.CalledProcessError as e:
        typer.echo(f"Celery Worker 启动失败: {e}", err=True)
        raise typer.Exit(code=1)


@shell_app.command()
def celery_beat(
    env: EnvironmentEnum = typer.Option(EnvironmentEnum.DEV, "--env", help="运行环境 (dev, prod)"),
    loglevel: str = typer.Option("info", "--loglevel", "-l", help="日志级别 (debug, info, warning, error)"),
):
    """
    启动 Celery Beat 定时任务调度器。
    """
    import subprocess
    
    typer.echo(f"启动 Celery Beat...")
    typer.echo(f"  环境: {env.value}")
    typer.echo(f"  日志级别: {loglevel}")
    
    # 设置环境变量
    os.environ["ENVIRONMENT"] = env.value
    
    # 构建 Celery Beat 启动命令
    celery_cmd = [
        "celery",
        "-A", "app.celery_app:celery_app",
        "beat",
        f"--loglevel={loglevel}",
    ]
    
    typer.echo(f"\n执行命令: {' '.join(celery_cmd)}\n")
    
    # 启动 Celery Beat
    try:
        subprocess.run(celery_cmd, check=True)
    except KeyboardInterrupt:
        typer.echo("\nCelery Beat 已停止")
    except subprocess.CalledProcessError as e:
        typer.echo(f"Celery Beat 启动失败: {e}", err=True)
        raise typer.Exit(code=1)


@shell_app.command()
def mcp_server(
    env: EnvironmentEnum = typer.Option(EnvironmentEnum.DEV, "--env", help="运行环境 (dev, prod)"),
    host: str = typer.Option(None, "--host", help="监听地址（默认从配置读取）"),
    port: int = typer.Option(None, "--port", help="监听端口（默认从配置读取）"),
    log_level: str = typer.Option(None, "--log-level", help="日志级别（默认从配置读取）"),
    user_id: int = typer.Option(None, "--user-id", "-u", help="用户ID（可选，默认使用管理员）"),
):
    """
    启动 MCP streamable-http 服务器。
    
    使用官方 MCP SDK 的 streamable-http 模式启动独立服务器。
    配置优先级：命令行参数 > .env 配置文件
    """
    import asyncio
    import importlib
    
    # 设置环境变量（必须在导入 settings 之前）
    os.environ["ENVIRONMENT"] = env.value
    
    # 导入配置（在设置环境变量之后）
    from app.config.setting import settings
    
    # 使用命令行参数或配置文件的值
    actual_host = host or settings.MCP_SERVER_HOST
    actual_port = port or settings.MCP_SERVER_PORT
    actual_log_level = log_level or settings.MCP_SERVER_LOG_LEVEL
    
    typer.echo("=" * 60)
    typer.echo("启动 MCP streamable-http 服务器")
    typer.echo("=" * 60)
    typer.echo(f"  环境: {env.value}")
    typer.echo(f"  监听地址: {actual_host}")
    typer.echo(f"  监听端口: {actual_port}")
    typer.echo(f"  日志级别: {actual_log_level}")
    if user_id:
        typer.echo(f"  用户ID: {user_id}")
    typer.echo("")
    typer.echo(f"端点地址: POST http://{actual_host}:{actual_port}/mcp")
    typer.echo("")
    typer.echo("客户端配置：")
    typer.echo(f"  设置环境变量: MCP_SERVER_URL=http://{actual_host}:{actual_port}/mcp")
    typer.echo("=" * 60)
    typer.echo("")
    
    # 设置环境变量供服务端使用
    os.environ["MCP_HOST"] = actual_host
    os.environ["MCP_PORT"] = str(actual_port)
    
    # 使用 importlib 导入模块并调用主函数
    try:
        server_module = importlib.import_module("app.mcp_servers.operations_tools.server")
        asyncio.run(server_module.main(
            user_id=user_id,
            log_level=actual_log_level.upper()
        ))
    except KeyboardInterrupt:
        typer.echo("\nMCP 服务器已停止")
    except Exception as e:
        typer.echo(f"MCP 服务器启动失败: {e}", err=True)
        raise typer.Exit(code=1)


if __name__ == '__main__':
    # 启动服务
    # python3 main.py run --env=dev(不加默认为dev)
    # 生成迁移
    # python3 main.py revision "数据迁移" --env=dev(不加默认为dev)
    # 应用迁移
    # python3 main.py upgrade --env=dev(不加默认为dev)
    # 启动 Celery Worker
    # python3 main.py celery-worker --env=dev --queue=scripts --concurrency=4
    # 启动 Celery Beat
    # python3 main.py celery-beat --env=dev
    # 启动 MCP streamable-http 服务器
    # python3 main.py mcp-server --env=dev --host=0.0.0.0 --port=8001
    # python3 main.py mcp-server --env=dev --port=8001 --user-id=1
    
    shell_app()

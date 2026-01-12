# -*- coding: utf-8 -*-
"""
MCP服务器配置
从全局配置 settings 统一读取
"""

from pathlib import Path
from pydantic import BaseModel

from app.config.setting import settings


class MCPConfig(BaseModel):
    """MCP服务器配置（从 settings 读取）"""
    
    # 服务器信息
    server_name: str = settings.MCP_SERVER_NAME
    server_version: str = "1.0.0"
    
    # 服务端配置
    host: str = settings.MCP_SERVER_HOST
    port: int = settings.MCP_SERVER_PORT
    server_url: str = settings.MCP_SERVER_URL  # 完整的服务器 URL（供客户端使用）
    
    # API配置（用于调用现有API）
    api_base_url: str = f"http://localhost:{settings.SERVER_PORT}"
    api_timeout: int = settings.MCP_API_TIMEOUT
    
    # 日志配置
    log_level: str = settings.MCP_SERVER_LOG_LEVEL
    log_dir: Path = settings.LOGGER_DIR / "mcp"
    
    # MCP配置
    max_batch_size: int = settings.MCP_MAX_BATCH_SIZE
    
    
# 全局配置实例
mcp_config = MCPConfig()

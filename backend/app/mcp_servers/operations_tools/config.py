# -*- coding: utf-8 -*-
"""
MCP服务器配置
"""

from pathlib import Path
from pydantic import BaseModel
from typing import Optional


class MCPConfig(BaseModel):
    """MCP服务器配置"""
    
    # 服务器信息
    server_name: str = "operations-tools"
    server_version: str = "1.0.0"
    
    # FastAPI配置（用于调用现有API）
    api_base_url: str = "http://localhost:8000"
    api_timeout: int = 300  # API调用超时时间（秒）
    
    # 日志配置
    log_level: str = "INFO"
    log_dir: Path = Path(__file__).parent.parent.parent / "logs" / "mcp"
    
    # MCP配置
    max_batch_size: int = 50  # 批量操作最大数量
    
    
# 全局配置实例
mcp_config = MCPConfig()

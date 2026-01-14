# -*- coding: utf-8 -*-
"""
MCP工具注册入口
统一注册所有工具，避免装饰器覆盖问题
"""

from typing import List, Dict, Any
from mcp.server import Server
from mcp.types import Tool, TextContent

from app.api.v1.module_system.auth.schema import AuthSchema

# 导入各模块的工具定义
from .server_tools import SERVER_TOOLS, handle_server_tool
from .task_tools import TASK_TOOLS, handle_task_tool
from .query_tools import QUERY_TOOLS, handle_query_tool


def register_all_tools(mcp_server: Server, auth: AuthSchema):
    """
    统一注册所有MCP工具
    
    Args:
        mcp_server: MCP服务器实例
        auth: 认证上下文
    """
    
    # 统一注册工具列表（合并所有工具）
    @mcp_server.list_tools()
    async def list_all_tools() -> List[Tool]:
        """列出所有可用工具"""
        return SERVER_TOOLS + TASK_TOOLS + QUERY_TOOLS
    
    # 统一注册工具调用处理器
    @mcp_server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """统一工具调用处理器"""
        # 根据工具名称分发到对应的处理器
        tool_names = {tool.name for tool in SERVER_TOOLS}
        if name in tool_names:
            return await handle_server_tool(name, arguments, auth)
        
        tool_names = {tool.name for tool in TASK_TOOLS}
        if name in tool_names:
            return await handle_task_tool(name, arguments, auth)
        
        tool_names = {tool.name for tool in QUERY_TOOLS}
        if name in tool_names:
            return await handle_query_tool(name, arguments, auth)
        
        return [TextContent(type="text", text=f"未知工具: {name}")]


__all__ = ['register_all_tools']

# -*- coding: utf-8 -*-
"""
MCP客户端封装
使用官方 MCP SDK 的 streamable-http 客户端
"""

from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from mcp import ClientSession

from app.core.logger import logger
from app.config.setting import settings


class MCPClient:
    """MCP客户端（使用官方 SDK streamable-http）"""
    
    def __init__(self, server_url: Optional[str] = None, user_id: Optional[int] = None):
        """
        初始化MCP客户端
        
        Args:
            server_url: MCP服务器URL（可选，默认从配置获取）
            user_id: 用户ID（可选）
        """
        # 如果没有提供URL，使用配置文件中的设置
        if server_url is None:
            self.server_url = settings.MCP_SERVER_URL
            logger.info(f"使用配置的MCP服务器: {self.server_url}")
        else:
            self.server_url = server_url
            logger.info(f"使用指定的MCP服务器: {self.server_url}")
        
        self.user_id = user_id
        self.tools: List[Dict[str, Any]] = []
        self._session: Optional[ClientSession] = None
        
    @asynccontextmanager
    async def connect(self):
        """连接到MCP服务器"""
        # 检查 MCP 客户端是否启用
        if not settings.MCP_CLIENT_ENABLE:
            raise RuntimeError("MCP 客户端未启用，请在配置中设置 MCP_CLIENT_ENABLE=True")
        
        try:
            logger.info(f"连接到MCP服务器: {self.server_url}")
            logger.info(f"用户ID: {self.user_id}")
            
            # 使用官方 SDK 的 streamable-http 客户端
            try:
                from mcp.client.streamable_http import streamablehttp_client
            except ImportError:
                raise RuntimeError(
                    "无法导入 streamable-http 客户端。"
                    "请确保 MCP SDK 版本 >= 1.10.0 并支持 streamable-http transport。"
                    "安装命令: pip install 'mcp>=1.10.0'"
                )
            
            # 准备请求头
            headers = {
                "X-User-ID": str(self.user_id) if self.user_id else "1"
            }
            
            # 使用 streamablehttp_client 连接
            async with streamablehttp_client(self.server_url, headers=headers) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    self._session = session
                    
                    # 初始化会话
                    logger.info("正在初始化MCP会话...")
                    await session.initialize()
                    logger.info("MCP会话初始化成功")
                    
                    # 获取可用工具列表
                    logger.info("正在获取MCP工具列表...")
                    tools_result = await session.list_tools()
                    self.tools = [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.inputSchema
                        }
                        for tool in tools_result.tools
                    ]
                    logger.info(f"MCP客户端已连接，可用工具: {len(self.tools)}个")
                    
                    yield self
            
        except Exception as e:
            logger.error(f"MCP客户端连接失败: {str(e)}")
            logger.error(f"服务器URL: {self.server_url}")
            logger.error(f"用户ID: {self.user_id}")
            raise
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用MCP工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        logger.info(f"调用MCP工具: {tool_name}, 参数: {arguments}")
        
        if not self._session:
            raise RuntimeError("MCP会话未初始化，请先调用 connect()")
        
        try:
            result = await self._session.call_tool(tool_name, arguments)
            
            # 解析返回结果
            # MCP工具调用返回格式: CallToolResult(content=[TextContent(...)])
            if result and result.content:
                response_text = ""
                for content_item in result.content:
                    if hasattr(content_item, 'text'):
                        response_text += content_item.text
                    elif isinstance(content_item, dict):
                        if content_item.get("type") == "text" and "text" in content_item:
                            response_text += content_item["text"]
                        elif "text" in content_item:
                            response_text += content_item["text"]
                    elif isinstance(content_item, str):
                        response_text += content_item
                
                return {
                    "success": True,
                    "result": response_text,
                    "raw": result
                }
            
            return {
                "success": True,
                "result": "操作完成",
                "raw": result
            }
                
        except Exception as e:
            logger.error(f"调用MCP工具失败: {tool_name}, 错误: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        return [
            {
                "name": tool.get("name"),
                "description": tool.get("description"),
                "parameters": tool.get("inputSchema", {})
            }
            for tool in self.tools
        ]
    
    def get_tool_by_name(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取工具信息"""
        for tool in self.tools:
            if tool.get("name") == tool_name:
                return {
                    "name": tool.get("name"),
                    "description": tool.get("description"),
                    "parameters": tool.get("inputSchema", {})
                }
        return None


# 导出 MCPClient
__all__ = ['MCPClient']

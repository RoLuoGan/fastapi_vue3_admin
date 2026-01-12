# -*- coding: utf-8 -*-
"""
服务器节点管理工具
封装服务器节点的CRUD操作
"""

from typing import Optional, List, Dict, Any
from mcp.server import Server
from mcp.types import Tool, TextContent

from app.api.v1.module_operations.server.service import ServerService
from app.api.v1.module_operations.server.schema import ServerCreateSchema, ServerUpdateSchema
from app.api.v1.module_system.auth.schema import AuthSchema


def register_server_tools(mcp_server: Server, auth: AuthSchema):
    """注册服务器节点管理工具"""
    
    @mcp_server.list_tools()
    async def list_tools() -> List[Tool]:
        """列出所有服务器管理工具"""
        return [
            Tool(
                name="list_servers",
                description="查询服务器节点列表，支持分页和条件过滤",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project": {
                            "type": "string",
                            "description": "项目名称过滤"
                        },
                        "status": {
                            "type": "boolean",
                            "description": "状态过滤（True启用/False禁用）"
                        },
                        "ip": {
                            "type": "string",
                            "description": "IP地址过滤"
                        },
                        "page": {
                            "type": "integer",
                            "description": "页码",
                            "default": 1
                        },
                        "page_size": {
                            "type": "integer",
                            "description": "每页数量",
                            "default": 10
                        }
                    }
                }
            ),
            Tool(
                name="get_server",
                description="根据ID获取服务器节点详细信息",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "integer",
                            "description": "服务器节点ID"
                        }
                    },
                    "required": ["id"]
                }
            ),
            Tool(
                name="create_server",
                description="创建新的服务器节点",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "节点名称"
                        },
                        "ip": {
                            "type": "string",
                            "description": "IP地址"
                        },
                        "port": {
                            "type": "integer",
                            "description": "SSH端口",
                            "default": 22
                        },
                        "username": {
                            "type": "string",
                            "description": "登录用户名"
                        },
                        "password": {
                            "type": "string",
                            "description": "登录密码（可选，与private_key二选一）"
                        },
                        "project": {
                            "type": "string",
                            "description": "所属项目"
                        },
                        "environment": {
                            "type": "string",
                            "description": "环境标识（如production、staging、dev）"
                        },
                        "status": {
                            "type": "boolean",
                            "description": "是否启用",
                            "default": True
                        }
                    },
                    "required": ["name", "ip", "username", "project"]
                }
            ),
            Tool(
                name="update_server",
                description="更新服务器节点信息",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "integer",
                            "description": "服务器节点ID"
                        },
                        "name": {
                            "type": "string",
                            "description": "节点名称"
                        },
                        "status": {
                            "type": "boolean",
                            "description": "是否启用"
                        },
                        "description": {
                            "type": "string",
                            "description": "节点描述"
                        }
                    },
                    "required": ["id"]
                }
            ),
            Tool(
                name="delete_servers",
                description="删除服务器节点（支持批量删除）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "要删除的节点ID列表"
                        }
                    },
                    "required": ["ids"]
                }
            )
        ]
    
    @mcp_server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """调用服务器管理工具"""
        
        if name == "list_servers":
            # 构建搜索条件
            search = {}
            if "project" in arguments:
                search["project"] = arguments["project"]
            if "status" in arguments:
                search["status"] = arguments["status"]
            if "ip" in arguments:
                search["ip"] = arguments["ip"]
            
            result = await ServerService.get_server_page_service(
                auth=auth,
                page_no=arguments.get("page", 1),
                page_size=arguments.get("page_size", 10),
                search=search
            )
            
            return [TextContent(
                type="text",
                text=f"查询成功，共找到 {result.get('total', 0)} 个节点：\n{result}"
            )]
        
        elif name == "get_server":
            result = await ServerService.get_server_detail_service(
                auth=auth,
                id=arguments["id"]
            )
            return [TextContent(
                type="text",
                text=f"节点详情：\n{result}"
            )]
        
        elif name == "create_server":
            schema = ServerCreateSchema(**arguments)
            result = await ServerService.create_server_service(
                auth=auth,
                data=schema
            )
            return [TextContent(
                type="text",
                text=f"创建成功，节点ID: {result.get('id')}\n{result}"
            )]
        
        elif name == "update_server":
            node_id = arguments.pop("id")
            schema = ServerUpdateSchema(**arguments)
            result = await ServerService.update_server_service(
                auth=auth,
                id=node_id,
                data=schema
            )
            return [TextContent(
                type="text",
                text=f"更新成功\n{result}"
            )]
        
        elif name == "delete_servers":
            result = await ServerService.batch_delete_server_service(
                auth=auth,
                ids=arguments["ids"]
            )
            return [TextContent(
                type="text",
                text=f"删除操作完成\n{result}"
            )]
        
        else:
            return [TextContent(
                type="text",
                text=f"未知工具: {name}"
            )]

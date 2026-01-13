# -*- coding: utf-8 -*-
"""
服务器节点管理工具
封装服务器节点的CRUD操作
"""

import logging
from typing import Optional, List, Dict, Any
from mcp.server import Server
from mcp.types import Tool, TextContent

from app.api.v1.module_operations.server.service import ServerService
from app.api.v1.module_operations.server.schema import ServerCreateSchema, ServerUpdateSchema
from app.api.v1.module_system.auth.schema import AuthSchema

logger = logging.getLogger(__name__)


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
                        },
                        "order_by": {
                            "type": "array",
                            "description": "排序规则，例如：[{\"created_at\": \"desc\"}]",
                            "items": {
                                "type": "object",
                                "additionalProperties": {
                                    "type": "string",
                                    "enum": ["asc", "desc"]
                                }
                            }
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
        
        # 记录工具调用
        logger.info(f"[MCP工具调用] 工具名称: {name}, 参数: {arguments}")
        
        try:
            if name == "list_servers":
                # 构建搜索条件
                search = {}
                if "project" in arguments:
                    search["project"] = arguments["project"]
                if "status" in arguments:
                    search["status"] = arguments["status"]
                if "ip" in arguments:
                    search["ip"] = arguments["ip"]
                
                # 获取排序参数
                order_by = arguments.get("order_by", [{"created_at": "desc"}])
                
                logger.info(f"[MCP工具调用] list_servers - 搜索条件: {search}, 排序: {order_by}")
                
                result = await ServerService.get_server_page_service(
                    auth=auth,
                    page_no=arguments.get("page", 1),
                    page_size=arguments.get("page_size", 10),
                    search=search,
                    order_by=order_by
                )
                
                logger.info(f"[MCP工具返回] list_servers - 总数: {result.get('total', 0)}, 数据: {result}")
                
                return [TextContent(
                    type="text",
                    text=f"查询成功，共找到 {result.get('total', 0)} 个节点：\n{result}"
                )]
            
            elif name == "get_server":
                logger.info(f"[MCP工具调用] get_server - 节点ID: {arguments['id']}")
                
                result = await ServerService.get_server_detail_service(
                    auth=auth,
                    id=arguments["id"]
                )
                
                logger.info(f"[MCP工具返回] get_server - 结果: {result}")
                
                return [TextContent(
                    type="text",
                    text=f"节点详情：\n{result}"
                )]
            
            elif name == "create_server":
                logger.info(f"[MCP工具调用] create_server - 参数: {arguments}")
                
                schema = ServerCreateSchema(**arguments)
                result = await ServerService.create_server_service(
                    auth=auth,
                    data=schema
                )
                
                logger.info(f"[MCP工具返回] create_server - 节点ID: {result.get('id')}, 结果: {result}")
                
                return [TextContent(
                    type="text",
                    text=f"创建成功，节点ID: {result.get('id')}\n{result}"
                )]
            
            elif name == "update_server":
                node_id = arguments.pop("id")
                logger.info(f"[MCP工具调用] update_server - 节点ID: {node_id}, 参数: {arguments}")
                
                schema = ServerUpdateSchema(**arguments)
                result = await ServerService.update_server_service(
                    auth=auth,
                    id=node_id,
                    data=schema
                )
                
                logger.info(f"[MCP工具返回] update_server - 结果: {result}")
                
                return [TextContent(
                    type="text",
                    text=f"更新成功\n{result}"
                )]
            
            elif name == "delete_servers":
                logger.info(f"[MCP工具调用] delete_servers - 节点IDs: {arguments['ids']}")
                
                result = await ServerService.batch_delete_server_service(
                    auth=auth,
                    ids=arguments["ids"]
                )
                
                logger.info(f"[MCP工具返回] delete_servers - 结果: {result}")
                
                return [TextContent(
                    type="text",
                    text=f"删除操作完成\n{result}"
                )]
            
            else:
                logger.warning(f"[MCP工具调用] 未知工具: {name}")
                return [TextContent(
                    type="text",
                    text=f"未知工具: {name}"
                )]
        
        except Exception as e:
            logger.error(f"[MCP工具错误] 工具名称: {name}, 错误: {str(e)}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"工具调用失败: {str(e)}"
            )]

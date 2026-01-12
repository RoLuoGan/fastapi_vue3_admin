# -*- coding: utf-8 -*-
"""
综合查询工具
提供跨模块的查询和统计功能
"""

from typing import List, Dict, Any
from mcp.server import Server
from mcp.types import Tool, TextContent

from app.api.v1.module_operations.server.service import ServerService
from app.api.v1.module_operations.service_module.service import ServiceService
from app.api.v1.module_operations.task.service import TaskService
from app.api.v1.module_system.auth.schema import AuthSchema


def register_query_tools(mcp_server: Server, auth: AuthSchema):
    """注册综合查询工具"""
    
    @mcp_server.list_tools()
    async def list_query_tools() -> List[Tool]:
        """列出所有查询工具"""
        return [
            Tool(
                name="search_resources",
                description="综合搜索运维资源（服务器、服务模块、任务等）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "搜索关键词"
                        },
                        "resource_type": {
                            "type": "string",
                            "description": "资源类型",
                            "enum": ["server", "service", "task", "all"],
                            "default": "all"
                        }
                    },
                    "required": ["keyword"]
                }
            ),
            Tool(
                name="get_statistics",
                description="获取运维统计数据（节点数量、任务状态分布等）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "stat_type": {
                            "type": "string",
                            "description": "统计类型",
                            "enum": ["server_count", "task_status", "service_count", "all"],
                            "default": "all"
                        }
                    }
                }
            ),
            Tool(
                name="list_services",
                description="查询服务模块列表",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project": {
                            "type": "string",
                            "description": "项目名称过滤"
                        },
                        "status": {
                            "type": "boolean",
                            "description": "状态过滤"
                        },
                        "page": {
                            "type": "integer",
                            "default": 1
                        },
                        "page_size": {
                            "type": "integer",
                            "default": 10
                        }
                    }
                }
            ),
            Tool(
                name="get_service",
                description="获取服务模块详情",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "integer",
                            "description": "服务模块ID"
                        }
                    },
                    "required": ["id"]
                }
            )
        ]
    
    @mcp_server.call_tool()
    async def call_query_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """调用查询工具"""
        
        if name == "search_resources":
            keyword = arguments["keyword"]
            resource_type = arguments.get("resource_type", "all")
            results = {}
            
            # 搜索服务器
            if resource_type in ["server", "all"]:
                servers = await ServerService.get_server_page_service(
                    auth=auth,
                    page_no=1,
                    page_size=20,
                    search={"name": keyword}
                )
                results["servers"] = servers
            
            # 搜索任务
            if resource_type in ["task", "all"]:
                tasks = await TaskService.get_task_page_service(
                    auth=auth,
                    page_no=1,
                    page_size=20,
                    search={"task_type": keyword}
                )
                results["tasks"] = tasks
            
            return [TextContent(
                type="text",
                text=f"搜索结果（关键词：{keyword}）：\n{results}"
            )]
        
        elif name == "get_statistics":
            stat_type = arguments.get("stat_type", "all")
            stats = {}
            
            # 统计服务器数量
            if stat_type in ["server_count", "all"]:
                servers = await ServerService.get_server_page_service(
                    auth=auth,
                    page_no=1,
                    page_size=1,
                    search={}
                )
                stats["total_servers"] = servers.get("total", 0)
                
                # 按状态统计
                active_servers = await ServerService.get_server_page_service(
                    auth=auth,
                    page_no=1,
                    page_size=1,
                    search={"status": True}
                )
                stats["active_servers"] = active_servers.get("total", 0)
            
            # 统计任务状态
            if stat_type in ["task_status", "all"]:
                tasks = await TaskService.get_task_page_service(
                    auth=auth,
                    page_no=1,
                    page_size=1,
                    search={}
                )
                stats["total_tasks"] = tasks.get("total", 0)
            
            return [TextContent(
                type="text",
                text=f"运维统计数据：\n{stats}"
            )]
        
        elif name == "list_services":
            search = {}
            if "project" in arguments:
                search["project"] = arguments["project"]
            if "status" in arguments:
                search["status"] = arguments["status"]
            
            result = await ServiceService.get_service_page_service(
                auth=auth,
                page_no=arguments.get("page", 1),
                page_size=arguments.get("page_size", 10),
                search=search
            )
            return [TextContent(
                type="text",
                text=f"服务模块列表（共{result.get('total', 0)}个）：\n{result}"
            )]
        
        elif name == "get_service":
            result = await ServiceService.get_service_detail_service(
                auth=auth,
                id=arguments["id"]
            )
            return [TextContent(
                type="text",
                text=f"服务模块详情：\n{result}"
            )]
        
        else:
            return [TextContent(
                type="text",
                text=f"未知工具: {name}"
            )]

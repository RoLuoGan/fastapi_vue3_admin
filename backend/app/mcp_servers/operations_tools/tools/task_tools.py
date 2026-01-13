# -*- coding: utf-8 -*-
"""
任务执行工具
封装任务的创建、查询、取消等操作
"""

from typing import List, Dict, Any
from mcp.server import Server
from mcp.types import Tool, TextContent

from app.api.v1.module_operations.task.service import TaskService
from app.api.v1.module_system.auth.schema import AuthSchema


def register_task_tools(mcp_server: Server, auth: AuthSchema):
    """注册任务管理工具"""
    
    @mcp_server.list_tools()
    async def list_task_tools() -> List[Tool]:
        """列出所有任务管理工具"""
        return [
            Tool(
                name="execute_task",
                description="执行运维任务（部署、重启、初始化等）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_type": {
                            "type": "string",
                            "description": "任务类型（node_operator/server_operator）",
                            "enum": ["node_operator", "server_operator"]
                        },
                        "operator_type": {
                            "type": "string",
                            "description": "操作类型（deploy/restart/stop/init等）",
                            "enum": ["deploy", "restart", "stop", "start", "init", "update"]
                        },
                        "operator_metas": {
                            "type": "array",
                            "description": "操作元数据列表，每个元素包含节点信息和操作参数",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "node_id": {
                                        "type": "integer",
                                        "description": "节点ID"
                                    },
                                    "service_id": {
                                        "type": "integer",
                                        "description": "服务模块ID"
                                    },
                                    "params": {
                                        "type": "object",
                                        "description": "额外参数"
                                    }
                                }
                            }
                        }
                    },
                    "required": ["task_type", "operator_type", "operator_metas"]
                }
            ),
            Tool(
                name="get_task_status",
                description="查询任务执行状态",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "integer",
                            "description": "任务ID"
                        }
                    },
                    "required": ["task_id"]
                }
            ),
            Tool(
                name="get_task_log",
                description="获取任务执行日志",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "integer",
                            "description": "任务ID"
                        },
                        "tail_lines": {
                            "type": "integer",
                            "description": "读取最后N行日志",
                            "default": 100
                        }
                    },
                    "required": ["task_id"]
                }
            ),
            Tool(
                name="cancel_task",
                description="取消正在执行的任务",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "integer",
                            "description": "任务ID"
                        }
                    },
                    "required": ["task_id"]
                }
            ),
            Tool(
                name="list_tasks",
                description="查询任务列表",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "description": "任务状态过滤",
                            "enum": ["running", "success", "failed", "cancelled"]
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
            )
        ]
    
    @mcp_server.call_tool()
    async def call_task_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """调用任务管理工具"""
        
        if name == "execute_task":
            result = await TaskService.create_and_execute_task_service(
                auth=auth,
                validated_metas=arguments["operator_metas"],
                task_type=arguments["task_type"],
                operator_type=arguments["operator_type"]
            )
            return [TextContent(
                type="text",
                text=f"任务已创建并开始执行\n任务ID: {result.get('task_id')}\n状态: {result.get('status')}"
            )]
        
        elif name == "get_task_status":
            result = await TaskService.get_task_detail_service(
                auth=auth,
                id=arguments["task_id"]
            )
            return [TextContent(
                type="text",
                text=f"任务状态：\n{result}"
            )]
        
        elif name == "get_task_log":
            tail_lines = arguments.get("tail_lines", 100)
            result = await TaskService.get_task_log_tail_service(
                auth=auth,
                task_id=arguments["task_id"],
                tail_lines=tail_lines
            )
            return [TextContent(
                type="text",
                text=f"任务日志（最后{tail_lines}行）：\n{result}"
            )]
        
        elif name == "cancel_task":
            result = await TaskService.cancel_task_service(
                auth=auth,
                task_id=arguments["task_id"]
            )
            return [TextContent(
                type="text",
                text=f"任务取消结果：\n{result}"
            )]
        
        elif name == "list_tasks":
            search = {}
            if "status" in arguments:
                search["task_status"] = arguments["status"]
            
            result = await TaskService.get_task_page_service(
                auth=auth,
                page_no=arguments.get("page", 1),
                page_size=arguments.get("page_size", 10),
                search=search,
                order_by=[{"created_at": "desc"}]
            )
            return [TextContent(
                type="text",
                text=f"任务列表（共{result.get('total', 0)}个）：\n{result}"
            )]
        
        else:
            return [TextContent(
                type="text",
                text=f"未知工具: {name}"
            )]

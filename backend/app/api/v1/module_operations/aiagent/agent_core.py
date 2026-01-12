# -*- coding: utf-8 -*-
"""
AI Agent 核心逻辑
基于LangChain实现，集成MCP客户端调用运维工具
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage, BaseMessage
from langchain_core.tools import Tool
from langchain_core.callbacks.base import AsyncCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable, RunnablePassthrough

from app.config.setting import settings
from app.api.v1.module_system.auth.schema import AuthSchema

from .mcp_client import MCPClient
from .rule_engine import RuleEngine
from .crud import AIAgentCRUD
from .models import SessionStatus, MessageRole, OperationStatus

logger = logging.getLogger(__name__)


# DeepSeek系统提示词
DEEPSEEK_SYSTEM_PROMPT = """你是一个专业的运维管理助手，负责帮助用户管理服务器、执行任务、部署服务等。

## 核心原则
1. **安全第一**：所有删除、重启、部署等操作都需要明确告知用户并等待确认
2. **精确理解**：确保理解用户意图后再调用工具，不确定时主动询问
3. **结构化输出**：使用清晰的格式展示结果（如表格、列表）
4. **错误处理**：遇到错误时，提供明确的解决建议

## 工具使用规范
- 查询类操作（list、get、search）：直接执行，无需确认
- 创建类操作（create）：先确认参数，再执行
- 修改类操作（update）：必须确认影响范围
- 删除类操作（delete）：必须明确提示风险并获得确认
- 批量操作：必须显示具体影响的资源列表
- 任务执行（deploy、restart）：必须确认环境和影响范围

## 操作流程
1. 解析用户指令，提取关键信息（操作类型、目标资源、参数）
2. 如果信息不完整，主动询问缺失的参数
3. 对于敏感操作，明确说明影响并请求确认
4. 调用对应工具执行操作
5. 格式化展示结果，并提供后续建议

## 示例对话
用户：重启生产环境的 web 服务
助手：我理解您要重启生产环境的 web 服务。为了确保安全，请确认以下信息：
- 目标环境：production
- 服务模块：web
- 影响节点：[显示节点列表]
- 预计停机时间：约 30 秒
是否继续执行？

当前用户：{username}
当前时间：{current_time}
"""


class StreamingCallbackHandler(AsyncCallbackHandler):
    """流式回调处理器，用于实时输出Agent的思考和执行过程"""
    
    def __init__(self, queue: asyncio.Queue):
        self.queue = queue
    
    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        """LLM生成新token时"""
        await self.queue.put({"type": "token", "content": token})
    
    async def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs) -> None:
        """工具调用开始时"""
        await self.queue.put({
            "type": "tool_start",
            "tool": serialized.get("name"),
            "input": input_str
        })
    
    async def on_tool_end(self, output: str, **kwargs) -> None:
        """工具调用结束时"""
        await self.queue.put({"type": "tool_end", "output": output})


class AIAgent:
    """AI Agent核心类"""
    
    def __init__(
        self,
        auth: AuthSchema,
        session_id: int,
        mcp_client: MCPClient,
        llm_model: str = "deepseek"
    ):
        """
        初始化AI Agent
        
        Args:
            auth: 认证信息
            session_id: 会话ID
            mcp_client: MCP客户端
            llm_model: LLM模型名称
        """
        self.auth = auth
        self.session_id = session_id
        self.mcp_client = mcp_client
        self.llm_model = llm_model
        
        self.crud = AIAgentCRUD(auth)
        self.rule_engine = RuleEngine(auth)
        
        # 初始化LLM
        self.llm = self._init_llm()
        
        # 初始化工具
        self.tools = []
        self._init_tools()
        
        # 初始化Agent
        self.agent_executor = None
        self._init_agent()
    
    def _init_llm(self) -> ChatOpenAI:
        """初始化LLM"""
        if self.llm_model == "deepseek":
            return ChatOpenAI(
                model="deepseek-chat",
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_BASE_URL or "https://api.deepseek.com",
                temperature=0.1,
                max_tokens=2000,
                streaming=True
            )
        elif self.llm_model == "gpt-4o-mini":
            return ChatOpenAI(
                model="gpt-4o-mini",
                openai_api_key=settings.OPENAI_API_KEY,
                temperature=0.1,
                streaming=True
            )
        else:
            # 默认使用DeepSeek
            return ChatOpenAI(
                model="deepseek-chat",
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_BASE_URL or "https://api.deepseek.com",
                temperature=0.1,
                max_tokens=2000,
                streaming=True
            )
    
    def _init_tools(self):
        """初始化工具列表（从MCP客户端获取）"""
        mcp_tools = self.mcp_client.get_tools()
        
        for mcp_tool in mcp_tools:
            # 包装MCP工具为LangChain Tool
            tool = Tool(
                name=mcp_tool["name"],
                description=mcp_tool["description"],
                func=lambda args, name=mcp_tool["name"]: self._call_mcp_tool_sync(name, args),
                coroutine=lambda args, name=mcp_tool["name"]: self._call_mcp_tool(name, args)
            )
            self.tools.append(tool)
        
        logger.info(f"已加载 {len(self.tools)} 个MCP工具")
    
    async def _call_mcp_tool(self, tool_name: str, arguments: Any) -> str:
        """
        调用MCP工具（异步）
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        # 参数预处理
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except:
                arguments = {"input": arguments}
        
        logger.info(f"准备调用MCP工具: {tool_name}, 参数: {arguments}")
        
        # 规则检查：是否需要确认
        need_confirm, reason = await self.rule_engine.check_operation(
            operation_type=tool_name,
            params=arguments,
            user=self.auth.current_user
        )
        
        # 记录操作日志
        operation_log = await self.crud.create_operation_log(
            session_id=self.session_id,
            operation_type=tool_name,
            tool_name=tool_name,
            target_resource=str(arguments.get("id", arguments.get("ids", ""))),
            params=arguments,
            need_confirm=need_confirm,
            confirm_reason=reason,
            status=OperationStatus.PENDING if need_confirm else OperationStatus.CONFIRMED
        )
        
        # 如果需要确认，返回等待确认的消息
        if need_confirm:
            return f"⚠️ 该操作需要确认：{reason}\n操作ID: {operation_log.id}\n请在前端确认后继续。"
        
        # 调用MCP工具
        result = await self.mcp_client.call_tool(tool_name, arguments)
        
        # 更新操作日志
        if result.get("success"):
            await self.crud.update_operation_log(
                operation_log.id,
                status=OperationStatus.SUCCESS,
                result=result,
                executed_at=datetime.now()
            )
            return result.get("result", "操作成功")
        else:
            await self.crud.update_operation_log(
                operation_log.id,
                status=OperationStatus.FAILED,
                error_message=result.get("error"),
                executed_at=datetime.now()
            )
            return f"操作失败: {result.get('error')}"
    
    def _call_mcp_tool_sync(self, tool_name: str, arguments: Any) -> str:
        """同步版本的工具调用（用于兼容）"""
        import asyncio
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self._call_mcp_tool(tool_name, arguments))
    
    def _init_agent(self):
        """初始化Agent - 使用简化的实现"""
        # 构建Prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", DEEPSEEK_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])
        
        # 简化实现：直接使用 LLM，不使用 AgentExecutor
        # 避免 langchain 版本兼容问题
        self.agent_executor = None  # 设置为 None，后续在 chat 方法中直接调用 LLM
    
    async def chat(self, message: str) -> Dict[str, Any]:
        """
        处理用户消息（非流式）
        
        Args:
            message: 用户消息
            
        Returns:
            Agent响应
        """
        # 保存用户消息
        await self.crud.create_message(
            session_id=self.session_id,
            role=MessageRole.USER,
            content=message
        )
        
        # 获取历史消息
        history = await self.crud.get_session_history(self.session_id, limit=10)
        
        # 转换为LangChain消息格式
        chat_history = []
        for msg in history[:-1]:  # 排除刚刚添加的用户消息
            if msg.role == MessageRole.USER:
                chat_history.append(HumanMessage(content=msg.content))
            elif msg.role == MessageRole.ASSISTANT:
                chat_history.append(AIMessage(content=msg.content))
        
        # 构建消息
        formatted_prompt = self.prompt.format_messages(
            chat_history=chat_history,
            input=message,
            username=self.auth.user.username if self.auth.user else 'unknown',
            current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        # 直接调用LLM
        response = await self.llm.ainvoke(formatted_prompt)
        response_content = response.content
        
        # 保存Assistant消息
        assistant_msg = await self.crud.create_message(
            session_id=self.session_id,
            role=MessageRole.ASSISTANT,
            content=response_content
        )
        
        # 更新会话Token统计
        # TODO: 实现Token计数
        
        return {
            "message_id": assistant_msg.id,
            "content": response_content,
            "intermediate_steps": []
        }
    
    async def chat_stream(self, message: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理用户消息（流式）
        
        Args:
            message: 用户消息
            
        Yields:
            流式响应块
        """
        # 1. 立即保存用户消息并返回消息ID
        user_msg = await self.crud.create_message(
            session_id=self.session_id,
            role=MessageRole.USER,
            content=message
        )
        # 通知前端用户消息已保存
        yield {"type": "user_saved", "message_id": user_msg.id}
        
        # 获取历史消息
        history = await self.crud.get_session_history(self.session_id, limit=10)
        
        # 转换为LangChain消息格式
        chat_history = []
        for msg in history[:-1]:
            if msg.role == MessageRole.USER:
                chat_history.append(HumanMessage(content=msg.content))
            elif msg.role == MessageRole.ASSISTANT:
                chat_history.append(AIMessage(content=msg.content))
        
        # 构建消息
        formatted_prompt = self.prompt.format_messages(
            chat_history=chat_history,
            input=message,
            username=self.auth.user.username if self.auth.user else 'unknown',
            current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        # 流式调用LLM
        full_content = ""
        assistant_msg_id = None
        try:
            async for chunk in self.llm.astream(formatted_prompt):
                if hasattr(chunk, 'content') and chunk.content:
                    full_content += chunk.content
                    yield {"type": "text", "content": chunk.content}
            
            # 2. AI流式输出完成后保存历史记录
            if full_content:
                assistant_msg = await self.crud.create_message(
                    session_id=self.session_id,
                    role=MessageRole.ASSISTANT,
                    content=full_content
                )
                assistant_msg_id = assistant_msg.id
            
            # 返回完成状态和助手消息ID
            yield {"type": "complete", "message_id": assistant_msg_id}
        
        except Exception as e:
            logger.error(f"流式响应错误: {str(e)}")
            yield {"type": "error", "error": str(e)}

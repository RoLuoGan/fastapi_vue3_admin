# -*- coding: utf-8 -*-
"""
AI Agent 核心逻辑
基于LangChain实现，集成MCP客户端调用运维工具
使用官方LangChain MCP Adapters和流式工具调用
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage, ToolMessage, AIMessageChunk
from langchain_core.tools import BaseTool
from langchain_core.runnables import RunnablePassthrough
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.config.setting import settings
from app.api.v1.module_system.auth.schema import AuthSchema

from .rule_engine import RuleEngine
from .crud import AIAgentCRUD
from .models import SessionStatus, MessageRole, OperationStatus
from .prompts import OPERATIONS_ASSISTANT_PROMPT

logger = logging.getLogger(__name__)


class AIAgent:
    """AI Agent核心类"""
    
    def __init__(
        self,
        auth: AuthSchema,
        session_id: int,
        llm_model: str = "deepseek"
    ):
        """
        初始化AI Agent
        
        Args:
            auth: 认证信息
            session_id: 会话ID
            llm_model: LLM模型名称
        """
        self.auth = auth
        self.session_id = session_id
        self.llm_model = llm_model
        
        self.crud = AIAgentCRUD(auth)
        self.rule_engine = RuleEngine(auth)
        
        # 初始化LLM
        self.llm = self._init_llm()
        
        # 初始化工具列表（从MCP客户端获取）
        self.tools: List[BaseTool] = []
        
        # 工具名称集合（用于验证，防止调用不存在的工具）
        self.available_tool_names: set = set()
        
        # MCP服务器配置
        self.mcp_servers_config = {}
        self.mcp_adapter_client: Optional[MultiServerMCPClient] = None
        
        # 初始化Agent
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
    
    async def _init_tools(self):
        """初始化工具列表（从MCP客户端获取）"""
        try:
            # 配置MCP服务器
            mcp_servers_config = {
                "operations-tools": {
                    "url": settings.MCP_SERVER_URL,
                    "transport": "streamable_http"
                }
            }
            
            # 创建MCP适配器客户端
            self.mcp_adapter_client = MultiServerMCPClient(mcp_servers_config)
            
            # 获取LangChain兼容的工具（这些工具会通过 bind_tools 绑定给 LLM）
            self.tools = await self.mcp_adapter_client.get_tools()
            
            # 存储工具名称集合（用于安全验证，防止调用不存在的工具）
            self.available_tool_names = {tool.name for tool in self.tools}
            
            logger.info(f"已加载 {len(self.tools)} 个MCP工具: {list(self.available_tool_names)}")
            
        except Exception as e:
            logger.error(f"初始化MCP工具失败: {str(e)}")
            self.tools = []
            self.available_tool_names = set()
            logger.warning("MCP工具初始化失败，将不使用工具")
    
    def _init_agent(self):
        """初始化Agent"""
        # 构建Prompt（从 prompts.py 导入）
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", OPERATIONS_ASSISTANT_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])
        
        # 初始化工具（异步加载MCP工具）
        asyncio.create_task(self._init_tools())
    
    async def _call_mcp_tool(self, tool_name: str, arguments: Any) -> str:
        """
        调用MCP工具（使用 MultiServerMCPClient）
        
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
        
        # 🔒 安全验证：检查工具是否存在
        if tool_name not in self.available_tool_names:
            logger.warning(f"尝试调用不存在的工具: {tool_name}, 可用工具: {self.available_tool_names}")
            return f"❌ 错误：工具 '{tool_name}' 不存在。当前可用工具：{', '.join(sorted(self.available_tool_names))}"
        
        # 规则检查：是否需要确认
        need_confirm, reason = await self.rule_engine.check_operation(
            operation_type=tool_name,
            params=arguments,
            user=self.auth.user
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
        
        # 调用MCP工具（使用 MultiServerMCPClient）
        try:
            # 从工具列表中查找对应的工具
            tool = None
            for t in self.tools:
                if t.name == tool_name:
                    tool = t
                    break
            
            if not tool:
                raise ValueError(f"工具不存在: {tool_name}")
            
            # 调用工具
            tool_result = await tool.ainvoke(arguments)
            
            # 更新操作日志
            await self.crud.update_operation_log(
                operation_log.id,
                status=OperationStatus.SUCCESS,
                result={"success": True, "result": tool_result},
                executed_at=datetime.now()
            )
            
            return str(tool_result)
            
        except Exception as e:
            logger.error(f"调用MCP工具失败: {str(e)}")
            
            # 更新操作日志
            await self.crud.update_operation_log(
                operation_log.id,
                status=OperationStatus.FAILED,
                error_message=str(e),
                executed_at=datetime.now()
            )
            
            return f"操作失败: {str(e)}"
    
    def _call_mcp_tool_sync(self, tool_name: str, arguments: Any) -> str:
        """同步版本的工具调用（用于兼容）"""
        import asyncio
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self._call_mcp_tool(tool_name, arguments))
    
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
        
        # 使用 bind_tools 绑定工具（LLM会自动知道可用工具）
        llm_with_tools = self.llm.bind_tools(self.tools)
        
        # 调用LLM
        response = await llm_with_tools.ainvoke(formatted_prompt)
        response_content = response.content
        
        # 处理工具调用
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name")
                tool_args = tool_call.get("args", {})
                
                # 调用工具
                tool_result = await self._call_mcp_tool(tool_name, tool_args)
                
                # 将工具结果添加到消息历史
                chat_history.append(AIMessage(content="", tool_calls=[tool_call]))
                chat_history.append(ToolMessage(content=tool_result, tool_call_id=tool_call.get("id")))
                
                # 重新调用LLM，传入工具结果
                formatted_prompt = self.prompt.format_messages(
                    chat_history=chat_history,
                    input="",  # 工具调用后，input 应该为空，让 LLM 基于工具结果生成最终响应
                    username=self.auth.user.username if self.auth.user else 'unknown',
                    current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                response = await llm_with_tools.ainvoke(formatted_prompt)
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
        处理用户消息（流式，支持工具调用循环）
        
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
        
        # 使用工具绑定
        llm_with_tools = self.llm.bind_tools(self.tools)
        
        # 流式调用LLM，处理工具调用循环
        full_content = ""
        assistant_msg_id = None
        
        try:
            # 工具调用循环
            max_iterations = 10  # 防止无限循环
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                
                # 流式调用LLM，累积所有chunk以获取完整的工具调用信息
                current_content = ""
                accumulated_chunk = None
                
                async for chunk in llm_with_tools.astream(formatted_prompt):
                    # 累积chunk以构建完整的AIMessage
                    if accumulated_chunk is None:
                        accumulated_chunk = chunk
                    else:
                        # 合并chunk（AIMessageChunk支持合并）
                        if isinstance(accumulated_chunk, AIMessageChunk) and isinstance(chunk, AIMessageChunk):
                            accumulated_chunk = accumulated_chunk + chunk
                        else:
                            # 如果不是AIMessageChunk，尝试合并属性
                            if hasattr(chunk, 'content') and chunk.content:
                                if hasattr(accumulated_chunk, 'content'):
                                    accumulated_chunk.content = (accumulated_chunk.content or "") + (chunk.content or "")
                                else:
                                    accumulated_chunk = chunk
                    
                    # 实时输出文本内容
                    if hasattr(chunk, 'content') and chunk.content:
                        current_content += chunk.content
                        full_content += chunk.content  # 只添加新内容，不重复添加
                        yield {"type": "text", "content": chunk.content}
                
                # 检查完整的消息中是否有工具调用
                tool_calls = []
                if accumulated_chunk:
                    # 尝试多种方式获取tool_calls
                    if hasattr(accumulated_chunk, 'tool_calls') and accumulated_chunk.tool_calls:
                        tool_calls = accumulated_chunk.tool_calls
                    elif hasattr(accumulated_chunk, 'tool_calls') and callable(getattr(accumulated_chunk, 'tool_calls', None)):
                        try:
                            tool_calls = accumulated_chunk.tool_calls()
                        except:
                            pass
                
                logger.debug(f"工具调用检查: tool_calls={tool_calls}, current_content={current_content[:100]}")
                
                # 如果有工具调用
                if tool_calls:
                    logger.info(f"检测到工具调用: {tool_calls}")
                    # 通知前端工具调用（使用单独的事件类型）
                    for tool_call in tool_calls:
                        # 处理不同的tool_call格式
                        if isinstance(tool_call, dict):
                            tool_name = tool_call.get("name") or tool_call.get("function", {}).get("name", "")
                            tool_args = tool_call.get("args") or tool_call.get("function", {}).get("arguments", {})
                            tool_call_id = tool_call.get("id") or tool_call.get("function", {}).get("id", "")
                            # 如果args是字符串，尝试解析为JSON
                            if isinstance(tool_args, str):
                                try:
                                    tool_args = json.loads(tool_args)
                                except:
                                    tool_args = {}
                        else:
                            # 如果是对象，尝试获取属性
                            tool_name = getattr(tool_call, 'name', '') or getattr(tool_call, 'function', {}).get('name', '')
                            tool_args = getattr(tool_call, 'args', {}) or getattr(tool_call, 'function', {}).get('arguments', {})
                            tool_call_id = getattr(tool_call, 'id', '') or getattr(tool_call, 'function', {}).get('id', '')
                            if isinstance(tool_args, str):
                                try:
                                    tool_args = json.loads(tool_args)
                                except:
                                    tool_args = {}
                        
                        # 调用工具
                        tool_result = await self._call_mcp_tool(tool_name, tool_args)
                        
                        # 判断工具调用是否成功（通过返回结果判断）
                        # 如果返回结果以 ❌ 或 ⚠️ 开头，则认为是失败或需要确认
                        tool_result_str = str(tool_result) if tool_result else ""
                        is_success = not (tool_result_str.startswith("❌") or tool_result_str.startswith("⚠️"))
                        
                        # 使用 mcp_tool_call 事件类型返回完整的工具调用信息
                        yield {
                            "type": "mcp_tool_call",
                            "tool": tool_name,
                            "tool_call_id": tool_call_id,
                            "input": tool_args,
                            "output": tool_result,
                            "success": is_success
                        }
                        
                        # 将工具结果添加到消息历史
                        chat_history.append(AIMessage(content=current_content, tool_calls=[tool_call]))
                        chat_history.append(ToolMessage(content=tool_result, tool_call_id=tool_call.get("id")))
                        
                        # 重新构建prompt，包含工具结果
                        formatted_prompt = self.prompt.format_messages(
                            chat_history=chat_history,
                            input="",  # 工具调用后，input 应该为空，让 LLM 基于工具结果生成最终响应
                            username=self.auth.user.username if self.auth.user else 'unknown',
                            current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        )
                        
                        # 继续循环，让LLM基于工具结果生成响应
                        continue
                
                # 没有工具调用，结束循环
                else:
                    break
            
            # 2. AI流式输出完成后保存历史记录
            if full_content:
                # 收集所有工具调用信息用于保存到历史记录
                collected_tool_calls = []
                # 从 chat_history 中收集所有工具调用和结果
                for msg in chat_history:
                    if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                        # 这是一个包含工具调用的AI消息
                        for tool_call in msg.tool_calls:
                            if isinstance(tool_call, dict):
                                tool_name = tool_call.get('name') or tool_call.get('function', {}).get('name', '')
                                tool_args = tool_call.get('args') or tool_call.get('function', {}).get('arguments', {})
                                tool_call_id = tool_call.get('id') or tool_call.get('function', {}).get('id', '')
                            else:
                                tool_name = getattr(tool_call, 'name', '') or getattr(tool_call, 'function', {}).get('name', '')
                                tool_args = getattr(tool_call, 'args', {}) or getattr(tool_call, 'function', {}).get('arguments', {})
                                tool_call_id = getattr(tool_call, 'id', '') or getattr(tool_call, 'function', {}).get('id', '')
                            
                            # 从chat_history中查找对应的工具结果
                            tool_output = ''
                            for result_msg in chat_history:
                                if isinstance(result_msg, ToolMessage) and result_msg.tool_call_id == tool_call_id:
                                    tool_output = result_msg.content
                                    break
                            
                            collected_tool_calls.append({
                                'tool': tool_name,
                                'tool_call_id': tool_call_id,
                                'input': tool_args,
                                'output': tool_output,
                                'success': not (str(tool_output).startswith('❌') or str(tool_output).startswith('⚠️'))
                            })
                
                assistant_msg = await self.crud.create_message(
                    session_id=self.session_id,
                    role=MessageRole.ASSISTANT,
                    content=full_content,
                    tool_calls=collected_tool_calls if collected_tool_calls else None
                )
                assistant_msg_id = assistant_msg.id
            
            # 返回完成状态和助手消息ID
            yield {"type": "complete", "message_id": assistant_msg_id}
        
        except Exception as e:
            logger.error(f"流式响应错误: {str(e)}")
            yield {"type": "error", "error": str(e)}
        
        finally:
            # 清理MCP适配器客户端（MultiServerMCPClient 是上下文管理器，不需要手动关闭）
            # 注意：MultiServerMCPClient 使用 async with 上下文管理器，会自动管理连接
            pass
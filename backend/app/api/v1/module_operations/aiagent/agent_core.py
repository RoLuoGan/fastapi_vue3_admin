# -*- coding: utf-8 -*-
"""
AI Agent 核心逻辑
基于LangChain实现，集成MCP客户端调用运维工具
使用官方LangChain MCP Adapters和流式工具调用
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator, Callable
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage, ToolMessage, AIMessageChunk
from langchain_core.tools import BaseTool
from langchain_core.runnables import RunnablePassthrough
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.config.setting import settings
from app.api.v1.module_system.auth.schema import AuthSchema

from .crud import AIAgentCRUD
from .models import SessionStatus, MessageRole, OperationStatus
from .prompts import OPERATIONS_ASSISTANT_PROMPT

logger = logging.getLogger(__name__)


class ToolConfirmationRedisState:
    """工具确认Redis状态机管理"""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.key_prefix = "aiagent:tool_confirmation"

    def _get_key(self, operation_id: int) -> str:
        """获取Redis键"""
        return f"{self.key_prefix}:{operation_id}"

    async def set_pending(self, operation_id: int, data: Dict[str, Any], timeout: int = 1800) -> bool:
        """设置待确认状态

        Args:
            operation_id: 操作ID
            data: 状态数据
            timeout: 超时时间(秒)

        Returns:
            是否设置成功
        """
        try:
            key = self._get_key(operation_id)
            state_data = {
                "status": "pending",
                "data": data,
                "created_at": datetime.now().isoformat(),
                "timeout": timeout
            }

            success = await self.redis.set(
                key,
                json.dumps(state_data, ensure_ascii=False),
                ex=timeout
            )
            return success
        except Exception as e:
            logger.error(f"[RedisState] 设置工具确认状态失败: operation_id={operation_id}, error={str(e)}")
            return False

    async def wait_for_confirmation(self, operation_id: int, timeout: int = 1800) -> Dict[str, Any]:
        """等待确认结果

        Args:
            operation_id: 操作ID
            timeout: 等待超时时间(秒)，默认30分钟

        Returns:
            确认结果数据
        """
        key = self._get_key(operation_id)

        # 使用Redis的阻塞等待机制
        start_time = asyncio.get_event_loop().time()
        poll_interval = 1  # 每秒检查一次
        check_count = 0

        while True:
            check_count += 1
            try:
                # 检查状态
                state_data = await self.redis.get(key)
                if not state_data:
                    # 状态已过期或不存在，抛出超时异常
                    raise asyncio.TimeoutError("确认状态已过期，请重新发起请求")

                state = json.loads(state_data)

                if state["status"] == "confirmed":
                    # 已确认，清理状态
                    await self.redis.delete(key)
                    return state["result"]

                elif state["status"] == "rejected":
                    # 已拒绝，清理状态
                    await self.redis.delete(key)
                    return state["result"]

                # 继续等待
                await asyncio.sleep(poll_interval)

                # 检查超时
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    raise asyncio.TimeoutError(f"确认超时（{timeout}秒）")

            except json.JSONDecodeError:
                await asyncio.sleep(poll_interval)
            except Exception:
                raise

    async def set_result(self, operation_id: int, confirmed: bool, result: Dict[str, Any]) -> bool:
        """设置确认结果

        Args:
            operation_id: 操作ID
            confirmed: 是否确认
            result: 结果数据

        Returns:
            是否设置成功
        """
        try:
            key = self._get_key(operation_id)

            # 获取当前状态
            state_data = await self.redis.get(key)
            if not state_data:
                return False

            state = json.loads(state_data)

            # 更新状态
            state["status"] = "confirmed" if confirmed else "rejected"
            state["result"] = result
            state["updated_at"] = datetime.now().isoformat()

            # 保存更新后的状态
            success = await self.redis.set(
                key,
                json.dumps(state, ensure_ascii=False),
                ex=60  # 结果保留1分钟
            )

            return success

        except Exception as e:
            return False

    async def cleanup(self, operation_id: int) -> bool:
        """清理状态

        Args:
            operation_id: 操作ID

        Returns:
            是否清理成功
        """
        try:
            key = self._get_key(operation_id)
            await self.redis.delete(key)
            return True
        except Exception as e:
            return False


class AIAgent:
    """AI Agent核心类"""
    
    def __init__(
        self,
        auth: AuthSchema,
        session_id: int,
        llm_model: str = "deepseek",
        redis_client = None
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

        # Redis状态机管理
        self.redis_state_manager = ToolConfirmationRedisState(redis_client) if redis_client else None
    
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
    
    async def _call_mcp_tool(self, tool_name: str, arguments: Any, require_confirm: bool = False) -> str:
        """
        调用MCP工具（使用 MultiServerMCPClient）

        Args:
            tool_name: 工具名称
            arguments: 工具参数
            require_confirm: 是否需要确认（操作类工具需要，查询类工具不需要）

        Returns:
            工具执行结果
        """
        # 参数预处理
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except:
                arguments = {"input": arguments}

        logger.info(f"准备调用MCP工具: {tool_name}, 参数: {arguments}, 需要确认: {require_confirm}")

        # 🔒 安全验证：检查工具是否存在
        if tool_name not in self.available_tool_names:
            available_tools_str = ', '.join(sorted(self.available_tool_names)) if self.available_tool_names else "无可用工具"
            logger.warning(f"尝试调用不存在的工具: {tool_name}, 可用工具: {available_tools_str}")

            if not self.available_tool_names:
                return "❌ 错误：当前系统没有配置任何运维工具，无法执行查询操作。请联系管理员配置MCP服务器。"
            else:
                return f"❌ 错误：工具 '{tool_name}' 不存在。当前可用工具：{available_tools_str}"

        # 创建操作日志
        operation_log = await self.crud.create_operation_log(
            session_id=self.session_id,
            operation_type=tool_name,
            tool_name=tool_name,
            target_resource=str(arguments.get("id", arguments.get("ids", ""))),
            params=arguments,
            need_confirm=require_confirm,
            confirm_reason="系统自动确认流程" if require_confirm else "查询类工具直接执行",
            status=OperationStatus.PENDING if require_confirm else OperationStatus.CONFIRMED
        )

        # 如果需要确认，返回等待确认的消息（用于操作类工具）
        if require_confirm:
            return f"⚠️ 该操作需要确认：即将执行 {tool_name}\n操作ID: {operation_log.id}\n请在前端确认后继续。"

        # 查询类工具直接执行
        return await self._execute_mcp_tool(operation_log, tool_name, arguments)

    async def _execute_mcp_tool(self, operation_log, tool_name: str, arguments: Any) -> str:
        """
        实际执行MCP工具

        Args:
            operation_log: 操作日志对象
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果
        """
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

            # 更新操作日志为成功
            await self.crud.update_operation_log(
                operation_log.id,
                status=OperationStatus.SUCCESS,
                result={"success": True, "result": tool_result},
                executed_at=datetime.now()
            )

            return str(tool_result)

        except Exception as e:
            logger.error(f"调用MCP工具失败: {str(e)}")

            # 更新操作日志为失败
            await self.crud.update_operation_log(
                operation_log.id,
                status=OperationStatus.FAILED,
                error_message=str(e),
                executed_at=datetime.now()
            )

            return f"操作失败: {str(e)}"

    async def confirm_and_execute_tool(self, operation_id: int, confirmed: bool) -> str:
        """
        确认并执行工具调用

        Args:
            operation_id: 操作ID
            confirmed: 是否确认执行

        Returns:
            执行结果
        """
        # 获取操作日志
        operation_log = await self.crud.get_operation_log(operation_id)
        if not operation_log:
            return "❌ 操作不存在或已过期"

        if operation_log.status != OperationStatus.PENDING:
            if operation_log.status == OperationStatus.CONFIRMED:
                return "✅ 操作已被确认并执行"
            elif operation_log.status == OperationStatus.REJECTED:
                return "❌ 操作已被拒绝"
            else:
                return f"❌ 操作状态异常: {operation_log.status}"

        # 尝试通知等待的agent确认结果（通过Redis状态机）
        if self.redis_state_manager:
            try:
                await self.redis_state_manager.set_result(operation_id, confirmed, {
                    "confirmed": confirmed,
                    "operation_log": operation_log
                })
            except Exception as e:
                logger.warning(f"设置Redis确认结果失败，可能已过期: {str(e)}")

        if not confirmed:
            # 用户拒绝，更新状态为拒绝
            await self.crud.update_operation_log(
                operation_id,
                status=OperationStatus.REJECTED,
                executed_at=datetime.now()
            )
            return "❌ 用户已拒绝执行该操作"

        # 执行工具
        return await self._execute_mcp_tool(operation_log, operation_log.tool_name, operation_log.params)

    def _call_mcp_tool_sync(self, tool_name: str, arguments: Any, require_confirm: bool = False) -> str:
        """同步版本的工具调用（用于兼容）"""
        import asyncio
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self._call_mcp_tool(tool_name, arguments, require_confirm))
    
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
        
        # 处理工具调用 - 所有工具调用都需要人工确认
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name")
                tool_args = tool_call.get("args", {})

                # 在非流式模式下，所有工具调用都需要人工确认，不支持直接执行
                tool_result = f"⚠️ 工具调用（{tool_name}）需要人工确认，请使用流式聊天接口来执行此操作。"
                
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
                    logger.info(f"检测到工具调用: {len(tool_calls)}个工具")

                    # 由于模型一次只调用一个工具，我们只处理第一个工具调用
                    tool_call = tool_calls[0]  # 只取第一个工具调用

                    # 处理tool_call格式
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

                    # 所有工具调用都需要人工确认
                    logger.info(f"工具调用需要确认: {tool_name}")

                    # 创建操作日志（状态为待确认）
                    operation_log = await self.crud.create_operation_log(
                        session_id=self.session_id,
                        operation_type=tool_name,
                        tool_name=tool_name,
                        target_resource=str(tool_args.get("id", tool_args.get("ids", ""))),
                        params=tool_args,
                        need_confirm=True,
                        confirm_reason=f"即将执行工具调用: {tool_name}",
                        status=OperationStatus.PENDING
                    )

                    # 发送确认事件给前端
                    confirm_event = {
                        "type": "mcp_tool_confirm",
                        "operation_id": operation_log.id,
                        "tool_name": tool_name,
                        "tool_call_id": tool_call_id,
                        "tool_args": tool_args,
                        "confirm_reason": f"即将执行工具调用: {tool_name}",
                        "timestamp": datetime.now().isoformat()
                    }
                    yield confirm_event

                    # 等待确认结果
                    if self.redis_state_manager:
                        try:
                            logger.info(f"等待工具确认结果: operation_id={operation_log.id}")

                            # 设置待确认状态（30分钟过期时间）
                            await self.redis_state_manager.set_pending(operation_log.id, {
                                "tool_name": tool_name,
                                "tool_args": tool_args,
                                "session_id": self.session_id
                            }, timeout=1800)

                            # 等待确认结果
                            confirmation_result = await self.redis_state_manager.wait_for_confirmation(operation_log.id, timeout=1800)

                            if confirmation_result.get("confirmed", False):
                                # 用户确认，执行工具
                                tool_result = await self._execute_mcp_tool(operation_log, tool_name, tool_args)

                                # 发送工具执行结果事件
                                yield {
                                    "type": "mcp_tool_call",
                                    "tool": tool_name,
                                    "tool_call_id": tool_call_id,
                                    "input": tool_args,
                                    "output": tool_result,
                                    "success": not (str(tool_result).startswith("❌") or str(tool_result).startswith("⚠️"))
                                }

                                # 将工具结果添加到消息历史
                                chat_history.append(AIMessage(content=current_content, tool_calls=[tool_call]))
                                chat_history.append(ToolMessage(content=tool_result, tool_call_id=tool_call_id))

                                # 重新构建prompt，包含工具结果
                                formatted_prompt = self.prompt.format_messages(
                                    chat_history=chat_history,
                                    input="",  # 工具调用后，input 应该为空，让 LLM 基于工具结果生成最终响应
                                    username=self.auth.user.username if self.auth.user else 'unknown',
                                    current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                )

                                # 继续循环，让LLM基于工具结果生成响应
                                continue
                            else:
                                # 用户拒绝
                                rejection_message = f"⚠️ 用户已拒绝执行工具调用: {tool_name}"
                                yield {
                                    "type": "text",
                                    "content": rejection_message
                                }
                                current_content += rejection_message

                                # 清理拒绝的操作日志
                                await self.crud.update_operation_log(
                                    operation_log.id,
                                    status=OperationStatus.REJECTED,
                                    executed_at=datetime.now()
                                )

                        except asyncio.TimeoutError as e:
                            timeout_message = f"⚠️ 工具调用确认超时: {tool_name}。请重新发起请求。"
                            yield {
                                "type": "text",
                                "content": timeout_message
                            }
                            current_content += timeout_message

                            # 清理超时的操作日志状态
                            await self.crud.update_operation_log(
                                operation_log.id,
                                status=OperationStatus.REJECTED,
                                executed_at=datetime.now()
                            )

                        finally:
                            # 清理Redis状态
                            if self.redis_state_manager:
                                await self.redis_state_manager.cleanup(operation_log.id)
                    else:
                        # 如果没有Redis，回退到简单处理
                        logger.warning("Redis状态机不可用，跳过工具确认")
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
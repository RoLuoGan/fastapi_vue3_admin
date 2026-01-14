/**
 * AI Agent 聊天逻辑
 */

import { ref, computed } from 'vue'
import AIAgentAPI from '@/api/operations/aiagent'
import type { StreamChunk, McpToolCall } from '@/api/operations/aiagent'
import { ElMessage } from 'element-plus'

export interface Message {
  id?: number
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at?: string
  isStreaming?: boolean  // 是否正在流式输出
  toolCalls?: McpToolCall[]  // MCP工具调用列表
}

export function useChat() {
  const currentSessionId = ref<number | null>(null)
  const messages = ref<Message[]>([])
  const loading = ref(false)
  const inputMessage = ref('')
  const abortController = ref<AbortController | null>(null)
  const streamingContent = ref('')  // 当前正在流式输出的内容

  console.log('[useChat] 初始化聊天 composable')

  // 创建新会话
  const createNewSession = async (sessionName?: string) => {
    console.log('[useChat] 开始创建新会话, sessionName:', sessionName)
    try {
      const requestData: any = {}
      if (sessionName) {
        requestData.session_name = sessionName
      }
      // 如果不提供名称，后端会自动生成
      console.log('[useChat] 创建会话请求数据:', requestData)
      
      const res = await AIAgentAPI.createSession(requestData)
      console.log('[useChat] 创建会话响应:', res)
      console.log('[useChat] 响应数据详情:', JSON.stringify(res, null, 2))
      
      if (res.data.code === 0) {
        currentSessionId.value = res.data.data.session_id
        messages.value = []
        console.log('[useChat] 会话创建成功, session_id:', res.data.data.session_id)
        ElMessage.success('会话创建成功')
        return res.data.data
      } else {
        console.error('[useChat] 创建会话失败, code:', res.data.code, 'message:', res.data.msg)
        ElMessage.error(res.data.msg || '创建会话失败')
        return null
      }
    } catch (error: any) {
      console.error('[useChat] 创建会话异常:', error)
      console.error('[useChat] 错误详情:', {
        message: error?.message,
        response: error?.response,
        data: error?.response?.data,
        status: error?.response?.status,
        statusText: error?.response?.statusText,
        config: error?.config,
        stack: error?.stack
      })
      ElMessage.error('创建会话失败: ' + (error?.message || '未知错误'))
      return null
    }
  }

  // 加载会话历史
  const loadHistory = async (sessionId: number) => {
    console.log('[useChat] 开始加载会话历史, session_id:', sessionId)
    try {
      const res = await AIAgentAPI.getSessionHistory(sessionId)
      console.log('[useChat] 加载历史响应:', res)
      console.log('[useChat] 响应数据详情:', JSON.stringify(res, null, 2))
      
      if (res.data.code === 0) {
        currentSessionId.value = sessionId
        // 将后端的 tool_calls 映射为前端的 toolCalls
        messages.value = (res.data.data.messages || []).map((msg: any) => ({
          ...msg,
          toolCalls: msg.tool_calls || undefined
        }))
        console.log('[useChat] 历史加载成功, 消息数量:', messages.value.length)
        console.log('[useChat] 消息列表:', messages.value)
        return res.data.data
      } else {
        console.error('[useChat] 加载历史失败, code:', res.data.code, 'message:', res.data.msg)
        ElMessage.error(res.data.msg || '加载历史失败')
        return null
      }
    } catch (error: any) {
      console.error('[useChat] 加载历史异常:', error)
      console.error('[useChat] 错误详情:', {
        message: error?.message,
        response: error?.response,
        data: error?.response?.data,
        status: error?.response?.status,
        statusText: error?.response?.statusText,
        config: error?.config,
        stack: error?.stack
      })
      ElMessage.error('加载历史失败: ' + (error?.message || '未知错误'))
      return null
    }
  }

  // 发送消息（流式）
  const sendMsg = async (content?: string) => {
    const msgContent = content || inputMessage.value
    console.log('[useChat] 开始发送消息（流式）, content:', msgContent)
    
    if (!msgContent.trim()) {
      console.warn('[useChat] 消息内容为空')
      ElMessage.warning('请输入消息')
      return
    }

    if (!currentSessionId.value) {
      console.warn('[useChat] 没有活动会话，先创建新会话')
      const session = await createNewSession()
      if (!session) {
        return
      }
    }

    console.log('[useChat] 当前会话ID:', currentSessionId.value)

    // 添加用户消息到界面
    const userMessage: Message = {
      role: 'user',
      content: msgContent,
      created_at: new Date().toISOString()
    }
    messages.value.push(userMessage)
    console.log('[useChat] 已添加用户消息到列表')

    // 添加空的助手消息，用于流式填充
    const assistantMessage: Message = {
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
      isStreaming: true
    }
    messages.value.push(assistantMessage)
    const assistantMsgIndex = messages.value.length - 1

    // 清空输入框
    inputMessage.value = ''
    streamingContent.value = ''

    // 显示加载状态
    loading.value = true
    
    // 创建 AbortController 用于取消请求
    abortController.value = new AbortController()

    const requestData = {
      session_id: currentSessionId.value!,
      message: msgContent
    }
    console.log('[useChat] 发送消息请求数据（流式）:', requestData)
    
    // 用户消息的索引（在助手消息之前）
    const userMsgIndex = assistantMsgIndex - 1

    // 辅助函数：更新用户消息ID
    const updateUserMessageId = (messageId: number) => {
      messages.value[userMsgIndex] = {
        ...messages.value[userMsgIndex],
        id: messageId
      }
    }

    // 辅助函数：更新助手消息并触发 Vue 响应式
    const updateAssistantMessage = (content: string, isStreaming: boolean = true, messageId?: number, toolCalls?: McpToolCall[]) => {
      messages.value[assistantMsgIndex] = {
        ...messages.value[assistantMsgIndex],
        content,
        isStreaming,
        ...(messageId ? { id: messageId } : {}),
        ...(toolCalls ? { toolCalls } : {})
      }
    }

    await AIAgentAPI.sendMessageStream(
      requestData,
      {
        onChunk: (chunk: StreamChunk) => {
          console.log('[useChat] 收到流式块:', chunk)
          if (chunk.type === 'user_saved' && chunk.message_id) {
            // 用户消息已保存到数据库，更新本地消息ID
            console.log('[useChat] 用户消息已保存, ID:', chunk.message_id)
            updateUserMessageId(chunk.message_id)
          } else if (chunk.type === 'text' && chunk.content) {
            // 追加内容到助手消息
            streamingContent.value += chunk.content
            // 使用替换整个对象的方式触发 Vue 响应式更新
            updateAssistantMessage(streamingContent.value)
          } else if (chunk.type === 'mcp_tool_call') {
            // MCP工具调用（新的事件类型）
            const currentMsg = messages.value[assistantMsgIndex]
            const existingToolCalls = currentMsg.toolCalls || []
            const newToolCall: McpToolCall = {
              tool: chunk.tool || '',
              tool_call_id: chunk.tool_call_id,
              input: chunk.input || {},
              output: chunk.output || '',
              success: chunk.success !== false
            }
            const updatedToolCalls = [...existingToolCalls, newToolCall]
            updateAssistantMessage(streamingContent.value, true, undefined, updatedToolCalls)
            console.log('[useChat] MCP工具调用已记录:', newToolCall)
          } else if (chunk.type === 'tool_start') {
            // 工具调用开始（向后兼容）
            const toolInfo = `\n🔧 正在调用工具: ${chunk.tool}\n`
            streamingContent.value += toolInfo
            updateAssistantMessage(streamingContent.value)
          } else if (chunk.type === 'tool_end') {
            // 工具调用结束（向后兼容）
            const toolResult = `✅ 工具执行完成\n`
            streamingContent.value += toolResult
            updateAssistantMessage(streamingContent.value)
          } else if (chunk.type === 'complete') {
            // AI消息已保存到数据库
            console.log('[useChat] AI消息已保存, ID:', chunk.message_id)
            const currentMsg = messages.value[assistantMsgIndex]
            updateAssistantMessage(streamingContent.value, false, chunk.message_id, currentMsg.toolCalls)
            loading.value = false
            abortController.value = null
          }
        },
        onComplete: () => {
          // 流结束（备用处理，正常情况由 complete chunk 处理）
          console.log('[useChat] 流式连接关闭')
          if (loading.value) {
            const currentMsg = messages.value[assistantMsgIndex]
            updateAssistantMessage(streamingContent.value, false, undefined, currentMsg?.toolCalls)
            loading.value = false
            abortController.value = null
          }
        },
        onError: (error: string) => {
          console.error('[useChat] 流式响应错误:', error)
          // 如果没有内容，移除助手消息
          if (!streamingContent.value) {
            messages.value.splice(assistantMsgIndex, 1)
            // 也移除用户消息
            messages.value.pop()
          } else {
            updateAssistantMessage(streamingContent.value + `\n\n❌ 错误: ${error}`, false)
          }
          ElMessage.error('发送消息失败: ' + error)
          loading.value = false
          abortController.value = null
        }
      },
      abortController.value.signal
    )
  }

  // 停止发送消息
  const stopSend = () => {
    console.log('[useChat] 停止发送消息')
    if (abortController.value) {
      abortController.value.abort()
      abortController.value = null
    }
    // 如果有正在流式输出的消息，标记为完成
    const lastMsg = messages.value[messages.value.length - 1]
    if (lastMsg && lastMsg.isStreaming) {
      lastMsg.isStreaming = false
      if (!lastMsg.content) {
        // 如果没有内容，移除空消息
        messages.value.pop()
      }
    }
    loading.value = false
    streamingContent.value = ''
  }

  // 清空当前会话
  const clearSession = () => {
    currentSessionId.value = null
    messages.value = []
    streamingContent.value = ''
    if (abortController.value) {
      abortController.value.abort()
      abortController.value = null
    }
    loading.value = false
  }

  return {
    currentSessionId,
    messages,
    loading,
    inputMessage,
    streamingContent,
    createNewSession,
    loadHistory,
    sendMsg,
    stopSend,
    clearSession
  }
}

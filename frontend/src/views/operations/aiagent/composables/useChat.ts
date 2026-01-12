/**
 * AI Agent 聊天逻辑
 */

import { ref, computed } from 'vue'
import AIAgentAPI from '@/api/operations/aiagent'
import { ElMessage } from 'element-plus'

export interface Message {
  id?: number
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at?: string
}

export function useChat() {
  const currentSessionId = ref<number | null>(null)
  const messages = ref<Message[]>([])
  const loading = ref(false)
  const inputMessage = ref('')
  const abortController = ref<AbortController | null>(null)

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
        messages.value = res.data.data.messages || []
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

  // 发送消息
  const sendMsg = async (content?: string) => {
    const msgContent = content || inputMessage.value
    console.log('[useChat] 开始发送消息, content:', msgContent)
    
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

    // 清空输入框
    inputMessage.value = ''

    // 显示加载状态
    loading.value = true
    
    // 创建 AbortController 用于取消请求
    abortController.value = new AbortController()

    try {
      const requestData = {
        session_id: currentSessionId.value!,
        message: msgContent
      }
      console.log('[useChat] 发送消息请求数据:', requestData)
      
      const res = await AIAgentAPI.sendMessage(requestData, {
        signal: abortController.value.signal
      })
      console.log('[useChat] 发送消息响应:', res)
      console.log('[useChat] 响应数据详情:', JSON.stringify(res, null, 2))

      if (res.data.code === 0) {
        // 添加AI回复
        const assistantMessage: Message = {
          id: res.data.data.message_id,
          role: res.data.data.role as 'assistant',
          content: res.data.data.content,
          created_at: new Date().toISOString()
        }
        messages.value.push(assistantMessage)
        console.log('[useChat] 消息发送成功，已添加助手回复')
      } else {
        console.error('[useChat] 发送消息失败, code:', res.data.code, 'message:', res.data.msg)
        ElMessage.error(res.data.msg || '发送失败')
        // 移除用户消息
        messages.value.pop()
      }
    } catch (error: any) {
      // 如果是取消请求，不显示错误
      if (error.name === 'AbortError' || error.message?.includes('aborted') || error.code === 'ERR_CANCELED') {
        console.log('[useChat] 请求已取消')
        // 移除用户消息
        if (messages.value.length > 0 && messages.value[messages.value.length - 1].role === 'user') {
          messages.value.pop()
        }
        return
      }
      console.error('[useChat] 发送消息异常:', error)
      console.error('[useChat] 错误详情:', {
        message: error?.message,
        response: error?.response,
        data: error?.response?.data,
        status: error?.response?.status,
        statusText: error?.response?.statusText,
        config: error?.config,
        stack: error?.stack
      })
      ElMessage.error('发送消息失败: ' + (error?.message || '未知错误'))
      // 移除用户消息
      if (messages.value.length > 0 && messages.value[messages.value.length - 1].role === 'user') {
        messages.value.pop()
      }
    } finally {
      loading.value = false
      abortController.value = null
    }
  }

  // 停止发送消息
  const stopSend = () => {
    console.log('[useChat] 停止发送消息')
    if (abortController.value) {
      abortController.value.abort()
      loading.value = false
      abortController.value = null
    }
  }

  // 清空当前会话
  const clearSession = () => {
    currentSessionId.value = null
    messages.value = []
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
    createNewSession,
    loadHistory,
    sendMsg,
    stopSend,
    clearSession
  }
}

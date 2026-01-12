/**
 * 操作确认逻辑
 */

import { ref } from 'vue'
import AIAgentAPI from '@/api/operations/aiagent'
import { ElMessage } from 'element-plus'

export interface PendingOperation {
  operation_id: number
  session_id: number
  operation_type: string
  tool_name: string
  target_resource?: string
  params: any
  confirm_reason: string
  created_at: string
}

export function useConfirm() {
  const pendingOps = ref<PendingOperation[]>([])
  const loading = ref(false)

  // 加载待确认操作
  const loadPendingOperations = async (sessionId?: number) => {
    console.log('[useConfirm] 开始加载待确认操作, session_id:', sessionId)
    loading.value = true
    try {
      const params = { session_id: sessionId }
      console.log('[useConfirm] 请求参数:', params)
      
      const res = await AIAgentAPI.getPendingOperations(params)
      console.log('[useConfirm] 待确认操作响应:', res)
      console.log('[useConfirm] 响应数据详情:', JSON.stringify(res, null, 2))
      
      if (res.data.code === 0) {
        pendingOps.value = res.data.data || []
        console.log('[useConfirm] 待确认操作加载成功, 数量:', pendingOps.value.length)
        console.log('[useConfirm] 操作列表:', pendingOps.value)
        return res.data.data
      } else {
        console.error('[useConfirm] 加载待确认操作失败, code:', res.data.code, 'message:', res.data.msg)
        ElMessage.error(res.data.msg || '加载失败')
        return []
      }
    } catch (error: any) {
      console.error('[useConfirm] 加载待确认操作异常:', error)
      console.error('[useConfirm] 错误详情:', {
        message: error?.message,
        response: error?.response,
        data: error?.response?.data,
        status: error?.response?.status,
        statusText: error?.response?.statusText,
        config: error?.config,
        stack: error?.stack
      })
      ElMessage.error('加载失败: ' + (error?.message || '未知错误'))
      return []
    } finally {
      loading.value = false
    }
  }

  // 确认操作
  const confirmOp = async (operationId: number, confirmed: boolean, comment?: string) => {
    console.log('[useConfirm] 开始确认操作, operation_id:', operationId, 'confirmed:', confirmed, 'comment:', comment)
    try {
      const requestData = {
        confirmed,
        comment
      }
      console.log('[useConfirm] 确认操作请求数据:', requestData)
      
      const res = await AIAgentAPI.confirmOperation(operationId, requestData)
      console.log('[useConfirm] 确认操作响应:', res)
      console.log('[useConfirm] 响应数据详情:', JSON.stringify(res, null, 2))

      if (res.data.code === 0) {
        ElMessage.success(confirmed ? '操作已确认并执行' : '操作已拒绝')
        // 从列表中移除
        pendingOps.value = pendingOps.value.filter(op => op.operation_id !== operationId)
        console.log('[useConfirm] 操作确认成功，已从列表中移除')
        return res.data.data
      } else {
        console.error('[useConfirm] 确认操作失败, code:', res.data.code, 'message:', res.data.msg)
        ElMessage.error(res.data.msg || '操作失败')
        return null
      }
    } catch (error: any) {
      console.error('[useConfirm] 确认操作异常:', error)
      console.error('[useConfirm] 错误详情:', {
        message: error?.message,
        response: error?.response,
        data: error?.response?.data,
        status: error?.response?.status,
        statusText: error?.response?.statusText,
        config: error?.config,
        stack: error?.stack
      })
      ElMessage.error('操作失败: ' + (error?.message || '未知错误'))
      return null
    }
  }

  return {
    pendingOps,
    loading,
    loadPendingOperations,
    confirmOp
  }
}

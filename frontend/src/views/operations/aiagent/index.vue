<template>
  <div class="aiagent-container">
    <el-container>
      <!-- 左侧会话列表 -->
      <el-aside width="300px">
        <SessionList
          :sessions="sessions"
          :current-session-id="currentSessionId"
          @select="handleSelectSession"
          @new-session="handleCreateSession"
          @end="handleEndSession"
          @delete="handleDeleteSession"
        />
      </el-aside>

      <!-- 主聊天区域 -->
      <el-main>
        <ChatWindow
          :session-id="currentSessionId"
          :messages="messages"
          :loading="loading"
          @send="handleSendMessage"
          @stop="handleStopMessage"
          @new-session="handleCreateSession"
        />
      </el-main>
    </el-container>

    <!-- 待确认操作对话框 -->
    <ConfirmDialog
      v-model="confirmVisible"
      :operation="currentOperation"
      @confirm="handleConfirmOperation"
    />

    <!-- 待确认操作提示 -->
    <el-badge
      v-if="pendingOpsCount > 0"
      :value="pendingOpsCount"
      class="pending-badge"
    >
      <el-button
        type="warning"
        :icon="Warning"
        circle
        @click="showPendingOperations"
      />
    </el-badge>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Warning } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import AIAgentAPI from '@/api/operations/aiagent'
import { useChat } from './composables/useChat'
import { useConfirm } from './composables/useConfirm'
import ChatWindow from './components/ChatWindow.vue'
import SessionList from './components/SessionList.vue'
import ConfirmDialog from './components/ConfirmDialog.vue'

// 使用composables
const {
  currentSessionId,
  messages,
  loading,
  createNewSession,
  loadHistory,
  sendMsg,
  stopSend,
  clearSession
} = useChat()

const {
  pendingOps,
  loadPendingOperations,
  confirmOp
} = useConfirm()

// 会话列表
const sessions = ref<any[]>([])
const confirmVisible = ref(false)
const currentOperation = ref<any>(null)

// 待确认操作数量
const pendingOpsCount = computed(() => pendingOps.value.length)

// 加载会话列表
const loadSessions = async () => {
  console.log('[AIAgent/index.vue] 开始加载会话列表')
  try {
    const params = { page: 1, page_size: 50 }
    console.log('[AIAgent/index.vue] 请求参数:', params)
    
    const res = await AIAgentAPI.getUserSessions(params)
    console.log('[AIAgent/index.vue] 会话列表响应:', res)
    console.log('[AIAgent/index.vue] 响应数据:', JSON.stringify(res, null, 2))
    
    if (res.data.code === 0) {
      sessions.value = res.data.data?.sessions || []
      console.log('[AIAgent/index.vue] 会话列表加载成功, 数量:', sessions.value.length)
      console.log('[AIAgent/index.vue] 会话列表数据:', sessions.value)
    } else {
      console.error('[AIAgent/index.vue] 会话列表加载失败, code:', res.data.code, 'message:', res.data.msg)
      ElMessage.error(res.data.msg || '加载会话列表失败')
    }
  } catch (error: any) {
    console.error('[AIAgent/index.vue] 加载会话列表异常:', error)
    console.error('[AIAgent/index.vue] 错误详情:', {
      message: error?.message,
      response: error?.response,
      data: error?.response?.data,
      status: error?.response?.status,
      statusText: error?.response?.statusText,
      config: error?.config,
      stack: error?.stack
    })
    ElMessage.error('加载会话列表失败: ' + (error?.message || '未知错误'))
  }
}

// 创建新会话
const handleCreateSession = async () => {
  const session = await createNewSession()
  if (session) {
    await loadSessions()
  }
}

// 选择会话
const handleSelectSession = async (sessionId: number) => {
  await loadHistory(sessionId)
}

// 发送消息
const handleSendMessage = async (message: string) => {
  await sendMsg(message)
  // 发送后检查待确认操作
  await loadPendingOperations(currentSessionId.value || undefined)
}

// 停止发送消息
const handleStopMessage = () => {
  stopSend()
}

// 结束会话
const handleEndSession = async (sessionId: number) => {
  try {
    await ElMessageBox.confirm('确定要结束这个会话吗？', '确认', {
      type: 'warning'
    })
    
    const res = await AIAgentAPI.endSession(sessionId)
    if (res.data.code === 0) {
      ElMessage.success('会话已结束')
      await loadSessions()
      if (currentSessionId.value === sessionId) {
        clearSession()
      }
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('结束会话失败:', error)
    }
  }
}

// 删除会话（暂未实现后端接口）
const handleDeleteSession = (sessionId: number) => {
  ElMessage.warning('删除功能暂未实现')
}

// 显示待确认操作
const showPendingOperations = async () => {
  if (pendingOps.value.length > 0) {
    currentOperation.value = pendingOps.value[0]
    confirmVisible.value = true
  }
}

// 确认操作
const handleConfirmOperation = async (operationId: number, confirmed: boolean, comment: string) => {
  await confirmOp(operationId, confirmed, comment)
  
  // 重新加载待确认操作
  await loadPendingOperations(currentSessionId.value || undefined)
  
  // 如果还有待确认操作，显示下一个
  if (pendingOps.value.length > 0) {
    currentOperation.value = pendingOps.value[0]
  }
}

// 初始化
onMounted(async () => {
  console.log('[AIAgent/index.vue] ========== 组件已挂载，开始初始化 ==========')
  try {
    console.log('[AIAgent/index.vue] 步骤1: 加载会话列表')
    await loadSessions()
    
    console.log('[AIAgent/index.vue] 步骤2: 加载待确认操作')
    await loadPendingOperations()
    
    console.log('[AIAgent/index.vue] ========== 初始化完成 ==========')
  } catch (error: any) {
    console.error('[AIAgent/index.vue] ========== 初始化失败 ==========')
    console.error('[AIAgent/index.vue] 错误:', error)
    console.error('[AIAgent/index.vue] 错误详情:', {
      message: error?.message,
      response: error?.response,
      stack: error?.stack
    })
    ElMessage.error('页面初始化失败: ' + (error?.message || '未知错误'))
  }
})

// 定时刷新待确认操作（每10秒）
setInterval(() => {
  if (currentSessionId.value) {
    loadPendingOperations(currentSessionId.value)
  }
}, 10000)
</script>

<style scoped lang="scss">
.aiagent-container {
  height: calc(100vh - 84px);
  position: relative;

  .el-container {
    height: 100%;
  }

  .el-aside {
    background: #fff;
  }

  .el-main {
    padding: 0;
  }
}

.pending-badge {
  position: fixed;
  right: 40px;
  bottom: 40px;
  z-index: 1000;
}
</style>

<template>
  <div class="chat-window">
    <!-- 消息列表 -->
    <div class="messages-container" ref="messagesRef">
      <el-empty v-if="messages.length === 0" description="暂无消息，开始对话吧">
        <el-button v-if="!sessionId" type="primary" @click="$emit('new-session')">创建会话</el-button>
      </el-empty>

      <div v-else class="messages-list">
        <div
          v-for="(msg, index) in messages"
          :key="index"
          :class="['message-item', `message-${msg.role}`]"
        >
          <div class="message-avatar">
            <el-avatar v-if="msg.role === 'user'" :size="32">
              <el-icon><User /></el-icon>
            </el-avatar>
            <el-avatar v-else :size="32" style="background-color: #409eff">
              <el-icon><Service /></el-icon>
            </el-avatar>
          </div>

          <div class="message-content">
            <div class="message-header">
              <span class="message-role">{{ getRoleName(msg.role) }}</span>
              <span class="message-time" v-if="msg.created_at">
                {{ formatTime(msg.created_at) }}
              </span>
              <span v-if="msg.isStreaming" class="streaming-indicator">
                <el-icon class="is-loading"><Loading /></el-icon>
                生成中...
              </span>
            </div>
            <div class="message-text markdown-body" v-html="formatContent(msg.content)"></div>
            <span v-if="msg.isStreaming" class="typing-cursor">|</span>
            
            <!-- MCP工具调用汇总卡片 -->
            <ToolCallsSummary
              v-if="msg.toolCalls && msg.toolCalls.length > 0"
              :tool-calls="msg.toolCalls"
              :is-streaming="msg.isStreaming"
            />
          </div>
        </div>

        <!-- 加载指示器（仅在没有流式消息时显示） -->
        <div v-if="loading && !hasStreamingMessage" class="message-item message-assistant">
          <div class="message-avatar">
            <el-avatar :size="32" style="background-color: #409eff">
              <el-icon><Service /></el-icon>
            </el-avatar>
          </div>
          <div class="message-content">
            <div class="message-header">
              <span class="message-role">AI助手</span>
            </div>
            <div class="message-text">
              <el-icon class="is-loading"><Loading /></el-icon>
              正在思考中...
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- MCP工具确认弹窗 -->
    <el-dialog
      v-model="confirmDialogVisible"
      title="工具调用确认"
      width="600px"
      :close-on-click-modal="false"
      :show-close="false"
      center
    >
      <div v-if="currentConfirmation" class="confirmation-content">
        <div class="confirmation-header">
          <el-alert
            title="即将执行运维操作"
            :description="currentConfirmation.confirm_reason"
            type="warning"
            show-icon
            :closable="false"
          />
        </div>

        <div class="confirmation-details">
          <h4>操作详情</h4>

            <div class="detail-item">
              <span class="label">工具名称：</span>
              <span class="value">{{ currentConfirmation.tool_name }}</span>
            </div>
            <div class="detail-item">
              <span class="label">操作ID：</span>
              <span class="value">{{ currentConfirmation.operation_id }}</span>
            </div>
            <div class="detail-item">
              <span class="label">调用时间：</span>
              <span class="value">{{ formatTime(currentConfirmation.timestamp) }}
                <span v-if="getTimeDiff(currentConfirmation.timestamp) > 5" class="time-warning">
                  ({{ getTimeDiff(currentConfirmation.timestamp).toFixed(1) }}分钟前)
                </span>
              </span>
            </div>
            <div class="detail-item">
              <span class="label">参数：</span>
              <pre class="value args-json">{{ JSON.stringify(currentConfirmation.tool_args, null, 2) }}</pre>
            </div>
          </div>

        <div class="confirmation-actions">
          <el-button @click="handleReject" :loading="confirming" type="danger">
            拒绝执行
          </el-button>
          <el-button @click="handleConfirm" :loading="confirming" type="primary">
            确认执行
          </el-button>
        </div>
      </div>
    </el-dialog>

    <!-- 输入区域 -->
    <div class="input-container">
      <el-input
        v-model="inputValue"
        type="textarea"
        :rows="3"
        placeholder="输入您的问题，例如：查询生产环境的服务器列表、重启web服务..."
        :disabled="!sessionId || loading"
        @keydown.ctrl.enter="handleSend"
      />
      <div class="input-actions">
        <el-button
          v-if="!loading"
          type="primary"
          :icon="Position"
          circle
          :disabled="!sessionId || !inputValue.trim()"
          @click="handleSend"
          class="send-button"
        />
        <el-button
          v-else
          type="danger"
          :icon="CircleClose"
          circle
          @click="handleStop"
          class="stop-button"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, computed, onMounted } from 'vue'
import { User, Loading, Position, Service, CircleClose } from '@element-plus/icons-vue'
import { marked } from 'marked'
import ToolCallsSummary from './ToolCallsSummary.vue'
import type { McpToolCall } from '@/api/operations/aiagent'

const props = defineProps<{
  sessionId: number | null
  messages: Array<{
    id?: number
    role: 'user' | 'assistant' | 'system'
    content: string
    created_at?: string
    isStreaming?: boolean
    toolCalls?: McpToolCall[]
  }>
  loading: boolean
  pendingConfirmations?: Array<{
    operation_id: number
    tool_name: string
    tool_call_id: string
    tool_args: any
    confirm_reason: string
    timestamp: string
  }>
}>()

const emit = defineEmits<{
  'send': [message: string]
  'stop': []
  'new-session': []
  'confirm-tool': [operationId: number, confirmed: boolean, comment?: string]
}>()

const inputValue = ref('')
const messagesRef = ref<HTMLElement>()

// 确认弹窗相关
const confirmDialogVisible = ref(false)
const currentConfirmation = ref<any>(null)
const confirming = ref(false)

// 配置 marked 选项
onMounted(() => {
  marked.setOptions({
    breaks: true, // 支持回车换行
    gfm: true, // 启用 GitHub 风格的 Markdown
    sanitize: false, // 不进行 HTML 清理（需要信任内容）
    smartLists: true, // 优化列表输出
    smartypants: false // 不使用智能标点
  })
})

// 检查是否有正在流式输出的消息
const hasStreamingMessage = computed(() => {
  return props.messages.some(msg => msg.isStreaming)
})

// 发送消息
const handleSend = () => {
  if (!inputValue.value.trim()) return
  emit('send', inputValue.value)
  inputValue.value = ''
}

// 停止发送
const handleStop = () => {
  emit('stop')
}

// 确认工具调用
const handleConfirm = async () => {
  if (!currentConfirmation.value) return

  // 检查确认请求是否过期
  const confirmTime = new Date(currentConfirmation.value.timestamp)
  const now = new Date()
  const timeDiff = (now.getTime() - confirmTime.getTime()) / 1000 / 60 // 分钟

  if (timeDiff > 10) {
    ElMessage.warning('确认请求已过期，请重新发送消息')
    confirmDialogVisible.value = false
    currentConfirmation.value = null
    return
  }

  confirming.value = true
  try {
    await emit('confirm-tool', currentConfirmation.value.operation_id, true)
    confirmDialogVisible.value = false
    currentConfirmation.value = null
  } catch (error) {
    console.error('[ChatWindow] 确认请求失败:', error)
  } finally {
    confirming.value = false
  }
}

// 拒绝工具调用
const handleReject = async () => {
  if (!currentConfirmation.value) return

  // 检查确认请求是否过期
  const confirmTime = new Date(currentConfirmation.value.timestamp)
  const now = new Date()
  const timeDiff = (now.getTime() - confirmTime.getTime()) / 1000 / 60 // 分钟

  if (timeDiff > 10) {
    ElMessage.warning('确认请求已过期，请重新发送消息')
    confirmDialogVisible.value = false
    currentConfirmation.value = null
    return
  }

  confirming.value = true
  try {
    await emit('confirm-tool', currentConfirmation.value.operation_id, false)
    confirmDialogVisible.value = false
    currentConfirmation.value = null
  } catch (error) {
    console.error('[ChatWindow] 拒绝请求失败:', error)
  } finally {
    confirming.value = false
  }
}

// 角色名称
const getRoleName = (role: string) => {
  const names: Record<string, string> = {
    user: '用户',
    assistant: 'AI助手',
    system: '系统'
  }
  return names[role] || role
}

// 格式化时间
const formatTime = (time: string) => {
  const date = new Date(time)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

// 获取时间差（分钟）
const getTimeDiff = (time: string) => {
  const date = new Date(time)
  const now = new Date()
  return (now.getTime() - date.getTime()) / 1000 / 60
}

// 格式化内容（使用 marked 解析 Markdown）
const formatContent = (content: string) => {
  try {
    return marked.parse(content) as string
  } catch (error) {
    console.error('Markdown 解析失败:', error)
    return content // 解析失败时返回原始内容
  }
}

// 自动滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

// 监听消息变化，自动滚动
watch(() => props.messages.length, scrollToBottom)
watch(() => props.loading, scrollToBottom)

// 深度监听消息内容变化（用于流式输出时滚动）
watch(
  () => props.messages,
  () => {
    scrollToBottom()
  },
  { deep: true }
)

// 监听待确认操作，自动显示确认弹窗
watch(
  () => props.pendingConfirmations,
  (newConfirmations) => {
    if (newConfirmations && newConfirmations.length > 0 && !confirmDialogVisible.value) {
      // 检查是否有过期的确认请求
      const now = new Date()
      const validConfirmations = newConfirmations.filter(c => {
        const confirmTime = new Date(c.timestamp)
        const timeDiff = (now.getTime() - confirmTime.getTime()) / 1000 / 60 // 分钟
        return timeDiff <= 10 // 只保留10分钟内的确认请求
      })

      if (validConfirmations.length > 0) {
        // 显示第一个有效的确认操作
        currentConfirmation.value = validConfirmations[0]
        confirmDialogVisible.value = true
      }
    }
  },
  { deep: true }
)
</script>

<style scoped lang="scss">
.chat-window {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
  padding: 0 40px 40px 40px;
  box-sizing: border-box;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px 0;
}

.messages-list {
  max-width: 900px;
  margin: 0 auto;
}

// 修改el-empty的描述文字样式
:deep(.el-empty__description) {
  color: #000 !important;
  font-size: 16px !important;
}

.message-item {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;

  &.message-user {
    flex-direction: row-reverse;

    .message-content {
      align-items: flex-end;
    }

    .message-text {
      background: #409eff;
      color: #fff;
    }
  }
}

.message-avatar {
  flex-shrink: 0;
}

.message-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.message-header {
  display: flex;
  gap: 12px;
  align-items: center;
  font-size: 12px;
  color: #909399;
}

.message-role {
  font-weight: 500;
}

.message-text {
  padding: 12px 16px;
  background: #f4f4f5;
  border-radius: 8px;
  line-height: 1.6;
  word-wrap: break-word;
  white-space: normal;
}

// Markdown 样式
.markdown-body {
  // 标题样式 - 减小间距
  :deep(h1),
  :deep(h2),
  :deep(h3),
  :deep(h4),
  :deep(h5),
  :deep(h6) {
    margin-top: 12px;
    margin-bottom: 6px;
    font-weight: 600;
    line-height: 1.4;
  }
  
  // 第一个标题不需要上边距
  :deep(h1:first-child),
  :deep(h2:first-child),
  :deep(h3:first-child),
  :deep(h4:first-child),
  :deep(h5:first-child),
  :deep(h6:first-child) {
    margin-top: 0;
  }

  :deep(h1) {
    font-size: 24px;
    border-bottom: 1px solid #e4e7ed;
    padding-bottom: 8px;
  }

  :deep(h2) {
    font-size: 20px;
    border-bottom: 1px solid #f0f0f0;
    padding-bottom: 6px;
  }

  :deep(h3) {
    font-size: 18px;
  }

  :deep(h4) {
    font-size: 16px;
  }

  :deep(h5) {
    font-size: 14px;
  }

  :deep(h6) {
    font-size: 13px;
  }

  // 段落样式 - 移除上下边距以避免多余换行
  :deep(p) {
    margin: 0;
    line-height: 1.6;
  }
  
  // 段落之间的间距 - 减小间距
  :deep(p + p) {
    margin-top: 4px;
  }

  // 列表样式 - 减小间距
  :deep(ul),
  :deep(ol) {
    margin: 6px 0;
    padding-left: 20px;
  }

  :deep(li) {
    margin: 2px 0;
    line-height: 1.6;
  }

  :deep(ul li) {
    list-style-type: disc;
  }

  :deep(ol li) {
    list-style-type: decimal;
  }

  // 代码块样式 - 减小间距
  :deep(pre) {
    background: #282c34;
    color: #abb2bf;
    padding: 12px;
    border-radius: 6px;
    overflow-x: auto;
    margin: 8px 0;
    font-family: 'Courier New', 'Consolas', monospace;
    font-size: 14px;
    line-height: 1.5;
  }

  :deep(code) {
    background: rgba(0, 0, 0, 0.06);
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Courier New', 'Consolas', monospace;
    font-size: 0.9em;
    color: #e83e8c;
  }

  :deep(pre code) {
    background: transparent;
    padding: 0;
    color: inherit;
    font-size: inherit;
  }

  // 引用样式 - 减小间距
  :deep(blockquote) {
    border-left: 4px solid #409eff;
    margin: 8px 0;
    padding: 6px 12px;
    background: #f4f9ff;
    color: #606266;
  }

  // 表格样式
  :deep(table) {
    border-collapse: collapse;
    margin: 12px 0;
    width: 100%;
  }

  :deep(th),
  :deep(td) {
    border: 1px solid #e4e7ed;
    padding: 8px 12px;
    text-align: left;
  }

  :deep(th) {
    background: #f5f7fa;
    font-weight: 600;
  }

  :deep(tr:nth-child(even)) {
    background: #fafafa;
  }

  // 链接样式
  :deep(a) {
    color: #409eff;
    text-decoration: none;
    transition: color 0.2s;

    &:hover {
      color: #66b1ff;
      text-decoration: underline;
    }
  }

  // 图片样式
  :deep(img) {
    max-width: 100%;
    height: auto;
    border-radius: 4px;
    margin: 8px 0;
  }

  // 分割线样式
  :deep(hr) {
    border: none;
    border-top: 1px solid #e4e7ed;
    margin: 16px 0;
  }

  // 粗体和斜体
  :deep(strong) {
    font-weight: 600;
  }

  :deep(em) {
    font-style: italic;
  }

  // 删除线
  :deep(del) {
    text-decoration: line-through;
    color: #909399;
  }

  // 任务列表
  :deep(input[type="checkbox"]) {
    margin-right: 8px;
  }
}

.input-container {
  border-top:1px solid #e4e7ed;
  padding: 16px 0;
  background: #fff;
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
}

.input-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.send-button,
.stop-button {
  width: 40px;
  height: 40px;
  font-size: 18px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.send-button {
  background-color: #409eff;
  border-color: #409eff;
  
  &:hover:not(:disabled) {
    background-color: #66b1ff;
    border-color: #66b1ff;
  }
}

.stop-button {
  background-color: #f56c6c;
  border-color: #f56c6c;
  
  &:hover {
    background-color: #f78989;
    border-color: #f78989;
  }
}

.is-loading {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

// 确认弹窗样式
.confirmation-content {
  .confirmation-header {
    margin-bottom: 20px;
  }

  .confirmation-details {
    margin-bottom: 20px;

    h4 {
      margin-bottom: 12px;
      color: #303133;
      font-size: 16px;
      font-weight: 500;
    }

    .detail-item {
      display: flex;
      margin-bottom: 8px;
      align-items: flex-start;

      .label {
        min-width: 80px;
        color: #606266;
        font-weight: 500;
        flex-shrink: 0;
      }

          .value {
            color: #303133;
            word-break: break-word;

            .time-warning {
              color: #e6a23c;
              font-size: 12px;
              margin-left: 8px;
            }

            &.args-json {
          background: #f5f5f5;
          padding: 8px;
          border-radius: 4px;
          font-family: 'Courier New', monospace;
          font-size: 12px;
          max-height: 200px;
          overflow-y: auto;
          white-space: pre-wrap;
          margin: 0;
          width: 100%;
        }
      }
    }
  }

  .confirmation-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    padding-top: 20px;
    border-top: 1px solid #ebeef5;
  }
}

// 流式输出相关样式
.streaming-indicator {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #409eff;
  font-size: 12px;
  margin-left: 8px;
}

.typing-cursor {
  display: inline-block;
  animation: blink 1s step-end infinite;
  color: #409eff;
  font-weight: bold;
  margin-left: 2px;
}

@keyframes blink {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0;
  }
}
</style>
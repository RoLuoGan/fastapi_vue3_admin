<template>
  <div class="chat-window">
    <!-- 消息列表 -->
    <div class="messages-container" ref="messagesRef">
      <el-empty v-if="messages.length === 0" description="暂无消息，开始对话吧">
        <el-button type="primary" @click="$emit('new-session')">创建会话</el-button>
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
            <div class="message-text">
              <span v-html="formatContent(msg.content)"></span>
              <span v-if="msg.isStreaming" class="typing-cursor">|</span>
            </div>
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
import { ref, watch, nextTick, computed } from 'vue'
import { User, Loading, Position, Service, CircleClose } from '@element-plus/icons-vue'

const props = defineProps<{
  sessionId: number | null
  messages: Array<{
    id?: number
    role: 'user' | 'assistant' | 'system'
    content: string
    created_at?: string
    isStreaming?: boolean
  }>
  loading: boolean
}>()

const emit = defineEmits<{
  'send': [message: string]
  'stop': []
  'new-session': []
}>()

const inputValue = ref('')
const messagesRef = ref<HTMLElement>()

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

// 格式化内容（支持基本的Markdown格式）
const formatContent = (content: string) => {
  let formatted = content
  
  // 代码块
  formatted = formatted.replace(/```(\w+)?\n([\s\S]*?)```/g, (_, lang, code) => {
    return `<pre><code>${escapeHtml(code.trim())}</code></pre>`
  })
  
  // 行内代码
  formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>')
  
  // 粗体
  formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  
  // 斜体
  formatted = formatted.replace(/\*([^*]+)\*/g, '<em>$1</em>')
  
  // 换行
  formatted = formatted.replace(/\n/g, '<br/>')
  
  return formatted
}

// HTML转义
const escapeHtml = (text: string) => {
  const map: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  }
  return text.replace(/[&<>"']/g, m => map[m])
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
</script>

<style scoped lang="scss">
.chat-window {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.messages-list {
  max-width: 900px;
  margin: 0 auto;
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
  white-space: pre-wrap;

  :deep(pre) {
    background: #282c34;
    color: #abb2bf;
    padding: 12px;
    border-radius: 4px;
    overflow-x: auto;
  }

  :deep(code) {
    background: rgba(0, 0, 0, 0.05);
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'Courier New', monospace;
  }

  :deep(ul), :deep(ol) {
    padding-left: 20px;
  }
}

.input-container {
  border-top: 1px solid #e4e7ed;
  padding: 16px 20px;
  background: #fff;
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

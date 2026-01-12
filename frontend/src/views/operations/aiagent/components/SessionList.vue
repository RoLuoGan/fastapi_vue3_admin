<template>
  <div class="session-list">
    <div class="session-header">
      <h3>会话列表</h3>
      <el-button
        type="primary"
        size="small"
        :icon="Plus"
        @click="$emit('new-session')"
      >
        新建会话
      </el-button>
    </div>

    <el-scrollbar height="calc(100vh - 180px)">
      <div class="session-items">
        <div
          v-for="session in sessions"
          :key="session.id"
          :class="['session-item', { active: session.id === currentSessionId }]"
          @click="$emit('select', session.id)"
        >
          <div class="session-info">
            <div class="session-name">{{ session.session_name }}</div>
            <div class="session-meta">
              <el-tag :type="getStatusType(session.status)" size="small">
                {{ getStatusText(session.status) }}
              </el-tag>
              <span class="session-time">{{ formatTime(session.updated_at) }}</span>
            </div>
          </div>
          
          <el-dropdown trigger="click" @command="(cmd) => handleCommand(cmd, session.id)">
            <el-icon class="session-actions"><MoreFilled /></el-icon>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="end" v-if="session.status === 'active'">
                  结束会话
                </el-dropdown-item>
                <el-dropdown-item command="delete" divided>
                  删除会话
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <el-empty v-if="sessions.length === 0" description="暂无会话" />
      </div>
    </el-scrollbar>
  </div>
</template>

<script setup lang="ts">
import { Plus, MoreFilled } from '@element-plus/icons-vue'

interface Session {
  id: number
  session_name: string
  status: string
  llm_model: string
  total_tokens: number
  created_at: string
  updated_at: string
}

defineProps<{
  sessions: Session[]
  currentSessionId: number | null
}>()

const emit = defineEmits<{
  'select': [sessionId: number]
  'new-session': []
  'end': [sessionId: number]
  'delete': [sessionId: number]
}>()

const handleCommand = (command: string, sessionId: number) => {
  if (command === 'end') {
    emit('end', sessionId)
  } else if (command === 'delete') {
    emit('delete', sessionId)
  }
}

const getStatusType = (status: string) => {
  const types: Record<string, any> = {
    active: 'success',
    ended: 'info',
    error: 'danger',
    takeover: 'warning'
  }
  return types[status] || 'info'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    active: '进行中',
    ended: '已结束',
    error: '错误',
    takeover: '已接管'
  }
  return texts[status] || status
}

const formatTime = (time: string) => {
  const date = new Date(time)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 86400000) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}
</script>

<style scoped lang="scss">
.session-list {
  height: 100%;
  background: #fff;
  border-right: 1px solid #e4e7ed;
}

.session-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #e4e7ed;

  h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 500;
  }
}

.session-items {
  padding: 8px;
}

.session-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  margin-bottom: 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;

  &:hover {
    background: #f5f7fa;
  }

  &.active {
    background: #ecf5ff;
    border: 1px solid #409eff;
  }
}

.session-info {
  flex: 1;
  min-width: 0;
}

.session-name {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 12px;
  color: #909399;
}

.session-time {
  font-size: 12px;
}

.session-actions {
  cursor: pointer;
  color: #909399;
  
  &:hover {
    color: #409eff;
  }
}
</style>

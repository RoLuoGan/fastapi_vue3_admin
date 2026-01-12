<template>
  <el-dialog
    v-model="visible"
    title="操作确认"
    width="600px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-alert
      type="warning"
      :closable="false"
      style="margin-bottom: 16px"
    >
      <template #title>
        <div style="font-size: 14px; font-weight: 500;">
          以下操作需要您的确认，请仔细核对信息
        </div>
      </template>
    </el-alert>

    <div v-if="operation" class="operation-info">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="操作类型">
          <el-tag>{{ operation.operation_type }}</el-tag>
        </el-descriptions-item>
        
        <el-descriptions-item label="工具名称">
          {{ operation.tool_name }}
        </el-descriptions-item>

        <el-descriptions-item label="目标资源" v-if="operation.target_resource">
          {{ operation.target_resource }}
        </el-descriptions-item>

        <el-descriptions-item label="操作参数">
          <el-scrollbar max-height="200px">
            <pre class="params-pre">{{ JSON.stringify(operation.params, null, 2) }}</pre>
          </el-scrollbar>
        </el-descriptions-item>

        <el-descriptions-item label="需要确认原因">
          <el-text type="danger">{{ operation.confirm_reason }}</el-text>
        </el-descriptions-item>

        <el-descriptions-item label="发起时间">
          {{ formatTime(operation.created_at) }}
        </el-descriptions-item>
      </el-descriptions>

      <div class="comment-input" style="margin-top: 16px;">
        <el-input
          v-model="comment"
          type="textarea"
          :rows="3"
          placeholder="请输入确认备注（可选）"
        />
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleReject" :loading="loading">
          <el-icon><Close /></el-icon>
          拒绝执行
        </el-button>
        <el-button type="primary" @click="handleConfirm" :loading="loading">
          <el-icon><Check /></el-icon>
          确认执行
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Check, Close } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

interface Operation {
  operation_id: number
  session_id: number
  operation_type: string
  tool_name: string
  target_resource?: string
  params: any
  confirm_reason: string
  created_at: string
}

const props = defineProps<{
  modelValue: boolean
  operation: Operation | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'confirm': [operationId: number, confirmed: boolean, comment: string]
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const comment = ref('')
const loading = ref(false)

// 确认操作
const handleConfirm = async () => {
  if (!props.operation) return
  
  loading.value = true
  try {
    emit('confirm', props.operation.operation_id, true, comment.value)
    handleClose()
  } finally {
    loading.value = false
  }
}

// 拒绝操作
const handleReject = async () => {
  if (!props.operation) return
  
  loading.value = true
  try {
    emit('confirm', props.operation.operation_id, false, comment.value)
    handleClose()
  } finally {
    loading.value = false
  }
}

// 关闭对话框
const handleClose = () => {
  comment.value = ''
  visible.value = false
}

// 格式化时间
const formatTime = (time: string) => {
  return new Date(time).toLocaleString('zh-CN')
}
</script>

<style scoped lang="scss">
.operation-info {
  padding: 8px 0;
}

.params-pre {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  background: #f5f5f5;
  padding: 8px;
  border-radius: 4px;
  margin: 0;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>

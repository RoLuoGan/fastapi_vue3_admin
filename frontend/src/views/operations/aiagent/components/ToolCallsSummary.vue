<template>
  <div class="tool-calls-summary">
    <el-collapse>
      <el-collapse-item name="tools">
        <template #title>
          <div class="summary-header">
            <div class="summary-left">
              <el-icon class="tool-icon is-loading" v-if="isStreaming">
                <Loading />
              </el-icon>
              <el-icon class="tool-icon" v-else>
                <Tools />
              </el-icon>
              <span class="summary-text">工具调用</span>
              <el-tag type="info" size="small">{{ toolCalls.length }}次</el-tag>
            </div>
            <div class="summary-right">
              <el-tag 
                v-if="allSuccess" 
                type="success" 
                size="small"
                class="status-tag"
              >
                全部成功
              </el-tag>
              <el-tag 
                v-else-if="hasFailure" 
                type="danger" 
                size="small"
                class="status-tag"
              >
                部分失败
              </el-tag>
            </div>
          </div>
        </template>

        <div class="tool-calls-list">
          <McpToolCallCard
            v-for="(toolCall, index) in toolCalls"
            :key="index"
            :tool-call="toolCall"
            :step="index + 1"
          />
        </div>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Tools, Loading } from '@element-plus/icons-vue'
import McpToolCallCard from './McpToolCallCard.vue'
import type { McpToolCall } from '@/api/operations/aiagent'

const props = defineProps<{
  toolCalls: McpToolCall[]
  isStreaming?: boolean
}>()

// 判断是否全部成功
const allSuccess = computed(() => {
  return props.toolCalls.length > 0 && props.toolCalls.every(call => call.success)
})

// 判断是否有失败
const hasFailure = computed(() => {
  return props.toolCalls.some(call => !call.success)
})
</script>

<style scoped lang="scss">
.tool-calls-summary {
  margin-top: 12px;
  max-width: 100%;

  :deep(.el-collapse) {
    border: none;
    border-radius: 8px;
    overflow: hidden;
  }

  :deep(.el-collapse-item__header) {
    height: auto;
    line-height: normal;
    padding: 12px 16px;
    background: #f5f7fa;
    border: 1px solid #e4e7ed;
    border-radius: 8px;
    margin-bottom: 8px;
    transition: all 0.3s;

    &:hover {
      background: #ecf5ff;
    }
  }

  :deep(.el-collapse-item__wrap) {
    border: none;
    background: transparent;
  }

  :deep(.el-collapse-item__content) {
    padding: 0;
  }

  .summary-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
  }

  .summary-left {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;
  }

  .tool-icon {
    font-size: 18px;
    color: #409eff;
    flex-shrink: 0;

    &.is-loading {
      animation: rotating 2s linear infinite;
    }
  }

  .summary-text {
    font-size: 14px;
    font-weight: 500;
    color: #303133;
  }

  .summary-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .status-tag {
    margin-left: 8px;
  }

  .tool-calls-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 8px 0;
  }

  @keyframes rotating {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }
}
</style>
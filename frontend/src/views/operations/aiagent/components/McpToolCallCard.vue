<template>
  <div class="mcp-tool-call-card">
    <el-card class="tool-card" shadow="hover">
      <template #header>
        <div class="tool-card-header">
          <div class="tool-header-left">
            <el-icon class="tool-icon" :class="{ 'success': toolCall.success, 'error': !toolCall.success }">
              <Tools v-if="toolCall.success" />
              <Warning v-else />
            </el-icon>
            <span class="tool-name">{{ toolCall.tool }}</span>
            <el-tag v-if="toolCall.success" type="success" size="small">成功</el-tag>
            <el-tag v-else type="danger" size="small">失败</el-tag>
          </div>
        </div>
      </template>

      <div class="tool-card-body">
        <!-- 输入参数 -->
        <div class="tool-section">
          <div class="section-title">
            <el-icon><DocumentCopy /></el-icon>
            <span>输入参数</span>
          </div>
          <div class="section-content">
            <pre class="json-content">{{ formatJson(toolCall.input) }}</pre>
          </div>
        </div>

        <!-- 输出结果 -->
        <div class="tool-section">
          <div class="section-title">
            <el-icon><CircleCheck /></el-icon>
            <span>执行结果</span>
          </div>
          <div class="section-content">
            <div class="output-content" v-html="formatOutput(toolCall.output)"></div>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { Tools, Warning, DocumentCopy, CircleCheck } from '@element-plus/icons-vue'
import type { McpToolCall } from '@/api/operations/aiagent'

defineProps<{
  toolCall: McpToolCall
}>()

// 格式化JSON
const formatJson = (obj: any): string => {
  if (!obj) return ''
  try {
    return JSON.stringify(obj, null, 2)
  } catch {
    return String(obj)
  }
}

// 格式化输出（支持Markdown和换行）
const formatOutput = (output: string): string => {
  if (!output) return ''
  // 简单的换行处理，将\n转换为<br>
  return output
    .replace(/\n/g, '<br>')
    .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre class="code-block">$2</pre>')
}
</script>

<style scoped lang="scss">
.mcp-tool-call-card {
  margin: 12px 0;
  max-width: 100%;

  .tool-card {
    border-radius: 8px;
    border: 1px solid #e4e7ed;
    background: #fafafa;

    :deep(.el-card__header) {
      padding: 12px 16px;
      background: #fff;
      border-bottom: 1px solid #e4e7ed;
    }

    :deep(.el-card__body) {
      padding: 16px;
    }
  }

  .tool-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .tool-header-left {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;
  }

  .tool-icon {
    font-size: 18px;

    &.success {
      color: #67c23a;
    }

    &.error {
      color: #f56c6c;
    }
  }

  .tool-name {
    font-weight: 600;
    font-size: 14px;
    color: #303133;
    flex: 1;
  }

  .tool-card-body {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .tool-section {
    background: #fff;
    border-radius: 6px;
    padding: 12px;
    border: 1px solid #e4e7ed;
  }

  .section-title {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    font-weight: 600;
    color: #606266;
    margin-bottom: 10px;
    padding-bottom: 8px;
    border-bottom: 1px solid #f0f0f0;

    .el-icon {
      font-size: 16px;
      color: #409eff;
    }
  }

  .section-content {
    max-height: 400px;
    overflow-y: auto;
  }

  .json-content {
    margin: 0;
    padding: 12px;
    background: #282c34;
    color: #abb2bf;
    border-radius: 4px;
    font-family: 'Courier New', 'Consolas', monospace;
    font-size: 13px;
    line-height: 1.5;
    overflow-x: auto;
    white-space: pre-wrap;
    word-wrap: break-word;
  }

  .output-content {
    color: #303133;
    font-size: 14px;
    line-height: 1.6;
    white-space: pre-wrap;
    word-wrap: break-word;

    .code-block {
      background: #282c34;
      color: #abb2bf;
      padding: 12px;
      border-radius: 4px;
      font-family: 'Courier New', 'Consolas', monospace;
      font-size: 13px;
      overflow-x: auto;
      margin: 8px 0;
    }
  }
}
</style>


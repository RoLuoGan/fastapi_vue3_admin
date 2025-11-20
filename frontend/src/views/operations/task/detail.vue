<template>
  <div class="task-detail page-root">
    <el-page-header @back="handleBack" content="任务详情" class="mb-4" />

    <el-card shadow="never" class="mb-4">
      <template #header>
        <div class="flex justify-between items-center">
          <span>基本信息</span>
          <div class="flex gap-2">
            <el-button type="primary" plain icon="Refresh" @click="reloadDetail">
              刷新
            </el-button>
            <el-button
              type="success"
              plain
              icon="Document"
              @click="toggleParamDrawer"
              v-hasPerm="['operations:task:query']"
            >
              构建参数查看
            </el-button>
            <el-button
              type="danger"
              icon="Delete"
              @click="handleDelete"
              v-hasPerm="['operations:task:delete']"
            >
              删除构建
            </el-button>
          </div>
        </div>
      </template>
      <el-descriptions v-if="taskDetail" :column="2" border>
        <el-descriptions-item label="任务ID">
          {{ taskDetail.id }}
        </el-descriptions-item>
        <el-descriptions-item label="任务类型">
          <el-tag :type="taskTypeTag(taskDetail.task_type)">
            {{ taskTypeLabel(taskDetail.task_type) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="任务进度" :span="2">
          <div class="flex items-center gap-4">
            <el-tag :type="statusTag(taskDetail.task_status)" style="min-width: 60px">
              {{ statusLabel(taskDetail.task_status) }}
            </el-tag>
            <el-progress
              :percentage="taskDetail.progress || 0"
              :status="progressStatus(taskDetail.task_status)"
              :text-inside="true"
              :stroke-width="18"
              style="flex: 1; max-width: 300px"
            />
          </div>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">
          {{ taskDetail.created_at || "-" }}
        </el-descriptions-item>
        <el-descriptions-item label="更新时间">
          {{ taskDetail.updated_at || "-" }}
        </el-descriptions-item>
        <el-descriptions-item label="错误信息" :span="2">
          <span :class="['error-text', { 'is-empty': !taskDetail.error_message }]">
            {{ taskDetail.error_message || "-" }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="日志文件" :span="2">
          <span>
            {{ taskDetail.log_path || "-" }}
            <template v-if="taskDetail.log_size">
              （{{ formatSize(taskDetail.log_size) }}）
            </template>
          </span>
        </el-descriptions-item>
      </el-descriptions>
      <el-skeleton v-else :rows="6" animated />
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="flex justify-between items-center">
          <span>控制台输出</span>
          <div class="flex gap-2 items-center">
            <span class="text-xs text-gray-500">
              状态：{{ streamStatusLabel }}
            </span>
            <el-button size="small" icon="Top" @click="scrollToTop">
              顶部
            </el-button>
            <el-button size="small" icon="Bottom" @click="scrollToBottom">
              底部
            </el-button>
            <el-button plain icon="Refresh" @click="restartStream">
              重连
            </el-button>
          </div>
        </div>
      </template>
      <div ref="logContainerRef" class="log-container">
        <p
          v-for="entry in logLines"
          :key="entry.id"
          class="log-line"
          :class="`log-line--${entry.type}`"
        >
          <span class="log-timestamp">[{{ entry.timestamp }}]</span>
          <span class="log-message">{{ entry.message }}</span>
        </p>
        <p v-if="logLines.length === 0" class="log-empty">
          暂无日志输出，等待任务写入日志…
        </p>
      </div>
    </el-card>

    <el-drawer v-model="paramDrawerVisible" title="构建参数" size="40%">
      <el-scrollbar height="100%">
        <pre class="param-json">{{ prettyParams }}</pre>
      </el-scrollbar>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import NodeAPI, { type TaskDetail } from "@/api/operations/node";
import { Auth } from "@/utils/auth";

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const taskDetail = ref<TaskDetail>();

interface LogEntry {
  id: string;
  timestamp: string;
  message: string;
  type: "log" | "info" | "error" | "end" | "system";
}

const logLines = ref<LogEntry[]>([]);
const streamStatusLabel = ref("未连接");
const eventSource = ref<EventSource | null>(null);
const paramDrawerVisible = ref(false);
const logContainerRef = ref<HTMLElement>();
const isTaskFinished = ref(false);

const taskId = computed<number>(() => {
  const paramId = route.params.id;
  if (paramId) {
    return Number(paramId);
  }
  const queryId = route.query.id;
  return Number(queryId);
});

const prettyParams = computed(() => {
  if (!taskDetail.value?.params) return "暂无参数";
  return JSON.stringify(taskDetail.value.params, null, 2);
});

// ==================== 工具函数 ====================

function taskTypeLabel(type?: string) {
  if (type === "deploy") return "部署";
  if (type === "restart") return "重启";
  return type || "-";
}

function taskTypeTag(type?: string) {
  if (type === "deploy") return "success";
  if (type === "restart") return "warning";
  return "info";
}

function statusLabel(status?: string) {
  switch (status) {
    case "running":
      return "执行中";
    case "success":
      return "成功";
    case "partial_success":
      return "部分成功";
    case "failed":
      return "失败";
    default:
      return status || "-";
  }
}

function statusTag(status?: string) {
  switch (status) {
    case "running":
      return "warning";
    case "success":
      return "success";
    case "partial_success":
      return "warning";
    case "failed":
      return "danger";
    default:
      return "info";
  }
}

function progressStatus(status?: string) {
  if (status === "success") return "success";
  if (status === "partial_success") return "warning";
  if (status === "failed") return "exception";
  return undefined;
}

function formatSize(size?: number) {
  if (!size) return "-";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(2)} KB`;
  return `${(size / (1024 * 1024)).toFixed(2)} MB`;
}

function pad(value: number): string {
  return value.toString().padStart(2, "0");
}

function nowTimestamp(): string {
  const now = new Date();
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(
    now.getMinutes()
  )}:${pad(now.getSeconds())}`;
}

function normalizeTimestamp(raw?: string): string {
  if (!raw) return nowTimestamp();
  const parsed = new Date(raw);
  if (!Number.isNaN(parsed.getTime())) {
    return `${parsed.getFullYear()}-${pad(parsed.getMonth() + 1)}-${pad(parsed.getDate())} ${pad(
      parsed.getHours()
    )}:${pad(parsed.getMinutes())}:${pad(parsed.getSeconds())}`;
  }
  return raw;
}

// ==================== 日志管理 ====================

function appendLogEntry(entry: LogEntry) {
  // 去重：非system类型的事件使用id去重
  if (entry.type !== "system" && entry.id) {
    const exists = logLines.value.some((item) => item.id === entry.id);
    if (exists) {
      return;
    }
  }
  logLines.value.push(entry);
  nextTick(() => {
    if (logContainerRef.value) {
      logContainerRef.value.scrollTop = logContainerRef.value.scrollHeight;
    }
  });
}

function appendSystemLog(message: string, type: LogEntry["type"] = "system") {
  appendLogEntry({
    id: `${type}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    timestamp: nowTimestamp(),
    message,
    type,
  });
}

// ==================== SSE事件处理 ====================

/**
 * 统一处理SSE事件
 * 解析标准化的SSE事件格式: { type, payload, timestamp, requestId }
 */
function handleSSEEvent(event: MessageEvent, defaultType: LogEntry["type"] = "log"): void {
  const rawData = event.data;
  
  console.log("[SSE] handleSSEEvent 被调用, rawData:", rawData, "defaultType:", defaultType);
  
  if (!rawData || (typeof rawData === "string" && rawData.trim().length === 0)) {
    console.warn("[SSE] 事件数据为空");
    return;
  }
  
  let data: any;
  try {
    data = JSON.parse(rawData);
    console.log("[SSE] 解析后的数据:", data);
  } catch (error) {
    console.error("[SSE] 解析事件数据失败:", error, rawData);
    return;
  }

  if (!data || typeof data !== "object" || Array.isArray(data)) {
    console.warn("[SSE] 数据格式不正确:", data);
    return;
  }

  const eventType = data.type;
  const payload = data.payload || {};
  const timestampRaw = data.timestamp;
  
  console.log("[SSE] 事件类型:", eventType, "payload:", payload);

  // 处理任务状态更新事件
  if (eventType === "task_status") {
    if (taskDetail.value && payload) {
      if (payload.taskStatus) {
        taskDetail.value.task_status = payload.taskStatus;
        // 如果任务已结束，关闭SSE连接并停止定时刷新
        if (["success", "partial_success", "failed"].includes(payload.taskStatus)) {
          stopLogStream();
          stopTaskDetailRefresh();
          streamStatusLabel.value = "任务已结束";
          isTaskFinished.value = true;
        } else if (payload.taskStatus !== "running") {
          stopTaskDetailRefresh();
        }
      }
      if (payload.progress !== undefined) {
        taskDetail.value.progress = payload.progress;
      }
      if (payload.errorMessage !== undefined) {
        taskDetail.value.error_message = payload.errorMessage;
      }
      if (timestampRaw && typeof timestampRaw === "number") {
        const date = new Date(timestampRaw * 1000);
        taskDetail.value.updated_at = date.toISOString().replace("T", " ").substring(0, 19);
      }
    }
    return;
  }

  // 处理日志类事件（task_log, task_info, task_error, task_end）
  const message = payload.content || payload.message || payload.data || "";
  console.log("[SSE] 提取的消息内容:", message, "payload:", payload);
  
  if (!message || (typeof message === "string" && message.trim().length === 0)) {
    console.warn("[SSE] 消息内容为空，跳过处理");
    return;
  }

  const entryId =
    (event.lastEventId && `${event.lastEventId}`.length > 0
      ? `${event.lastEventId}`
      : `${eventType}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`);

  // 优先从日志内容中提取时间戳（格式: [2025-11-20 12:19:06] ...）
  let timestamp: string;
  const messageStr = String(message).trim();
  
  // 尝试从日志内容中提取时间戳（支持多种格式）
  // 格式1: [2025-11-20 12:19:06] ...
  // 格式2: [脚本输出] [2025-11-20 12:19:06] ...
  // 使用全局匹配，取最后一个时间戳（最接近实际日志时间）
  const timestampMatches = messageStr.matchAll(/\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]/g);
  const allMatches = Array.from(timestampMatches);
  let hasTimestampInMessage = false;
  
  if (allMatches.length > 0) {
    // 取最后一个时间戳（最接近实际日志时间）
    const lastMatch = allMatches[allMatches.length - 1];
    timestamp = normalizeTimestamp(lastMatch[1]);
    hasTimestampInMessage = true;
  } else if (timestampRaw && typeof timestampRaw === "number") {
    // 使用事件的时间戳
    const date = new Date(timestampRaw * 1000);
    timestamp = normalizeTimestamp(date.toISOString());
  } else {
    // 使用当前时间
    timestamp = normalizeTimestamp(timestampRaw) || nowTimestamp();
  }

  // 映射事件类型到前端日志类型
  let logType: LogEntry["type"] = defaultType;
  if (eventType === "task_log") {
    logType = "log";
  } else if (eventType === "task_info") {
    logType = "info";
  } else if (eventType === "task_error") {
    logType = "error";
  } else if (eventType === "task_end") {
    logType = "end";
  }

  // 如果是结束事件，设置标志并关闭连接
  if (eventType === "task_end") {
    isTaskFinished.value = true;
    streamStatusLabel.value = "已结束";
    stopLogStream();
    stopTaskDetailRefresh();
  }

  // 如果日志内容已经包含时间戳，从消息中移除时间戳部分，避免重复显示
  let displayMessage = String(message).trim();
  if (hasTimestampInMessage && allMatches.length > 0) {
    // 移除消息中所有的时间戳部分（保留其他内容）
    // 例如: [2025-11-20 12:19:06] [脚本输出] [2025-11-20 12:19:06] 消息内容
    // 变成: [脚本输出] 消息内容
    displayMessage = displayMessage.replace(/\[\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\]\s*/g, "");
    // 清理多余的空格
    displayMessage = displayMessage.trim();
  }
  
  const logEntry = {
    id: entryId,
    timestamp,
    message: displayMessage,
    type: logType,
  };
  
  console.log("[SSE] 准备添加日志条目:", logEntry);
  appendLogEntry(logEntry);
  console.log("[SSE] 日志条目已添加，当前日志行数:", logLines.value.length);
}

// ==================== SSE连接管理 ====================

function startLogStream() {
  stopLogStream();
  
  if (!taskId.value) {
    streamStatusLabel.value = "未连接";
    return;
  }
  
  // 如果任务已结束，不启动SSE连接，直接加载完整日志
  if (isTaskFinished.value) {
    streamStatusLabel.value = "任务已结束";
    if (logLines.value.length === 0 || logLines.value.every(entry => entry.type === "system")) {
      loadCompleteLogs();
    }
    return;
  }
  
  // 检查任务状态，如果已结束则不启动SSE连接
  if (taskDetail.value?.task_status && ["success", "partial_success", "failed"].includes(taskDetail.value.task_status)) {
    isTaskFinished.value = true;
    streamStatusLabel.value = "任务已结束";
    if (logLines.value.length === 0 || logLines.value.every(entry => entry.type === "system")) {
      loadCompleteLogs();
    }
    return;
  }
  
  const token = Auth.getAccessToken();
  if (!token) {
    streamStatusLabel.value = "未登录";
    return;
  }
  
  const baseURL = import.meta.env.VITE_APP_BASE_API?.replace(/\/$/, "") || "";
  const params = new URLSearchParams({ token });
  const lastLogEntry = [...logLines.value].reverse().find((entry) => entry.type !== "system");
  if (lastLogEntry?.id) {
    params.set("last_event_id", lastLogEntry.id);
  }
  
  const url = `${baseURL}/operations/node/task/${taskId.value}/stream?${params.toString()}`;
  const source = new EventSource(url, { withCredentials: false });
  eventSource.value = source;
  streamStatusLabel.value = "连接中…";

  source.addEventListener("open", () => {
    console.log("[SSE] 连接已建立, readyState:", source.readyState);
    streamStatusLabel.value = "已连接";
    
    // 连接建立后再次检查任务状态
    if (taskDetail.value?.task_status && ["success", "partial_success", "failed"].includes(taskDetail.value.task_status)) {
      console.log("[SSE] 连接建立后发现任务已结束，关闭连接");
      isTaskFinished.value = true;
      stopLogStream();
      streamStatusLabel.value = "任务已结束";
      if (logLines.value.length === 0 || logLines.value.every(entry => entry.type === "system")) {
        loadCompleteLogs();
      }
      return;
    }
  });

  // 统一处理标准化的SSE事件
  source.addEventListener("task_log", (event) => {
    console.log("[SSE] 收到task_log事件:", event);
    try {
      handleSSEEvent(event as MessageEvent, "log");
    } catch (error) {
      console.error("[SSE] 处理task_log事件失败:", error, event);
    }
  });

  source.addEventListener("task_status", (event) => {
    console.log("[SSE] 收到task_status事件:", event);
    try {
      handleSSEEvent(event as MessageEvent);
    } catch (error) {
      console.error("[SSE] 处理task_status事件失败:", error, event);
    }
  });

  source.addEventListener("task_info", (event) => {
    console.log("[SSE] 收到task_info事件:", event);
    try {
      handleSSEEvent(event as MessageEvent, "info");
    } catch (error) {
      console.error("[SSE] 处理task_info事件失败:", error, event);
    }
  });

  source.addEventListener("task_error", (event) => {
    console.log("[SSE] 收到task_error事件:", event);
    try {
      handleSSEEvent(event as MessageEvent, "error");
    } catch (error) {
      console.error("[SSE] 处理task_error事件失败:", error, event);
    }
  });

  source.addEventListener("task_end", (event) => {
    console.log("[SSE] 收到task_end事件:", event);
    try {
      handleSSEEvent(event as MessageEvent, "end");
    } catch (error) {
      console.error("[SSE] 处理task_end事件失败:", error, event);
    }
  });

  // 添加通用的 message 事件监听器作为后备（处理没有 event 类型的事件）
  source.onmessage = (event: MessageEvent) => {
    console.log("[SSE] 收到message事件（通用）:", event, "data:", event.data);
    try {
      // 尝试从数据中解析事件类型
      const rawData = event.data;
      if (rawData) {
        try {
          const data = JSON.parse(rawData);
          console.log("[SSE] message事件解析后的数据:", data);
          if (data && data.type) {
            // 根据类型调用对应的处理函数
            const defaultType = data.type === "task_log" ? "log" : "log";
            handleSSEEvent(event, defaultType);
          } else {
            handleSSEEvent(event, "log");
          }
        } catch (e) {
          console.warn("[SSE] message事件数据解析失败:", e, rawData);
        }
      }
    } catch (error) {
      console.error("[SSE] 处理message事件失败:", error, event);
    }
  };

  // 添加通用的 message 事件监听器作为后备（处理没有 event 类型的事件）
  source.onmessage = (event: MessageEvent) => {
    console.log("[SSE] 收到message事件（通用）:", event);
    try {
      // 尝试从数据中解析事件类型
      const rawData = event.data;
      if (rawData) {
        try {
          const data = JSON.parse(rawData);
          if (data && data.type) {
            // 根据类型调用对应的处理函数
            handleSSEEvent(event, data.type === "task_log" ? "log" : "log");
          } else {
            handleSSEEvent(event, "log");
          }
        } catch (e) {
          console.warn("[SSE] message事件数据解析失败:", e, rawData);
        }
      }
    } catch (error) {
      console.error("[SSE] 处理message事件失败:", error, event);
    }
  };

  source.addEventListener("error", (event) => {
    console.log("[SSE] 收到error事件:", {
      event,
      readyState: source.readyState,
      url: source.url,
      taskId: taskId.value,
      taskStatus: taskDetail.value?.task_status,
      isTaskFinished: isTaskFinished.value,
    });
    
    // CONNECTING状态(0)的错误可能是连接建立过程中的正常情况，暂时忽略
    if (source.readyState === EventSource.CONNECTING) {
      console.log("[SSE] 连接建立中，忽略错误");
      return;
    }
    
    if (isTaskFinished.value) {
      console.log("[SSE] 任务已结束，关闭连接");
      stopLogStream();
      streamStatusLabel.value = "任务已结束";
      return;
    }
    
    if (taskDetail.value?.task_status && ["success", "partial_success", "failed"].includes(taskDetail.value.task_status)) {
      isTaskFinished.value = true;
      stopLogStream();
      streamStatusLabel.value = "任务已结束";
      return;
    }
    
    if (source.readyState === EventSource.CLOSED) {
      console.log("[SSE] 连接已关闭");
      if (taskDetail.value?.task_status && ["success", "partial_success", "failed"].includes(taskDetail.value.task_status)) {
        isTaskFinished.value = true;
        streamStatusLabel.value = "任务已结束";
        stopLogStream();
        return;
      }
      // 如果连接关闭但任务还在运行，可能是网络问题
      streamStatusLabel.value = "连接已断开";
    } else if (source.readyState === EventSource.OPEN) {
      console.log("[SSE] 连接已打开，但收到错误事件");
    }
  });
}

function stopLogStream() {
  if (eventSource.value) {
    eventSource.value.close();
    eventSource.value = null;
  }
}

// ==================== 任务详情管理 ====================

/**
 * 检查任务是否正在运行
 */
function isTaskRunning(): boolean {
  return taskDetail.value?.task_status === "running";
}

/**
 * 获取任务详情
 */
async function fetchTaskDetail() {
  if (!taskId.value) return;
  loading.value = true;
  try {
    const response = await NodeAPI.getTaskDetail(taskId.value);
    const previousStatus = taskDetail.value?.task_status;
    taskDetail.value = response.data.data;
    
    const currentStatus = taskDetail.value?.task_status;
    const isRunning = currentStatus === "running";
    const isFinished = currentStatus && ["success", "partial_success", "failed"].includes(currentStatus);
    
    if (isFinished) {
      isTaskFinished.value = true;
      if (previousStatus && previousStatus === "running") {
        stopTaskDetailRefresh();
      }
    } else {
      isTaskFinished.value = false;
    }
    
    // 如果任务不是运行状态，停止定时刷新
    if (!isRunning) {
      stopTaskDetailRefresh();
    }
  } catch (error: any) {
    console.error(error);
  } finally {
    loading.value = false;
  }
}

// ==================== 定时刷新管理 ====================

let taskDetailRefreshTimer: number | null = null;

function stopTaskDetailRefresh() {
  if (taskDetailRefreshTimer) {
    clearInterval(taskDetailRefreshTimer);
    taskDetailRefreshTimer = null;
  }
}

function startTaskDetailRefresh() {
  stopTaskDetailRefresh();
  if (isTaskRunning()) {
    taskDetailRefreshTimer = window.setInterval(async () => {
      if (!isTaskRunning()) {
        stopTaskDetailRefresh();
        return;
      }
      await fetchTaskDetail();
    }, 5000);
  }
}

// ==================== 完整日志加载 ====================

async function loadCompleteLogs() {
  if (!taskId.value) return;
  try {
    const response = await NodeAPI.getTaskLog(taskId.value);
    const content = response.data.data?.content || "";
    if (content) {
      const lines = content.split("\n").filter((line: string) => line.trim().length > 0);
      logLines.value = [];
      lines.forEach((line: string) => {
        const match = line.match(/^\[([^\]]+)\]\s*(.*)$/);
        if (match) {
          const [, timestamp, message] = match;
          appendLogEntry({
            id: `log-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
            timestamp: normalizeTimestamp(timestamp),
            message: message.trim(),
            type: "log",
          });
        } else {
          appendLogEntry({
            id: `log-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
            timestamp: nowTimestamp(),
            message: line.trim(),
            type: "log",
          });
        }
      });
    }
  } catch (error: any) {
    console.error("加载完整日志失败", error);
  }
}

// ==================== 用户操作 ====================

function restartStream() {
  if (taskDetail.value?.task_status && ["success", "partial_success", "failed"].includes(taskDetail.value.task_status)) {
    ElMessage.warning("任务已结束，无法重连");
    return;
  }
  appendSystemLog("正在重新建立连接…");
  startLogStream();
}

function handleBack() {
  router.back();
}

function toggleParamDrawer() {
  paramDrawerVisible.value = true;
}

async function handleDelete() {
  if (!taskId.value) return;
  try {
    await ElMessageBox.confirm("确认删除该构建任务吗？删除后日志文件也将被清理。", "提示", {
      type: "warning",
    });
    await NodeAPI.deleteTask([taskId.value]);
    ElMessage.success("删除任务成功");
    router.back();
  } catch (error: any) {
    if (error !== "cancel") {
      console.error(error);
    }
  }
}

function reloadDetail() {
  fetchTaskDetail();
}

function scrollToTop() {
  if (logContainerRef.value) {
    logContainerRef.value.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  }
}

function scrollToBottom() {
  if (logContainerRef.value) {
    logContainerRef.value.scrollTo({
      top: logContainerRef.value.scrollHeight,
      behavior: 'smooth'
    });
  }
}

// ==================== 生命周期 ====================

watch(
  () => taskId.value,
  async (newId) => {
    if (!newId) return;
    stopTaskDetailRefresh();
    stopLogStream();
    logLines.value = [];
    isTaskFinished.value = false;
    
    await fetchTaskDetail();
    startLogStream();
    startTaskDetailRefresh();
  },
  { immediate: true }
);

// onMounted 不需要，watch 的 immediate: true 已经会在初始化时执行

onBeforeUnmount(() => {
  stopLogStream();
  stopTaskDetailRefresh();
});
</script>

<style scoped>
.page-root {
  padding: 16px;
}

.log-container {
  height: 420px;
  overflow-y: auto;
  overflow-x: hidden;
  background: #111;
  color: #d0f0ff;
  font-family: "JetBrains Mono", "Fira Code", Consolas, monospace;
  padding: 16px;
  border-radius: 8px;
  line-height: 1.6;
  white-space: pre-wrap;
  scroll-behavior: smooth;
}

.log-container::-webkit-scrollbar {
  width: 8px;
}

.log-container::-webkit-scrollbar-track {
  background: #1a1a1a;
  border-radius: 4px;
}

.log-container::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 4px;
}

.log-container::-webkit-scrollbar-thumb:hover {
  background: #777;
}

.log-line {
  margin: 0;
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.log-timestamp {
  color: #67c23a;
  font-weight: 500;
  min-width: 160px;
}

.log-line--info .log-timestamp {
  color: #409eff;
}

.log-line--error .log-timestamp {
  color: #f56c6c;
}

.log-line--end .log-timestamp {
  color: #e6a23c;
}

.log-line--system .log-timestamp {
  color: #909399;
}

.log-message {
  white-space: pre-wrap;
  word-break: break-word;
  flex: 1;
}

.log-empty {
  color: rgba(255, 255, 255, 0.4);
  margin: 0;
}

.error-text {
  color: #d03050;
}

.error-text.is-empty {
  color: var(--el-text-color-secondary);
}

.param-json {
  background: #1f1f1f;
  color: #f4f4f4;
  padding: 16px;
  border-radius: 8px;
  font-family: "JetBrains Mono", "Fira Code", Consolas, monospace;
  font-size: 13px;
  line-height: 1.6;
}
</style>


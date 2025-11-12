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
        <el-descriptions-item label="所属服务">
          {{ taskDetail.service?.name || taskDetail.service_name || "-" }}
        </el-descriptions-item>
        <el-descriptions-item label="节点IP">
          {{ taskDetail.ip || "-" }}
        </el-descriptions-item>
        <el-descriptions-item label="任务状态">
          <el-tag :type="statusTag(taskDetail.task_status)">
            {{ statusLabel(taskDetail.task_status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="任务进度">
          <el-progress
            :percentage="taskDetail.progress || 0"
            :status="progressStatus(taskDetail.task_status)"
            :text-inside="true"
            :stroke-width="18"
            style="width: 180px"
          />
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
            <el-button plain icon="Refresh" @click="restartStream">
              重连
            </el-button>
          </div>
        </div>
      </template>
      <div ref="logContainerRef" class="log-container">
        <p v-for="(line, index) in logLines" :key="index" class="log-line">
          {{ line }}
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
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import NodeAPI, { type TaskDetail } from "@/api/operations/node";
import { Auth } from "@/utils/auth";

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const taskDetail = ref<TaskDetail>();
const logLines = ref<string[]>([]);
const streamStatusLabel = ref("未连接");
const eventSource = ref<EventSource | null>(null);
const paramDrawerVisible = ref(false);
const logContainerRef = ref<HTMLElement>();

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
    case "failed":
      return "danger";
    default:
      return "info";
  }
}

function progressStatus(status?: string) {
  if (status === "success") return "success";
  if (status === "failed") return "exception";
  return undefined;
}

function formatSize(size?: number) {
  if (!size) return "-";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(2)} KB`;
  return `${(size / (1024 * 1024)).toFixed(2)} MB`;
}

async function fetchTaskDetail() {
  if (!taskId.value) return;
  loading.value = true;
  try {
    const response = await NodeAPI.getTaskDetail(taskId.value);
    taskDetail.value = response.data.data;
  } catch (error: any) {
    console.error(error);
  } finally {
    loading.value = false;
  }
}

function appendLog(line: string) {
  logLines.value.push(line);
  nextTick(() => {
    if (logContainerRef.value) {
      logContainerRef.value.scrollTop = logContainerRef.value.scrollHeight;
    }
  });
}

function startLogStream() {
  stopLogStream();
  if (!taskId.value) {
    streamStatusLabel.value = "未连接";
    return;
  }
  const token = Auth.getAccessToken();
  if (!token) {
    streamStatusLabel.value = "未登录";
    return;
  }
  const baseURL = import.meta.env.VITE_APP_BASE_API?.replace(/\/$/, "") || "";
  const url = `${baseURL}/operations/node/task/${taskId.value}/stream?token=${encodeURIComponent(token)}`;
  const source = new EventSource(url, { withCredentials: false });
  eventSource.value = source;
  streamStatusLabel.value = "连接中…";

  source.addEventListener("open", () => {
    streamStatusLabel.value = "已连接";
  });

  source.addEventListener("log", (event) => {
    appendLog((event as MessageEvent).data);
  });

  source.addEventListener("info", (event) => {
    appendLog((event as MessageEvent).data);
  });

  source.addEventListener("error", (event) => {
    console.error("日志流异常", event);
    streamStatusLabel.value = "连接异常";
    if (source.readyState === EventSource.CLOSED) {
      appendLog("[系统] 日志流已关闭");
    }
  });

  source.addEventListener("end", (event) => {
    appendLog((event as MessageEvent).data);
    streamStatusLabel.value = "已结束";
    stopLogStream();
  });
}

function stopLogStream() {
  if (eventSource.value) {
    eventSource.value.close();
    eventSource.value = null;
  }
}

function restartStream() {
  logLines.value.push("[系统] 正在重新建立连接…");
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

watch(
  () => taskId.value,
  (newId) => {
    if (!newId) return;
    logLines.value = [];
    fetchTaskDetail();
    startLogStream();
  },
  { immediate: true }
);

onMounted(() => {
  if (taskId.value) {
    fetchTaskDetail();
    startLogStream();
  }
});

onBeforeUnmount(() => {
  stopLogStream();
});
</script>

<style scoped>
.page-root {
  padding: 16px;
}

.log-container {
  max-height: 420px;
  overflow-y: auto;
  background: #111;
  color: #d0f0ff;
  font-family: "JetBrains Mono", "Fira Code", Consolas, monospace;
  padding: 16px;
  border-radius: 8px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.log-line {
  margin: 0;
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


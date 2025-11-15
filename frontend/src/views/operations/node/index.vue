<!-- 服务节点管理 -->
<template>
  <div class="app-container">
    <div class="flex gap-4">
      <!-- 左侧表格区域 -->
      <div class="flex-1">
        <!-- 搜索区域 -->
        <div class="search-container">
          <el-form
            ref="queryFormRef"
            :model="queryFormData"
            :inline="true"
            label-suffix=":"
            @submit.prevent="handleQuery"
          >
            <el-form-item
              prop="name"
              label="服务名称"
            >
              <el-input
                v-model="queryFormData.name"
                placeholder="请输入服务名称"
                clearable
              />
            </el-form-item>
            <el-form-item
              prop="status"
              label="状态"
            >
              <el-select
                v-model="queryFormData.status"
                placeholder="请选择状态"
                style="width: 167.5px"
                clearable
              >
                <el-option
                  value="true"
                  label="启用"
                />
                <el-option
                  value="false"
                  label="停用"
                />
              </el-select>
            </el-form-item>
            <el-form-item
              prop="project"
              label="运维管理项目"
            >
              <el-select
                v-model="queryFormData.project"
                placeholder="请选择运维管理项目"
                style="width: 167.5px"
                clearable
              >
                <el-option
                  v-for="item in projectOptions"
                  :key="item.dict_value"
                  :label="item.dict_label"
                  :value="item.dict_value"
                />
              </el-select>
            </el-form-item>
            <el-form-item
              prop="module_group"
              label="模块分组"
            >
              <el-select
                v-model="queryFormData.module_group"
                placeholder="请选择模块分组"
                style="width: 167.5px"
                clearable
              >
                <el-option
                  v-for="item in moduleGroupOptions"
                  :key="item.dict_value"
                  :label="item.dict_label"
                  :value="item.dict_value"
                />
              </el-select>
            </el-form-item>
            <el-form-item class="search-buttons">
              <el-button
                v-hasPerm="['operations:node:query']"
                type="primary"
                icon="search"
                native-type="submit"
              >查询</el-button>
              <el-button
                v-hasPerm="['operations:node:query']"
                icon="refresh"
                @click="handleResetQuery"
              >重置</el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- 内容区域 -->
        <el-card class="data-table">
          <template #header>
            <div class="card-header">
              <span>
                <el-tooltip content="服务节点管理维护系统的服务模块和节点信息。">
                  <QuestionFilled class="w-4 h-4 mx-1" />
                </el-tooltip>
                服务节点列表
              </span>
            </div>
          </template>

          <!-- 功能区域 -->
          <div class="data-table__toolbar">
            <div class="data-table__toolbar--left">
              <el-row :gutter="10">
                <el-col :span="1.5">
                  <el-button
                    v-hasPerm="['operations:node:deploy']"
                    type="warning"
                    icon="Upload"
                    :disabled="selectNodeIds.length === 0"
                    @click="handleDeploy"
                  >部署</el-button>
                </el-col>
                <el-col :span="1.5">
                  <el-button
                    v-hasPerm="['operations:node:restart']"
                    type="info"
                    icon="RefreshRight"
                    :disabled="selectNodeIds.length === 0"
                    @click="handleRestart"
                  >重启</el-button>
                </el-col>
              </el-row>
            </div>
            <div class="data-table__toolbar--right">
              <el-row :gutter="10">
                <el-col :span="1.5">
                  <el-tooltip content="刷新">
                    <el-button
                      v-hasPerm="['operations:node:refresh']"
                      type="primary"
                      icon="refresh"
                      circle
                      @click="handleRefresh"
                    />
                  </el-tooltip>
                </el-col>
              </el-row>
            </div>
          </div>

          <!-- 表格区域：树形表格 -->
          <el-table
            ref="dataTableRef"
            v-loading="loading"
            row-key="id"
            :data="pageTableData"
            :tree-props="{children: 'nodes', hasChildren: 'hasChildren'}"
            class="data-table__content"
            height="600"
            border
            stripe
          >
            <template #empty>
              <el-empty
                :image-size="80"
                description="暂无数据"
              />
            </template>
            <!-- 自定义多选列：使用 checkbox 实现级联选择/半选状态 -->
            <el-table-column
              label="选择"
              width="80"
              align="center"
            >
              <template #default="{ row }">
                <el-checkbox
                  :model-value="checkedMap[row.id] === true"
                  :indeterminate="indeterminateMap[row.id] === true"
                  @change="(val) => onCheckboxChange(row, !!val)"
                />
              </template>
            </el-table-column>
            <el-table-column
              type="index"
              fixed
              label="序号"
              min-width="60"
            />
            <el-table-column
              label="项目"
              prop="project"
              min-width="120"
            >
              <template #default="scope">
                <span v-if="scope.row.nodes">{{ scope.row.project || '-' }}</span>
                <span v-else>{{ scope.row.project || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column
              label="模块分组"
              prop="module_group"
              min-width="120"
            >
              <template #default="scope">
                <span v-if="scope.row.nodes">{{ scope.row.module_group || '-' }}</span>
                <span v-else>{{ scope.row.module_group || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column
              label="名称/IP"
              prop="name"
              min-width="180"
            >
              <template #default="scope">
                <span v-if="scope.row.nodes">{{ scope.row.name }}</span>
                <span v-else>{{ scope.row.ip }}</span>
              </template>
            </el-table-column>
            <el-table-column
              label="端口"
              prop="port"
              min-width="80"
            >
              <template #default="scope">
                <span v-if="!scope.row.nodes">{{ scope.row.port || '-' }}</span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column
              label="状态"
              prop="status"
              min-width="80"
            >
              <template #default="scope">
                <el-tag :type="scope.row.status === true ? 'success' : 'danger'">
                  {{ scope.row.status === true ? "启用" : "停用" }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              label="描述"
              prop="description"
              min-width="150"
              show-overflow-tooltip
            />
            <el-table-column
              label="创建时间"
              prop="created_at"
              min-width="180"
            />
          </el-table>
        </el-card>
      </div>

      <!-- 右侧任务进度栏 -->
      <div class="w-80">
        <el-card>
          <template #header>
            <div class="card-header flex justify-between items-center">
              <span>任务进度</span>
              <el-button
                text
                type="primary"
                icon="refresh"
                @click="loadRecentTasks"
              >刷新</el-button>
            </div>
          </template>
          <div class="task-list">
            <div
              v-for="task in taskList"
              :key="task.id"
              class="task-item"
              @click="handleOpenTaskDetailFromList(task.id)"
            >
              <div class="task-header">
                <div>
                  <span class="task-ip">任务 #{{ task.id }}</span>
                </div>
                <el-tag
                  size="small"
                  :type="task.task_type === 'deploy' ? 'success' : 'warning'"
                >
                  {{ task.task_type === 'deploy' ? '部署' : '重启' }}
                </el-tag>
              </div>
              <div class="task-progress">
                <el-progress
                  :percentage="task.progress || 0"
                  :status="progressStatus(task.task_status)"
                  :text-inside="true"
                  :stroke-width="14"
                />
              </div>
              <div class="task-info">
                <span class="task-time">{{ task.created_at || '-' }}</span>
                <div class="task-status">
                  <el-icon
                    v-if="task.task_status === 'success'"
                    class="status-icon success"
                  >
                    <CircleCheck />
                  </el-icon>
                  <el-icon
                    v-else-if="task.task_status === 'failed'"
                    class="status-icon failed"
                  >
                    <CircleClose />
                  </el-icon>
                  <el-icon
                    v-else
                    class="status-icon running"
                  >
                    <Loading />
                  </el-icon>
                  <span class="status-text">{{ getTaskStatusText(task.task_status || 'running') }}</span>
                </div>
              </div>
              <div
                v-if="task.error_message"
                class="task-error"
              >{{ task.error_message }}</div>
            </div>
            <div
              v-if="taskList.length === 0"
              class="empty-tasks"
            >
              <el-empty
                :image-size="60"
                description="暂无任务"
              />
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 服务/节点相关弹窗已下线 -->
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: "OperationsNode",
  inheritAttrs: false,
});

import NodeAPI, { ServiceTable, TaskTable, ServiceQueryParam } from "@/api/operations/node";
import { useRouter } from "vue-router";
import { QuestionFilled, CircleCheck, CircleClose, Loading } from "@element-plus/icons-vue";
import DictAPI from "@/api/system/dict";
import { ElMessage, ElMessageBox } from "element-plus";
import { onBeforeUnmount } from "vue";

const queryFormRef = ref();
const dataTableRef = ref();
const total = ref(0);
const selectIds = ref<number[]>([]);
const selectNodeIds = ref<number[]>([]);
const loading = ref(false);

// 保存每个节点的选中 / 半选状态（使用 ref 包装对象，减少响应式开销）
const checkedMap = ref<Record<number, boolean>>({});
const indeterminateMap = ref<Record<number, boolean>>({});
// 父节点映射：nodeId -> parentId（不需要响应式）
const parentMap: Record<number, number | null> = {};
// 节点缓存：nodeId -> node（避免重复查找，不需要响应式）
const nodeMap: Record<number, any> = {};
// 子节点映射：nodeId -> childIds（不需要响应式）
const childrenMap: Record<number, number[]> = {};

// 分页表单
const pageTableData = ref<ServiceTable[]>([]);

// 查询参数
const queryFormData = reactive<ServiceQueryParam>({
  name: undefined,
  status: undefined,
  project: undefined,
  module_group: undefined,
});

// 任务列表
const taskList = ref<TaskTable[]>([]);
const router = useRouter();

// 字典选项
const projectOptions = ref<any[]>([]);
const moduleGroupOptions = ref<any[]>([]);
const idcOptions = ref<any[]>([]);
const tagsOptions = ref<any[]>([]);

// 构建映射关系和初始化状态（一次性建立所有缓存）
function buildMaps(list: any[], parentId: number | null = null) {
  for (const node of list) {
    // 缓存节点
    nodeMap[node.id] = node;
    // 设置父节点
    parentMap[node.id] = parentId;
    // 初始化选中状态
    checkedMap.value[node.id] = false;
    indeterminateMap.value[node.id] = false;

    // 缓存子节点ID列表
    if (node.nodes && node.nodes.length) {
      childrenMap[node.id] = node.nodes.map((c: any) => c.id);
      buildMaps(node.nodes, node.id);
    } else {
      childrenMap[node.id] = [];
    }
  }
}

// 获取所有后代 id（包含自己）- 使用迭代避免递归
function collectDescendantIds(nodeId: number): number[] {
  const result: number[] = [];
  const stack = [nodeId];

  while (stack.length > 0) {
    const currentId = stack.pop()!;
    result.push(currentId);

    const childIds = childrenMap[currentId] || [];
    // 将子节点加入栈中
    for (let i = childIds.length - 1; i >= 0; i--) {
      stack.push(childIds[i]);
    }
  }

  return result;
}

// 当 checkbox 改变时：级联到子节点，并回溯更新父节点的状态
function onCheckboxChange(row: any, checked: boolean) {
  const nodeId = row.id;
  if (!nodeMap[nodeId]) return;

  // 1) 级联到所有后代（使用迭代，避免递归）
  const descendantIds = collectDescendantIds(nodeId);
  for (const id of descendantIds) {
    checkedMap.value[id] = checked;
    indeterminateMap.value[id] = false;
  }

  // 2) 回溯更新父节点：查看父的子节点是否全部选中/部分/未选
  let parentId = parentMap[nodeId];
  while (parentId != null) {
    const childIds = childrenMap[parentId] || [];
    const allChecked = childIds.every((id) => checkedMap.value[id] === true);
    const noneChecked = childIds.every(
      (id) => checkedMap.value[id] === false && indeterminateMap.value[id] === false
    );

    if (allChecked) {
      checkedMap.value[parentId] = true;
      indeterminateMap.value[parentId] = false;
    } else if (noneChecked) {
      checkedMap.value[parentId] = false;
      indeterminateMap.value[parentId] = false;
    } else {
      checkedMap.value[parentId] = false;
      indeterminateMap.value[parentId] = true;
    }

    parentId = parentMap[parentId];
  }

  // 3) 更新选中状态
  updateSelectionState();
}

// 更新选中状态（提取选中的节点ID）
function updateSelectionState() {
  // 获取所有选中的 id
  const selectedIds = Object.keys(checkedMap.value)
    .filter((id) => checkedMap.value[Number(id)] === true)
    .map((id) => Number(id));

  selectIds.value = selectedIds;

  // 提取所有选中的节点ID（排除服务模块，只取叶子节点）
  const nodeIdSet = new Set<number>();
  for (const id of selectedIds) {
    const node = nodeMap[id];
    // 如果没有 nodes 属性或子节点为空，说明是叶子节点
    if (node && (!node.nodes || node.nodes.length === 0)) {
      nodeIdSet.add(id);
    }
  }
  selectNodeIds.value = Array.from(nodeIdSet);
}

// 加载服务树数据
async function loadingData() {
  loading.value = true;
  try {
    const response = await NodeAPI.getServiceTree(queryFormData);
    // 展示所有服务模块，但只显示有service_id的节点（过滤掉没有关联服务模块的节点）
    const processedData = (response.data.data || []).map((service: any) => {
      // 过滤掉没有service_id的节点（这些节点不应该单独显示）
      if (service.nodes) {
        service.nodes = service.nodes.filter((node: any) => node.service_id);
      }
      return service;
    });
    pageTableData.value = processedData;

    // 清空旧的缓存
    Object.keys(nodeMap).forEach((key) => delete nodeMap[Number(key)]);
    Object.keys(parentMap).forEach((key) => delete parentMap[Number(key)]);
    Object.keys(childrenMap).forEach((key) => delete childrenMap[Number(key)]);
    Object.keys(checkedMap.value).forEach((key) => delete checkedMap.value[Number(key)]);
    Object.keys(indeterminateMap.value).forEach(
      (key) => delete indeterminateMap.value[Number(key)]
    );
    selectIds.value = [];
    selectNodeIds.value = [];

    // 构建所有映射关系
    buildMaps(pageTableData.value);
  } catch (error: any) {
    console.error(error);
  } finally {
    loading.value = false;
  }
}

// 加载字典选项
async function loadDictOptions() {
  try {
    const [projectRes, moduleGroupRes, idcRes, tagsRes] = await Promise.all([
      DictAPI.getInitDict("operations_project"),
      DictAPI.getInitDict("operations_module_group"),
      DictAPI.getInitDict("operations_idc"),
      DictAPI.getInitDict("operations_server_tags"),
    ]);
    projectOptions.value = projectRes.data.data || [];
    moduleGroupOptions.value = moduleGroupRes.data.data || [];
    idcOptions.value = idcRes.data.data || [];
    tagsOptions.value = tagsRes.data.data || [];
  } catch (error: any) {
    console.error(error);
  }
}

// 定时器ID
let recentTasksTimer: number | null = null;

/**
 * 停止定时刷新任务列表
 */
function stopRecentTasksRefresh() {
  if (recentTasksTimer !== null) {
    clearInterval(recentTasksTimer);
    recentTasksTimer = null;
  }
}

/**
 * 检查是否有正在运行的任务
 */
function hasRunningTasks(): boolean {
  return taskList.value.some((task) => task.task_status === "running");
}

// 加载最近任务
async function loadRecentTasks() {
  try {
    const response = await NodeAPI.getRecentTasks(20);
    taskList.value = response.data.data || [];

    // 检查是否有正在运行的任务，如果没有则停止定时刷新
    if (!hasRunningTasks()) {
      stopRecentTasksRefresh();
    }
  } catch (error: any) {
    console.error(error);
  }
}

// 查询
async function handleQuery() {
  loadingData();
}

// 重置查询
async function handleResetQuery() {
  queryFormRef.value.resetFields();
  loadingData();
}

// 刷新
async function handleRefresh() {
  await loadingData();
  await loadRecentTasks();
}

const nodeActionConfig: Record<
  "deploy" | "restart",
  { confirmMessage: string; api: (ids: number[]) => Promise<any> }
> = {
  deploy: {
    confirmMessage: "确认部署选中的节点?",
    api: (ids) => NodeAPI.deploy(ids),
  },
  restart: {
    confirmMessage: "确认重启选中的节点?",
    api: (ids) => NodeAPI.restart(ids),
  },
};

function scheduleTaskPolling() {
  setTimeout(async () => {
    await loadRecentTasks();
    if (hasRunningTasks() && recentTasksTimer === null) {
      recentTasksTimer = window.setInterval(() => {
        loadRecentTasks();
      }, 5000);
    }
  }, 2000);
}

function handleNodeOperation(type: keyof typeof nodeActionConfig) {
  if (selectNodeIds.value.length === 0) {
    ElMessage.warning("请至少选择一个节点");
    return;
  }
  const config = nodeActionConfig[type];
  ElMessageBox.confirm(config.confirmMessage, "提示", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "info",
  })
    .then(async () => {
      try {
        loading.value = true;
        await config.api(selectNodeIds.value);
        // 响应拦截器已经自动显示成功消息，这里不需要重复显示
        handleRefresh();
        // 刷新任务列表，并启动定时刷新（如果有正在运行的任务）
        scheduleTaskPolling();
      } catch (error: any) {
        console.error(error);
      } finally {
        loading.value = false;
      }
    })
    .catch(() => {
      ElMessageBox.close();
    });
}

// 部署
async function handleDeploy() {
  handleNodeOperation("deploy");
}

// 重启
async function handleRestart() {
  handleNodeOperation("restart");
}

// 获取任务状态文本
function getTaskStatusText(status: string) {
  const statusMap: Record<string, string> = {
    running: "执行中",
    success: "完成",
    failed: "失败",
  };
  return statusMap[status] || status;
}

function progressStatus(status?: string) {
  if (status === "success") return "success";
  if (status === "failed") return "exception";
  return undefined;
}

function handleOpenTaskDetailFromList(taskId?: number) {
  if (!taskId) return;
  router.push({
    path: `/operations/task/detail/${taskId}`,
  });
}

onMounted(() => {
  loadDictOptions();
  loadingData();
  loadRecentTasks();
  // 如果有正在运行的任务，启动定时刷新
  if (hasRunningTasks()) {
    recentTasksTimer = window.setInterval(() => {
      loadRecentTasks();
    }, 5000);
  }
});

onBeforeUnmount(() => {
  // 清除定时器，防止页面关闭后继续请求
  stopRecentTasksRefresh();
});
</script>

<style lang="scss" scoped>
.task-list {
  max-height: 600px;
  overflow-y: auto;
}

.task-item {
  padding: 12px;
  margin-bottom: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  background: #f9fafb;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    border-color: #409eff;
    background: #f0f9ff;
  }
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  gap: 8px;
}

.task-ip {
  font-weight: bold;
  color: #303133;
}

.task-service {
  font-size: 12px;
  margin-left: 8px;
  color: #909399;
}

.task-progress {
  margin-bottom: 6px;
}

.task-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.task-time {
  font-size: 12px;
  color: #909399;
}

.task-status {
  display: flex;
  align-items: center;
  gap: 4px;
}

.status-icon {
  font-size: 16px;

  &.success {
    color: #67c23a;
  }

  &.failed {
    color: #f56c6c;
  }

  &.running {
    color: #909399;
    animation: rotate 1s linear infinite;
  }
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.status-text {
  font-size: 12px;
  color: #606266;
}

.task-error {
  margin-top: 4px;
  padding: 4px 8px;
  background: #fef0f0;
  color: #f56c6c;
  border-radius: 2px;
  font-size: 12px;
}

.empty-tasks {
  text-align: center;
  padding: 40px 0;
}
</style>



<!-- 服务节点管理 -->
<template>
  <div class="app-container">
    <div class="flex gap-4">
      <!-- 左侧表格区域 -->
      <div class="flex-1">
        <!-- 搜索区域 -->
        <div class="search-container">
          <el-form ref="queryFormRef" :model="queryFormData" :inline="true" label-suffix=":" @submit.prevent="handleQuery">
            <el-form-item prop="name" label="服务名称">
              <el-input v-model="queryFormData.name" placeholder="请输入服务名称" clearable />
            </el-form-item>
            <el-form-item prop="status" label="状态">
              <el-select v-model="queryFormData.status" placeholder="请选择状态" style="width: 167.5px" clearable>
                <el-option value="true" label="启用" />
                <el-option value="false" label="停用" />
              </el-select>
            </el-form-item>
            <el-form-item prop="project" label="运维管理项目">
              <el-select v-model="queryFormData.project" placeholder="请选择运维管理项目" style="width: 167.5px" clearable>
                <el-option v-for="item in projectOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value" />
              </el-select>
            </el-form-item>
            <el-form-item prop="module_group" label="模块分组">
              <el-select v-model="queryFormData.module_group" placeholder="请选择模块分组" style="width: 167.5px" clearable>
                <el-option v-for="item in moduleGroupOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value" />
              </el-select>
            </el-form-item>
            <el-form-item class="search-buttons">
              <el-button v-hasPerm="['operations:node:query']" type="primary" icon="search" native-type="submit">查询</el-button>
              <el-button v-hasPerm="['operations:node:query']" icon="refresh" @click="handleResetQuery">重置</el-button>
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
                  <el-button v-hasPerm="['operations:node:deploy']" type="warning" icon="Upload" :disabled="selectNodeIds.length === 0" @click="handleDeploy">部署</el-button>
                </el-col>
                <el-col :span="1.5">
                  <el-button v-hasPerm="['operations:node:restart']" type="info" icon="RefreshRight" :disabled="selectNodeIds.length === 0" @click="handleRestart">重启</el-button>
                </el-col>
              </el-row>
            </div>
            <div class="data-table__toolbar--right">
              <el-row :gutter="10">
                <el-col :span="1.5">
                  <el-tooltip content="刷新">
                    <el-button v-hasPerm="['operations:node:refresh']" type="primary" icon="refresh" circle @click="handleRefresh" />
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
              <el-empty :image-size="80" description="暂无数据" />
            </template>
            <!-- 自定义多选列：使用 checkbox 实现级联选择/半选状态 -->
            <el-table-column label="选择" width="80" align="center">
              <template #default="{ row }">
                <el-checkbox
                  :model-value="checkedMap[row.id] === true"
                  :indeterminate="indeterminateMap[row.id] === true"
                  @change="(val) => onCheckboxChange(row, !!val)"
                />
              </template>
            </el-table-column>
            <el-table-column type="index" fixed label="序号" min-width="60" />
            <el-table-column label="项目" prop="project" min-width="120">
              <template #default="scope">
                <span v-if="scope.row.nodes">{{ scope.row.project || '-' }}</span>
                <span v-else>{{ scope.row.project || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="模块分组" prop="module_group" min-width="120">
              <template #default="scope">
                <span v-if="scope.row.nodes">{{ scope.row.module_group || '-' }}</span>
                <span v-else>{{ scope.row.module_group || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="名称/IP" prop="name" min-width="180">
              <template #default="scope">
                <span v-if="scope.row.nodes">{{ scope.row.name }}</span>
                <span v-else>{{ scope.row.ip }}</span>
              </template>
            </el-table-column>
            <el-table-column label="端口" prop="port" min-width="80">
              <template #default="scope">
                <span v-if="!scope.row.nodes">{{ scope.row.port || '-' }}</span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" prop="status" min-width="80">
              <template #default="scope">
                <el-tag :type="scope.row.status === true ? 'success' : 'danger'">
                  {{ scope.row.status === true ? "启用" : "停用" }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="描述" prop="description" min-width="150" show-overflow-tooltip />
            <el-table-column label="创建时间" prop="created_at" min-width="180" />
          </el-table>
        </el-card>
      </div>

      <!-- 右侧任务进度栏 -->
      <div class="w-80">
        <el-card>
          <template #header>
            <div class="card-header flex justify-between items-center">
              <span>任务进度</span>
              <el-button text type="primary" icon="refresh" @click="loadRecentTasks">刷新</el-button>
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
                <el-tag size="small" :type="task.task_type === 'deploy' ? 'success' : 'warning'">
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
                  <el-icon v-if="task.task_status === 'success'" class="status-icon success"><CircleCheck /></el-icon>
                  <el-icon v-else-if="task.task_status === 'failed'" class="status-icon failed"><CircleClose /></el-icon>
                  <el-icon v-else class="status-icon running"><Loading /></el-icon>
                  <span class="status-text">{{ getTaskStatusText(task.task_status || 'running') }}</span>
                </div>
              </div>
              <div v-if="task.error_message" class="task-error">{{ task.error_message }}</div>
            </div>
            <div v-if="taskList.length === 0" class="empty-tasks">
              <el-empty :image-size="60" description="暂无任务" />
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 服务模块弹窗 -->
    <el-dialog v-model="serviceDialogVisible.visible" :title="serviceDialogVisible.title" @close="handleCloseServiceDialog">
      <template v-if="serviceDialogVisible.type === 'detail'">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="服务名称" :span="2">{{ serviceDetailFormData.name }}</el-descriptions-item>
          <el-descriptions-item label="项目">{{ serviceDetailFormData.project || '-' }}</el-descriptions-item>
          <el-descriptions-item label="模块分组">{{ serviceDetailFormData.module_group || '-' }}</el-descriptions-item>
          <el-descriptions-item label="服务编码">{{ serviceDetailFormData.code || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag v-if="serviceDetailFormData.status" type="success">启用</el-tag>
            <el-tag v-else type="danger">停用</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间" :span="2">{{ serviceDetailFormData.created_at }}</el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">{{ serviceDetailFormData.description || '-' }}</el-descriptions-item>
        </el-descriptions>
      </template>
      <template v-else>
        <el-form ref="serviceFormRef" :model="serviceFormData" :rules="serviceRules" label-suffix=":" label-width="100px">
          <el-form-item label="服务名称" prop="name">
            <el-input v-model="serviceFormData.name" placeholder="请输入服务名称" :maxlength="100" />
          </el-form-item>
          <el-form-item label="服务编码" prop="code">
            <el-input v-model="serviceFormData.code" placeholder="请输入服务编码" :maxlength="50" />
          </el-form-item>
          <el-form-item label="运维管理项目" prop="project">
            <el-select v-model="serviceFormData.project" placeholder="请选择运维管理项目" clearable style="width: 100%">
              <el-option v-for="item in projectOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value" />
            </el-select>
          </el-form-item>
          <el-form-item label="模块分组" prop="module_group">
            <el-select v-model="serviceFormData.module_group" placeholder="请选择模块分组" clearable style="width: 100%">
              <el-option v-for="item in moduleGroupOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态" prop="status">
            <el-switch
              v-model="serviceFormData.status"
              inline-prompt
              active-text="启用"
              inactive-text="停用"
              :active-value="true"
              :inactive-value="false"
            />
          </el-form-item>
          <el-form-item label="描述" prop="description">
            <el-input v-model="serviceFormData.description" :rows="4" type="textarea" placeholder="请输入描述" :maxlength="255" show-word-limit />
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="handleCloseServiceDialog">取消</el-button>
          <el-button v-if="serviceDialogVisible.type !== 'detail'" type="primary" @click="handleSubmitService">确定</el-button>
          <el-button v-else type="primary" @click="handleCloseServiceDialog">确定</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 节点弹窗 -->
    <el-dialog v-model="nodeDialogVisible.visible" :title="nodeDialogVisible.title" @close="handleCloseNodeDialog">
      <template v-if="nodeDialogVisible.type === 'detail'">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="服务名称" :span="2">{{ nodeDetailFormData.service_name }}</el-descriptions-item>
          <el-descriptions-item label="节点IP">{{ nodeDetailFormData.ip }}</el-descriptions-item>
          <el-descriptions-item label="端口">{{ nodeDetailFormData.port || '-' }}</el-descriptions-item>
          <el-descriptions-item label="运维管理项目">{{ nodeDetailFormData.project || '-' }}</el-descriptions-item>
          <el-descriptions-item label="机房">{{ nodeDetailFormData.idc || '-' }}</el-descriptions-item>
          <el-descriptions-item label="服务器标签">{{ nodeDetailFormData.tags || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag v-if="nodeDetailFormData.status" type="success">启用</el-tag>
            <el-tag v-else type="danger">停用</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间" :span="2">{{ nodeDetailFormData.created_at }}</el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">{{ nodeDetailFormData.description || '-' }}</el-descriptions-item>
        </el-descriptions>
      </template>
      <template v-else>
        <el-form ref="nodeFormRef" :model="nodeFormData" :rules="nodeRules" label-suffix=":" label-width="100px">
          <el-form-item label="服务模块" prop="service_id">
            <el-select v-model="nodeFormData.service_id" placeholder="请选择服务模块" style="width: 100%">
              <el-option v-for="service in serviceOptions" :key="service.id" :label="service.name || ''" :value="service.id || 0" />
            </el-select>
          </el-form-item>
          <el-form-item label="节点IP" prop="ip">
            <el-input v-model="nodeFormData.ip" placeholder="请输入节点IP地址" :maxlength="50" />
          </el-form-item>
          <el-form-item label="端口" prop="port">
            <el-input-number v-model="nodeFormData.port" controls-position="right" :min="1" :max="65535" :value="nodeFormData.port || 22" style="width: 100%" />
          </el-form-item>
          <el-form-item label="运维管理项目" prop="project">
            <el-select v-model="nodeFormData.project" placeholder="请选择运维管理项目" clearable style="width: 100%">
              <el-option v-for="item in projectOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value" />
            </el-select>
          </el-form-item>
          <el-form-item label="机房" prop="idc">
            <el-select v-model="nodeFormData.idc" placeholder="请选择机房" clearable style="width: 100%">
              <el-option v-for="item in idcOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value" />
            </el-select>
          </el-form-item>
          <el-form-item label="服务器标签" prop="tags">
            <el-select v-model="nodeFormData.tags" placeholder="请选择服务器标签" clearable style="width: 100%">
              <el-option v-for="item in tagsOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态" prop="status">
            <el-switch
              v-model="nodeFormData.status"
              inline-prompt
              active-text="启用"
              inactive-text="停用"
              :active-value="true"
              :inactive-value="false"
            />
          </el-form-item>
          <el-form-item label="描述" prop="description">
            <el-input v-model="nodeFormData.description" :rows="4" type="textarea" placeholder="请输入描述" :maxlength="255" show-word-limit />
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="handleCloseNodeDialog">取消</el-button>
          <el-button v-if="nodeDialogVisible.type !== 'detail'" type="primary" @click="handleSubmitNode">确定</el-button>
          <el-button v-else type="primary" @click="handleCloseNodeDialog">确定</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: "OperationsNode",
  inheritAttrs: false,
});

import NodeAPI, { ServiceTable, NodeTable, TaskTable, ServiceForm, NodeForm, ServiceQueryParam } from "@/api/operations/node";
import { useRouter } from "vue-router";
import { QuestionFilled, CircleCheck, CircleClose, Loading } from "@element-plus/icons-vue";
import DictAPI from "@/api/system/dict";
import { onBeforeUnmount } from "vue";

const queryFormRef = ref();
const serviceFormRef = ref();
const nodeFormRef = ref();
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

// 服务模块表单
const serviceFormData = reactive<ServiceForm>({
  id: undefined,
  name: '',
  code: '',
  status: true,
  description: undefined,
});

// 节点表单
const nodeFormData = reactive<NodeForm>({
  id: undefined,
  service_id: undefined,
  ip: '',
  port: 22,
  status: true,
  description: undefined,
  project: undefined,
  idc: undefined,
  tags: undefined,
});

// 服务模块弹窗状态
const serviceDialogVisible = reactive({
  title: "",
  visible: false,
  type: 'create' as 'create' | 'update' | 'detail',
});

// 节点弹窗状态
const nodeDialogVisible = reactive({
  title: "",
  visible: false,
  type: 'create' as 'create' | 'update' | 'detail',
});

// 详情表单
const serviceDetailFormData = ref<ServiceTable>({});
const nodeDetailFormData = ref<NodeTable>({});

// 服务模块选项（用于节点表单）
const serviceOptions = ref<ServiceTable[]>([]);

// 任务列表
const taskList = ref<TaskTable[]>([]);
const router = useRouter();

// 字典选项
const projectOptions = ref<any[]>([]);
const moduleGroupOptions = ref<any[]>([]);
const idcOptions = ref<any[]>([]);
const tagsOptions = ref<any[]>([]);

// 表单验证规则
const serviceRules = reactive({
  name: [{ required: true, message: "请输入服务名称", trigger: "blur" }],
});

const nodeRules = reactive({
  service_id: [{ required: true, message: "请选择服务模块", trigger: "change" }],
  ip: [
    { required: true, message: "请输入节点IP地址", trigger: "blur" },
    { pattern: /^(\d{1,3}\.){3}\d{1,3}$/, message: "IP地址格式不正确", trigger: "blur" },
  ],
});

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
    checkedMap[id] = checked;
    indeterminateMap[id] = false;
  }

  // 2) 回溯更新父节点：查看父的子节点是否全部选中/部分/未选
  let parentId = parentMap[nodeId];
  while (parentId != null) {
    const childIds = childrenMap[parentId] || [];
    const allChecked = childIds.every((id) => checkedMap[id] === true);
    const noneChecked = childIds.every((id) => checkedMap[id] === false && indeterminateMap[id] === false);

    if (allChecked) {
      checkedMap[parentId] = true;
      indeterminateMap[parentId] = false;
    } else if (noneChecked) {
      checkedMap[parentId] = false;
      indeterminateMap[parentId] = false;
    } else {
      checkedMap[parentId] = false;
      indeterminateMap[parentId] = true;
    }

    parentId = parentMap[parentId];
  }

  // 3) 更新选中状态
  updateSelectionState();
}

// 更新选中状态（提取选中的节点ID）
function updateSelectionState() {
  // 获取所有选中的 id
  const selectedIds = Object.keys(checkedMap)
    .filter((id) => checkedMap[Number(id)] === true)
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
    Object.keys(nodeMap).forEach(key => delete nodeMap[Number(key)]);
    Object.keys(parentMap).forEach(key => delete parentMap[Number(key)]);
    Object.keys(childrenMap).forEach(key => delete childrenMap[Number(key)]);
    Object.keys(checkedMap).forEach(key => delete checkedMap[Number(key)]);
    Object.keys(indeterminateMap).forEach(key => delete indeterminateMap[Number(key)]);
    
    // 构建所有映射关系
    buildMaps(pageTableData.value);
    
    // 同时加载服务选项
    await loadServiceOptions();
  } catch (error: any) {
    console.error(error);
  } finally {
    loading.value = false;
  }
}

// 加载服务选项
async function loadServiceOptions() {
  try {
    const response = await NodeAPI.getServiceTree({ status: true });
    serviceOptions.value = response.data.data || [];
  } catch (error: any) {
    console.error(error);
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
  return taskList.value.some(task => task.task_status === "running");
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


// 打开服务模块弹窗
async function handleOpenServiceDialog(type: 'create' | 'update' | 'detail', id?: number) {
  serviceDialogVisible.type = type;
  if (id) {
    const response = await NodeAPI.getServiceDetail(id);
    if (type === 'detail') {
      serviceDialogVisible.title = "服务模块详情";
      Object.assign(serviceDetailFormData.value, response.data.data);
    } else if (type === 'update') {
      serviceDialogVisible.title = "修改服务模块";
      Object.assign(serviceFormData, response.data.data);
    }
  } else {
    serviceDialogVisible.title = "新增服务模块";
    serviceFormData.id = undefined;
    serviceFormData.name = '';
    serviceFormData.code = '';
    serviceFormData.status = true;
    serviceFormData.description = undefined;
    serviceFormData.project = undefined;
    serviceFormData.module_group = undefined;
  }
  serviceDialogVisible.visible = true;
}

// 关闭服务模块弹窗
async function handleCloseServiceDialog() {
  serviceDialogVisible.visible = false;
  if (serviceFormRef.value) {
    serviceFormRef.value.resetFields();
  }
}

// 提交服务模块
async function handleSubmitService() {
  serviceFormRef.value.validate(async (valid: any) => {
    if (valid) {
      loading.value = true;
      const id = serviceFormData.id;
      try {
        if (id) {
          await NodeAPI.updateService(id, serviceFormData);
        } else {
          await NodeAPI.createService(serviceFormData);
        }
        serviceDialogVisible.visible = false;
        handleRefresh();
      } catch (error: any) {
        console.error(error);
      } finally {
        loading.value = false;
      }
    }
  });
}

// 打开节点弹窗
async function handleOpenNodeDialog(type: 'create' | 'update' | 'detail', id?: number) {
  nodeDialogVisible.type = type;
  if (id) {
    const response = await NodeAPI.getNodeDetail(id);
    if (type === 'detail') {
      nodeDialogVisible.title = "节点详情";
      Object.assign(nodeDetailFormData.value, response.data.data);
    } else if (type === 'update') {
      nodeDialogVisible.title = "修改节点";
      Object.assign(nodeFormData, response.data.data);
    }
  } else {
    nodeDialogVisible.title = "新增节点";
    nodeFormData.id = undefined;
    nodeFormData.service_id = undefined;
    nodeFormData.ip = '';
    nodeFormData.port = 22;
    nodeFormData.status = true;
    nodeFormData.description = undefined;
    nodeFormData.project = undefined;
    nodeFormData.idc = undefined;
    nodeFormData.tags = undefined;
  }
  nodeDialogVisible.visible = true;
}

// 关闭节点弹窗
async function handleCloseNodeDialog() {
  nodeDialogVisible.visible = false;
  if (nodeFormRef.value) {
    nodeFormRef.value.resetFields();
  }
}

// 提交节点
async function handleSubmitNode() {
  nodeFormRef.value.validate(async (valid: any) => {
    if (valid) {
      loading.value = true;
      const id = nodeFormData.id;
      try {
        if (id) {
          await NodeAPI.updateNode(id, nodeFormData);
        } else {
          await NodeAPI.createNode(nodeFormData);
        }
        nodeDialogVisible.visible = false;
        handleRefresh();
      } catch (error: any) {
        console.error(error);
      } finally {
        loading.value = false;
      }
    }
  });
}

// 删除节点
async function handleDeleteNode(ids: number[]) {
  if (ids.length === 0) {
    ElMessage.warning("请至少选择一个节点");
    return;
  }
  ElMessageBox.confirm("确认删除选中的节点?", "警告", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  }).then(async () => {
    try {
      loading.value = true;
      await NodeAPI.deleteNode(ids);
      handleRefresh();
    } catch (error: any) {
      console.error(error);
    } finally {
      loading.value = false;
    }
  }).catch(() => {
    ElMessageBox.close();
  });
}

// 删除服务模块
async function handleDeleteService(ids: number[]) {
  ElMessageBox.confirm("确认删除该服务模块? 删除后将同时删除该服务下的所有节点!", "警告", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  }).then(async () => {
    try {
      loading.value = true;
      await NodeAPI.deleteService(ids);
      handleRefresh();
    } catch (error: any) {
      console.error(error);
    } finally {
      loading.value = false;
    }
  }).catch(() => {
    ElMessageBox.close();
  });
}

// 部署
async function handleDeploy() {
  if (selectNodeIds.value.length === 0) {
    ElMessage.warning("请至少选择一个节点");
    return;
  }
  ElMessageBox.confirm("确认部署选中的节点?", "提示", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "info",
  }).then(async () => {
    try {
      loading.value = true;
      await NodeAPI.deploy(selectNodeIds.value);
      // 响应拦截器已经自动显示成功消息，这里不需要重复显示
      handleRefresh();
      // 刷新任务列表，并启动定时刷新（如果有运行中的任务）
      setTimeout(async () => {
        await loadRecentTasks();
        // 如果有正在运行的任务，启动定时刷新
        if (hasRunningTasks() && recentTasksTimer === null) {
          recentTasksTimer = window.setInterval(() => {
            loadRecentTasks();
          }, 5000);
        }
      }, 2000);
    } catch (error: any) {
      console.error(error);
    } finally {
      loading.value = false;
    }
  }).catch(() => {
    ElMessageBox.close();
  });
}

// 重启
async function handleRestart() {
  if (selectNodeIds.value.length === 0) {
    ElMessage.warning("请至少选择一个节点");
    return;
  }
  ElMessageBox.confirm("确认重启选中的节点?", "提示", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "info",
  }).then(async () => {
    try {
      loading.value = true;
      await NodeAPI.restart(selectNodeIds.value);
      // 响应拦截器已经自动显示成功消息，这里不需要重复显示
      handleRefresh();
      // 刷新任务列表，并启动定时刷新（如果有运行中的任务）
      setTimeout(async () => {
        await loadRecentTasks();
        // 如果有正在运行的任务，启动定时刷新
        if (hasRunningTasks() && recentTasksTimer === null) {
          recentTasksTimer = window.setInterval(() => {
            loadRecentTasks();
          }, 5000);
        }
      }, 2000);
    } catch (error: any) {
      console.error(error);
    } finally {
      loading.value = false;
    }
  }).catch(() => {
    ElMessageBox.close();
  });
}

// 获取任务状态文本
function getTaskStatusText(status: string) {
  const statusMap: Record<string, string> = {
    running: '执行中',
    success: '完成',
    failed: '失败',
  };
  return statusMap[status] || status;
}

function progressStatus(status?: string) {
  if (status === 'success') return 'success';
  if (status === 'failed') return 'exception';
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



<template>
  <div class="app-container">
    <div class="flex gap-4">
      <!-- 左侧内容区域 -->
      <div class="flex-1">
    <!-- 搜索区域 -->
    <div class="search-container">
      <el-form :inline="true" :model="queryParams" @submit.prevent="handleQuery">
        <el-form-item label="脚本名称">
          <el-input v-model="queryParams.name" placeholder="请输入脚本名称" clearable />
        </el-form-item>
        <el-form-item label="脚本类型">
          <el-select v-model="queryParams.script_type" placeholder="请选择" clearable>
            <el-option label="Python" value="python" />
            <el-option label="Shell" value="shell" />
          </el-select>
        </el-form-item>
        <el-form-item label="执行队列">
          <el-select v-model="queryParams.queue_code" placeholder="请选择" clearable>
            <el-option v-for="item in queueOptions" :key="item.queue_code" :label="item.queue_name" :value="item.queue_code" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="queryParams.status" placeholder="请选择" clearable>
            <el-option label="启用" :value="true" />
            <el-option label="禁用" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="Search" @click="handleQuery">查询</el-button>
          <el-button icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <el-card>
      <div class="mb-4">
        <el-button v-hasPerm="['operations:script:create']" type="primary" icon="Plus" @click="handleAdd">新增脚本</el-button>
        <el-button v-hasPerm="['operations:script:delete']" type="danger" icon="Delete" :disabled="!selectedIds.length" @click="handleDeleteBatch">批量删除</el-button>
      </div>

      <el-table v-loading="loading" :data="tableData" @selection-change="handleSelectionChange" border stripe>
        <el-table-column type="selection" width="55" />
        <el-table-column label="脚本名称" prop="name" min-width="150" />
        <el-table-column label="脚本类型" prop="script_type" min-width="100">
          <template #default="{ row }">
            <el-tag :type="row.script_type === 'python' ? 'success' : 'warning'">
              {{ row.script_type === 'python' ? 'Python' : 'Shell' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="内容类型" prop="content_type" min-width="100">
          <template #default="{ row }">
            {{ row.content_type === 'text' ? '文本内容' : '本地路径' }}
          </template>
        </el-table-column>
        <el-table-column label="默认超时" prop="default_timeout" min-width="100">
          <template #default="{ row }">
            {{ row.default_timeout }}秒
          </template>
        </el-table-column>
        <el-table-column label="执行队列" prop="queue_code" min-width="120" />
        <el-table-column label="参数数量" min-width="100">
          <template #default="{ row }">
            {{ (row.params_schema || []).length }}
          </template>
        </el-table-column>
        <el-table-column label="状态" prop="status" min-width="80">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'danger'">
              {{ row.status ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" prop="created_at" min-width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button v-hasPerm="['operations:script:run']" link type="success" @click="handleRun(row)">运行</el-button>
            <el-button v-hasPerm="['operations:script:update']" link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button v-hasPerm="['operations:script:delete']" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <pagination
        v-if="total > 0"
        v-model:page="queryParams.page_no"
        v-model:limit="queryParams.page_size"
        :total="total"
        @pagination="loadData"
      />
    </el-card>
      </div>

      <!-- 右侧任务进度栏 -->
      <div class="w-80">
        <el-card>
          <template #header>
            <div class="flex justify-between items-center">
              <span>任务进度</span>
              <el-button text type="primary" icon="Refresh" @click="loadRecentTasks">刷新</el-button>
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
                <el-tag size="small" :type="getTaskTypeTag(task.task_type)">
                  {{ getTaskTypeLabel(task.task_type) }}
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
                  <el-icon v-else-if="task.task_status === 'partial_success'" class="status-icon partial"><WarningFilled /></el-icon>
                  <el-icon v-else-if="task.task_status === 'failed'" class="status-icon failed"><CircleClose /></el-icon>
                  <el-icon v-else-if="task.task_status === 'cancelled'" class="status-icon cancelled"><Close /></el-icon>
                  <el-icon v-else-if="task.task_status === 'cancelling'" class="status-icon cancelling"><Loading /></el-icon>
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

    <!-- 新增/编辑 弹窗 -->
    <el-dialog :title="dialog.title" v-model="dialog.visible" width="800" @close="closeDialog" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-tabs v-model="activeTab">
          <el-tab-pane label="基本信息" name="basic">
            <el-form-item label="脚本名称" prop="name">
              <el-input v-model="form.name" placeholder="请输入脚本名称" />
            </el-form-item>
            <el-form-item label="脚本类型" prop="script_type">
              <el-select v-model="form.script_type" placeholder="请选择">
                <el-option label="Python" value="python" />
                <el-option label="Shell" value="shell" />
              </el-select>
            </el-form-item>
            <el-form-item label="内容类型" prop="content_type">
              <el-radio-group v-model="form.content_type">
                <el-radio value="text">文本内容</el-radio>
                <el-radio value="local_path">本地路径</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="脚本内容" prop="content" v-if="form.content_type === 'text'">
              <el-input
                v-model="form.content"
                type="textarea"
                :rows="10"
                placeholder="请输入脚本内容"
                style="font-family: monospace;"
              />
            </el-form-item>
            <el-form-item label="脚本路径" prop="content" v-else>
              <el-input v-model="form.content" placeholder="请输入脚本本地路径，如 /opt/scripts/test.py" />
            </el-form-item>
            <el-form-item label="默认超时" prop="default_timeout">
              <el-input-number v-model="form.default_timeout" :min="60" :max="86400" :step="60" />
              <span class="ml-2 text-gray-400">秒</span>
            </el-form-item>
            <el-form-item label="执行队列" prop="queue_code">
              <el-select v-model="form.queue_code" placeholder="请选择执行队列" clearable>
                <el-option v-for="item in queueOptions" :key="item.queue_code" :label="item.queue_name" :value="item.queue_code" />
              </el-select>
            </el-form-item>
            <el-form-item label="状态" prop="status">
              <el-switch v-model="form.status" />
            </el-form-item>
          </el-tab-pane>

          <el-tab-pane label="脚本参数" name="params">
            <div class="mb-4">
              <el-button type="primary" icon="Plus" @click="addParam">添加参数</el-button>
            </div>
            <el-table :data="form.params_schema" border>
              <el-table-column label="参数名称" min-width="120">
                <template #default="{ row }">
                  <el-input v-model="row.name" placeholder="参数名" />
                </template>
              </el-table-column>
              <el-table-column label="参数类型" min-width="120">
                <template #default="{ row }">
                  <el-select v-model="row.param_type" placeholder="类型">
                    <el-option label="字符串" value="string" />
                    <el-option label="整数" value="int" />
                    <el-option label="浮点数" value="float" />
                    <el-option label="布尔值" value="bool" />
                    <el-option label="列表" value="list" />
                    <el-option label="字典" value="dict" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="必填" width="80">
                <template #default="{ row }">
                  <el-checkbox v-model="row.required" />
                </template>
              </el-table-column>
              <el-table-column label="默认值" min-width="120">
                <template #default="{ row }">
                  <el-input v-model="row.default" placeholder="默认值" />
                </template>
              </el-table-column>
              <el-table-column label="描述" min-width="150">
                <template #default="{ row }">
                  <el-input v-model="row.description" placeholder="参数描述" />
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80">
                <template #default="{ $index }">
                  <el-button link type="danger" @click="removeParam($index)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </el-form>
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>

    <!-- 运行脚本 弹窗 -->
    <el-dialog title="运行脚本" v-model="runDialog.visible" width="600" destroy-on-close>
      <el-form ref="runFormRef" :model="runForm" label-width="120px">
        <el-form-item label="脚本名称">
          <span class="font-bold">{{ runDialog.script?.name }}</span>
        </el-form-item>
        <el-form-item label="超时时间">
          <el-input-number v-model="runForm.timeout" :min="60" :max="86400" :step="60" />
          <span class="ml-2 text-gray-400">秒（默认: {{ runDialog.script?.default_timeout }}秒）</span>
        </el-form-item>
        
        <!-- 动态参数表单 -->
        <template v-if="runDialog.script?.params_schema?.length">
          <el-divider>脚本参数</el-divider>
          <el-form-item 
            v-for="param in runDialog.script.params_schema" 
            :key="param.name"
            :label="param.name"
            :required="param.required"
          >
            <template v-if="param.param_type === 'bool'">
              <el-switch v-model="runForm.params[param.name]" />
            </template>
            <template v-else-if="param.param_type === 'int'">
              <el-input-number v-model="runForm.params[param.name]" :placeholder="param.description || '请输入'" />
            </template>
            <template v-else-if="param.param_type === 'float'">
              <el-input-number v-model="runForm.params[param.name]" :precision="2" :placeholder="param.description || '请输入'" />
            </template>
            <template v-else-if="param.param_type === 'list' || param.param_type === 'dict'">
              <el-input 
                v-model="runForm.params[param.name]" 
                type="textarea" 
                :rows="3"
                :placeholder="param.description || '请输入JSON格式'" 
              />
            </template>
            <template v-else>
              <el-input v-model="runForm.params[param.name]" :placeholder="param.description || '请输入'" />
            </template>
            <div class="text-gray-400 text-xs" v-if="param.description">{{ param.description }}</div>
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="runDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitRun" :loading="runLoading">运行</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { CircleCheck, CircleClose, Loading, WarningFilled, Close } from '@element-plus/icons-vue';
import ScriptAPI, { ScriptTable, ScriptQueryParam, ScriptParamSchema, ScriptForm } from '@/api/operations/script';
import CeleryWorkerAPI, { QueueItem } from '@/api/operations/celery_worker';
import NodeAPI, { TaskTable } from '@/api/operations/node';

defineOptions({
  name: "ScriptManage",
});

const loading = ref(false);
const tableData = ref<ScriptTable[]>([]);
const total = ref(0);
const queryParams = reactive<ScriptQueryParam & { page_no?: number; page_size?: number }>({
  page_no: 1,
  page_size: 10,
});
const queueOptions = ref<QueueItem[]>([]);
const selectedIds = ref<number[]>([]);
const activeTab = ref('basic');

const dialog = reactive({
  visible: false,
  title: '',
  type: 'add' as 'add' | 'edit'
});
const submitLoading = ref(false);
const formRef = ref();
const form = reactive<ScriptForm>({
  name: '',
  script_type: 'shell',
  content_type: 'text',
  content: '',
  default_timeout: 3600,
  queue_code: undefined,
  params_schema: [],
  status: true
});

const rules = {
  name: [{ required: true, message: '请输入脚本名称', trigger: 'blur' }],
  script_type: [{ required: true, message: '请选择脚本类型', trigger: 'change' }],
  content: [{ required: true, message: '请输入脚本内容', trigger: 'blur' }],
};

// 运行脚本相关
const runDialog = reactive({
  visible: false,
  script: null as ScriptTable | null
});
const runForm = reactive({
  timeout: 3600,
  params: {} as Record<string, any>
});
const runFormRef = ref();
const runLoading = ref(false);

// 任务进度栏相关
const taskList = ref<TaskTable[]>([]);
const router = useRouter();
let recentTasksTimer: number | null = null;

onMounted(() => {
  loadData();
  loadQueueOptions();
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

async function loadData() {
  loading.value = true;
  try {
    const res = await ScriptAPI.getPage(queryParams);
    tableData.value = res.data.data?.items || [];
    total.value = res.data.data?.total || 0;
  } catch (error: any) {
    ElMessage.error(error.message || '加载失败');
  } finally {
    loading.value = false;
  }
}

async function loadQueueOptions() {
  try {
    const res = await CeleryWorkerAPI.getQueues();
    queueOptions.value = res.data.data || [];
  } catch (error: any) {
    console.error('加载队列列表失败', error);
  }
}

function handleQuery() {
  queryParams.page_no = 1;
  loadData();
}

function resetQuery() {
  queryParams.name = undefined;
  queryParams.script_type = undefined;
  queryParams.queue_code = undefined;
  queryParams.status = undefined;
  queryParams.page_no = 1;
  loadData();
}

function handleSelectionChange(selection: ScriptTable[]) {
  selectedIds.value = selection.map(item => item.id!).filter(id => id !== undefined);
}

function handleAdd() {
  dialog.title = '新增脚本';
  dialog.type = 'add';
  dialog.visible = true;
  activeTab.value = 'basic';
  resetForm();
}

function handleEdit(row: ScriptTable) {
  dialog.title = '编辑脚本';
  dialog.type = 'edit';
  dialog.visible = true;
  activeTab.value = 'basic';
  Object.assign(form, {
    id: row.id,
    name: row.name || '',
    script_type: row.script_type || 'shell',
    content_type: row.content_type || 'text',
    content: row.content || '',
    default_timeout: row.default_timeout || 3600,
    queue_code: row.queue_code,
    params_schema: row.params_schema || [],
    status: row.status !== false
  });
}

function resetForm() {
  form.id = undefined;
  form.name = '';
  form.script_type = 'shell';
  form.content_type = 'text';
  form.content = '';
  form.default_timeout = 3600;
  form.queue_code = undefined;
  form.params_schema = [];
  form.status = true;
}

function closeDialog() {
  dialog.visible = false;
  resetForm();
}

function addParam() {
  if (!form.params_schema) {
    form.params_schema = [];
  }
  form.params_schema.push({
    name: '',
    param_type: 'string',
    required: true,
    default: undefined,
    description: ''
  });
}

function removeParam(index: number) {
  form.params_schema?.splice(index, 1);
}

async function submitForm() {
  try {
    await formRef.value?.validate();
  } catch {
    ElMessage.warning('请填写必填项');
    return;
  }

  submitLoading.value = true;
  try {
    const submitData = { ...form };
    if (dialog.type === 'add') {
      await ScriptAPI.create(submitData);
      ElMessage.success('创建成功');
    } else {
      await ScriptAPI.update(form.id!, submitData);
      ElMessage.success('更新成功');
    }
    closeDialog();
    loadData();
  } catch (error: any) {
    ElMessage.error(error.message || '操作失败');
  } finally {
    submitLoading.value = false;
  }
}

async function handleDelete(row: ScriptTable) {
  try {
    await ElMessageBox.confirm(`确定删除脚本 "${row.name}" 吗？`, '提示', {
      type: 'warning'
    });
    await ScriptAPI.delete([row.id!]);
    ElMessage.success('删除成功');
    loadData();
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败');
    }
  }
}

async function handleDeleteBatch() {
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedIds.value.length} 个脚本吗？`, '提示', {
      type: 'warning'
    });
    await ScriptAPI.delete(selectedIds.value);
    ElMessage.success('删除成功');
    loadData();
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败');
    }
  }
}

function handleRun(row: ScriptTable) {
  runDialog.script = row;
  runDialog.visible = true;
  runForm.timeout = row.default_timeout || 3600;
  runForm.params = {};
  
  // 初始化参数默认值
  if (row.params_schema) {
    for (const param of row.params_schema) {
      if (param.default !== undefined && param.default !== null) {
        runForm.params[param.name] = param.default;
      } else if (param.param_type === 'bool') {
        runForm.params[param.name] = false;
      } else if (param.param_type === 'int' || param.param_type === 'float') {
        runForm.params[param.name] = 0;
      } else {
        runForm.params[param.name] = '';
      }
    }
  }
}

async function submitRun() {
  if (!runDialog.script) return;

  // 验证必填参数
  const params_schema = runDialog.script.params_schema || [];
  for (const param of params_schema) {
    if (param.required && (runForm.params[param.name] === undefined || runForm.params[param.name] === '')) {
      ElMessage.warning(`请填写参数: ${param.name}`);
      return;
    }
  }

  // 处理 list/dict 类型参数
  const processedParams: Record<string, any> = {};
  for (const param of params_schema) {
    let value = runForm.params[param.name];
    if ((param.param_type === 'list' || param.param_type === 'dict') && typeof value === 'string') {
      try {
        value = JSON.parse(value);
      } catch {
        ElMessage.warning(`参数 ${param.name} JSON格式不正确`);
        return;
      }
    }
    processedParams[param.name] = value;
  }

  runLoading.value = true;
  try {
    const res = await ScriptAPI.run({
      script_id: runDialog.script.id!,
      params: processedParams,
      timeout: runForm.timeout
    });
    ElMessage.success(res.data.data?.message || '脚本执行任务已启动');
    runDialog.visible = false;
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
    ElMessage.error(error.message || '运行失败');
  } finally {
    runLoading.value = false;
  }
}

// 加载最近任务（只显示脚本执行任务）
async function loadRecentTasks() {
  try {
    const response = await NodeAPI.getRecentTasks(20, 'run'); // 脚本执行任务类型为 run
    taskList.value = response.data.data || [];
    
    // 检查是否有正在运行的任务，如果没有则停止定时刷新
    if (!hasRunningTasks()) {
      stopRecentTasksRefresh();
    }
  } catch (error: any) {
    console.error(error);
  }
}

// 停止定时刷新任务列表
function stopRecentTasksRefresh() {
  if (recentTasksTimer !== null) {
    clearInterval(recentTasksTimer);
    recentTasksTimer = null;
  }
}

// 检查是否有正在运行的任务
function hasRunningTasks(): boolean {
  return taskList.value.some(task => task.task_status === 'running' || task.task_status === 'cancelling');
}

// 获取任务状态文本
function getTaskStatusText(status: string) {
  const statusMap: Record<string, string> = {
    running: '执行中',
    success: '完成',
    partial_success: '部分成功',
    failed: '失败',
    cancelling: '取消中',
    cancelled: '已取消',
  };
  return statusMap[status] || status;
}

function progressStatus(status?: string) {
  if (status === 'success') return 'success';
  if (status === 'partial_success') return 'warning';
  if (status === 'failed') return 'exception';
  if (status === 'cancelled') return undefined;
  if (status === 'cancelling') return 'warning';
  return undefined;
}

function getTaskTypeLabel(taskType?: string) {
  if (taskType === 'run') return '脚本执行';
  if (taskType === 'deploy') return '部署';
  if (taskType === 'restart') return '重启';
  if (taskType === 'init') return '初始化';
  return taskType || '-';
}

function getTaskTypeTag(taskType?: string) {
  if (taskType === 'run') return 'success';
  if (taskType === 'deploy') return 'success';
  if (taskType === 'restart') return 'warning';
  if (taskType === 'init') return 'info';
  return 'info';
}

function handleOpenTaskDetailFromList(taskId?: number) {
  if (!taskId) return;
  router.push({
    path: `/operations/task/detail/${taskId}`,
  });
}
</script>

<style scoped>
.app-container {
  padding: 16px;
}

.search-container {
  margin-bottom: 20px;
}

.w-80 {
  width: 320px;
  flex-shrink: 0;
}

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
}

.task-item:hover {
  border-color: #409eff;
  background: #f0f9ff;
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
}

.status-icon.success {
  color: #67c23a;
}

.status-icon.partial {
  color: #e6a23c;
}

.status-icon.failed {
  color: #f56c6c;
}

.status-icon.running {
  color: #909399;
  animation: rotate 1s linear infinite;
}

.status-icon.cancelling {
  color: #e6a23c;
  animation: rotate 1s linear infinite;
}

.status-icon.cancelled {
  color: #909399;
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


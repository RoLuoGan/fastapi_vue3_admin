<template>
  <div class="operations-task page-root">
    <div v-if="!showDetailPage">
    <el-card shadow="never" class="search-card">
      <template #header>
        <div class="flex justify-between items-center">
          <span>查询条件</span>
          <div class="flex gap-2">
            <el-button type="primary" plain icon="search" @click="handleQuery" v-hasPerm="['operations:task:query']">
              查询
            </el-button>
            <el-button icon="refresh" @click="handleReset">
              重置
            </el-button>
          </div>
        </div>
      </template>
      <el-form ref="queryFormRef" :model="queryFormData" inline label-width="90px" label-suffix=":">
        <el-form-item label="任务类型">
          <el-select v-model="queryFormData.task_type" placeholder="全部" clearable>
            <el-option label="部署" value="deploy" />
            <el-option label="重启" value="restart" />
          </el-select>
        </el-form-item>
        <el-form-item label="任务状态">
          <el-select v-model="queryFormData.task_status" placeholder="全部" clearable>
            <el-option label="执行中" value="running" />
            <el-option label="成功" value="success" />
            <el-option label="部分成功" value="partial_success" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-form-item>
        <el-form-item label="运维管理项目">
          <el-select v-model="queryFormData.project" placeholder="全部" clearable style="width: 200px">
            <el-option v-for="item in projectOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value" />
          </el-select>
        </el-form-item>
        <el-form-item label="机房">
          <el-select v-model="queryFormData.idc" placeholder="全部" clearable style="width: 200px">
            <el-option v-for="item in idcOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value" />
          </el-select>
        </el-form-item>
        <el-form-item label="模块分组">
          <el-select v-model="queryFormData.module_group" placeholder="全部" clearable style="width: 200px">
            <el-option v-for="item in moduleGroupOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="createdRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="YYYY-MM-DD HH:mm:ss"
            @change="handleDateChange"
          />
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="mt-4">
      <template #header>
        <div class="flex justify-between items-center">
          <span>任务列表</span>
          <div class="flex gap-2">
            <el-button
              type="danger"
              plain
              icon="delete"
              :disabled="selectionIds.length === 0"
              @click="handleDelete(selectionIds)"
              v-hasPerm="['operations:task:delete']"
            >
              批量删除
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        v-loading="loading"
        :data="tableData"
        border
        stripe
        @selection-change="handleSelectionChange"
        row-key="id"
      >
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column prop="id" label="任务ID" width="90" />
        <el-table-column prop="task_type" label="任务类型" width="110">
          <template #default="{ row }">
            <el-tag :type="taskTypeTag(row.task_type)">
              {{ taskTypeLabel(row.task_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="progress" label="进度" min-width="160">
          <template #default="{ row }">
            <el-progress
              :percentage="row.progress || 0"
              :status="progressStatus(row.task_status)"
              :text-inside="true"
              :stroke-width="18"
            />
          </template>
        </el-table-column>
        <el-table-column prop="task_status" label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.task_status)">
              {{ statusLabel(row.task_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误信息" min-width="200" show-overflow-tooltip />
        <el-table-column prop="created_at" label="创建时间" min-width="180" />
        <el-table-column prop="updated_at" label="更新时间" min-width="180" />
        <el-table-column fixed="right" label="操作" width="150" align="center">
          <template #default="{ row }">
            <el-button
              type="primary"
              link
              icon="view"
              size="small"
              @click="handleViewDetail(row.id!)"
              v-hasPerm="['operations:task:query']"
            >
              任务详情
            </el-button>
            <el-button
              type="danger"
              link
              icon="delete"
              size="small"
              @click="handleDelete([row.id!])"
              v-hasPerm="['operations:task:delete']"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="mt-4 flex justify-end">
        <el-pagination
          v-model:current-page="queryFormData.page_no"
          v-model:page-size="queryFormData.page_size"
          :total="total"
          :page-sizes="[10, 20, 30, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
    </div>
    <router-view v-else />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox, type FormInstance } from "element-plus";
import NodeAPI, {
  type TaskPageQuery,
  type TaskTable,
} from "@/api/operations/node";
import DictAPI from "@/api/system/dict";

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const tableData = ref<TaskTable[]>([]);
const total = ref(0);
const selectionIds = ref<number[]>([]);
const createdRange = ref<[string, string] | []>([]);

const showDetailPage = computed(() => route.name === "OperationsTaskDetail");

const queryFormRef = ref<FormInstance>();
const queryFormData = reactive<TaskPageQuery>({
  page_no: 1,
  page_size: 10,
  task_type: undefined,
  task_status: undefined,
  project: undefined,
  idc: undefined,
  module_group: undefined,
  start_time: undefined,
  end_time: undefined,
});

const projectOptions = ref<any[]>([]);
const idcOptions = ref<any[]>([]);
const moduleGroupOptions = ref<any[]>([]);

function handleDateChange(value: [string, string] | null) {
  if (value && value.length === 2) {
    queryFormData.start_time = value[0];
    queryFormData.end_time = value[1];
  } else {
    queryFormData.start_time = undefined;
    queryFormData.end_time = undefined;
  }
}

async function loadDictOptions() {
  try {
    const [projectRes, idcRes, moduleGroupRes] = await Promise.all([
      DictAPI.getInitDict("operations_project"),
      DictAPI.getInitDict("operations_idc"),
      DictAPI.getInitDict("operations_module_group"),
    ]);
    projectOptions.value = projectRes.data.data || [];
    idcOptions.value = idcRes.data.data || [];
    moduleGroupOptions.value = moduleGroupRes.data.data || [];
  } catch (error: any) {
    console.error(error);
  }
}

async function loadData() {
  loading.value = true;
  try {
    const response = await NodeAPI.getTaskPage(queryFormData);
    const result = response.data.data;
    tableData.value = result.items || [];
    total.value = result.total || 0;
  } catch (error: any) {
    console.error(error);
  } finally {
    loading.value = false;
  }
}

function handleQuery() {
  queryFormData.page_no = 1;
  loadData();
}

function handleReset() {
  queryFormRef.value?.resetFields();
  createdRange.value = [];
  queryFormData.page_no = 1;
  queryFormData.page_size = 10;
  queryFormData.start_time = undefined;
  queryFormData.end_time = undefined;
  loadData();
}

function handleSizeChange(size: number) {
  queryFormData.page_size = size;
  queryFormData.page_no = 1;
  loadData();
}

function handleCurrentChange(page: number) {
  queryFormData.page_no = page;
  loadData();
}

function handleSelectionChange(selection: TaskTable[]) {
  selectionIds.value = selection.map((item) => item.id!).filter(Boolean);
}

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

function handleViewDetail(id: number) {
  router.push({
    name: "OperationsTaskDetail",
    params: { id: String(id) },
  });
}

async function handleDelete(ids: number[]) {
  if (!ids.length) return;
  try {
    await ElMessageBox.confirm("确认删除所选任务吗？删除后日志文件也将被清理。", "提示", {
      type: "warning",
    });
    await NodeAPI.deleteTask(ids);
    ElMessage.success("删除任务成功");
    if (tableData.value.length === ids.length && queryFormData.page_no && queryFormData.page_no > 1) {
      queryFormData.page_no -= 1;
    }
    loadData();
  } catch (error: any) {
    if (error !== "cancel") {
      console.error(error);
    }
  }
}

onMounted(() => {
  loadDictOptions();
  loadData();
});
</script>

<style scoped>
.page-root {
  padding: 16px;
}

.search-card {
  border-radius: 8px;
}
</style>


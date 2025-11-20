<template>
  <div class="app-container">
    <el-card class="mb-4" shadow="hover">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="Job名称">
          <el-input v-model="searchForm.job_name" placeholder="请输入 Job 名称" clearable />
        </el-form-item>
        <el-form-item label="启用状态">
          <el-select v-model="searchForm.is_enabled" placeholder="全部" clearable style="width: 120px">
            <el-option label="启用" :value="true" />
            <el-option label="禁用" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="loadData">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card>
      <template #header>
        <div class="flex gap-2">
          <el-button type="primary" @click="openCreateDialog">
            <el-icon><Plus /></el-icon>新增
          </el-button>
          <el-button @click="openImportDialog">
            <el-icon><Upload /></el-icon>JSON导入
          </el-button>
          <el-button @click="exportConfig">
            <el-icon><Download /></el-icon>JSON导出
          </el-button>
        </div>
      </template>

      <el-table
        :data="tableData"
        row-key="id"
        v-loading="loading"
        border
        default-expand-all
        :tree-props="{ children: 'children' }"
      >
        <el-table-column label="名称" min-width="220">
          <template #default="{ row }">
            <div v-if="row.type === 'job'" class="flex items-center gap-2">
              <el-icon><Memo /></el-icon>
              <span>{{ row.job_name }}</span>
            </div>
            <div v-else class="flex items-center gap-2">
              <el-icon><Link /></el-icon>
              <span>{{ row.endpoint }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="启用" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_enabled ? 'success' : 'info'">
              {{ row.is_enabled ? "启用" : "禁用" }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="标签" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.labels_text || "-" }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Endpoint数量" width="140" align="center">
          <template #default="{ row }">
            <span v-if="row.type === 'job'">{{ row.endpoints_count }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="160" fixed="right" align="center">
          <template #default="{ row }">
            <template v-if="row.type === 'job'">
              <el-button type="primary" link @click="openEditDialog(row)">编辑</el-button>
              <el-button type="danger" link @click="deleteJob(row)">删除</el-button>
            </template>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Job 表单 -->
    <el-dialog
      v-model="jobDialog.visible"
      :title="jobDialog.isEdit ? '编辑 Job' : '新增 Job'"
      width="640px"
      :destroy-on-close="true"
    >
      <el-form :model="jobDialog.form" :rules="jobRules" ref="jobFormRef" label-width="100px">
        <el-form-item label="Job名称" prop="job_name">
          <el-input v-model="jobDialog.form.job_name" placeholder="示例：node_exporter" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="jobDialog.form.description" placeholder="描述信息" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="jobDialog.form.is_enabled" />
        </el-form-item>
        <el-form-item label="抓取间隔">
          <el-input v-model="jobDialog.form.scrape_interval" placeholder="默认继承全局，如 15s" />
        </el-form-item>
        <el-form-item label="Honor Labels">
          <el-switch v-model="jobDialog.form.honor_labels" />
        </el-form-item>
        <el-form-item label="Endpoints" prop="endpointsText">
          <el-input
            v-model="jobDialog.form.endpointsText"
            type="textarea"
            :rows="4"
            placeholder="每行一个 Endpoint，例如 10.0.0.1:9100"
          />
          <div class="text-xs text-gray-500 mt-1">自动使用 http 协议，路径 /metrics</div>
        </el-form-item>
        <el-form-item label="Labels">
          <div class="w-full">
            <div v-for="(label, index) in jobDialog.form.labels" :key="index" class="flex gap-2 mb-2">
              <el-input v-model="label.key" placeholder="key" />
              <el-input v-model="label.value" placeholder="value" />
              <el-button
                icon="Minus"
                @click="removeLabel(index)"
                v-if="jobDialog.form.labels.length > 1"
              />
            </div>
            <el-button type="primary" link icon="Plus" @click="addLabel">新增标签</el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="jobDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="jobDialog.loading" @click="submitJobForm">
          {{ jobDialog.isEdit ? "更新" : "创建" }}
        </el-button>
      </template>
    </el-dialog>

    <!-- JSON 导入 -->
    <el-dialog v-model="importDialog.visible" title="JSON 导入" width="640px">
      <el-form label-width="100px">
        <el-form-item label="覆盖同名 Job">
          <el-switch v-model="importDialog.overwrite" />
        </el-form-item>
        <el-form-item label="JSON 内容">
          <el-input
            v-model="importDialog.jsonText"
            type="textarea"
            :rows="10"
            placeholder="粘贴 JSON 配置"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="importDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="importDialog.loading" @click="submitImport">
          导入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts" setup>
import { reactive, ref, onMounted } from "vue";
import { ElMessage, ElMessageBox, FormInstance, FormRules } from "element-plus";
import {
  Plus,
  Upload,
  Download,
  Memo,
  Link,
} from "@element-plus/icons-vue";
import PrometheusAPI, {
  type PrometheusTreeJob,
  type PrometheusTreeEndpoint,
  type PrometheusJobDetail,
} from "@/api/operations/prometheus";

interface SearchForm {
  job_name?: string;
  is_enabled?: boolean | null;
}

interface TableJobNode extends PrometheusTreeJob {
  type: "job";
}

interface TableEndpointNode extends PrometheusTreeEndpoint {
  type: "endpoint";
}

type TableRow = TableJobNode | TableEndpointNode;

const loading = ref(false);
const tableData = ref<TableRow[]>([]);
const searchForm = reactive<SearchForm>({
  job_name: "",
  is_enabled: null,
});

const jobDialog = reactive({
  visible: false,
  isEdit: false,
  loading: false,
  currentId: null as number | null,
  form: {
    job_name: "",
    description: "",
    is_enabled: true,
    scrape_interval: "",
    honor_labels: false,
    endpointsText: "",
    labels: [{ key: "", value: "" }],
  },
});

const jobFormRef = ref<FormInstance>();

const jobRules: FormRules = {
  job_name: [{ required: true, message: "请输入 Job 名称", trigger: "blur" }],
  endpointsText: [{ required: true, message: "至少输入一个 Endpoint", trigger: "blur" }],
};

const importDialog = reactive({
  visible: false,
  overwrite: false,
  jsonText: "",
  loading: false,
});

const transformTree = (jobs: PrometheusTreeJob[]): TableRow[] => {
  return jobs.map((job) => ({
    ...job,
    type: "job",
    children:
      job.children?.map((child) => ({
        ...child,
        type: "endpoint" as const,
        id: `endpoint-${child.id}`,
      })) ?? [],
  }));
};

const loadData = async () => {
  try {
    loading.value = true;
    const { data } = await PrometheusAPI.getJobTree({
      job_name: searchForm.job_name || undefined,
      is_enabled: searchForm.is_enabled ?? undefined,
    });
    tableData.value = transformTree(data.data || []);
  } finally {
    loading.value = false;
  }
};

const resetSearch = () => {
  searchForm.job_name = "";
  searchForm.is_enabled = null;
  loadData();
};

const resetJobForm = () => {
  jobDialog.form = {
    job_name: "",
    description: "",
    is_enabled: true,
    scrape_interval: "",
    honor_labels: false,
    endpointsText: "",
    labels: [{ key: "", value: "" }],
  };
  jobDialog.currentId = null;
};

const openCreateDialog = () => {
  resetJobForm();
  jobDialog.isEdit = false;
  jobDialog.visible = true;
};

const openEditDialog = async (row: TableJobNode) => {
  try {
    jobDialog.loading = true;
    const { data } = await PrometheusAPI.getJobDetail(row.id);
    const detail = data.data;
    jobDialog.form.job_name = detail.job_name;
    jobDialog.form.description = detail.description || "";
    jobDialog.form.is_enabled = detail.is_enabled;
    jobDialog.form.scrape_interval = detail.scrape_interval || "";
    jobDialog.form.honor_labels = detail.honor_labels;
    jobDialog.form.endpointsText = (detail.endpoints || [])
      .map((endpoint) => endpoint.endpoint)
      .join("\n");
    jobDialog.form.labels = detail.labels.length ? detail.labels : [{ key: "", value: "" }];
    jobDialog.currentId = detail.id || null;
    jobDialog.isEdit = true;
    jobDialog.visible = true;
  } finally {
    jobDialog.loading = false;
  }
};

const addLabel = () => {
  jobDialog.form.labels.push({ key: "", value: "" });
};

const removeLabel = (index: number) => {
  if (jobDialog.form.labels.length === 1) return;
  jobDialog.form.labels.splice(index, 1);
};

const normalizeJobPayload = (): PrometheusJobDetail => {
  const endpoints = jobDialog.form.endpointsText
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean)
    .map((endpoint) => ({
      endpoint,
      is_enabled: true,
      scheme: "http",
      metrics_path: "/metrics",
    }));

  if (!endpoints.length) {
    throw new Error("请至少输入一个有效 Endpoint");
  }

  const labels = jobDialog.form.labels
    .filter((label) => label.key && label.value)
    .map((label) => ({ ...label }));

  return {
    job_name: jobDialog.form.job_name.trim(),
    description: jobDialog.form.description?.trim(),
    is_enabled: jobDialog.form.is_enabled,
    scrape_interval: jobDialog.form.scrape_interval?.trim() || null,
    honor_labels: jobDialog.form.honor_labels,
    endpoints,
    labels,
  };
};

const submitJobForm = async () => {
  try {
    if (!jobFormRef.value) return;
    await jobFormRef.value.validate();
    const payload = normalizeJobPayload();
    jobDialog.loading = true;
    if (jobDialog.isEdit && jobDialog.currentId) {
      await PrometheusAPI.updateJob(jobDialog.currentId, payload);
      ElMessage.success("更新成功");
    } else {
      await PrometheusAPI.createJob(payload);
      ElMessage.success("创建成功");
    }
    jobDialog.visible = false;
    loadData();
  } catch (error: any) {
    if (error?.message) {
      ElMessage.error(error.message);
    }
  } finally {
    jobDialog.loading = false;
  }
};

const deleteJob = async (row: TableJobNode) => {
  await ElMessageBox.confirm(`确定删除 Job [${row.job_name}] 吗？`, "提示", {
    type: "warning",
  });
  await PrometheusAPI.deleteJob([row.id]);
  ElMessage.success("删除成功");
  loadData();
};

const exportConfig = async () => {
  try {
    const { data } = await PrometheusAPI.exportJobs();
    const jsonStr = JSON.stringify(data.data || [], null, 2);
    const blob = new Blob([jsonStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `prometheus_config_${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
    ElMessage.success("导出成功");
  } catch {
    ElMessage.error("导出失败");
  }
};

const openImportDialog = () => {
  importDialog.jsonText = "";
  importDialog.overwrite = false;
  importDialog.visible = true;
};

const submitImport = async () => {
  try {
    importDialog.loading = true;
    let parsed: any;
    try {
      parsed = JSON.parse(importDialog.jsonText || "[]");
    } catch {
      ElMessage.error("JSON 格式错误");
      return;
    }
    if (!Array.isArray(parsed) || !parsed.length) {
      ElMessage.error("JSON 内容不能为空");
      return;
    }
    await PrometheusAPI.importJobs({
      overwrite: importDialog.overwrite,
      jobs: parsed,
    });
    ElMessage.success("导入成功");
    importDialog.visible = false;
    loadData();
  } finally {
    importDialog.loading = false;
  }
};

onMounted(() => {
  loadData();
});
</script>

<style scoped>
.mb-4 {
  margin-bottom: 16px;
}
.flex {
  display: flex;
  align-items: center;
}
.gap-2 {
  gap: 8px;
}
.text-gray-500 {
  color: #6b7280;
}
</style>


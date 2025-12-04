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
        :max-height="tableMaxHeight"
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

        <el-table-column label="启用" width="120" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_enabled"
              inline-prompt
              active-text="启用"
              inactive-text="禁用"
              :active-value="true"
              :inactive-value="false"
              @change="handleToggleStatus(row)"
              :loading="row.toggleLoading"
            />
          </template>
        </el-table-column>

        <el-table-column label="标签" min-width="240">
          <template #default="{ row }">
            <div v-if="row.labels_text" class="tags-container">
              <el-tag
                v-for="(label, index) in parseLabels(row.labels_text)"
                :key="index"
                type="primary"
                effect="plain"
                size="small"
                class="label-tag"
              >
                {{ label.key }}: {{ label.value }}
              </el-tag>
            </div>
            <span v-else>-</span>
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
      width="1400px"
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
        <el-form-item label="Targets" prop="targets">
          <div class="targets-container">
            <el-table :data="jobDialog.form.targets" border :style="{ width: '100%' }" max-height="400">
              <el-table-column type="index" label="#" width="60" align="center" />
              <el-table-column label="Endpoints" min-width="300">
                <template #default="{ row, $index }">
                  <el-input
                    v-model="row.endpointsText"
                    type="textarea"
                    :rows="3"
                    placeholder="每行一个 Endpoint，例如：&#10;10.0.0.1:9100&#10;10.0.0.2:9100"
                    @blur="validateEndpoints(row, $index)"
                  />
                  <div class="text-xs text-gray-500 mt-1">每行一个 Endpoint</div>
                </template>
              </el-table-column>
              <el-table-column label="启用" width="80" align="center">
                <template #default="{ row }">
                  <el-switch v-model="row.is_enabled" />
                </template>
              </el-table-column>
              <el-table-column label="Labels" min-width="300">
                <template #default="{ row, $index }">
                  <div class="target-labels">
                    <div v-for="(label, labelIndex) in row.labels" :key="labelIndex" class="flex gap-2 mb-2 label-input-row">
                      <el-input v-model="label.key" placeholder="标签键" style="flex: 1" size="small" />
                      <el-input v-model="label.value" placeholder="标签值" style="flex: 1" size="small" />
                      <el-button
                        type="danger"
                        @click="removeTargetLabel($index, labelIndex)"
                        v-if="row.labels.length > 1"
                        circle
                        size="small"
                      >
                        <el-icon><Minus /></el-icon>
                      </el-button>
                    </div>
                    <el-button type="primary" link size="small" @click="addTargetLabel($index)">
                      <el-icon><Plus /></el-icon>新增标签
                    </el-button>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100" align="center">
                <template #default="{ $index }">
                  <el-button
                    type="danger"
                    link
                    size="small"
                    icon="delete"
                    @click="handleRemoveTarget($index)"
                    :disabled="jobDialog.form.targets.length <= 1"
                  >
                    删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
            <div class="mt-2">
              <el-button type="primary" plain icon="plus" size="small" @click="handleAddTarget">
                添加Target
              </el-button>
            </div>
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
import { reactive, ref, onMounted, computed, onUnmounted } from "vue";
import { ElMessage, ElMessageBox, FormInstance, FormRules } from "element-plus";
import {
  Plus,
  Upload,
  Download,
  Memo,
  Link,
  Minus,
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
  toggleLoading?: boolean;
}

interface TableEndpointNode extends PrometheusTreeEndpoint {
  type: "endpoint";
  toggleLoading?: boolean;
}

type TableRow = TableJobNode | TableEndpointNode;

const loading = ref(false);
const tableData = ref<TableRow[]>([]);
const searchForm = reactive<SearchForm>({
  job_name: "",
  is_enabled: null,
});

// 计算表格最大高度，使表格可以滚动
const windowHeight = ref(window.innerHeight);
const tableMaxHeight = computed(() => {
  // 视口高度减去顶部导航、搜索表单、卡片头部和底部边距
  // 大约预留 300px 给其他元素
  return windowHeight.value - 300;
});

// 监听窗口大小变化，动态调整表格高度
const handleResize = () => {
  windowHeight.value = window.innerHeight;
};

onMounted(() => {
  loadData();
  window.addEventListener("resize", handleResize);
});

onUnmounted(() => {
  window.removeEventListener("resize", handleResize);
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
    targets: [
      {
        endpointsText: "",
        is_enabled: true,
        labels: [{ key: "", value: "" }],
      },
    ],
  },
});

const jobFormRef = ref<FormInstance>();

const jobRules: FormRules = {
  job_name: [{ required: true, message: "请输入 Job 名称", trigger: "blur" }],
  targets: [
    {
      validator: (rule, value, callback) => {
        if (!value || value.length === 0) {
          callback(new Error("至少需要配置一个 Target"));
          return;
        }
        const validTargets = value.filter((target: any) => {
          const endpointsText = target.endpointsText?.trim();
          if (!endpointsText) return false;
          const endpoints = endpointsText.split("\n").map((ep: string) => ep.trim()).filter(Boolean);
          return endpoints.length > 0;
        });
        if (validTargets.length === 0) {
          callback(new Error("至少需要配置一个有效的 Endpoint"));
          return;
        }
        callback();
      },
      trigger: "blur",
    },
  ],
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

// 解析 labels_text 字符串为标签数组
// 格式: key="value", key2="value2"
const parseLabels = (labelsText: string): Array<{ key: string; value: string }> => {
  if (!labelsText || !labelsText.trim()) {
    return [];
  }
  
  const labels: Array<{ key: string; value: string }> = [];
  const regex = /(\w+)="([^"]+)"/g;
  let match;
  
  while ((match = regex.exec(labelsText)) !== null) {
    labels.push({
      key: match[1],
      value: match[2],
    });
  }
  
  return labels;
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
    targets: [
      {
        endpointsText: "",
        is_enabled: true,
        labels: [{ key: "", value: "" }],
      },
    ],
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
    
    // 将 targets 转换为表单格式
    // 将相同 is_enabled 和 labels 的 endpoints 合并到一个 target 行
    if (detail.targets && detail.targets.length > 0) {
      const targetMap = new Map<string, any>();
      for (const target of detail.targets) {
        const is_enabled = target.endpoint?.is_enabled ?? true;
        const labels = target.labels && target.labels.length > 0 ? target.labels : [];
        const labelsKey = JSON.stringify(labels.sort((a: any, b: any) => a.key.localeCompare(b.key)));
        const key = `${is_enabled}_${labelsKey}`;
        
        if (targetMap.has(key)) {
          const existing = targetMap.get(key);
          const endpoint = target.endpoint?.endpoint || "";
          if (endpoint) {
            existing.endpointsText += (existing.endpointsText ? "\n" : "") + endpoint;
          }
        } else {
          const endpoint = target.endpoint?.endpoint || "";
          targetMap.set(key, {
            endpointsText: endpoint,
            is_enabled: is_enabled,
            labels: labels.length > 0 ? labels : [{ key: "", value: "" }],
          });
        }
      }
      jobDialog.form.targets = Array.from(targetMap.values());
    } else {
      // 如果没有 targets，创建一个空的 target
      jobDialog.form.targets = [
        {
          endpointsText: "",
          is_enabled: true,
          labels: [{ key: "", value: "" }],
        },
      ];
    }
    
    jobDialog.currentId = detail.id || null;
    jobDialog.isEdit = true;
    jobDialog.visible = true;
  } finally {
    jobDialog.loading = false;
  }
};

const handleAddTarget = () => {
  jobDialog.form.targets.push({
    endpointsText: "",
    is_enabled: true,
    labels: [{ key: "", value: "" }],
  });
};

const handleRemoveTarget = (index: number) => {
  if (jobDialog.form.targets.length > 1) {
    jobDialog.form.targets.splice(index, 1);
  }
};

const addTargetLabel = (targetIndex: number) => {
  jobDialog.form.targets[targetIndex].labels.push({ key: "", value: "" });
};

const removeTargetLabel = (targetIndex: number, labelIndex: number) => {
  if (jobDialog.form.targets[targetIndex].labels.length > 1) {
    jobDialog.form.targets[targetIndex].labels.splice(labelIndex, 1);
  }
};

const validateEndpoints = (row: any, index: number) => {
  const endpointsText = row.endpointsText?.trim();
  if (!endpointsText) return;
  
  const endpoints = endpointsText.split("\n").map((ep: string) => ep.trim()).filter(Boolean);
  const endpointPattern = /^[\w\.-]+:\d+$/;
  
  for (let i = 0; i < endpoints.length; i++) {
    if (!endpointPattern.test(endpoints[i])) {
      ElMessage.warning(`第${index + 1}行第${i + 1}个 Endpoint 格式不正确，应为 IP:PORT 或 域名:PORT`);
      return;
    }
  }
};

const normalizeJobPayload = (): PrometheusJobDetail => {
  const targets: any[] = [];
  
  for (const target of jobDialog.form.targets) {
    const endpointsText = target.endpointsText?.trim();
    if (!endpointsText) continue;
    
    // 解析多个 endpoints（每行一个）
    const endpoints = endpointsText
      .split("\n")
      .map((ep: string) => ep.trim())
      .filter(Boolean);
    
    if (endpoints.length === 0) continue;
    
    // 过滤有效的 labels
    const labels = target.labels
      .filter((label: any) => label.key && label.value)
      .map((label: any) => ({ ...label }));
    
    // 为每个 endpoint 创建一个 target
    for (const endpoint of endpoints) {
      targets.push({
        endpoint: {
          endpoint: endpoint,
          is_enabled: target.is_enabled ?? true,
          scheme: "http", // 默认使用 http 协议
        },
        labels: labels,
      });
    }
  }

  if (!targets.length) {
    throw new Error("请至少输入一个有效的 Endpoint");
  }

  return {
    job_name: jobDialog.form.job_name.trim(),
    description: jobDialog.form.description?.trim(),
    is_enabled: jobDialog.form.is_enabled,
    targets,
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

const handleToggleStatus = async (row: TableRow) => {
  const originalStatus = row.is_enabled;
  try {
    // 设置加载状态
    row.toggleLoading = true;
    
    if (row.type === "job") {
      await PrometheusAPI.toggleJobStatus(row.id as number, row.is_enabled);
      ElMessage.success(`${row.is_enabled ? "启用" : "禁用"}成功`);
    } else {
      // endpoint 的 id 可能是复合 ID，需要提取真实 ID
      const endpointId = typeof row.id === "string" ? parseInt(row.id.replace("endpoint-", "")) : (row.id as number);
      await PrometheusAPI.toggleEndpointStatus(endpointId, row.is_enabled);
      ElMessage.success(`${row.is_enabled ? "启用" : "禁用"}成功`);
    }
    
    // 刷新数据
    await loadData();
  } catch (error: any) {
    // 恢复原状态
    row.is_enabled = originalStatus;
    if (error?.message) {
      ElMessage.error(error.message);
    } else {
      ElMessage.error("状态更新失败");
    }
  } finally {
    row.toggleLoading = false;
  }
};
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

/* 标签容器样式 */
.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.label-tag {
  margin: 0;
  font-size: 12px;
  border-radius: 4px;
  padding: 2px 8px;
  border: 1px solid #409eff;
  color: #409eff;
  background-color: #ecf5ff;
}

.label-tag:hover {
  background-color: #d9ecff;
}

/* 标签输入行样式 */
.label-input-row {
  align-items: flex-start;
}

/* 标签预览样式 */
.tags-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px;
  background-color: #f5f7fa;
  border-radius: 4px;
  border: 1px dashed #dcdfe6;
}

.mt-3 {
  margin-top: 12px;
}

.mb-2 {
  margin-bottom: 8px;
}

.targets-container {
  width: 100%;
}

.target-labels {
  padding: 8px 0;
}

.label-input-row {
  align-items: flex-start;
}
</style>


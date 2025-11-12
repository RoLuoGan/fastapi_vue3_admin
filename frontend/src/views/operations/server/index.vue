<template>
  <div class="operations-server page-root">
    <el-card shadow="never" class="search-card">
      <template #header>
        <div class="flex justify-between items-center">
          <span>查询条件</span>
          <div class="flex gap-2">
            <el-button type="primary" plain icon="search" @click="handleQuery" v-hasPerm="['operations:node:query']">
              查询
            </el-button>
            <el-button icon="refresh" @click="handleReset">
              重置
            </el-button>
          </div>
        </div>
      </template>
      <el-form ref="queryFormRef" :model="queryFormData" inline label-width="90px" label-suffix=":">
        <el-form-item label="所属服务">
          <el-select v-model="queryFormData.service_id" placeholder="全部" clearable style="width: 200px">
            <el-option
              v-for="item in serviceOptions"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="节点IP">
          <el-input v-model="queryFormData.ip" placeholder="请输入节点IP" clearable />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="queryFormData.status" placeholder="全部" clearable>
            <el-option :value="true" label="启用" />
            <el-option :value="false" label="停用" />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="mt-4">
      <template #header>
        <div class="flex justify-between items-center">
          <span>服务器节点列表</span>
          <div class="flex gap-2">
            <el-button
              type="primary"
              icon="plus"
              @click="handleOpenDialog('create')"
              v-hasPerm="['operations:node:create']"
            >
              新增节点
            </el-button>
            <el-button
              type="danger"
              plain
              icon="delete"
              :disabled="selectionIds.length === 0"
              @click="handleDelete(selectionIds)"
              v-hasPerm="['operations:node:delete']"
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
        <el-table-column type="index" width="60" label="#" />
        <el-table-column prop="service_name" label="所属服务" min-width="160" />
        <el-table-column prop="ip" label="节点IP" min-width="160" />
        <el-table-column prop="port" label="端口" width="90" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'danger'">
              {{ row.status ? "启用" : "停用" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="created_at" label="创建时间" min-width="180" />
        <el-table-column fixed="right" label="操作" width="220" align="center">
          <template #default="{ row }">
            <el-button
              type="info"
              link
              size="small"
              icon="document"
              @click="handleOpenDialog('detail', row.id)"
              v-hasPerm="['operations:node:query']"
            >
              详情
            </el-button>
            <el-button
              type="primary"
              link
              size="small"
              icon="edit"
              @click="handleOpenDialog('update', row.id)"
              v-hasPerm="['operations:node:update']"
            >
              编辑
            </el-button>
            <el-button
              type="danger"
              link
              size="small"
              icon="delete"
              @click="handleDelete([row.id!])"
              v-hasPerm="['operations:node:delete']"
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

    <el-dialog
      v-model="dialog.visible"
      :title="dialog.title"
      width="640px"
      destroy-on-close
      @close="handleDialogClose"
    >
      <template v-if="dialog.type === 'detail'">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="所属服务" :span="2">
            {{ nodeDetail?.service_name || "-" }}
          </el-descriptions-item>
          <el-descriptions-item label="节点IP">
            {{ nodeDetail?.ip || "-" }}
          </el-descriptions-item>
          <el-descriptions-item label="端口">
            {{ nodeDetail?.port || "-" }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="nodeDetail?.status ? 'success' : 'danger'">
              {{ nodeDetail?.status ? "启用" : "停用" }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ nodeDetail?.created_at || "-" }}
          </el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">
            {{ nodeDetail?.description || "-" }}
          </el-descriptions-item>
        </el-descriptions>
      </template>
      <div v-else>
        <el-form ref="nodeFormRef" :model="nodeForm" :rules="nodeRules" label-width="100px" label-suffix=":">
          <el-form-item label="所属服务" prop="service_id">
            <el-select v-model="nodeForm.service_id" placeholder="请选择所属服务" clearable>
              <el-option
                v-for="item in serviceOptions"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="节点IP" prop="ip">
            <el-input v-model="nodeForm.ip" placeholder="请输入节点IP" />
          </el-form-item>
          <el-form-item label="端口" prop="port">
            <el-input-number v-model="nodeForm.port" :min="1" :max="65535" controls-position="right" />
          </el-form-item>
          <el-form-item label="状态" prop="status">
            <el-switch
              v-model="nodeForm.status"
              inline-prompt
              active-text="启用"
              inactive-text="停用"
              :active-value="true"
              :inactive-value="false"
            />
          </el-form-item>
          <el-form-item label="描述" prop="description">
            <el-input
              v-model="nodeForm.description"
              type="textarea"
              :rows="4"
              placeholder="请输入描述"
              :maxlength="255"
              show-word-limit
            />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <template v-if="dialog.type === 'detail'">
            <el-button type="primary" @click="dialog.visible = false">关闭</el-button>
          </template>
          <template v-else>
            <el-button @click="dialog.visible = false">取消</el-button>
            <el-button type="primary" :loading="dialogLoading" @click="handleSubmit">
              确认
            </el-button>
          </template>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from "element-plus";
import NodeAPI, {
  type NodeForm,
  type NodePageQuery,
  type NodeTable,
  type ServiceTable,
} from "@/api/operations/node";

type DialogType = "create" | "update" | "detail";

interface ServiceOption {
  id: number;
  name: string;
}

const loading = ref(false);
const dialogLoading = ref(false);
const tableData = ref<NodeTable[]>([]);
const total = ref(0);
const selectionIds = ref<number[]>([]);

const serviceOptions = ref<ServiceOption[]>([]);

const queryFormRef = ref<FormInstance>();
const queryFormData = reactive<NodePageQuery>({
  page_no: 1,
  page_size: 10,
  service_id: undefined,
  ip: "",
  status: undefined,
});

const dialog = reactive({
  visible: false,
  title: "",
  type: "create" as DialogType,
  targetId: undefined as number | undefined,
});

const nodeFormRef = ref<FormInstance>();
const nodeForm = reactive<NodeForm>({
  service_id: undefined,
  ip: "",
  port: 22,
  status: true,
  description: "",
});

const nodeDetail = ref<NodeTable>();

const nodeRules: FormRules<NodeForm> = {
  service_id: [{ required: true, message: "请选择所属服务", trigger: "change" }],
  ip: [
    { required: true, message: "请输入节点IP地址", trigger: "blur" },
    { pattern: /^(\d{1,3}\.){3}\d{1,3}$/, message: "IP地址格式不正确", trigger: "blur" },
  ],
  port: [{ required: true, message: "请输入端口", trigger: "change" }],
};

async function loadServiceOptions() {
  try {
    const response = await NodeAPI.getServiceTree({ status: true });
    const list = response.data.data || [];
    serviceOptions.value = list.map((item: ServiceTable) => ({
      id: item.id!,
      name: item.name || "-",
    }));
  } catch (error: any) {
    console.error(error);
  }
}

async function loadData() {
  loading.value = true;
  try {
    const response = await NodeAPI.getNodePage(queryFormData);
    const result = response.data.data;
    tableData.value = result.items || [];
    total.value = result.total || 0;
  } catch (error: any) {
    console.error(error);
  } finally {
    loading.value = false;
  }
}

function handleSelectionChange(selection: NodeTable[]) {
  selectionIds.value = selection.map((item) => item.id!).filter(Boolean);
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

function handleQuery() {
  queryFormData.page_no = 1;
  loadData();
}

function handleReset() {
  queryFormRef.value?.resetFields();
  queryFormData.page_no = 1;
  queryFormData.page_size = 10;
  loadData();
}

function resetForm() {
  nodeForm.service_id = undefined;
  nodeForm.ip = "";
  nodeForm.port = 22;
  nodeForm.status = true;
  nodeForm.description = "";
}

async function handleOpenDialog(type: DialogType, id?: number) {
  dialog.type = type;
  dialog.targetId = id;
  dialog.visible = true;
  dialog.title =
    type === "create"
      ? "新增服务器节点"
      : type === "update"
      ? "编辑服务器节点"
      : "服务器节点详情";

  if (type === "create") {
    resetForm();
    nodeDetail.value = undefined;
    return;
  }

  if (!id) return;
  loading.value = true;
  try {
    const response = await NodeAPI.getNodeDetail(id);
    const detail = response.data.data;
    nodeDetail.value = detail;
    if (type === "update") {
      nodeForm.id = detail.id;
      nodeForm.service_id = detail.service_id;
      nodeForm.ip = detail.ip || "";
      nodeForm.port = detail.port || 22;
      nodeForm.status = detail.status ?? true;
      nodeForm.description = detail.description || "";
    }
  } catch (error: any) {
    console.error(error);
  } finally {
    loading.value = false;
  }
}

function handleDialogClose() {
  dialog.targetId = undefined;
  nodeDetail.value = undefined;
  nodeFormRef.value?.clearValidate();
}

function handleSubmit() {
  nodeFormRef.value?.validate(async (valid) => {
    if (!valid) return;
    dialogLoading.value = true;
    try {
      if (dialog.type === "create") {
        await NodeAPI.createNode(nodeForm);
        ElMessage.success("新增节点成功");
      } else if (dialog.targetId) {
        await NodeAPI.updateNode(dialog.targetId, nodeForm);
        ElMessage.success("更新节点成功");
      }
      dialog.visible = false;
      loadData();
    } catch (error: any) {
      console.error(error);
    } finally {
      dialogLoading.value = false;
    }
  });
}

async function handleDelete(ids: number[]) {
  if (!ids.length) return;
  try {
    await ElMessageBox.confirm("确认删除所选服务器节点吗？此操作不可恢复", "提示", {
      type: "warning",
    });
    await NodeAPI.deleteNode(ids);
    ElMessage.success("删除成功");
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
  Promise.all([loadServiceOptions(), loadData()]);
});
</script>

<style scoped>
.page-root {
  padding: 16px;
}

.search-card {
  border-radius: 8px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>


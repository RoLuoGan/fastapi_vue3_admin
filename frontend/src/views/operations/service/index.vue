<template>
  <div class="operations-service page-root">
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
        <el-form-item label="服务名称">
          <el-input v-model="queryFormData.name" placeholder="请输入服务名称" clearable />
        </el-form-item>
        <el-form-item label="服务编码">
          <el-input v-model="queryFormData.code" placeholder="请输入服务编码" clearable />
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
          <span>服务模块列表</span>
          <div class="flex gap-2">
            <el-button
              type="primary"
              icon="plus"
              @click="handleOpenDialog('create')"
              v-hasPerm="['operations:node:create']"
            >
              新增服务
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
        <el-table-column type="index" label="#" width="60" />
        <el-table-column prop="name" label="服务名称" min-width="160" />
        <el-table-column prop="code" label="服务编码" min-width="140" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'danger'">
              {{ row.status ? "启用" : "停用" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="created_at" label="创建时间" min-width="180" />
        <el-table-column fixed="right" label="操作" width="200" align="center">
          <template #default="{ row }">
            <el-button
              type="info"
              link
              icon="document"
              size="small"
              @click="handleOpenDialog('detail', row.id)"
              v-hasPerm="['operations:node:query']"
            >
              详情
            </el-button>
            <el-button
              type="primary"
              link
              icon="edit"
              size="small"
              @click="handleOpenDialog('update', row.id)"
              v-hasPerm="['operations:node:update']"
            >
              编辑
            </el-button>
            <el-button
              type="danger"
              link
              icon="delete"
              size="small"
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
      width="600px"
      destroy-on-close
      @close="handleDialogClose"
    >
      <template v-if="dialog.type === 'detail'">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="服务名称" :span="2">
            {{ serviceDetail?.name || "-" }}
          </el-descriptions-item>
          <el-descriptions-item label="服务编码">
            {{ serviceDetail?.code || "-" }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="serviceDetail?.status ? 'success' : 'danger'">
              {{ serviceDetail?.status ? "启用" : "停用" }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ serviceDetail?.created_at || "-" }}
          </el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">
            {{ serviceDetail?.description || "-" }}
          </el-descriptions-item>
        </el-descriptions>
      </template>
      <div v-else>
        <el-form ref="serviceFormRef" :model="serviceForm" :rules="serviceRules" label-width="100px" label-suffix=":">
          <el-form-item label="服务名称" prop="name">
            <el-input v-model="serviceForm.name" placeholder="请输入服务名称" :maxlength="100" />
          </el-form-item>
          <el-form-item label="服务编码" prop="code">
            <el-input v-model="serviceForm.code" placeholder="请输入服务编码" :maxlength="50" />
          </el-form-item>
          <el-form-item label="状态" prop="status">
            <el-switch
              v-model="serviceForm.status"
              inline-prompt
              active-text="启用"
              inactive-text="停用"
              :active-value="true"
              :inactive-value="false"
            />
          </el-form-item>
          <el-form-item label="描述" prop="description">
            <el-input
              v-model="serviceForm.description"
              type="textarea"
              :rows="4"
              placeholder="请输入描述信息"
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
  type ServiceForm,
  type ServicePageQuery,
  type ServiceTable,
} from "@/api/operations/node";

type DialogType = "create" | "update" | "detail";

const loading = ref(false);
const dialogLoading = ref(false);
const tableData = ref<ServiceTable[]>([]);
const total = ref(0);
const selectionIds = ref<number[]>([]);

const queryFormRef = ref<FormInstance>();
const queryFormData = reactive<ServicePageQuery>({
  page_no: 1,
  page_size: 10,
  name: "",
  code: "",
  status: undefined,
});

const dialog = reactive({
  visible: false,
  title: "",
  type: "create" as DialogType,
  targetId: undefined as number | undefined,
});

const serviceFormRef = ref<FormInstance>();
const serviceForm = reactive<ServiceForm>({
  name: "",
  code: "",
  status: true,
  description: "",
});

const serviceDetail = ref<ServiceTable>();

const serviceRules: FormRules<ServiceForm> = {
  name: [
    { required: true, message: "请输入服务名称", trigger: "blur" },
    { min: 2, max: 100, message: "长度在2-100个字符", trigger: "blur" },
  ],
  code: [
    {
      pattern: /^[A-Za-z][A-Za-z0-9_]*$/,
      message: "编码需以字母开头，可包含字母、数字、下划线",
      trigger: "blur",
    },
  ],
};

async function loadData() {
  loading.value = true;
  try {
    const response = await NodeAPI.getServicePage(queryFormData);
    const result = response.data.data;
    tableData.value = result.items || [];
    total.value = result.total || 0;
  } catch (error: any) {
    console.error(error);
  } finally {
    loading.value = false;
  }
}

function handleSelectionChange(selection: ServiceTable[]) {
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
  serviceForm.name = "";
  serviceForm.code = "";
  serviceForm.status = true;
  serviceForm.description = "";
}

async function handleOpenDialog(type: DialogType, id?: number) {
  dialog.type = type;
  dialog.targetId = id;
  dialog.visible = true;
  dialog.title =
    type === "create"
      ? "新增服务模块"
      : type === "update"
      ? "编辑服务模块"
      : "服务模块详情";

  if (type === "create") {
    resetForm();
    serviceDetail.value = undefined;
    return;
  }

  if (!id) return;
  loading.value = true;
  try {
    const response = await NodeAPI.getServiceDetail(id);
    const detail = response.data.data;
    serviceDetail.value = detail;
    if (type === "update") {
      serviceForm.id = detail.id;
      serviceForm.name = detail.name || "";
      serviceForm.code = detail.code || "";
      serviceForm.status = detail.status ?? true;
      serviceForm.description = detail.description || "";
    }
  } catch (error: any) {
    console.error(error);
  } finally {
    loading.value = false;
  }
}

function handleDialogClose() {
  dialog.targetId = undefined;
  serviceDetail.value = undefined;
  serviceFormRef.value?.clearValidate();
}

function handleSubmit() {
  serviceFormRef.value?.validate(async (valid) => {
    if (!valid) return;
    dialogLoading.value = true;
    try {
      if (dialog.type === "create") {
        await NodeAPI.createService(serviceForm);
        ElMessage.success("新增服务成功");
      } else if (dialog.targetId) {
        await NodeAPI.updateService(dialog.targetId, serviceForm);
        ElMessage.success("更新服务成功");
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
    await ElMessageBox.confirm("确认删除所选服务模块吗？此操作不可恢复", "提示", {
      type: "warning",
    });
    await NodeAPI.deleteService(ids);
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

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>


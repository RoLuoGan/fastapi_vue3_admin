<template>
  <div class="app-container">
    <!-- 搜索区域 -->
    <div class="search-container">
      <el-form :inline="true" :model="queryParams" @submit.prevent="handleQuery">
        <el-form-item label="队列名称">
          <el-input v-model="queryParams.queue_name" placeholder="请输入队列名称" clearable />
        </el-form-item>
        <el-form-item label="队列编码">
          <el-input v-model="queryParams.queue_code" placeholder="请输入队列编码" clearable />
        </el-form-item>
        <el-form-item label="节点IP">
          <el-input v-model="queryParams.node_ip" placeholder="请输入节点IP" clearable />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="queryParams.status" placeholder="请选择" clearable>
            <el-option label="在线" :value="true" />
            <el-option label="离线" :value="false" />
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
        <el-button v-hasPerm="['operations:celery_worker:create']" type="primary" icon="Plus" @click="handleAdd">新增节点</el-button>
        <el-button v-hasPerm="['operations:celery_worker:delete']" type="danger" icon="Delete" :disabled="!selectedIds.length" @click="handleDeleteBatch">批量删除</el-button>
      </div>

      <el-table v-loading="loading" :data="tableData" @selection-change="handleSelectionChange" border stripe>
        <el-table-column type="selection" width="55" />
        <el-table-column label="执行队列名称" prop="queue_name" min-width="150" />
        <el-table-column label="执行队列编码" prop="queue_code" min-width="120" />
        <el-table-column label="节点IP" prop="node_ip" min-width="130" />
        <el-table-column label="节点主机名" prop="node_hostname" min-width="150" show-overflow-tooltip />
        <el-table-column label="状态" prop="status" min-width="80">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'danger'">
              {{ row.status ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最后心跳" prop="last_heartbeat_time" min-width="180" />
        <el-table-column label="创建时间" prop="created_at" min-width="180" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button v-hasPerm="['operations:celery_worker:update']" link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button v-hasPerm="['operations:celery_worker:delete']" link type="danger" @click="handleDelete(row)">删除</el-button>
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

    <!-- 新增/编辑 弹窗 -->
    <el-dialog :title="dialog.title" v-model="dialog.visible" width="500" @close="closeDialog">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="执行队列名称" prop="queue_name">
          <el-input v-model="form.queue_name" placeholder="请输入执行队列名称" />
        </el-form-item>
        <el-form-item label="执行队列编码" prop="queue_code">
          <el-input v-model="form.queue_code" placeholder="请输入队列编码（如scripts）" :disabled="dialog.type === 'edit'" />
          <div class="text-gray-400 text-xs">以字母开头，只能包含字母、数字和下划线</div>
        </el-form-item>
        <el-form-item label="节点IP" prop="node_ip">
          <el-input v-model="form.node_ip" placeholder="请输入节点IP" :disabled="dialog.type === 'edit'" />
        </el-form-item>
        <el-form-item label="节点主机名" prop="node_hostname">
          <el-input v-model="form.node_hostname" placeholder="请输入节点主机名（可选）" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-switch v-model="form.status" active-text="在线" inactive-text="离线" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import CeleryWorkerAPI, { CeleryWorkerTable, CeleryWorkerQueryParam, CeleryWorkerForm } from '@/api/operations/celery_worker';

defineOptions({
  name: "CeleryWorkerManage",
});

const loading = ref(false);
const tableData = ref<CeleryWorkerTable[]>([]);
const total = ref(0);
const queryParams = reactive<CeleryWorkerQueryParam & { page_no?: number; page_size?: number }>({
  page_no: 1,
  page_size: 10,
});
const selectedIds = ref<number[]>([]);

const dialog = reactive({
  visible: false,
  title: '',
  type: 'add' as 'add' | 'edit'
});
const submitLoading = ref(false);
const formRef = ref();
const form = reactive<CeleryWorkerForm & { id?: number }>({
  queue_name: '',
  queue_code: '',
  node_ip: '',
  node_hostname: '',
  status: true
});

const rules = {
  queue_name: [{ required: true, message: '请输入执行队列名称', trigger: 'blur' }],
  queue_code: [
    { required: true, message: '请输入执行队列编码', trigger: 'blur' },
    { pattern: /^[a-zA-Z][a-zA-Z0-9_]*$/, message: '以字母开头，只能包含字母、数字和下划线', trigger: 'blur' }
  ],
  node_ip: [
    { required: true, message: '请输入节点IP', trigger: 'blur' },
    { pattern: /^(\d{1,3}\.){3}\d{1,3}$/, message: 'IP地址格式不正确', trigger: 'blur' }
  ],
};

onMounted(() => {
  loadData();
});

async function loadData() {
  loading.value = true;
  try {
    const res = await CeleryWorkerAPI.getPage(queryParams);
    tableData.value = res.data.data?.items || [];
    total.value = res.data.data?.total || 0;
  } catch (error: any) {
    ElMessage.error(error.message || '加载失败');
  } finally {
    loading.value = false;
  }
}

function handleQuery() {
  queryParams.page_no = 1;
  loadData();
}

function resetQuery() {
  queryParams.queue_name = undefined;
  queryParams.queue_code = undefined;
  queryParams.node_ip = undefined;
  queryParams.status = undefined;
  queryParams.page_no = 1;
  loadData();
}

function handleSelectionChange(selection: CeleryWorkerTable[]) {
  selectedIds.value = selection.map(item => item.id!).filter(id => id !== undefined);
}

function handleAdd() {
  dialog.title = '新增节点';
  dialog.type = 'add';
  dialog.visible = true;
  resetForm();
}

function handleEdit(row: CeleryWorkerTable) {
  dialog.title = '编辑节点';
  dialog.type = 'edit';
  dialog.visible = true;
  Object.assign(form, {
    id: row.id,
    queue_name: row.queue_name || '',
    queue_code: row.queue_code || '',
    node_ip: row.node_ip || '',
    node_hostname: row.node_hostname || '',
    status: row.status !== false
  });
}

function resetForm() {
  form.id = undefined;
  form.queue_name = '';
  form.queue_code = '';
  form.node_ip = '';
  form.node_hostname = '';
  form.status = true;
}

function closeDialog() {
  dialog.visible = false;
  resetForm();
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
      await CeleryWorkerAPI.create(submitData);
      ElMessage.success('创建成功');
    } else {
      await CeleryWorkerAPI.update(form.id!, submitData);
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

async function handleDelete(row: CeleryWorkerTable) {
  try {
    await ElMessageBox.confirm(`确定删除节点 "${row.queue_code}@${row.node_ip}" 吗？`, '提示', {
      type: 'warning'
    });
    await CeleryWorkerAPI.delete([row.id!]);
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
    await ElMessageBox.confirm(`确定删除选中的 ${selectedIds.value.length} 个节点吗？`, '提示', {
      type: 'warning'
    });
    await CeleryWorkerAPI.delete(selectedIds.value);
    ElMessage.success('删除成功');
    loadData();
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败');
    }
  }
}
</script>

<style scoped>
.search-container {
  margin-bottom: 20px;
}
</style>


<template>
  <div class="app-container">
    <!-- 搜索区域 -->
    <div class="search-container">
      <el-form :inline="true" :model="queryParams" @submit.prevent="handleQuery">
        <el-form-item label="服务模块">
          <el-select v-model="queryParams.service_id" placeholder="请选择服务模块" clearable filterable>
            <el-option v-for="item in serviceOptions" :key="item.id || 0" :label="item.name" :value="item.id || 0" />
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
         <el-button v-hasPerm="['operations:package:create']" type="primary" icon="Plus" @click="handleAdd">新增版本包</el-button>
         <el-button v-hasPerm="['operations:package:create']" type="success" icon="Upload" @click="handleOneClickUpload">一键上传</el-button>
         <el-button v-hasPerm="['operations:package:delete']" type="danger" icon="Delete" :disabled="!selectedIds.length" @click="handleDeleteBatch">批量删除</el-button>
       </div>
       
       <el-table v-loading="loading" :data="tableData" @selection-change="handleSelectionChange" border stripe>
         <el-table-column type="selection" width="55" />
         <el-table-column label="服务模块" prop="service_id" min-width="120">
            <template #default="{ row }">
                {{ getServiceName(row.service_id) }}
            </template>
         </el-table-column>
         <el-table-column label="版本号" prop="version" min-width="180" />
         <el-table-column label="版本包路径" prop="package_path" show-overflow-tooltip min-width="250" />
         <el-table-column label="MD5" prop="md5" show-overflow-tooltip min-width="200" />
         <el-table-column label="文件大小" prop="size" min-width="100" />
         <el-table-column label="创建时间" prop="created_at" min-width="180" />
         <el-table-column label="操作" width="150" fixed="right">
           <template #default="{ row }">
             <el-button v-hasPerm="['operations:package:update']" link type="primary" @click="handleEdit(row)">编辑</el-button>
             <el-button v-hasPerm="['operations:package:delete']" link type="danger" @click="handleDelete(row)">删除</el-button>
           </template>
         </el-table-column>
       </el-table>
    </el-card>

    <!-- 新增/编辑 弹窗 -->
    <el-dialog :title="dialog.title" v-model="dialog.visible" width="500" @close="closeDialog">
       <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
          <el-form-item label="服务模块" prop="service_id">
            <el-select v-model="form.service_id" placeholder="请选择" :disabled="dialog.type === 'edit'" filterable style="width: 100%">
                <el-option v-for="item in serviceOptions" :key="item.id || 0" :label="item.name" :value="item.id || 0" />
            </el-select>
          </el-form-item>
          <el-form-item label="版本号" prop="version">
             <el-input v-model="form.version" placeholder="不填自动生成" :disabled="dialog.type === 'edit'" />
          </el-form-item>
          <el-form-item label="上传文件" v-if="dialog.type === 'add'">
             <el-upload
               action="#"
               :auto-upload="false"
               :on-change="handleFileChange"
               :on-remove="handleFileRemove"
               :limit="1"
               :file-list="fileList"
             >
               <el-button type="primary">选择文件</el-button>
             </el-upload>
          </el-form-item>
           <el-form-item label="MD5" prop="md5">
              <el-input v-model="form.md5" placeholder="可选，选择校验MD5" />
           </el-form-item>
           <el-form-item label="是否最新" prop="is_latest">
              <el-switch v-model="form.is_latest" />
              <span class="ml-2 text-gray-400 text-xs">更新为当前版本管理</span>
           </el-form-item>
       </el-form>
       <template #footer>
         <el-button @click="closeDialog">取消</el-button>
         <el-button type="primary" @click="submitForm" :loading="submitLoading">确定</el-button>
       </template>
    </el-dialog>

    <!-- 一键上传 弹窗 -->
    <el-dialog title="一键上传" v-model="oneClickDialog.visible" width="500">
        <el-form :model="oneClickForm" label-width="100px">
             <el-form-item label="服务模块">
                <el-select v-model="oneClickForm.service_id" filterable style="width: 100%">
                    <el-option v-for="item in serviceOptions" :key="item.id || 0" :label="item.name" :value="item.id || 0" />
                </el-select>
             </el-form-item>
             <el-form-item label="日期">
                 <el-input v-model="oneClickForm.date_str" placeholder="默认当天，如 1123" />
             </el-form-item>
             <div class="text-gray-400 text-xs ml-10 mb-2">
                逻辑：去对象存储拉取文件按照固定格式拉取模块版本包，获取MD5大小、文件大小文件信息，生成新的版本包路径，上传后保存数据并更新为最新包。
                <br/>
                源路径格式: /{日期}/{模块名}/{模块名}.tgz
             </div>
        </el-form>
        <template #footer>
             <el-button @click="oneClickDialog.visible = false">取消</el-button>
             <el-button type="primary" @click="submitOneClick" :loading="oneClickLoading">确定</el-button>
        </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import ServicePackageAPI, { ServicePackageTable, ServicePackageQueryParam } from '@/api/operations/service_package';
import NodeAPI, { ServiceTable } from '@/api/operations/node';

defineOptions({
  name: "ServicePackage",
});

const loading = ref(false);
const tableData = ref<ServicePackageTable[]>([]);
const queryParams = reactive<ServicePackageQueryParam>({});
const serviceOptions = ref<ServiceTable[]>([]);
const selectedIds = ref<number[]>([]);

const dialog = reactive({
    visible: false,
    title: '',
    type: 'add' as 'add' | 'edit'
});
const submitLoading = ref(false);
const formRef = ref();
const form = reactive({
    id: undefined as number | undefined,
    service_id: undefined as number | undefined,
    version: '',
    md5: '',
    is_latest: true,
    file: null as File | null
});
const fileList = ref<any[]>([]);

const oneClickDialog = reactive({
    visible: false
});
const oneClickForm = reactive({
    service_id: undefined as number | undefined,
    date_str: ''
});
const oneClickLoading = ref(false);

const rules = {
    service_id: [{ required: true, message: '请选择服务模块', trigger: 'change' }]
};

// Load Services
async function loadServices() {
    try {
        const res = await NodeAPI.getServiceTree();
        serviceOptions.value = res.data.data || [];
    } catch(e) {
        console.error(e);
    }
}

function getServiceName(id: number) {
    const found = serviceOptions.value.find(s => s.id === id);
    return found ? found.name : id;
}

async function handleQuery() {
    loading.value = true;
    try {
        const res = await ServicePackageAPI.getList(queryParams);
        tableData.value = res.data.data || [];
    } catch(e) {
        console.error(e);
    } finally {
        loading.value = false;
    }
}

function resetQuery() {
    queryParams.service_id = undefined;
    queryParams.version = undefined;
    handleQuery();
}

function handleSelectionChange(selection: any[]) {
    selectedIds.value = selection.map(item => item.id);
}

function handleAdd() {
    dialog.type = 'add';
    dialog.title = '新增版本包';
    dialog.visible = true;
    form.id = undefined;
    form.service_id = undefined;
    form.version = '';
    form.md5 = '';
    form.is_latest = true;
    form.file = null;
    fileList.value = [];
}

function handleEdit(row: ServicePackageTable) {
    dialog.type = 'edit';
    dialog.title = '编辑版本包';
    dialog.visible = true;
    form.id = row.id;
    form.service_id = row.service_id;
    form.version = row.version;
    form.md5 = row.md5 || '';
    form.is_latest = false; // default false when editing? Spec says "Inputs...".
    form.file = null;
}

function handleFileChange(uploadFile: any) {
    form.file = uploadFile.raw;
    fileList.value = [uploadFile];
}

function handleFileRemove() {
    form.file = null;
    fileList.value = [];
}

function closeDialog() {
    dialog.visible = false;
}

async function submitForm() {
    if (!formRef.value) return;
    await formRef.value.validate(async (valid: boolean) => {
        if (valid) {
            submitLoading.value = true;
            try {
                if (dialog.type === 'add') {
                    await ServicePackageAPI.create({
                        service_id: form.service_id!,
                        version: form.version,
                        md5: form.md5,
                        is_latest: form.is_latest,
                        file: form.file || undefined
                    });
                    ElMessage.success('创建成功');
                } else {
                    await ServicePackageAPI.update(form.id!, {
                        id: form.id!,
                        version: form.version,
                        md5: form.md5,
                        is_latest: form.is_latest
                    });
                    ElMessage.success('更新成功');
                }
                closeDialog();
                handleQuery();
            } catch(e) {
                console.error(e);
            } finally {
                submitLoading.value = false;
            }
        }
    });
}

function handleOneClickUpload() {
    oneClickDialog.visible = true;
    oneClickForm.service_id = undefined;
    oneClickForm.date_str = '';
}

async function submitOneClick() {
    if (!oneClickForm.service_id) {
        ElMessage.warning('请选择服务模块');
        return;
    }
    oneClickLoading.value = true;
    try {
        await ServicePackageAPI.oneClickUpload({
            service_id: oneClickForm.service_id!,
            date_str: oneClickForm.date_str || undefined
        });
        ElMessage.success('上传成功');
        oneClickDialog.visible = false;
        handleQuery();
    } catch(e) {
        console.error(e);
    } finally {
        oneClickLoading.value = false;
    }
}

function handleDelete(row: ServicePackageTable) {
    ElMessageBox.confirm('确认删除该版本包?', '提示', { type: 'warning' }).then(async () => {
        await ServicePackageAPI.delete([row.id]);
        ElMessage.success('删除成功');
        handleQuery();
    });
}

function handleDeleteBatch() {
    ElMessageBox.confirm(`确认删除选中的 ${selectedIds.value.length} 个版本包?`, '提示', { type: 'warning' }).then(async () => {
        await ServicePackageAPI.delete(selectedIds.value);
        ElMessage.success('删除成功');
        handleQuery();
    });
}

onMounted(() => {
    loadServices();
    handleQuery();
});
</script>


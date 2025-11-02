<!-- 我的应用管理 -->
<template> 
  <div class="app-container">
      <!-- 顶部搜索和操作区域 -->
      <div class="search-container">
        <el-form ref="queryFormRef" :model="queryFormData" :inline="true" label-suffix=":" @submit.prevent="handleQuery">
          <el-form-item prop="name" label="应用名称">
            <el-input v-model="queryFormData.name" placeholder="请输入应用名称" clearable/>
          </el-form-item>
          <el-form-item prop="status" label="状态">
            <el-select v-model="queryFormData.status" placeholder="请选择状态" clearable style="width: 170px;">
              <el-option label="启用" :value="true" />
              <el-option label="停用" :value="false" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="isExpand" prop="creator" label="创建人">
            <UserTableSelect
                v-model="queryFormData.creator"
                @confirm-click="handleConfirm"
                @clear-click="handleQuery"
            />
          </el-form-item>
          <el-form-item class="search-buttons">
            <el-button v-hasPerm="['application:myapp:query']" type="primary" icon="search" native-type="submit">查询</el-button>
            <el-button v-hasPerm="['application:myapp:query']" icon="refresh" @click="handleResetQuery">重置</el-button>
            <!-- 展开/收起 -->
            <template v-if="isExpandable">
              <el-link class="ml-3" type="primary" underline="never" @click="isExpand = !isExpand">
                {{ isExpand ? "收起" : "展开" }}
                <el-icon>
                  <template v-if="isExpand">
                    <ArrowUp />
                  </template>
                  <template v-else>
                    <ArrowDown />
                  </template>
                </el-icon>
              </el-link>
            </template>
          </el-form-item>
        </el-form>
      </div>

      <!-- 应用卡片展示区域 -->
      <el-card shadow="hover" class="app-grid-card"  >
        <template #header>
          <div class="card-header">
            <span>应用市场</span>
            <el-button v-hasPerm="['application:myapp:create']" type="primary" icon="plus" @click="handleCreateApp">
              创建应用
            </el-button>
          </div>
        </template>

        <!-- 应用网格 -->
        <div v-loading="loading" class="app-grid" >
          <el-card 
            v-for="app in applicationList" 
            :key="app.id"
            class="app-card-el"
            :body-style="{ padding: '12px' }"
            shadow="hover"
          >
            <template #header>
              <div class="app-card-header-el">
                <div class="app-info-header">
                  <el-avatar 
                    :size="40" 
                    :src="app.icon_url" 
                    class="app-avatar-el"
                  >
                    <el-icon size="20"><Monitor /></el-icon>
                  </el-avatar>
                  <div class="app-title-section">
                    <h3 class="app-name-el">{{ app.name }}</h3>
                    <el-tag 
                      :type="app.status ? 'success' : 'danger'" 
                      size="small"
                      class="app-status-tag"
                    >
                      {{ app.status ? '启用' : '停用' }}
                    </el-tag>
                  </div>
                </div>
                <el-dropdown 
                  v-hasPerm="['application:myapp:update']"
                  trigger="click" 
                  @command="(command) => handleAppAction(command, app)"
                >
                  <el-button 
                    type="text" 
                    icon="MoreFilled" 
                    size="small"
                    class="app-menu-btn"
                  />
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="edit" icon="Edit">编辑</el-dropdown-item>
                      <el-dropdown-item command="delete" icon="Delete" divided>删除</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </template>

            <div class="app-card-content">
              <p class="app-description">{{ app.description || '暂无描述' }}</p>
              
              <div class="app-meta-info">
                <div class="app-meta-row">
                  <div class="meta-item left">
                    <el-icon size="14" class="meta-icon"><User /></el-icon>
                    <span>{{ app.creator?.name || '未知' }}</span>
                  </div>
                  <div class="meta-item right">
                    <el-icon size="14" class="meta-icon"><Clock /></el-icon>
                    <span>{{ formatTime(app.created_at) }}</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="app-card-actions">
              <el-button 
                v-hasPerm="['application:myapp:open_external']"
                type="primary" 
                icon="Link" 
                size="small"
                :disabled="!app.status"
                class="action-btn"
                @click="openAppExternal(app.access_url)"
              >
                外部打开
              </el-button>
              <el-button 
                v-hasPerm="['application:myapp:open_internal']"
                type="default" 
                icon="View" 
                size="small"
                :disabled="!app.status"
                class="action-btn"
                @click="openAppInternal(app)"
              >
                内部打开
              </el-button>
            </div>
          </el-card>
        </div>
        
        <!-- 空状态 -->
        <div v-if="applicationList.length === 0 && !loading" >
          <el-empty :image-size="80" description="暂无数据" />
        </div>

        <!-- 分页区域 -->
        <template #footer>
          <!-- 使用卡片 footer 样式右对齐，无需额外容器 -->
          <pagination
            v-model:total="total"
            v-model:page="queryFormData.page_no"
            v-model:limit="queryFormData.page_size"
            :page-sizes="[12, 24, 48]"
            @pagination="loadApplicationList"
          />
        </template>
      </el-card>

    <!-- 应用创建/编辑弹窗 -->
    <el-drawer
      v-model="dialogVisible"
      :title="dialogTitle"
      :size="drawerSize"
      direction="rtl"
      @close="handleCloseDialog"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
        label-position="right"
      >
        <el-form-item label="应用名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入应用名称" />
        </el-form-item>
        
        <el-form-item label="访问地址" prop="access_url">
          <el-input v-model="formData.access_url" placeholder="请输入访问地址" />
        </el-form-item>
        
        <el-form-item label="图标地址" prop="icon_url">
          <el-input v-model="formData.icon_url" placeholder="请输入图标地址" />
        </el-form-item>
        
        <el-form-item label="应用状态" prop="status">
          <el-radio-group v-model="formData.status">
            <el-radio :value="true">启用</el-radio>
            <el-radio :value="false">停用</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="应用描述" prop="description">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="4"
            placeholder="请输入应用描述"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="handleCloseDialog">取消</el-button>
          <el-button type="primary" @click="handleSubmit">确定</el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: "MyApplication",
  inheritAttrs: false,
});

import { useAppStore } from "@/store/modules/app.store";
import { useTagsViewStore } from "@/store";
import { useRouter } from "vue-router";
import { DeviceEnum } from "@/enums/settings/device.enum";
import { Monitor, User, Clock } from '@element-plus/icons-vue';
import ApplicationAPI, { type ApplicationForm, type ApplicationInfo, type ApplicationPageQuery } from "@/api/application/myapp";
import { formatToDateTime } from "@/utils/dateUtil";

const appStore = useAppStore();
const tagsViewStore = useTagsViewStore();
const router = useRouter();

// 响应式数据
const queryFormRef = ref();
const formRef = ref();
const loading = ref(false);
const total = ref(0);
const dialogVisible = ref(false);
const dialogType = ref<'create' | 'edit'>('create');
const currentApp = ref<ApplicationInfo | null>(null);
const isExpand = ref(false);
const isExpandable = ref(true);

// 分页查询参数
const queryFormData = reactive<ApplicationPageQuery>({
  page_no: 1,
  page_size: 12,
  name: undefined,
  status: undefined,
  creator: undefined,
});

// 应用列表数据
const applicationList = ref<ApplicationInfo[]>([]);

// 表单数据
const formData = reactive<ApplicationForm>({
  name: '',
  access_url: '',
  icon_url: '',
  status: true,
  description: '',
});

// 表单验证规则
const formRules = reactive({
  name: [
    { required: true, message: "请输入应用名称", trigger: "blur" },
    { min: 2, max: 30, message: "长度在 2 到 30 个字符", trigger: "blur" }],
  access_url: [
    { required: true, message: "请输入访问地址", trigger: "blur" },
    { type: 'url' as const, message: "请输入正确的URL格式", trigger: "blur" }
  ],
  icon_url: [
    { required: true, message: "请输入图标地址", trigger: "blur" },
    { type: 'url' as const, message: "请输入正确的URL格式", trigger: "blur" }
  ],
  status: [{ required: true, message: "请选择应用状态", trigger: "change" }],
});

// 计算属性
const drawerSize = computed(() => (appStore.device === DeviceEnum.DESKTOP ? "500px" : "90%"));
const dialogTitle = computed(() => dialogType.value === 'create' ? '创建应用' : '编辑应用');

// 格式化时间
const formatTime = (time: string | undefined) => {
  if (!time) return '未知';
  return formatToDateTime(time, 'YYYY-MM-DD HH:mm:ss');
};

// 加载应用列表
async function loadApplicationList() {
  loading.value = true;
  try {
    const response = await ApplicationAPI.getApplicationList(queryFormData);
    applicationList.value = response.data.data.items;
    total.value = response.data.data.total;
  } catch (error) {
    console.error('加载应用列表失败:', error);
  } finally {
    loading.value = false;
  }
}

// 查询
async function handleQuery() {
  queryFormData.page_no = 1;
  await loadApplicationList();
}

// 选择创建人后触发查询
function handleConfirm() {
  handleQuery();
}

// 重置查询
async function handleResetQuery() {
  queryFormRef.value?.resetFields();
  queryFormData.page_no = 1;
  await loadApplicationList();
}

// 创建应用
function handleCreateApp() {
  console.log('handleCreateApp');
  dialogType.value = 'create';
  resetForm();
  dialogVisible.value = true;
}

// 编辑应用
function handleEditApp(app: ApplicationInfo) {
  dialogType.value = 'edit';
  currentApp.value = app;
  Object.assign(formData, app);
  dialogVisible.value = true;
}

// 删除应用
async function handleDeleteApp(app: ApplicationInfo) {
  try {
    await ElMessageBox.confirm('确认删除该应用？', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    });
    
    await ApplicationAPI.deleteApplication([app.id!]);
    await loadApplicationList();
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除应用失败:', error);
    }
  }
}

// 应用操作
async function handleAppAction(command: string, app: ApplicationInfo) {
  switch (command) {
    case 'edit':
      handleEditApp(app);
      break;
    case 'delete':
      await handleDeleteApp(app);
      break;
  }
}

// 外部打开应用
function openAppExternal(url: string | undefined) {
  if (url) {
    window.open(url, '_blank');
  }
}

// 内部打开应用
function openAppInternal(app: ApplicationInfo) {
  if (!app.status) {
    ElMessage.warning('应用已停用，无法打开');
    return;
  }
  
  if (!app.access_url) {
    ElMessage.warning('应用访问地址不存在');
    return;
  }
  
  // 创建一个动态路由路径
  const appPath = `/internal-app/${app.id}`;
  const appName = `InternalApp${app.id}`;
  const appTitle = app.name || '未命名应用';
  
  // 先导航到路由，这样可以动态设置路由的meta信息
  router.push({
    path: appPath,
    query: { url: app.access_url, appId: app.id?.toString() || '', appName: appTitle }
  }).then(() => {
    // 导航完成后，手动添加或更新标签视图
    nextTick(() => {
      // 查找是否已存在该标签
      const existingTag = tagsViewStore.visitedViews.find(tag => tag.path === appPath);
      
      if (existingTag) {
        // 如果存在，更新标题
        tagsViewStore.updateVisitedView({
          ...existingTag,
          title: appTitle,
        });
      } else {
        // 如果不存在，添加新标签
        tagsViewStore.addView({
          name: appName,
          title: appTitle,
          path: appPath,
          fullPath: appPath + `?url=${encodeURIComponent(app.access_url || '')}&appId=${app.id || ''}&appName=${encodeURIComponent(appTitle)}`,
          icon: 'Monitor',
          affix: false,
          keepAlive: false,
          query: { url: app.access_url, appId: app.id?.toString() || '', appName: appTitle },
        });
      }
    });
  });
}

// 重置表单
function resetForm() {
  Object.assign(formData, {
    name: '',
    access_url: '',
    icon_url: '',
    status: true,
    description: '',
  });
  formRef.value?.resetFields();
}

// 关闭弹窗
function handleCloseDialog() {
  dialogVisible.value = false;
  resetForm();
}

// 提交表单
async function handleSubmit() {
  try {
    await formRef.value?.validate();
    
    if (dialogType.value === 'create') {
      await ApplicationAPI.createApplication(formData);
    } else {
      await ApplicationAPI.updateApplication(currentApp.value!.id!, formData);
    }
    
    dialogVisible.value = false;
    resetForm();
    await loadApplicationList();
  } catch (error) {
    console.error('提交失败:', error);
  }
}

// 初始化
onMounted(() => {
  loadApplicationList();
});
</script>

<style lang="scss" scoped>
.app-grid-card {
  height: calc(100vh - 200px);
  position: relative;
  display: flex;
  flex-direction: column;
  
  :deep(.el-card__footer) {
    margin-top: auto;
    display: flex;
    justify-content: flex-end;
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.app-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    flex: 1;
  }

.app-card-el {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  transition: all 0.3s ease;
}

.app-card-header-el {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.app-info-header {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}


.app-name-el {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0 0 4px 0;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}



.app-card-content {
  margin: 12px 0;
}

.app-description {
  font-size: 14px;
  color: var(--el-text-color-regular);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.app-meta-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.app-meta-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  overflow: hidden;
}

.meta-item.left {
  flex: 1;
  justify-content: flex-start;
  min-width: 0;
}

.meta-item.right {
  flex: 1;
  justify-content: flex-end;
  text-align: right;
  min-width: 0;
}

.meta-icon {
  color: var(--el-text-color-placeholder);
  flex-shrink: 0;
}

.meta-item span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-card-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  
  .action-btn {
    flex: 1;
    font-size: 12px;
    padding: 4px 8px;
  }
}


.pagination-container {
  display: flex;
  justify-content: flex-end;
}


.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

</style>

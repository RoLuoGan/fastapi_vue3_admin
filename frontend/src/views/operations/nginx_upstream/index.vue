<template>
  <div class="operations-nginx-upstream page-root">
    <el-card shadow="never" class="search-card">
      <template #header>
        <div class="flex justify-between items-center">
          <span>查询条件</span>
          <div class="flex gap-2">
            <el-button type="primary" plain icon="search" @click="handleQuery" v-hasPerm="['operations:nginx_upstream:query']">
              查询
            </el-button>
            <el-button icon="refresh" @click="handleReset">
              重置
            </el-button>
          </div>
        </div>
      </template>
      <el-form ref="queryFormRef" :model="queryFormData" inline label-width="120px" label-suffix=":">
        <el-form-item label="Upstream名称">
          <el-input v-model="queryFormData.upstream" placeholder="请输入upstream名称" clearable />
        </el-form-item>
        <el-form-item label="Nginx节点">
          <el-select v-model="queryFormData.nginx_node_id" placeholder="全部" clearable style="width: 200px">
            <el-option v-for="node in nginxNodeOptions" :key="node.id!" :label="node.ip" :value="node.id!" />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="mt-4">
      <template #header>
        <div class="flex justify-between items-center">
          <span>Nginx Upstream列表</span>
          <div class="flex gap-2">
            <el-button
              type="primary"
              icon="plus"
              @click="handleOpenDialog('create')"
              v-hasPerm="['operations:nginx_upstream:create']"
            >
              新增Upstream
            </el-button>
            <el-button
              type="warning"
              plain
              icon="upload"
              :disabled="selectionIds.length === 0"
              @click="handleBatchSync"
              v-hasPerm="['operations:nginx_upstream:sync']"
            >
              批量同步
            </el-button>
            <el-button
              type="danger"
              plain
              icon="delete"
              :disabled="selectionIds.length === 0"
              @click="handleDelete(selectionIds)"
              v-hasPerm="['operations:nginx_upstream:delete']"
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
        <el-table-column prop="upstream" label="Upstream名称" min-width="160" />
        <el-table-column label="代理目标" min-width="240">
          <template #default="{ row }">
            <div v-if="row.proxy_targets && row.proxy_targets.length > 0">
              <el-tag 
                v-for="(target, index) in row.proxy_targets" 
                :key="index" 
                size="small" 
                class="mr-1 mb-1"
                :type="target.status === 'down' ? 'info' : 'success'"
              >
                {{ target.ip }}:{{ target.port }}
                <span v-if="target.status === 'down'" class="ml-1">(禁用)</span>
              </el-tag>
            </div>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="Nginx节点" min-width="140">
          <template #default="{ row }">
            {{ row.nginx_node?.ip || "-" }}
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="150" show-overflow-tooltip />
        <el-table-column fixed="right" label="操作" width="280" align="center">
          <template #default="{ row }">
            <el-button
              type="info"
              link
              size="small"
              icon="document"
              @click="handleOpenDialog('detail', row.id)"
              v-hasPerm="['operations:nginx_upstream:query']"
            >
              详情
            </el-button>
            <el-button
              type="primary"
              link
              size="small"
              icon="edit"
              @click="handleOpenDialog('update', row.id)"
              v-hasPerm="['operations:nginx_upstream:update']"
            >
              编辑
            </el-button>
            <el-button
              type="warning"
              link
              size="small"
              icon="upload"
              @click="handleSync([row.id!])"
              v-hasPerm="['operations:nginx_upstream:sync']"
            >
              同步
            </el-button>
            <el-button
              type="danger"
              link
              size="small"
              icon="delete"
              @click="handleDelete([row.id!])"
              v-hasPerm="['operations:nginx_upstream:delete']"
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

    <!-- 创建/编辑/详情对话框 -->
    <el-dialog
      v-model="dialog.visible"
      :title="dialog.title"
      width="800px"
      destroy-on-close
      @close="handleDialogClose"
    >
      <template v-if="dialog.type === 'detail'">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="Upstream名称">
            {{ upstreamDetail?.upstream || "-" }}
          </el-descriptions-item>
          <el-descriptions-item label="Nginx节点">
            {{ upstreamDetail?.nginx_node?.ip || "-" }}
          </el-descriptions-item>
          <el-descriptions-item label="代理目标" :span="2">
            <div v-if="upstreamDetail?.proxy_targets && upstreamDetail.proxy_targets.length > 0">
              <el-tag 
                v-for="(target, index) in upstreamDetail.proxy_targets" 
                :key="index" 
                class="mr-2 mb-2"
                :type="target.status === 'down' ? 'info' : 'success'"
              >
                {{ target.ip }}:{{ target.port }}
                <span v-if="target.status === 'down'" class="ml-1">(禁用)</span>
              </el-tag>
            </div>
            <span v-else>-</span>
          </el-descriptions-item>
          <el-descriptions-item label="Upstream模板" :span="2">
            <pre style="white-space: pre-wrap; word-break: break-all;">{{ upstreamDetail?.upstream_template || "-" }}</pre>
          </el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">
            {{ upstreamDetail?.description || "-" }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间" :span="2">
            {{ upstreamDetail?.created_at || "-" }}
          </el-descriptions-item>
        </el-descriptions>
      </template>
      <div v-else>
        <el-form ref="upstreamFormRef" :model="upstreamForm" :rules="upstreamRules" label-width="120px" label-suffix=":">
          <el-form-item label="Upstream名称" prop="upstream">
            <el-input v-model="upstreamForm.upstream" placeholder="请输入upstream名称（如：api_upstream）" />
          </el-form-item>
          <el-form-item label="Nginx节点" prop="nginx_node_id">
            <el-select
              v-model="(upstreamForm as any).nginx_node_ids"
              placeholder="请选择Nginx节点（可多选）"
              multiple
              clearable
              style="width: 100%"
            >
              <el-option
                v-for="node in nginxNodeOptions"
                :key="node.id!"
                :label="`${node.ip}:${node.port}`"
                :value="node.id!"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="代理目标" prop="proxy_targets">
            <div class="proxy-targets-container">
              <el-table :data="upstreamForm.proxy_targets || []" border :style="{ width: '100%' }" max-height="300">
                <el-table-column type="index" label="#" width="60" align="center" />
                <el-table-column label="IP地址" width="160">
                  <template #default="{ row, $index }">
                    <el-input v-model="row.ip" placeholder="请输入IP地址" />
                  </template>
                </el-table-column>
                <el-table-column label="端口" width="100">
                  <template #default="{ row, $index }">
                    <el-input-number v-model="row.port" :min="1" :max="65535" controls-position="right" style="width: 100%" />
                  </template>
                </el-table-column>
                <el-table-column label="状态" width="100" align="center">
                  <template #default="{ row }">
                    <el-select v-model="row.status" placeholder="状态" style="width: 100%">
                      <el-option label="启用" value="up" />
                      <el-option label="禁用" value="down" />
                    </el-select>
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
                      :disabled="upstreamForm.proxy_targets && upstreamForm.proxy_targets.length <= 1"
                    >
                      删除
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div class="mt-2 flex gap-2">
                <el-button type="primary" plain icon="plus" size="small" @click="handleAddTarget">
                  添加代理目标
                </el-button>
                <el-button type="success" plain icon="Connection" size="small" @click="handleAddServiceNodes">
                  从服务模块添加
                </el-button>
              </div>
            </div>
          </el-form-item>
          <el-form-item label="Upstream模板" prop="upstream_template">
            <el-input
              v-model="upstreamForm.upstream_template"
              type="textarea"
              :rows="8"
              placeholder="Jinja2模板格式，留空使用默认模板"
            />
            <div class="flex justify-between items-center mt-1">
              <div class="text-xs text-gray-500">
              提示：支持Jinja2模板语法，变量：service_name（服务名）、hosts（代理目标列表，包含ip、port、status字段）
              </div>
              <el-button
                type="primary"
                link
                size="small"
                icon="View"
                @click="handlePreviewTemplate"
                :disabled="!upstreamForm.upstream_template || !upstreamForm.upstream || !upstreamForm.proxy_targets || upstreamForm.proxy_targets.length === 0"
              >
                预览模板
              </el-button>
            </div>
          </el-form-item>
          <el-form-item label="描述" prop="description">
            <el-input
              v-model="upstreamForm.description"
              type="textarea"
              :rows="3"
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

    <!-- 服务模块选择对话框 -->
    <el-dialog
      v-model="serviceSelectDialog.visible"
      title="选择服务模块"
      width="500px"
      destroy-on-close
    >
      <el-form label-width="120px" label-suffix=":">
        <el-form-item label="服务模块">
          <el-select
            v-model="serviceSelectDialog.serviceId"
            placeholder="请选择服务模块"
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="service in serviceOptions"
              :key="service.id!"
              :label="service.name"
              :value="service.id!"
              :disabled="!service.nodes || service.nodes.length === 0"
            >
              <span>{{ service.name }}</span>
              <span class="text-xs text-gray-400 ml-2">
                ({{ service.nodes?.length || 0 }}个节点)
              </span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-alert
          v-if="serviceSelectDialog.serviceId"
          :title="getServiceNodesPreview(serviceSelectDialog.serviceId)"
          type="info"
          :closable="false"
          class="mb-4"
        />
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="serviceSelectDialog.visible = false">取消</el-button>
          <el-button
            type="primary"
            @click="handleConfirmAddServiceNodes"
            :disabled="!serviceSelectDialog.serviceId"
          >
            确认添加
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 模板预览对话框 -->
    <el-dialog
      v-model="templatePreviewDialog.visible"
      title="Upstream模板预览"
      width="800px"
      destroy-on-close
    >
      <div class="preview-container">
        <el-alert
          v-if="templatePreviewDialog.error"
          :title="templatePreviewDialog.error"
          type="error"
          :closable="false"
          class="mb-4"
        />
        <div v-else>
          <div class="mb-4">
            <h4 class="text-sm font-semibold mb-2">渲染结果：</h4>
            <el-input
              :model-value="templatePreviewDialog.content"
              type="textarea"
              :rows="12"
              readonly
              class="font-mono text-sm"
            />
          </div>
          <div class="text-xs text-gray-500">
            <h4 class="text-sm font-semibold mb-2">模板变量：</h4>
            <pre class="bg-gray-50 p-3 rounded">{{ JSON.stringify(templatePreviewDialog.vars, null, 2) }}</pre>
          </div>
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="templatePreviewDialog.visible = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from "element-plus";
import NginxUpstreamAPI, {
  type NginxUpstreamForm,
  type NginxUpstreamPageQuery,
  type NginxUpstreamTable,
  type ProxyTarget,
  type PreviewTemplateRequest,
} from "@/api/operations/nginx_upstream";
import NodeAPI, { type NodeTable, type ServiceTable } from "@/api/operations/node";

// 对话框类型
type DialogType = "create" | "update" | "detail";

const loading = ref(false);
const dialogLoading = ref(false);
const tableData = ref<NginxUpstreamTable[]>([]);
const total = ref(0);
const selectionIds = ref<number[]>([]);

const nginxNodeOptions = ref<NodeTable[]>([]);
const serviceOptions = ref<ServiceTable[]>([]);

const queryFormRef = ref<FormInstance>();
const queryFormData = reactive<NginxUpstreamPageQuery>({
  page_no: 1,
  page_size: 10,
  upstream: "",
  nginx_node_id: undefined,
});

const dialog = reactive({
  visible: false,
  title: "",
  type: "create" as DialogType,
  targetId: undefined as number | undefined,
});

const serviceSelectDialog = reactive({
  visible: false,
  serviceId: undefined as number | undefined,
});

const templatePreviewDialog = reactive({
  visible: false,
  content: "",
  vars: {} as any,
  error: "",
});

const upstreamFormRef = ref<FormInstance>();
const upstreamForm = reactive<NginxUpstreamForm & { nginx_node_ids?: number[] }>({
  upstream: "",
  proxy_targets: [{ ip: "", port: 80, service_id: undefined, status: "up" }],
  nginx_node_id: undefined,
  nginx_node_ids: [],
  upstream_template: `upstream {{ service_name }}_upstream {
{% for host in hosts %}
    server {{ host.ip }}:{{ host.port }}{% if host.status == 'down' %} down{% endif %};
{% endfor %}
}`,
  description: "",
});

const upstreamDetail = ref<NginxUpstreamTable>();

const upstreamRules: FormRules<NginxUpstreamForm> = {
  upstream: [
    { required: true, message: "请输入upstream名称", trigger: "blur" },
    { pattern: /^[A-Za-z][A-Za-z0-9_-]*$/, message: "upstream名称必须以字母开头，且仅包含字母/数字/下划线/横线", trigger: "blur" },
  ],
  nginx_node_id: [
    {
      validator: (rule, value, callback) => {
        const nodeIds = (upstreamForm as any).nginx_node_ids;
        if (!nodeIds || nodeIds.length === 0) {
          callback(new Error("请至少选择一个Nginx节点"));
          return;
        }
        callback();
      },
      trigger: "change",
    },
  ],
  proxy_targets: [
    {
      validator: (rule, value, callback) => {
        if (!value || value.length === 0) {
          callback(new Error("请至少添加一个代理目标"));
          return;
        }
        for (const target of value) {
          if (!target.ip || !target.port) {
            callback(new Error("请填写完整的代理目标信息"));
            return;
          }
          const ipPattern = /^(\d{1,3}\.){3}\d{1,3}$/;
          if (!ipPattern.test(target.ip)) {
            callback(new Error(`IP地址 ${target.ip} 格式不正确`));
            return;
          }
        }
        callback();
      },
      trigger: "blur",
    },
  ],
};

// 加载Nginx节点选项（只加载配置了nginx服务的节点）
async function loadNginxNodeOptions() {
  try {
    const response = await NodeAPI.getNodePage({ page_no: 1, page_size: 1000, status: true });
    const allNodes = response.data.data?.items || [];
    // 筛选出配置了nginx服务的节点
    nginxNodeOptions.value = allNodes.filter((node) =>
      node.services?.some((service) => service.module_group?.toLowerCase().includes("nginx"))
    );
  } catch (error: any) {
    console.error(error);
  }
}

// 加载服务模块选项（带endpoint_port的）
async function loadServiceOptions() {
  try {
    const response = await NodeAPI.getServiceTree({ status: true });
    serviceOptions.value = response.data.data || [];
  } catch (error: any) {
    console.error(error);
  }
}

async function loadData() {
  loading.value = true;
  try {
    const response = await NginxUpstreamAPI.getUpstreamPage(queryFormData);
    const result = response.data.data;
    tableData.value = result.items || [];
    total.value = result.total || 0;
  } catch (error: any) {
    console.error(error);
  } finally {
    loading.value = false;
  }
}

function handleSelectionChange(selection: NginxUpstreamTable[]) {
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
  upstreamForm.upstream = "";
  upstreamForm.proxy_targets = [{ ip: "", port: 80, service_id: undefined, status: "up" }];
  upstreamForm.nginx_node_id = undefined;
  (upstreamForm as any).nginx_node_ids = [];
  upstreamForm.upstream_template = `upstream {{ service_name }}_upstream {
{% for host in hosts %}
    server {{ host.ip }}:{{ host.port }}{% if host.status == 'down' %} down{% endif %};
{% endfor %}
}`;
  upstreamForm.description = "";
}

function handleAddTarget() {
  if (!upstreamForm.proxy_targets) {
    upstreamForm.proxy_targets = [];
  }
  upstreamForm.proxy_targets.push({ ip: "", port: 80, service_id: undefined, status: "up" });
}

function handleRemoveTarget(index: number) {
  if (upstreamForm.proxy_targets && upstreamForm.proxy_targets.length > 1) {
    upstreamForm.proxy_targets.splice(index, 1);
  }
}

// 打开服务模块选择对话框
function handleAddServiceNodes() {
  serviceSelectDialog.visible = true;
  serviceSelectDialog.serviceId = undefined;
}

// 获取服务模块节点预览信息
function getServiceNodesPreview(serviceId?: number): string {
  if (!serviceId) return "";
  const service = serviceOptions.value.find((s) => s.id === serviceId);
  if (!service || !service.nodes || service.nodes.length === 0) {
    return "该服务模块没有关联的节点";
  }
  const nodes = service.nodes.map((node) => `${node.ip}:${node.port || 22}`).join(", ");
  return `将添加 ${service.nodes.length} 个节点: ${nodes}`;
}

// 确认添加服务模块的节点
function handleConfirmAddServiceNodes() {
  if (!serviceSelectDialog.serviceId) return;

  const service = serviceOptions.value.find((s) => s.id === serviceSelectDialog.serviceId);
  if (!service || !service.nodes || service.nodes.length === 0) {
    ElMessage.warning("该服务模块没有关联的节点");
    return;
  }

  // 确保 proxy_targets 已初始化
  if (!upstreamForm.proxy_targets) {
    upstreamForm.proxy_targets = [];
  }

  // 获取服务的 endpoint_port（如果配置了）
  const endpointPort = (service as any).endpoint_port;

  // 添加服务模块下的所有节点
  service.nodes.forEach((node) => {
    // 检查是否已存在相同的IP和端口
    const exists = upstreamForm.proxy_targets!.some(
      (target) => target.ip === node.ip && target.port === (endpointPort || node.port || 22)
    );
    if (!exists) {
      upstreamForm.proxy_targets!.push({
        ip: node.ip || "",
        port: endpointPort || node.port || 22,
        service_id: service.id,
        status: "up",
      });
    }
  });

  ElMessage.success(`已添加 ${service.nodes.length} 个节点到代理目标`);
  serviceSelectDialog.visible = false;
  serviceSelectDialog.serviceId = undefined;
}

// 预览模板
async function handlePreviewTemplate() {
  if (!upstreamForm.upstream_template || !upstreamForm.upstream || !upstreamForm.proxy_targets || upstreamForm.proxy_targets.length === 0) {
    ElMessage.warning("请填写完整的upstream名称、模板和代理目标");
    return;
  }

  // 验证代理目标是否完整
  const incompleteTargets = upstreamForm.proxy_targets.filter((target) => !target.ip || !target.port);
  if (incompleteTargets.length > 0) {
    ElMessage.warning("请填写完整的代理目标信息（IP和端口）");
    return;
  }

  templatePreviewDialog.visible = true;
  templatePreviewDialog.content = "";
  templatePreviewDialog.vars = {};
  templatePreviewDialog.error = "";

  try {
    const requestData: PreviewTemplateRequest = {
      upstream: upstreamForm.upstream,
      upstream_template: upstreamForm.upstream_template,
      proxy_targets: upstreamForm.proxy_targets.filter((target) => target.ip && target.port),
    };

    const response = await NginxUpstreamAPI.previewTemplate(requestData);
    templatePreviewDialog.content = response.data.data.rendered_content;
    templatePreviewDialog.vars = response.data.data.template_vars;
  } catch (error: any) {
    console.error("预览模板失败:", error);
    templatePreviewDialog.error = error.response?.data?.msg || error.message || "预览模板失败";
  }
}

async function handleOpenDialog(type: DialogType, id?: number) {
  dialog.type = type;
  dialog.targetId = id;
  dialog.visible = true;
  dialog.title =
    type === "create"
      ? "新增Nginx Upstream"
      : type === "update"
      ? "编辑Nginx Upstream"
      : "Nginx Upstream详情";

  if (type === "create") {
    resetForm();
    upstreamDetail.value = undefined;
    return;
  }

  if (!id) return;
  loading.value = true;
  try {
    const response = await NginxUpstreamAPI.getUpstreamDetail(id);
    const detail = response.data.data;
    upstreamDetail.value = detail;
    if (type === "update") {
      upstreamForm.id = detail.id;
      upstreamForm.upstream = detail.upstream || "";
      // 确保proxy_targets中每个目标都有status字段（兼容旧数据）
      upstreamForm.proxy_targets = (detail.proxy_targets || [{ ip: "", port: 80, service_id: undefined, status: "up" }]).map(target => ({
        ...target,
        status: target.status || "up"
      }));
      upstreamForm.nginx_node_id = detail.nginx_node_id;
      (upstreamForm as any).nginx_node_ids = detail.nginx_node_id ? [detail.nginx_node_id] : [];
      upstreamForm.upstream_template = detail.upstream_template || `upstream {{ service_name }}_upstream {
{% for host in hosts %}
    server {{ host.ip }}:{{ host.port }}{% if host.status == 'down' %} down{% endif %};
{% endfor %}
}`;
      upstreamForm.description = detail.description || "";
    }
  } catch (error: any) {
    console.error(error);
  } finally {
    loading.value = false;
  }
}

function handleDialogClose() {
  dialog.targetId = undefined;
  upstreamDetail.value = undefined;
  upstreamFormRef.value?.clearValidate();
}

function handleSubmit() {
  upstreamFormRef.value?.validate(async (valid) => {
    if (!valid) return;
    
    const nodeIds = (upstreamForm as any).nginx_node_ids || [];
    if (nodeIds.length === 0) {
      ElMessage.warning("请至少选择一个Nginx节点");
      return;
    }
    
    dialogLoading.value = true;
    try {
      if (dialog.type === "create") {
        // 去重nginx节点ID
        const uniqueNodeIds = Array.from(new Set(nodeIds));
        
        console.log(`[NginxUpstream] 开始创建upstream: ${upstreamForm.upstream}, 节点数量: ${uniqueNodeIds.length}`);
        
        // 为每个选中的节点创建一个upstream记录
        const results = await Promise.allSettled(
          uniqueNodeIds.map(async (nodeId: number) => {
            const formData = {
              ...upstreamForm,
              nginx_node_id: nodeId,
            };
            // 移除nginx_node_ids字段
            delete (formData as any).nginx_node_ids;
            
            console.log(`[NginxUpstream] 创建upstream: ${upstreamForm.upstream}, nginx_node_id: ${nodeId}`);
            return NginxUpstreamAPI.createUpstream(formData);
          })
        );
        
        // 统计成功和失败的数量
        const successCount = results.filter(r => r.status === 'fulfilled').length;
        const failedCount = results.filter(r => r.status === 'rejected').length;
        
        console.log(`[NginxUpstream] 创建完成: 成功=${successCount}, 失败=${failedCount}`);
        
        if (failedCount > 0) {
          // 显示失败的详细信息
          const failedReasons = results
            .filter(r => r.status === 'rejected')
            .map((r: any) => r.reason?.response?.data?.msg || r.reason?.message || '未知错误')
            .join('; ');
          
          if (successCount > 0) {
            ElMessage.warning(`部分创建成功：${successCount} 个成功，${failedCount} 个失败。失败原因：${failedReasons}`);
          } else {
            ElMessage.error(`创建失败：${failedReasons}`);
          }
        } else {
          ElMessage.success(`成功创建 ${successCount} 个Nginx Upstream`);
        }
        
        if (successCount > 0) {
          dialog.visible = false;
          loadData();
        }
      } else if (dialog.targetId) {
        // 更新时只使用第一个节点（保持原有逻辑）
        const formData = {
          ...upstreamForm,
          nginx_node_id: nodeIds[0],
        };
        delete (formData as any).nginx_node_ids;
        await NginxUpstreamAPI.updateUpstream(dialog.targetId, formData);
        ElMessage.success("更新Nginx Upstream成功");
        dialog.visible = false;
        loadData();
      }
    } catch (error: any) {
      console.error('[NginxUpstream] 提交失败:', error);
    } finally {
      dialogLoading.value = false;
    }
  });
}

async function handleSync(ids: number[]) {
  if (!ids.length) return;
  try {
    await ElMessageBox.confirm("确认同步所选Upstream配置到Nginx节点吗？", "提示", {
      type: "warning",
    });
    await NginxUpstreamAPI.syncUpstream({ upstream_ids: ids });
    ElMessage.success("同步任务已创建");
    loadData();
  } catch (error: any) {
    if (error !== "cancel") {
      console.error(error);
    }
  }
}

async function handleBatchSync() {
  if (!selectionIds.value.length) return;
  await handleSync(selectionIds.value);
}

async function handleDelete(ids: number[]) {
  if (!ids.length) return;
  try {
    await ElMessageBox.confirm("确认删除所选Nginx Upstream吗？此操作不可恢复", "提示", {
      type: "warning",
    });
    await NginxUpstreamAPI.deleteUpstream(ids);
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
  Promise.all([loadNginxNodeOptions(), loadServiceOptions(), loadData()]);
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

.proxy-targets-container {
  width: 100%;
}
</style>

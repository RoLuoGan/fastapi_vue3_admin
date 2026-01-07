<!-- 服务节点管理 -->
<template>
  <div class="app-container">
    <div class="flex gap-4">
      <!-- 左侧表格区域 -->
      <div class="flex-1">
        <!-- 搜索区域 -->
        <div class="search-container">
          <el-form ref="queryFormRef" :model="queryFormData" :inline="true" label-suffix=":" @submit.prevent="handleQuery">
            <el-form-item prop="name" label="服务名称">
              <el-input v-model="queryFormData.name" placeholder="请输入服务名称" clearable />
            </el-form-item>
            <el-form-item prop="status" label="状态">
              <el-select v-model="queryFormData.status" placeholder="请选择状态" style="width: 167.5px" clearable>
                <el-option value="true" label="启用" />
                <el-option value="false" label="停用" />
              </el-select>
            </el-form-item>
            <el-form-item prop="project" label="运维管理项目">
              <el-select v-model="queryFormData.project" placeholder="请选择运维管理项目" style="width: 167.5px" clearable>
                <el-option v-for="item in projectOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value" />
              </el-select>
            </el-form-item>
            <el-form-item prop="module_group" label="模块分组">
              <el-select v-model="queryFormData.module_group" placeholder="请选择模块分组" style="width: 167.5px" clearable>
                <el-option v-for="item in moduleGroupOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value" />
              </el-select>
            </el-form-item>
            <el-form-item class="search-buttons">
              <el-button v-hasPerm="['operations:node:query']" type="primary" icon="search" native-type="submit">查询</el-button>
              <el-button v-hasPerm="['operations:node:query']" icon="refresh" @click="handleResetQuery">重置</el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- 内容区域 -->
        <el-card class="data-table">
          <template #header>
            <div class="card-header">
              <span>
                <el-tooltip content="服务节点管理维护系统的服务模块和节点信息。">
                  <QuestionFilled class="w-4 h-4 mx-1" />
                </el-tooltip>
                服务节点列表
              </span>
            </div>
          </template>

          <!-- 功能区域 -->
          <div class="data-table__toolbar">
            <div class="data-table__toolbar--left">
              <el-row :gutter="10">
                <el-col :span="1.5">
                  <el-button v-hasPerm="['operations:node:deploy']" type="warning" icon="Upload" :disabled="selectNodeIds.length === 0" @click="handleDeploy">部署</el-button>
                </el-col>
                <el-col :span="1.5">
                  <el-button v-hasPerm="['operations:node:restart']" type="info" icon="RefreshRight" :disabled="selectNodeIds.length === 0" @click="handleRestart">重启</el-button>
                </el-col>
                <el-col :span="1.5">
                  <el-button v-hasPerm="['operations:node:start']" type="success" icon="VideoPlay" :disabled="selectNodeIds.length === 0" @click="handleStart">启动</el-button>
                </el-col>
                <el-col :span="1.5">
                  <el-button v-hasPerm="['operations:node:stop']" type="danger" icon="VideoPause" :disabled="selectNodeIds.length === 0" @click="handleStop">停止</el-button>
                </el-col>
                <el-col :span="1.5">
                  <el-button type="primary" icon="ArrowDown" plain @click="handleExpandAll">全部展开</el-button>
                </el-col>
                <el-col :span="1.5">
                  <el-button type="primary" icon="ArrowUp" plain @click="handleCollapseAll">全部折叠</el-button>
                </el-col>
              </el-row>
            </div>
            <div class="data-table__toolbar--right">
              <el-row :gutter="10">
                <el-col :span="1.5">
                  <el-tooltip content="刷新">
                    <el-button v-hasPerm="['operations:node:refresh']" type="primary" icon="refresh" circle @click="handleRefresh" />
                  </el-tooltip>
                </el-col>
              </el-row>
            </div>
          </div>

          <!-- 表格区域：树形表格 -->
          <el-table 
            ref="dataTableRef" 
            v-loading="loading" 
            :row-key="getRowKey" 
            :data="pageTableData" 
            :tree-props="{children: 'nodes', hasChildren: 'hasChildren'}" 
            class="data-table__content" 
            height="600" 
            border 
            stripe 
            @select="handleSelect"
            @select-all="handleSelectAll"
            @selection-change="handleSelectionChange"
          >
            <template #empty>
              <el-empty :image-size="80" description="暂无数据" />
            </template>
            <el-table-column type="selection" min-width="55" align="center" />
            <el-table-column type="index" fixed label="序号" min-width="60" />
            <el-table-column label="项目" prop="project" min-width="120">
              <template #default="scope">
                <span v-if="scope.row.nodes">{{ scope.row.project || '-' }}</span>
                <span v-else>{{ scope.row.project || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="模块分组" prop="module_group" min-width="120">
              <template #default="scope">
                <span v-if="scope.row.nodes">{{ scope.row.module_group || '-' }}</span>
                <span v-else>{{ scope.row.module_group || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="名称/IP" prop="name" min-width="180">
              <template #default="scope">
                <span v-if="scope.row.nodes">{{ scope.row.name }}</span>
                <span v-else>{{ scope.row.ip }}</span>
              </template>
            </el-table-column>
            <el-table-column label="ssh端口" prop="port" min-width="80">
              <template #default="scope">
                <span v-if="!scope.row.nodes">{{ scope.row.port || '-' }}</span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column label="服务端口" prop="endpoint_port" min-width="100">
              <template #default="scope">
                <span v-if="scope.row.nodes">{{ scope.row.endpoint_port ?? '-' }}</span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column label="当前模块软件包版本号" prop="current_package_version" min-width="180">
              <template #default="scope">
                <span v-if="scope.row.nodes">{{ scope.row.current_package_version || '-' }}</span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" prop="status" min-width="80">
              <template #default="scope">
                <el-tag :type="scope.row.status === true ? 'success' : 'danger'">
                  {{ scope.row.status === true ? "启用" : "停用" }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="描述" prop="description" min-width="150" show-overflow-tooltip />
            <el-table-column label="创建时间" prop="created_at" min-width="180" />
          </el-table>
        </el-card>
      </div>

      <!-- 右侧任务进度栏 -->
      <div class="w-80">
        <el-card>
          <template #header>
            <div class="card-header flex justify-between items-center">
              <span>任务进度</span>
              <el-button text type="primary" icon="refresh" @click="loadRecentTasks">刷新</el-button>
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

    <!-- 部署确认弹窗 -->
    <el-dialog v-model="deployDialog.visible" title="部署确认" width="700px" append-to-body>
      <el-table :data="deployDialog.data" border stripe>
        <el-table-column prop="service_name" label="部署模块" />
        <el-table-column label="当前版本号">
           <template #default="{ row }">
              <el-select v-model="row.version" placeholder="请选择版本" :loading="row.loading" @visible-change="(val) => handleVersionVisibleChange(val, row)">
                 <el-option v-for="ver in row.versions" :key="ver.id" :label="ver.version" :value="ver.version" />
              </el-select>
           </template>
        </el-table-column>
        <el-table-column prop="node_count" label="部署节点数" />
      </el-table>
      <div class="mt-4 flex justify-end gap-8 text-sm">
         <span>汇总:</span>
         <span>部署总模块数: {{ deployDialog.data.length }}</span>
         <span>部署总节点数: {{ deployTotalNodes }}</span>
      </div>
      <template #footer>
        <el-button @click="deployDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="confirmDeploy" :loading="loading">确定部署</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: "OperationsNode",
  inheritAttrs: false,
});

import NodeAPI, { ServiceTable, TaskTable, ServiceQueryParam } from "@/api/operations/node";
import ServicePackageAPI from "@/api/operations/service_package";
import { useRouter } from "vue-router";
import { QuestionFilled, CircleCheck, CircleClose, Loading, WarningFilled, ArrowDown, ArrowUp, VideoPlay, VideoPause, Close } from "@element-plus/icons-vue";
import DictAPI from "@/api/system/dict";
import { onBeforeUnmount } from "vue";

// 操作元数据类型定义
interface PageOperatorMeta {
  service_id: number;
  service_name?: string;
  node_ids: number[];
  nodes?: { id: number; ip: string; port?: number }[];
  [key: string]: any;
}

type TaskTagType = "primary" | "success" | "warning" | "info" | "danger";

const queryFormRef = ref();
const dataTableRef = ref();
const total = ref(0);
const selectIds = ref<number[]>([]);
const selectNodeIds = ref<number[]>([]);
const loading = ref(false);
// 防止选择事件递归
const isHandlingSelection = ref(false);

// 分页表单
const pageTableData = ref<ServiceTable[]>([]);

// 查询参数
const queryFormData = reactive<ServiceQueryParam>({
  name: undefined,
  status: undefined,
  project: undefined,
  module_group: undefined,
});

// 部署确认弹窗状态
const deployDialog = reactive({
  visible: false,
  data: [] as any[]
});
const deployTotalNodes = computed(() => {
    return deployDialog.data.reduce((sum, item) => sum + (item.node_count || 0), 0);
});

// 服务模块选项（用于节点表单）
const serviceOptions = ref<ServiceTable[]>([]);

// 任务列表
const taskList = ref<TaskTable[]>([]);
const router = useRouter();
const supportedTaskTypes = ["deploy", "restart", "start", "stop"];

// 子节点联动标志（防止父节点取消子节点时的连锁反应）
const isChildLinkage = ref(false);

// 字典选项
const projectOptions = ref<any[]>([]);
const moduleGroupOptions = ref<any[]>([]);
const idcOptions = ref<any[]>([]);
const tagsOptions = ref<any[]>([]);

/**
 * 生成行的唯一Key（解决父子节点ID冲突问题）
 * 父节点：service_${id}
 * 子节点：node_${composite_id} (composite_id格式：模块ID_节点ID)
 */
function getRowKey(row: any): string {
  if (row.nodes && Array.isArray(row.nodes)) {
    // 父节点（服务模块）
    return `service_${row.id}`;
  } else {
    // 子节点（IP节点）- 使用复合ID（模块ID_节点ID）防止不同模块下相同节点ID冲突
    if (row.composite_id) {
      return `node_${row.composite_id}`;
    }
    // 兼容处理：如果没有composite_id，使用原始ID（不应该出现这种情况）
    return `node_${row.id}`;
  }
}

// 选择行（单行选择）
async function handleSelect(selection: any[], row: any) {
  const rowKey = getRowKey(row);
  console.log('===== handleSelect 开始 =====');
  console.log('当前点击行:', {
    rowKey: rowKey,
    id: row.id,
    name: row.name,
    ip: row.ip,
    hasNodes: !!row.nodes,
    nodesCount: row.nodes?.length || 0
  });
  console.log('当前选中项数量:', selection.length);
  console.log('当前选中项:', selection.map((s: any) => ({ 
    rowKey: getRowKey(s),
    id: s.id, 
    name: s.name || s.ip 
  })));
  
  // 防止递归调用
  if (isHandlingSelection.value) {
    console.log('正在处理中，跳过递归调用');
    return;
  }
  
  isHandlingSelection.value = true;
  try {
    // 等待 DOM 更新，确保获取到正确的选中状态
    await nextTick();
    
    if (row.nodes) {
      console.log('检测到父节点（服务模块）:', row.name);
      
      // 重新获取最新的选中状态，使用rowKey比较
      const currentSelection = dataTableRef.value?.getSelectionRows() || [];
      const isSelected = currentSelection.some((item: any) => getRowKey(item) === rowKey);
      
      console.log('父节点最新选中状态:', isSelected);
      console.log('最新选中项:', currentSelection.map((s: any) => ({ 
        rowKey: getRowKey(s),
        id: s.id, 
        name: s.name || s.ip 
      })));
      
      if (isSelected) {
        console.log('✓ 选中父节点，将选中所有子节点:', row.nodes.map((n: any) => n.ip));
        // 选中该模块下的所有节点
        row.nodes?.forEach((node: any) => {
          console.log('  - 选中子节点:', node.ip, '(Key:', getRowKey(node), 'ID:', node.id, ')');
          dataTableRef.value?.toggleRowSelection(node, true);
        });
      } else {
        console.log('✗ 取消父节点');
        // 如果是子节点联动导致的取消，不要取消子节点（避免连锁反应）
        if (isChildLinkage.value) {
          console.log('  检测到子节点联动标志，跳过取消子节点操作，避免连锁反应');
        } else {
          console.log('  将取消所有子节点:', row.nodes.map((n: any) => n.ip));
          // 取消选择时，取消该模块下所有节点的选择
          // 但需要检查每个子节点是否真的需要取消（避免取消用户单独选中的子节点）
          const currentSelection = dataTableRef.value?.getSelectionRows() || [];
          row.nodes?.forEach((node: any) => {
            const nodeKey = getRowKey(node);
            const isNodeSelected = currentSelection.some((item: any) => getRowKey(item) === nodeKey);
            if (isNodeSelected) {
              console.log('  - 取消子节点:', node.ip, '(Key:', nodeKey, 'ID:', node.id, ')');
              dataTableRef.value?.toggleRowSelection(node, false);
            } else {
              console.log('  - 子节点已处于未选中状态，跳过:', node.ip);
            }
          });
        }
      }
    } else {
      console.log('检测到子节点（IP节点）:', row.ip);
      
      // 使用 selection 参数判断子节点是否被选中（这是 Element Plus 传递的最新状态）
      const isChildSelected = selection.some((item: any) => getRowKey(item) === rowKey);
      
      console.log('子节点选中状态（从selection参数）:', isChildSelected);
      console.log('当前所有选中项（从selection参数）:', selection.map((s: any) => ({ 
        rowKey: getRowKey(s),
        id: s.id, 
        name: s.name || s.ip 
      })));
      
      // 检查该子节点的父节点（需要比较完整的节点对象，因为ID可能重复）
      const parent = pageTableData.value.find((service: any) =>
        service.nodes && service.nodes.some((node: any) => 
          getRowKey(node) === rowKey
        )
      );
      
      if (parent && parent.nodes) {
        console.log('子节点所属父节点:', parent.name);
        
        // 等待 DOM 更新，确保选中状态已同步
        await nextTick();
        
        // 重新获取最新的选中状态（用于检查所有子节点）
        const currentSelection = dataTableRef.value?.getSelectionRows() || [];
        
        // 再次确认子节点是否在选中列表中（使用rowKey比较）
        const isChildReallySelected = currentSelection.some((item: any) => getRowKey(item) === rowKey);
        
        console.log('子节点实际选中状态（从getSelectionRows）:', isChildReallySelected);
        console.log('当前所有选中项（从getSelectionRows）:', currentSelection.map((s: any) => ({ 
          rowKey: getRowKey(s),
          id: s.id, 
          name: s.name || s.ip 
        })));
        
        // 检查父节点当前是否被选中
        const isParentSelected = currentSelection.some((item: any) => getRowKey(item) === getRowKey(parent));
        
        // 如果子节点确实被选中，才处理父节点
        if (isChildReallySelected) {
          // 检查该父节点下的所有子节点是否都被选中（使用rowKey比较）
          const allChildrenSelected = parent.nodes.every((child: any) =>
            currentSelection.some((item: any) => getRowKey(item) === getRowKey(child))
          );
          
          console.log('所有兄弟节点是否都选中:', allChildrenSelected);
          console.log('父节点当前选中状态:', isParentSelected);
          console.log('父节点下所有子节点状态:', parent.nodes.map((n: any) => ({
            ip: n.ip,
            id: n.id,
            composite_id: n.composite_id,
            rowKey: getRowKey(n),
            isSelected: currentSelection.some((item: any) => getRowKey(item) === getRowKey(n))
          })));
          
          if (allChildrenSelected) {
            // 所有子节点都选中，选中父节点（如果还没选中）
            if (!isParentSelected) {
              console.log('✓ 所有子节点已选中，自动选中父节点:', parent.name);
              dataTableRef.value?.toggleRowSelection(parent, true);
            }
          } else {
            // 不是所有子节点都选中，取消父节点（如果父节点当前是选中状态）
            // 设置子节点联动标志，防止父节点取消子节点时的连锁反应
            if (isParentSelected) {
              console.log('✗ 存在未选中的子节点，取消父节点:', parent.name);
              isChildLinkage.value = true;
              dataTableRef.value?.toggleRowSelection(parent, false);
              // 延迟重置标志，确保父节点的 handleSelect 能检测到
              setTimeout(() => {
                isChildLinkage.value = false;
              }, 50);
            } else {
              console.log('✗ 存在未选中的子节点，父节点已处于未选中状态，无需操作');
            }
          }
        } else {
          // 子节点没有被选中（可能是被取消了），确保父节点也被取消（如果父节点当前是选中状态）
          // 设置子节点联动标志，防止父节点取消子节点时的连锁反应
          if (isParentSelected) {
            console.log('✗ 子节点没有被选中，取消父节点:', parent.name);
            isChildLinkage.value = true;
            dataTableRef.value?.toggleRowSelection(parent, false);
            // 延迟重置标志，确保父节点的 handleSelect 能检测到
            setTimeout(() => {
              isChildLinkage.value = false;
            }, 50);
          } else {
            console.log('✗ 子节点没有被选中，父节点已处于未选中状态，无需操作');
          }
        }
      }
    }
    
    await updateSelectionState();
    console.log('===== handleSelect 结束 =====\n');
  } finally {
    isHandlingSelection.value = false;
  }
}

// 全选
async function handleSelectAll(selection: any[]) {
  console.log('===== handleSelectAll 开始 =====');
  console.log('全选操作，当前选中项数量:', selection.length);
  console.log('页面数据总数:', pageTableData.value.length);
  
  // 防止递归调用
  if (isHandlingSelection.value) {
    console.log('正在处理中，跳过递归调用');
    return;
  }
  
  isHandlingSelection.value = true;
  try {
    // 如果是全选，需要展开所有节点
    if (selection.length > 0) {
      console.log('执行全选操作');
      // 遍历所有服务模块，选中其下的所有节点
      pageTableData.value.forEach((service: any) => {
        console.log(`处理服务模块: ${service.name} (ID: ${service.id})`);
        if (service.nodes && service.nodes.length > 0) {
          console.log(`  子节点数量: ${service.nodes.length}`);
          service.nodes.forEach((node: any) => {
            const compositeId = node.composite_id ? ` (复合ID: ${node.composite_id})` : '';
            console.log(`  - 选中子节点: ${node.ip} (ID: ${node.id}${compositeId})`);
            dataTableRef.value?.toggleRowSelection(node, true);
          });
        } else {
          console.log('  该服务模块无子节点');
        }
      });
    } else {
      console.log('执行取消全选操作');
    }
    
    await updateSelectionState();
    console.log('===== handleSelectAll 结束 =====\n');
  } finally {
    isHandlingSelection.value = false;
  }
}

// 行选中变化（保留此函数用于其他可能的监听）
function handleSelectionChange() {
  console.log('[handleSelectionChange] 选择状态变化');
  updateSelectionState();
}

async function updateSelectionState() {
  console.log('[updateSelectionState] 开始更新选择状态');
  await nextTick();
  const selection =
    (typeof dataTableRef.value?.getSelectionRows === "function" && dataTableRef.value.getSelectionRows()) || [];
  
  console.log('[updateSelectionState] 当前选中的行数:', selection.length);
  console.log('[updateSelectionState] 选中的行详情:', selection.map((s: any) => ({ 
    id: s.id, 
    name: s.name || s.ip,
    type: s.nodes ? '父节点' : '子节点',
    isParent: !!s.nodes 
  })));
  
  selectIds.value = selection.map((item: any) => item.id);
  
  // 提取节点ID（前端已通过 getRowKey 处理ID冲突问题）
  const nodeIdSet = new Set<number>();
  selection.forEach((item: any) => {
    if (item?.nodes && Array.isArray(item.nodes)) {
      console.log(`  [父节点] ${item.name} (ID: ${item.id}) 包含 ${item.nodes.length} 个子节点:`);
      item.nodes.forEach((node: any) => {
        const compositeId = node.composite_id ? ` (复合ID: ${node.composite_id})` : '';
        console.log(`    └─ [子] ${node.ip} (ID: ${node.id}${compositeId})`);
        if (node?.id) {
          nodeIdSet.add(node.id);
        }
      });
    } else if (!item?.nodes && item?.id) {
      const compositeId = item.composite_id ? ` (复合ID: ${item.composite_id})` : '';
      console.log(`  [子节点] ${item.ip} (ID: ${item.id}${compositeId})`);
      nodeIdSet.add(item.id);
    }
  });
  selectNodeIds.value = Array.from(nodeIdSet);
  
  console.log('[updateSelectionState] 最终选中的节点ID列表:', selectNodeIds.value);
  console.log('[updateSelectionState] 最终选中的节点数量:', selectNodeIds.value.length);
  console.log('[updateSelectionState] 更新完成\n');
}

// 加载服务树数据
async function loadingData() {
  loading.value = true;
  try {
    const response = await NodeAPI.getServiceTree(queryFormData);
    // 接口返回的 nodes 已经通过多对多关系关联，直接使用即可
    const processedData = (response.data.data || []).map((service: any) => {
      // 确保 nodes 数组存在（即使为空也要保留）
      if (!service.nodes) {
        service.nodes = [];
      }
      // 为每个子节点生成复合ID（模块ID_节点ID），防止不同模块下相同节点ID冲突
      if (service.nodes && Array.isArray(service.nodes)) {
        service.nodes = service.nodes.map((node: any) => {
          // 生成复合ID：service_id_node_id
          node.composite_id = `${service.id}_${node.id}`;
          return node;
        });
      }
      // 为树形表格添加 hasChildren 属性
      service.hasChildren = service.nodes && service.nodes.length > 0;
      return service;
    });
    
    console.log('[数据加载] 数据加载成功，共 %d 个服务模块', processedData.length);
    // 调试：打印每个服务的节点数量
    processedData.forEach((service: any) => {
      const nodeCount = service.nodes?.length || 0;
      console.log(`  - ${service.name} (ID: ${service.id}): ${nodeCount} 个节点`);
      if (service.nodes && service.nodes.length > 0) {
        service.nodes.forEach((node: any) => {
          console.log(`    └─ ${node.ip} (节点ID: ${node.id}, 复合ID: ${node.composite_id})`);
        });
      }
    });
    pageTableData.value = processedData;
    // 同时加载服务选项
    await loadServiceOptions();
  } catch (error: any) {
    console.error(error);
  } finally {
    loading.value = false;
  }
}

// 加载服务选项
async function loadServiceOptions() {
  try {
    const response = await NodeAPI.getServiceTree({ status: true });
    serviceOptions.value = response.data.data || [];
  } catch (error: any) {
    console.error(error);
  }
}

// 加载字典选项
async function loadDictOptions() {
  try {
    const [projectRes, moduleGroupRes, idcRes, tagsRes] = await Promise.all([
      DictAPI.getInitDict("operations_project"),
      DictAPI.getInitDict("operations_module_group"),
      DictAPI.getInitDict("operations_idc"),
      DictAPI.getInitDict("operations_server_tags"),
    ]);
    projectOptions.value = projectRes.data.data || [];
    moduleGroupOptions.value = moduleGroupRes.data.data || [];
    idcOptions.value = idcRes.data.data || [];
    tagsOptions.value = tagsRes.data.data || [];
  } catch (error: any) {
    console.error(error);
  }
}

// 定时器ID
let recentTasksTimer: number | null = null;

/**
 * 停止定时刷新任务列表
 */
function stopRecentTasksRefresh() {
  if (recentTasksTimer !== null) {
    clearInterval(recentTasksTimer);
    recentTasksTimer = null;
  }
}

/**
 * 检查是否有正在运行的任务
 */
function hasRunningTasks(): boolean {
  return taskList.value.some(task => task.task_status === "running");
}

// 加载最近任务（只显示节点操作任务：部署/重启）
async function loadRecentTasks() {
  try {
    // 不传 task_type，后端会返回所有任务，前端可以过滤或显示全部
    const response = await NodeAPI.getRecentTasks(20);
    // 过滤出节点操作相关的任务（deploy、restart）
    const allTasks = response.data.data || [];
    taskList.value = allTasks.filter(
      (task: TaskTable) => !!task.task_type && supportedTaskTypes.includes(task.task_type)
    );
    
    // 检查是否有正在运行的任务，如果没有则停止定时刷新
    if (!hasRunningTasks()) {
      stopRecentTasksRefresh();
    }
  } catch (error: any) {
    console.error(error);
  }
}

// 查询
async function handleQuery() {
  loadingData();
}

// 重置查询
async function handleResetQuery() {
  queryFormRef.value.resetFields();
  loadingData();
}

// 刷新
async function handleRefresh() {
  await loadingData();
  await loadRecentTasks();
}


/**
 * 构建操作元数据（按服务模块分组节点）
 */
function buildOperatorMetas(nodeIds: number[]): PageOperatorMeta[] {
  const metaMap = new Map<number, number[]>();
  
  // 获取当前真正选中的行（使用 getSelectionRows 确保准确性）
  const currentSelection = dataTableRef.value?.getSelectionRows() || [];
  
  // 使用 getRowKey 来匹配节点，避免 ID 冲突问题
  const selectedRowKeys = new Set(currentSelection.map((row: any) => getRowKey(row)));
  
  console.log('[buildOperatorMetas] 当前选中的行数:', currentSelection.length);
  console.log('[buildOperatorMetas] 选中的行Key列表:', Array.from(selectedRowKeys));
  
  // 遍历所有服务模块
  const serviceMetaMap = new Map<number, { service_name: string; node_ids: number[]; nodes: any[]; project?: string; module_group?: string }>();
  
  pageTableData.value.forEach((service: any) => {
    if (service.nodes && Array.isArray(service.nodes)) {
      // 找出属于该服务的选中节点（使用 getRowKey 匹配，避免 ID 冲突）
      const selectedNodes = service.nodes.filter((node: any) => {
        const nodeKey = getRowKey(node);
        return selectedRowKeys.has(nodeKey);
      });
      
      const serviceNodeIds = selectedNodes.map((node: any) => node.id);
      
      if (serviceNodeIds.length > 0) {
        serviceMetaMap.set(service.id, {
          service_name: service.name || '',
          node_ids: serviceNodeIds,
          nodes: selectedNodes,
          project: service.project,
          module_group: service.module_group
        });
        console.log(`[buildOperatorMetas] 服务 ${service.name} (ID: ${service.id}) 包含 ${serviceNodeIds.length} 个选中节点: [${serviceNodeIds.join(', ')}]`);
      }
    }
  });
  
  // 转换为数组格式，包含 service_name 和每个节点的 ip 和 port
  const result = Array.from(serviceMetaMap.entries()).map(([service_id, meta]) => {
    // 构建节点信息列表，包含 ip 和 port
    const nodes = meta.nodes.map((node: any) => ({
      id: node.id,
      ip: node.ip || '',
      port: node.port || 22
    }));
    
    return {
      service_id,
      service_name: meta.service_name,
      node_ids: meta.node_ids,
      nodes: nodes,  // 添加节点信息，包含 ip 和 port
      project: meta.project,
      module_group: meta.module_group
    };
  });
  
  console.log('[buildOperatorMetas] 最终生成的操作元数据:', result);
  return result;
}

// 加载版本列表
async function loadVersions(row: any) {
    row.loading = true;
    try {
        const res = await ServicePackageAPI.getList({ service_id: row.service_id });
        row.versions = res.data.data || [];
        // 如果没有选版本且有版本，默认选中第一个（最新的）
        if (!row.version && row.versions.length > 0) {
            // 优先选当前版本
            if (row.current_version) {
                const found = row.versions.find((v: any) => v.version === row.current_version);
                if (found) {
                    row.version = found.version;
                } else {
                    row.version = row.versions[0].version;
                }
            } else {
                row.version = row.versions[0].version;
            }
        }
    } catch(e) {
        console.error(e);
    } finally {
        row.loading = false;
    }
}

function handleVersionVisibleChange(visible: boolean, row: any) {
    if (visible && (!row.versions || row.versions.length === 0)) {
        loadVersions(row);
    }
}

async function confirmDeploy() {
    // Validate
    for (const row of deployDialog.data) {
        if (!row.version) {
            ElMessage.warning(`请为 ${row.service_name} 选择版本`);
            return;
        }
    }
    
    loading.value = true;
    try {
        const operatorMetas = [];
        for (const row of deployDialog.data) {
            if (row.version) {
                const found = row.versions.find((v: any) => v.version === row.version);
                if (found) {
                    // 确保传递 service_name 和 nodes (包含IP和port)
                    const meta = {
                        service_id: row.service_id,
                        service_name: row.service_name || '',
                        node_ids: row.node_ids,
                        // 只传递必要的节点信息，避免传递多余字段或Proxy对象
                        nodes: row.nodes ? row.nodes.map((n: any) => ({ id: n.id, ip: n.ip, port: n.port || 22 })) : [], 
                        version: row.version,
                        package_path: found.package_path,
                        md5: found.md5,
                        project: row.project,
                        module_group: row.module_group
                    };
                    console.log('[confirmDeploy] Row Meta:', meta);
                    operatorMetas.push(meta);
                }
            }
        }
        
        console.log('[confirmDeploy] 提交的任务参数:', operatorMetas);

        const requestData: any = {
            task_type: 'node_operator',
            operator_type: 'deploy',
            operator_metas: operatorMetas
        };
        
        await NodeAPI.deploy(requestData);
        ElMessage.success('部署任务已提交');
        deployDialog.visible = false;
        handleRefresh();
        
        setTimeout(async () => {
            await loadRecentTasks();
            if (hasRunningTasks() && recentTasksTimer === null) {
              recentTasksTimer = window.setInterval(() => {
                loadRecentTasks();
              }, 5000);
            }
        }, 2000);
    } catch(e) {
        console.error(e);
    } finally {
        loading.value = false;
    }
}

// 部署
async function handleDeploy() {
  if (selectNodeIds.value.length === 0) {
    ElMessage.warning("请至少选择一个节点");
    return;
  }
  
  const operatorMetas = buildOperatorMetas(selectNodeIds.value);
  
  deployDialog.data = operatorMetas.map((meta: any) => {
      const service = pageTableData.value.find((s: any) => s.id === meta.service_id);
      return {
          service_id: meta.service_id,
          service_name: meta.service_name || service?.name || '',
          node_count: meta.node_ids.length,
          current_version: service?.current_package_version,
          version: service?.current_package_version || '',
          versions: [],
          loading: false,
          node_ids: meta.node_ids,
          nodes: meta.nodes || [],
          project: meta.project || service?.project,
          module_group: meta.module_group || service?.module_group
      };
  });
  
  deployDialog.visible = true;
  // Preload
  deployDialog.data.forEach(row => loadVersions(row));
}

// 重启
async function handleRestart() {
  if (selectNodeIds.value.length === 0) {
    ElMessage.warning("请至少选择一个节点");
    return;
  }
  
  // 构建操作元数据
  const operatorMetas = buildOperatorMetas(selectNodeIds.value);
  console.log('[重启] 操作元数据:', operatorMetas);
  
  ElMessageBox.confirm("确认重启选中的节点?", "提示", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "info",
  }).then(async () => {
    try {
      loading.value = true;
      // 使用新的数据格式调用 API
      const requestData: any = {
        task_type: 'node_operator',
        operator_type: 'restart',
        operator_metas: operatorMetas
      };
      await NodeAPI.restart(requestData);
      // 响应拦截器已经自动显示成功消息，这里不需要重复显示
      handleRefresh();
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
      console.error(error);
    } finally {
      loading.value = false;
    }
  }).catch(() => {
    ElMessageBox.close();
  });
}

// 启动
async function handleStart() {
  if (selectNodeIds.value.length === 0) {
    ElMessage.warning("请至少选择一个节点");
    return;
  }

  const operatorMetas = buildOperatorMetas(selectNodeIds.value);
  ElMessageBox.confirm("确认启动选中的节点?", "提示", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "info",
  }).then(async () => {
    try {
      loading.value = true;
      const requestData: any = {
        task_type: 'node_operator',
        operator_type: 'start',
        operator_metas: operatorMetas
      };
      await NodeAPI.start(requestData);
      handleRefresh();
      setTimeout(async () => {
        await loadRecentTasks();
        if (hasRunningTasks() && recentTasksTimer === null) {
          recentTasksTimer = window.setInterval(() => {
            loadRecentTasks();
          }, 5000);
        }
      }, 2000);
    } catch (error: any) {
      console.error(error);
    } finally {
      loading.value = false;
    }
  }).catch(() => {
    ElMessageBox.close();
  });
}

// 停止
async function handleStop() {
  if (selectNodeIds.value.length === 0) {
    ElMessage.warning("请至少选择一个节点");
    return;
  }

  const operatorMetas = buildOperatorMetas(selectNodeIds.value);
  ElMessageBox.confirm("确认停止选中的节点?", "提示", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  }).then(async () => {
    try {
      loading.value = true;
      const requestData: any = {
        task_type: 'node_operator',
        operator_type: 'stop',
        operator_metas: operatorMetas
      };
      await NodeAPI.stop(requestData);
      handleRefresh();
      setTimeout(async () => {
        await loadRecentTasks();
        if (hasRunningTasks() && recentTasksTimer === null) {
          recentTasksTimer = window.setInterval(() => {
            loadRecentTasks();
          }, 5000);
        }
      }, 2000);
    } catch (error: any) {
      console.error(error);
    } finally {
      loading.value = false;
    }
  }).catch(() => {
    ElMessageBox.close();
  });
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

const taskTypeMetaMap: Record<string, { label: string; tag: TaskTagType }> = {
  deploy: { label: '部署', tag: 'success' },
  restart: { label: '重启', tag: 'info' },
  start: { label: '启动', tag: 'success' },
  stop: { label: '停止', tag: 'danger' },
};

const defaultTaskTypeMeta: { label: string; tag: TaskTagType } = { label: '-', tag: 'info' };

function getTaskTypeMeta(type?: string) {
  if (!type) {
    return defaultTaskTypeMeta;
  }
  return taskTypeMetaMap[type] || { label: type, tag: 'info' as TaskTagType };
}

function getTaskTypeLabel(type?: string) {
  return getTaskTypeMeta(type).label;
}

function getTaskTypeTag(type?: string) {
  return getTaskTypeMeta(type).tag;
}

function progressStatus(status?: string) {
  if (status === 'success') return 'success';
  if (status === 'partial_success') return 'warning';
  if (status === 'failed') return 'exception';
  if (status === 'cancelled') return undefined; // 取消状态不显示特殊进度条颜色
  if (status === 'cancelling') return 'warning'; // 取消中显示警告色
  return undefined;
}

function handleOpenTaskDetailFromList(taskId?: number) {
  if (!taskId) return;
  router.push({
    path: `/operations/task/detail/${taskId}`,
  });
}

// 全部展开
function handleExpandAll() {
  pageTableData.value.forEach((row: any) => {
    if (row.nodes && row.nodes.length > 0) {
      dataTableRef.value?.toggleRowExpansion(row, true);
    }
  });
}

// 全部折叠
function handleCollapseAll() {
  pageTableData.value.forEach((row: any) => {
    if (row.nodes && row.nodes.length > 0) {
      dataTableRef.value?.toggleRowExpansion(row, false);
    }
  });
}

onMounted(() => {
  loadDictOptions();
  loadingData();
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
</script>

<style lang="scss" scoped>
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

  &:hover {
    border-color: #409eff;
    background: #f0f9ff;
  }
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

.task-service {
  font-size: 12px;
  margin-left: 8px;
  color: #909399;
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
  
  &.success {
    color: #67c23a;
  }
  
  &.partial {
    color: #e6a23c;
  }
  
  &.failed {
    color: #f56c6c;
  }
  
  &.running {
    color: #909399;
    animation: rotate 1s linear infinite;
  }
  
  &.cancelling {
    color: #e6a23c;
    animation: rotate 1s linear infinite;
  }
  
  &.cancelled {
    color: #909399;
  }
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



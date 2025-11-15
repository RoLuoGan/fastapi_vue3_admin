import request from "@/utils/request";

const API_PATH = "/operations/node";

const NodeAPI = {
  // 服务模块相关
  getServicePage(query: ServicePageQuery) {
    return request<ApiResponse<PageResult<ServiceTable[]>>>({
      url: `${API_PATH}/service/page`,
      method: "get",
      params: query,
    });
  },

  getServiceTree(query?: ServiceQueryParam) {
    return request<ApiResponse<ServiceTable[]>>({
      url: `${API_PATH}/service/tree`,
      method: "get",
      params: query,
    });
  },

  getServiceDetail(id: number) {
    return request<ApiResponse<ServiceTable>>({
      url: `${API_PATH}/service/detail/${id}`,
      method: "get",
    });
  },

  createService(body: ServiceForm) {
    return request<ApiResponse<ServiceTable>>({
      url: `${API_PATH}/service/create`,
      method: "post",
      data: body,
    });
  },

  updateService(id: number, body: ServiceForm) {
    return request<ApiResponse<ServiceTable>>({
      url: `${API_PATH}/service/update/${id}`,
      method: "put",
      data: body,
    });
  },

  deleteService(body: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/service/delete`,
      method: "delete",
      data: body,
    });
  },

  // 节点相关
  getNodePage(query: NodePageQuery) {
    return request<ApiResponse<PageResult<NodeTable[]>>>({
      url: `${API_PATH}/node/page`,
      method: "get",
      params: query,
    });
  },

  getNodeDetail(id: number) {
    return request<ApiResponse<NodeTable>>({
      url: `${API_PATH}/node/detail/${id}`,
      method: "get",
    });
  },

  createNode(body: NodeForm) {
    return request<ApiResponse<NodeTable>>({
      url: `${API_PATH}/node/create`,
      method: "post",
      data: body,
    });
  },

  updateNode(id: number, body: NodeForm) {
    return request<ApiResponse<NodeTable>>({
      url: `${API_PATH}/node/update/${id}`,
      method: "put",
      data: body,
    });
  },

  deleteNode(body: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/node/delete`,
      method: "delete",
      data: body,
    });
  },

  // 任务相关
  getTaskPage(query: TaskPageQuery) {
    return request<ApiResponse<PageResult<TaskTable[]>>>({
      url: `${API_PATH}/task/page`,
      method: "get",
      params: query,
    });
  },

  getRecentTasks(limit?: number) {
    return request<ApiResponse<TaskTable[]>>({
      url: `${API_PATH}/task/recent`,
      method: "get",
      params: { limit },
    });
  },

  getTaskDetail(id: number) {
    return request<ApiResponse<TaskDetail>>({
      url: `${API_PATH}/task/detail/${id}`,
      method: "get",
    });
  },

  getTaskLog(id: number) {
    return request<ApiResponse<TaskLog>>({
      url: `${API_PATH}/task/log/${id}`,
      method: "get",
    });
  },

  deleteTask(body: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/task/delete`,
      method: "delete",
      data: body,
    });
  },

  // 统一的任务执行接口（新格式：支持多模块多节点）
  executeTask(data: ExecuteTaskRequest) {
    console.log('[NodeAPI.executeTask] 接收到的数据:', data);
    console.log('[NodeAPI.executeTask] 数据类型:', typeof data);
    console.log('[NodeAPI.executeTask] 数据JSON:', JSON.stringify(data, null, 2));
    return request<ApiResponse>({
      url: `${API_PATH}/execute`,
      method: "post",
      data: data,
    });
  },

  // 部署（使用统一接口）
  deploy(data: ExecuteTaskRequest) {
    console.log('[NodeAPI.deploy] 接收到的数据:', data);
    return this.executeTask(data);
  },

  // 重启（使用统一接口）
  restart(data: ExecuteTaskRequest) {
    console.log('[NodeAPI.restart] 接收到的数据:', data);
    return this.executeTask(data);
  },
};

export default NodeAPI;

export interface ServiceQueryParam {
  name?: string;
  code?: string;
  status?: boolean;
  project?: string;
  module_group?: string;
  start_time?: string;
  end_time?: string;
}

export interface ServicePageQuery extends PageQuery {
  name?: string;
  code?: string;
  status?: boolean;
  project?: string;
  module_group?: string;
  start_time?: string;
  end_time?: string;
}

export interface ServiceTable {
  id?: number;
  name?: string;
  code?: string;
  status?: boolean;
  description?: string;
  project?: string;
  module_group?: string;
  created_at?: string;
  updated_at?: string;
  creator?: creatorType;
  nodes?: NodeTable[];
}

export interface ServiceForm {
  id?: number;
  name?: string;
  code?: string;
  status?: boolean;
  description?: string;
  project?: string;
  module_group?: string;
  nodes?: number[];
}

export interface NodeTable {
  id?: number;
  service_id?: number;
  service_name?: string;
  services?: ServiceTable[];
  ip?: string;
  port?: number;
  status?: boolean;
  description?: string;
  project?: string;
  idc?: string;
  tags?: string;
  created_at?: string;
  updated_at?: string;
  creator?: creatorType;
}

export interface NodeForm {
  id?: number;
  service_id?: number;
  service_ids?: number[];
  ip?: string;
  port?: number;
  status?: boolean;
  description?: string;
  project?: string;
  idc?: string;
  tags?: string;
}

export interface NodePageQuery extends PageQuery {
  service_id?: number;
  ip?: string;
  status?: boolean;
  project?: string;
  idc?: string;
  tags?: string;
  start_time?: string;
  end_time?: string;
}

export interface TaskTable {
  id?: number;
  task_type?: string;
  task_status?: string;
  progress?: number;
  params?: Record<string, any> | null;
  log_path?: string | null;
  error_message?: string;
  project?: string;
  idc?: string;
  module_group?: string;
  created_at?: string;
  updated_at?: string;
}

export interface TaskPageQuery extends PageQuery {
  task_type?: string;
  task_status?: string;
  project?: string;
  idc?: string;
  module_group?: string;
  start_time?: string;
  end_time?: string;
}

export interface TaskDetail extends TaskTable {
  log_size?: number;
}

export interface TaskLog {
  content: string;
}

export interface OperatorMeta {
  service_id: number;
  node_ids: number[];
}

export interface ExecuteTaskRequest {
  task_type: 'node_operator';
  operator_type: 'deploy' | 'restart';
  operator_metas: OperatorMeta[];
}


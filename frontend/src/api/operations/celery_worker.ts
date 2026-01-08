import request from "@/utils/request";

const API_PATH = "/operations/celery-worker";

const CeleryWorkerAPI = {
  // 获取Worker列表
  getList(query?: CeleryWorkerQueryParam) {
    return request<ApiResponse<CeleryWorkerTable[]>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  // 分页查询Worker
  getPage(query: CeleryWorkerPageQuery) {
    return request<ApiResponse<PageResult<CeleryWorkerTable[]>>>({
      url: `${API_PATH}/page`,
      method: "get",
      params: query,
    });
  },

  // 获取队列列表
  getQueues() {
    return request<ApiResponse<QueueItem[]>>({
      url: `${API_PATH}/queues`,
      method: "get",
    });
  },

  // 获取Worker详情
  getDetail(id: number) {
    return request<ApiResponse<CeleryWorkerTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },

  // 创建Worker
  create(data: CeleryWorkerForm) {
    return request<ApiResponse<CeleryWorkerTable>>({
      url: `${API_PATH}/create`,
      method: "post",
      data,
    });
  },

  // 更新Worker
  update(id: number, data: CeleryWorkerForm) {
    return request<ApiResponse<CeleryWorkerTable>>({
      url: `${API_PATH}/update/${id}`,
      method: "put",
      data,
    });
  },

  // 删除Worker
  delete(ids: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: "delete",
      data: ids,
    });
  },

  // 注册Worker (供内部调用)
  register(data: CeleryWorkerRegisterForm) {
    return request<ApiResponse<CeleryWorkerTable>>({
      url: `${API_PATH}/register`,
      method: "post",
      data,
    });
  },
};

export default CeleryWorkerAPI;

// 类型定义
export interface CeleryWorkerQueryParam {
  queue_name?: string;
  queue_code?: string;
  node_ip?: string;
  status?: boolean;
}

export interface CeleryWorkerPageQuery extends PageQuery {
  queue_name?: string;
  queue_code?: string;
  node_ip?: string;
  status?: boolean;
}

export interface CeleryWorkerTable {
  id?: number;
  queue_name?: string;
  queue_code?: string;
  node_ip?: string;
  node_hostname?: string;
  status?: boolean;
  last_heartbeat?: number;
  last_heartbeat_time?: string;
  created_at?: string;
  updated_at?: string;
}

export interface CeleryWorkerForm {
  queue_name: string;
  queue_code: string;
  node_ip: string;
  node_hostname?: string;
  status: boolean;
}

export interface CeleryWorkerRegisterForm {
  queue_name: string;
  queue_code: string;
  node_ip: string;
  node_hostname?: string;
}

export interface QueueItem {
  queue_code: string;
  queue_name: string;
}



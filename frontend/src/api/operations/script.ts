import request from "@/utils/request";

const API_PATH = "/operations/script";

const ScriptAPI = {
  // 获取脚本列表
  getList(query?: ScriptQueryParam) {
    return request<ApiResponse<ScriptTable[]>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  // 分页查询脚本
  getPage(query: ScriptPageQuery) {
    return request<ApiResponse<PageResult<ScriptTable[]>>>({
      url: `${API_PATH}/page`,
      method: "get",
      params: query,
    });
  },

  // 获取脚本详情
  getDetail(id: number) {
    return request<ApiResponse<ScriptTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },

  // 创建脚本
  create(data: ScriptForm) {
    return request<ApiResponse<ScriptTable>>({
      url: `${API_PATH}/create`,
      method: "post",
      data,
    });
  },

  // 更新脚本
  update(id: number, data: ScriptForm) {
    return request<ApiResponse<ScriptTable>>({
      url: `${API_PATH}/update/${id}`,
      method: "put",
      data,
    });
  },

  // 删除脚本
  delete(ids: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: "delete",
      data: ids,
    });
  },

  // 运行脚本
  run(data: ScriptRunForm) {
    return request<ApiResponse<ScriptRunResult>>({
      url: `${API_PATH}/run`,
      method: "post",
      data,
    });
  },
};

export default ScriptAPI;

// 类型定义
export interface ScriptQueryParam {
  name?: string;
  script_type?: string;
  content_type?: string;
  queue_code?: string;
  status?: boolean;
}

export interface ScriptPageQuery extends PageQuery {
  name?: string;
  script_type?: string;
  content_type?: string;
  queue_code?: string;
  status?: boolean;
}

export interface ScriptParamSchema {
  name: string;
  param_type: "string" | "int" | "float" | "bool" | "list" | "dict";
  required: boolean;
  default?: any;
  description?: string;
}

export interface ScriptTable {
  id?: number;
  name?: string;
  script_type?: string;
  content_type?: string;
  content?: string;
  default_timeout?: number;
  queue_code?: string;
  params_schema?: ScriptParamSchema[];
  status?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface ScriptForm {
  name: string;
  script_type: string;
  content_type: string;
  content: string;
  default_timeout: number;
  queue_code?: string;
  params_schema?: ScriptParamSchema[];
  status: boolean;
}

export interface ScriptRunForm {
  script_id: number;
  params?: Record<string, any>;
  timeout?: number;
  target_nodes?: string[];
}

export interface ScriptRunResult {
  message: string;
  task_id: number;
  task_type: string;
  operator_type: string;
}



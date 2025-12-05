import request from "@/utils/request";

const API_PATH = "/operations/nginx-upstream";

const NginxUpstreamAPI = {
  // 分页查询
  getUpstreamPage(query: NginxUpstreamPageQuery) {
    return request<ApiResponse<PageResult<NginxUpstreamTable[]>>>({
      url: `${API_PATH}/page`,
      method: "get",
      params: query,
    });
  },

  // 查询详情
  getUpstreamDetail(id: number) {
    return request<ApiResponse<NginxUpstreamTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },

  // 创建
  createUpstream(body: NginxUpstreamForm) {
    return request<ApiResponse<NginxUpstreamTable>>({
      url: `${API_PATH}/create`,
      method: "post",
      data: body,
    });
  },

  // 更新
  updateUpstream(id: number, body: NginxUpstreamForm) {
    return request<ApiResponse<NginxUpstreamTable>>({
      url: `${API_PATH}/update/${id}`,
      method: "put",
      data: body,
    });
  },

  // 删除
  deleteUpstream(body: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: "delete",
      data: body,
    });
  },

  // 同步配置
  syncUpstream(body: SyncUpstreamRequest) {
    return request<ApiResponse>({
      url: `${API_PATH}/sync`,
      method: "post",
      data: body,
    });
  },

  // 预览模板
  previewTemplate(body: PreviewTemplateRequest) {
    return request<ApiResponse<PreviewTemplateResponse>>({
      url: `${API_PATH}/preview-template`,
      method: "post",
      data: body,
    });
  },
};

export default NginxUpstreamAPI;

export interface ProxyTarget {
  ip: string;
  port: number;
  service_id?: number;
  status?: string; // "up" | "down"
}

export interface NginxUpstreamTable {
  id?: number;
  upstream?: string;
  proxy_targets?: ProxyTarget[];
  nginx_node_ids?: number[]; // 修改
  nginx_nodes?: Array<{ // 修改
    id?: number;
    ip?: string;
    port?: number;
  }>;
  upstream_template?: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
  creator?: creatorType;
}

export interface NginxUpstreamForm {
  id?: number;
  upstream?: string;
  proxy_targets?: ProxyTarget[];
  nginx_node_ids?: number[]; // 修改
  upstream_template?: string;
  description?: string;
}

export interface NginxUpstreamPageQuery extends PageQuery {
  upstream?: string;
  nginx_node_id?: number;
  start_time?: string;
  end_time?: string;
}

export interface SyncUpstreamRequest {
  upstream_ids: number[];
}

export interface PreviewTemplateRequest {
  upstream: string;
  upstream_template: string;
  proxy_targets: ProxyTarget[];
}

export interface PreviewTemplateResponse {
  rendered_content: string;
  template_vars: {
    service_name: string;
    hosts: ProxyTarget[];
  };
}

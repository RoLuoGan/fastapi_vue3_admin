import request from "@/utils/request";

const API_PREFIX = "/operations/prometheus";

export interface PrometheusTreeEndpoint {
  id: number | string;
  type: "endpoint";
  endpoint: string;
  is_enabled: boolean;
  labels_text: string;
}

export interface PrometheusTreeJob {
  id: number;
  type: "job";
  job_name: string;
  is_enabled: boolean;
  labels_text: string;
  endpoints_count: number;
  children: PrometheusTreeEndpoint[];
}

export interface PrometheusLabelItem {
  key: string;
  value: string;
}

export interface PrometheusEndpointItem {
  endpoint: string;
  is_enabled?: boolean;
  scheme?: string;
}

export interface PrometheusJobDetail {
  id?: number;
  job_name: string;
  description?: string;
  is_enabled: boolean;
  endpoints: PrometheusEndpointItem[];
  labels: PrometheusLabelItem[];
}

export interface PrometheusJobQuery {
  job_name?: string;
  is_enabled?: boolean | null;
}

// 导入导出使用的简化格式
export interface PrometheusJobExport {
  job_name: string;
  description?: string;
  is_enabled: boolean;
  endpoints: string[]; // 简化格式：字符串数组
  labels: PrometheusLabelItem[];
}

const PrometheusAPI = {
  getJobTree(params?: PrometheusJobQuery) {
    return request<ApiResponse<PrometheusTreeJob[]>>({
      url: `${API_PREFIX}/job/tree`,
      method: "get",
      params,
    });
  },
  getJobDetail(jobId: number) {
    return request<ApiResponse<PrometheusJobDetail>>({
      url: `${API_PREFIX}/job/${jobId}`,
      method: "get",
    });
  },
  createJob(data: PrometheusJobDetail) {
    return request<ApiResponse>({
      url: `${API_PREFIX}/job`,
      method: "post",
      data,
    });
  },
  updateJob(jobId: number, data: PrometheusJobDetail) {
    return request<ApiResponse>({
      url: `${API_PREFIX}/job/${jobId}`,
      method: "put",
      data,
    });
  },
  deleteJob(ids: number[]) {
    return request<ApiResponse>({
      url: `${API_PREFIX}/job`,
      method: "delete",
      data: { ids },
    });
  },
  exportJobs() {
    return request<ApiResponse<PrometheusJobExport[]>>({
      url: `${API_PREFIX}/job/export`,
      method: "get",
    });
  },
  importJobs(data: { overwrite: boolean; jobs: PrometheusJobExport[] }) {
    return request<ApiResponse>({
      url: `${API_PREFIX}/job/import`,
      method: "post",
      data,
    });
  },
  toggleJobStatus(jobId: number, isEnabled: boolean) {
    return request<ApiResponse>({
      url: `${API_PREFIX}/job/${jobId}/toggle-status`,
      method: "patch",
      data: { is_enabled: isEnabled },
    });
  },
  toggleEndpointStatus(endpointId: number, isEnabled: boolean) {
    return request<ApiResponse>({
      url: `${API_PREFIX}/endpoint/${endpointId}/toggle-status`,
      method: "patch",
      data: { is_enabled: isEnabled },
    });
  },
};

export default PrometheusAPI;


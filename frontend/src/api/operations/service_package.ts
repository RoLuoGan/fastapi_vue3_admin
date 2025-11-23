import request from "@/utils/request";

const API_PATH = "/operations/service-package";

export interface ServicePackageQueryParam {
  service_id?: number;
  version?: string;
}

export interface ServicePackageTable {
  id: number;
  service_id: number;
  version: string;
  package_path: string;
  md5?: string;
  size?: number;
  created_at?: string;
  updated_at?: string;
}

export interface ServicePackageCreateForm {
  service_id: number;
  version?: string;
  package_path?: string;
  md5?: string;
  is_latest?: boolean;
  file?: File;
}

export interface ServicePackageUpdateForm {
  id: number;
  version?: string;
  package_path?: string;
  md5?: string;
  is_latest?: boolean;
}

export interface OneClickUploadForm {
  service_id: number;
  date_str?: string;
}

const ServicePackageAPI = {
  getList(query: ServicePackageQueryParam) {
    return request<ApiResponse<ServicePackageTable[]>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  create(data: ServicePackageCreateForm) {
    const formData = new FormData();
    formData.append("service_id", data.service_id.toString());
    if (data.version) formData.append("version", data.version);
    if (data.package_path) formData.append("package_path", data.package_path);
    if (data.md5) formData.append("md5", data.md5);
    formData.append("is_latest", data.is_latest ? "true" : "false");
    if (data.file) formData.append("file", data.file);

    return request<ApiResponse<ServicePackageTable>>({
      url: `${API_PATH}/create`,
      method: "post",
      data: formData,
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
  },

  update(id: number, data: ServicePackageUpdateForm) {
    return request<ApiResponse<ServicePackageTable>>({
      url: `${API_PATH}/update/${id}`,
      method: "put",
      data: data,
    });
  },

  delete(ids: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: "delete",
      data: { ids: ids }, // Controller expects {ids: [...]} via embed=True? No, Body(..., embed=True) expects {"ids": [...]}
    });
  },

  oneClickUpload(data: OneClickUploadForm) {
    return request<ApiResponse<ServicePackageTable>>({
      url: `${API_PATH}/one-click-upload`,
      method: "post",
      data: data,
    });
  },
};

export default ServicePackageAPI;


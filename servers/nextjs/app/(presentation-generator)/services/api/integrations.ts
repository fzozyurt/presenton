import { getHeader } from "@/app/(presentation-generator)/services/api/header";
import { ApiResponseHandler } from "@/app/(presentation-generator)/services/api/api-error-handler";
import { getApiUrl } from "@/utils/api";

export interface DataSource {
  id: string;
  type: string;
  name: string;
  credential_ref: string | null;
  base_config: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface Credential {
  id: string;
  module: string;
  type: string;
  status: string;
  label: string | null;
  fingerprint: string;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Binding {
  id: string;
  presentation_id: string;
  datasource_id: string;
  alias: string | null;
  binding_config: Record<string, any> | null;
  created_at: string;
}

export interface ReportRun {
  id: string;
  presentation_id: string;
  binding_id: string | null;
  status: string;
  error_message: string | null;
  result_data: Record<string, any> | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export class IntegrationsApi {
  static base = "/api/v1/integrations";

  // Data Sources
  static async listDataSources(): Promise<DataSource[]> {
    const res = await fetch(getApiUrl(`${this.base}/data-sources`), { method: "GET" });
    return await ApiResponseHandler.handleResponse(res, "Failed to list data sources");
  }

  static async createDataSource(body: {
    type: string;
    name: string;
    credential_ref?: string;
    base_config?: Record<string, any>;
  }): Promise<DataSource> {
    const res = await fetch(getApiUrl(`${this.base}/data-sources`), {
      method: "POST",
      headers: getHeader(),
      body: JSON.stringify(body),
    });
    return await ApiResponseHandler.handleResponse(res, "Failed to create data source");
  }

  static async updateDataSource(
    dsId: string,
    body: Partial<{ type: string; name: string; credential_ref: string | null; base_config: Record<string, any> | null }>,
  ): Promise<DataSource> {
    const res = await fetch(getApiUrl(`${this.base}/data-sources/${dsId}`), {
      method: "PUT",
      headers: getHeader(),
      body: JSON.stringify(body),
    });
    return await ApiResponseHandler.handleResponse(res, "Failed to update data source");
  }

  static async deleteDataSource(dsId: string): Promise<{ success: boolean; message?: string }> {
    const res = await fetch(getApiUrl(`${this.base}/data-sources/${dsId}`), {
      method: "DELETE",
      headers: getHeader(),
    });
    return await ApiResponseHandler.handleResponseWithResult(res, "Failed to delete data source");
  }

  // Credentials
  static async listCredentials(): Promise<Credential[]> {
    const res = await fetch(getApiUrl(`${this.base}/credentials`), { method: "GET" });
    return await ApiResponseHandler.handleResponse(res, "Failed to list credentials");
  }

  static async createCredential(body: {
    module: string;
    type: string;
    label?: string;
    secret: Record<string, any>;
  }): Promise<Credential> {
    const res = await fetch(getApiUrl(`${this.base}/credentials`), {
      method: "POST",
      headers: getHeader(),
      body: JSON.stringify(body),
    });
    return await ApiResponseHandler.handleResponse(res, "Failed to create credential");
  }

  static async deleteCredential(credId: string): Promise<{ success: boolean; message?: string }> {
    const res = await fetch(getApiUrl(`${this.base}/credentials/${credId}`), {
      method: "DELETE",
      headers: getHeader(),
    });
    return await ApiResponseHandler.handleResponseWithResult(res, "Failed to delete credential");
  }

  // Bindings
  static async listBindings(presentationId?: string): Promise<Binding[]> {
    const url = presentationId
      ? `${this.base}/bindings?presentation_id=${encodeURIComponent(presentationId)}`
      : `${this.base}/bindings`;
    const res = await fetch(getApiUrl(url), { method: "GET" });
    return await ApiResponseHandler.handleResponse(res, "Failed to list bindings");
  }

  static async createBinding(body: {
    presentation_id: string;
    datasource_id: string;
    alias?: string;
    binding_config?: Record<string, any>;
  }): Promise<Binding> {
    const res = await fetch(getApiUrl(`${this.base}/bindings`), {
      method: "POST",
      headers: getHeader(),
      body: JSON.stringify(body),
    });
    return await ApiResponseHandler.handleResponse(res, "Failed to create binding");
  }

  static async deleteBinding(bndId: string): Promise<{ success: boolean; message?: string }> {
    const res = await fetch(getApiUrl(`${this.base}/bindings/${bndId}`), {
      method: "DELETE",
      headers: getHeader(),
    });
    return await ApiResponseHandler.handleResponseWithResult(res, "Failed to delete binding");
  }
}

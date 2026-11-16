import {
  ColumnOverrideItem,
  ColumnProfile,
  DatasetMetadata,
  IndustryProfile,
  PaginatedPreview,
} from '../types/dataset';
import { AnonymizationConfig, AnonymizationPreset } from '../types/anonymization';
import { DiffResponse, RunAnalytics } from '../types/analytics';

const BASE_URL = '/api';

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const headers = new Headers(options.headers || {});

  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = response.statusText;
    let errorData = null;
    try {
      errorData = await response.json();
      if (errorData && errorData.detail) {
        errorDetail = typeof errorData.detail === 'string' 
          ? errorData.detail 
          : JSON.stringify(errorData.detail);
      }
    } catch {
      // Body not JSON
    }
    throw new ApiError(response.status, errorDetail, errorData);
  }

  return response.json();
}

export const api = {
  // Datasets
  async uploadDataset(
    file: File,
    name?: string
  ): Promise<{ dataset_id: string; row_count: number; columns: string[]; preview: any[] }> {
    const formData = new FormData();
    formData.append('file', file);
    if (name) {
      formData.append('name', name);
    }
    return request('/datasets/upload', {
      method: 'POST',
      body: formData,
    });
  },

  async loadDemoDataset(): Promise<{ dataset_id: string; row_count: number; message: string; preview: any[] }> {
    return request('/datasets/load-demo', {
      method: 'POST',
    });
  },

  async loadIndustryDemo(
    industry: string
  ): Promise<{ dataset_id: string; row_count: number; columns: string[]; preview: any[]; industry: string; message: string }> {
    return request(`/datasets/load-industry-demo/${industry}`, {
      method: 'POST',
    });
  },

  async listDatasets(): Promise<DatasetMetadata[]> {
    return request('/datasets');
  },

  async getDataset(id: string): Promise<DatasetMetadata> {
    return request(`/datasets/${id}`);
  },

  async getDatasetPreview(
    id: string,
    page: number = 1,
    size: number = 15,
    maskSensitive: boolean = true
  ): Promise<PaginatedPreview> {
    const res = await request<PaginatedPreview>(`/datasets/${id}/preview?page=${page}&size=${size}&mask_sensitive=${maskSensitive}`);
    const rows = res.rows || (res as any).records || [];
    return { ...res, rows, records: rows };
  },

  async discoverDataset(id: string): Promise<{ dataset_id: string; profiles: ColumnProfile[] }> {
    return request(`/datasets/${id}/discover`);
  },

  async updateOverrides(
    id: string,
    overrides: ColumnOverrideItem[]
  ): Promise<{ dataset_id: string; profiles: ColumnProfile[]; message: string }> {
    return request(`/datasets/${id}/overrides`, {
      method: 'POST',
      body: JSON.stringify({ overrides }),
    });
  },

  async getLatestRunForDataset(id: string): Promise<RunAnalytics | null> {
    try {
      return await request(`/datasets/${id}/latest-run`);
    } catch {
      return null;
    }
  },

  async anonymizeDataset(id: string, config: AnonymizationConfig): Promise<RunAnalytics> {
    return request(`/datasets/${id}/anonymize`, {
      method: 'POST',
      body: JSON.stringify(config),
    });
  },

  // Runs & Analytics
  async getRun(runId: string): Promise<any> {
    return request(`/runs/${runId}`);
  },

  async getRunAnalytics(runId: string): Promise<RunAnalytics> {
    return request(`/runs/${runId}/analytics`);
  },

  async getRunDiff(runId: string, page: number = 1, size: number = 50): Promise<DiffResponse> {
    const res = await request<any>(`/runs/${runId}/diff?page=${page}&size=${size}`);
    const rows = res.rows || res.diff || [];
    const columns = res.columns || (rows.length > 0 && rows[0].cells ? Object.keys(rows[0].cells) : []);
    return {
      ...res,
      columns,
      rows,
    };
  },

  // Export URLs & Download triggers
  getExportUrl(runId: string, format: 'csv' | 'xlsx' | 'json'): string {
    return `${BASE_URL}/runs/${runId}/export/${format}`;
  },

  getPdfReportUrl(runId: string): string {
    return `${BASE_URL}/runs/${runId}/report/pdf`;
  },

  async downloadExport(runId: string, format: 'csv' | 'xlsx' | 'json'): Promise<void> {
    const url = this.getExportUrl(runId, format);
    const response = await fetch(url);
    if (!response.ok) {
      let errorDetail = `Export failed with status ${response.status} (${response.statusText})`;
      try {
        const errorData = await response.json();
        if (errorData && errorData.detail) {
          errorDetail = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
        }
      } catch {
        // Body not JSON
      }
      throw new ApiError(response.status, errorDetail);
    }
    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.setAttribute('download', `privshield_anonymized_${runId}.${format === 'xlsx' ? 'xlsx' : format}`);
    document.body.appendChild(link);
    link.click();
    window.URL.revokeObjectURL(downloadUrl);
    document.body.removeChild(link);
  },

  async downloadPdfReport(runId: string): Promise<void> {
    const url = this.getPdfReportUrl(runId);
    const response = await fetch(url);
    if (!response.ok) {
      let errorDetail = `PDF report generation failed with status ${response.status} (${response.statusText})`;
      try {
        const errorData = await response.json();
        if (errorData && errorData.detail) {
          errorDetail = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
        }
      } catch {
        // Body not JSON
      }
      throw new ApiError(response.status, errorDetail);
    }
    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.setAttribute('download', `privshield_privacy_report_${runId}.pdf`);
    document.body.appendChild(link);
    link.click();
    window.URL.revokeObjectURL(downloadUrl);
    document.body.removeChild(link);
  },

  // Industry Profiles
  async listProfiles(): Promise<IndustryProfile[]> {
    return request('/profiles');
  },

  async getProfile(profileId: string): Promise<IndustryProfile> {
    return request(`/profiles/${profileId}`);
  },

  async applyProfile(
    profileId: string,
    columns: string[],
    datasetId?: string
  ): Promise<Record<string, any>> {
    return request(`/profiles/${profileId}/apply`, {
      method: 'POST',
      body: JSON.stringify({ columns, dataset_id: datasetId }),
    });
  },

  // Presets
  async listPresets(): Promise<AnonymizationPreset[]> {
    return request('/presets');
  },

  async createPreset(preset: { name: string; description: string; rules: any }): Promise<any> {
    return request('/presets', {
      method: 'POST',
      body: JSON.stringify(preset),
    });
  },

  // Health
  async checkHealth(): Promise<{ status: string; uptime_seconds: number }> {
    return request('/health');
  },
};

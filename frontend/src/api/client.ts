import axios from 'axios'

// In development: Vite proxies /api → localhost:8000
// In production (Vercel): reads VITE_API_URL env var, defaults to localhost:8000
const baseURL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}`
  : ''

export const api = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const message =
      err.response?.data?.detail || err.message || 'Unknown error'
    return Promise.reject(new Error(message))
  },
)

// ── Projects ──────────────────────────────────────────────────────────────────
import type {
  Project, ProjectCreate, Document, ExtractedTable, LineItem, AuditLog,
} from '../types'

export const projectsApi = {
  list: () => api.get<Project[]>('/api/projects').then(r => r.data),
  create: (data: ProjectCreate) => api.post<Project>('/api/projects', data).then(r => r.data),
  get: (id: string) => api.get<Project>(`/api/projects/${id}`).then(r => r.data),
  update: (id: string, data: Partial<ProjectCreate>) =>
    api.patch<Project>(`/api/projects/${id}`, data).then(r => r.data),
  delete: (id: string) => api.delete(`/api/projects/${id}`).then(r => r.data),
  auditLog: (id: string) => api.get<AuditLog[]>(`/api/projects/${id}/audit-log`).then(r => r.data),
}

// ── Documents ─────────────────────────────────────────────────────────────────
export const documentsApi = {
  list: (projectId: string) =>
    api.get<Document[]>(`/api/projects/${projectId}/documents`).then(r => r.data),
  upload: (projectId: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post<Document>(`/api/projects/${projectId}/documents`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data)
  },
  updateMeta: (projectId: string, docId: string, data: object) =>
    api.patch<Document>(`/api/projects/${projectId}/documents/${docId}/metadata`, data).then(r => r.data),
  delete: (projectId: string, docId: string) =>
    api.delete(`/api/projects/${projectId}/documents/${docId}`).then(r => r.data),
  extract: (projectId: string, docId: string) =>
    api.post<Document>(`/api/projects/${projectId}/documents/${docId}/extract`).then(r => r.data),
  getTables: (projectId: string, docId: string) =>
    api.get<ExtractedTable[]>(`/api/projects/${projectId}/documents/${docId}/tables`).then(r => r.data),
  updateTableType: (projectId: string, docId: string, tableId: string, table_type: string) =>
    api.patch<ExtractedTable>(
      `/api/projects/${projectId}/documents/${docId}/tables/${tableId}`,
      { table_type, user_confirmed: true },
    ).then(r => r.data),
}

// ── Mapping ───────────────────────────────────────────────────────────────────
export const mappingApi = {
  runMapping: (projectId: string) =>
    api.post<{ message: string }>(`/api/projects/${projectId}/run-mapping`).then(r => r.data),
  listLineItems: (projectId: string, params?: { statement_type?: string; review_status?: string }) =>
    api.get<LineItem[]>(`/api/projects/${projectId}/line-items`, { params }).then(r => r.data),
  updateLineItem: (projectId: string, itemId: string, data: object) =>
    api.patch<LineItem>(`/api/projects/${projectId}/line-items/${itemId}`, data).then(r => r.data),
  bulkApprove: (projectId: string) =>
    api.post<{ message: string }>(`/api/projects/${projectId}/line-items/bulk-approve`).then(r => r.data),
}

// ── Model / Forecast / Chat / LLM ─────────────────────────────────────────────

export interface StatementRow {
  standard_id: string
  standard_label: string
  values: Record<string, number | null>
  is_derived: boolean
  source: string
}

export interface StatementTable {
  statement_type: string
  periods: string[]
  rows: StatementRow[]
}

export interface FinancialModel {
  project_id: string
  income_statement: StatementTable
  balance_sheet: StatementTable
  cash_flow: StatementTable
  key_ratios: Record<string, Record<string, number | null>>
}

export interface ForecastData {
  project_id: string
  forecast_periods: string[]
  historical_periods?: string[]
  forecast: Record<string, Record<string, number | null>>
  assumptions: Record<string, string | { growth_rate: number; rationale: string }>
}

export interface ChatMessage {
  id: string
  project_id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface LLMStatus {
  loaded: boolean
  model_name: string | null
  device: string | null
  quantized: boolean
  error: string | null
}

export const modelApi = {
  buildModel: (projectId: string, useLlm = true) =>
    api.post<FinancialModel>(`/api/model/${projectId}/build`, { project_id: projectId, use_llm: useLlm }).then(r => r.data),
  getModel: (projectId: string) =>
    api.get<FinancialModel>(`/api/model/${projectId}`).then(r => r.data),
  runForecast: (projectId: string, forecastYears = 3, useLlm = true) =>
    api.post<ForecastData>(`/api/model/${projectId}/forecast`, {
      project_id: projectId,
      forecast_years: forecastYears,
      use_llm: useLlm,
    }).then(r => r.data),
  getForecast: (projectId: string) =>
    api.get<ForecastData>(`/api/model/${projectId}/forecast`).then(r => r.data),
  exportExcel: (projectId: string, includeForecast = true) =>
    api.get<Blob>(`/api/model/${projectId}/export`, {
      params: { include_forecast: includeForecast },
      responseType: 'blob',
    }).then(r => r.data),
  llmStatus: () =>
    api.get<LLMStatus>('/api/model/llm/status').then(r => r.data),
  llmLoad: (modelName?: string) =>
    api.post<{ message: string }>('/api/model/llm/load', null, {
      params: modelName ? { model_name: modelName } : {},
    }).then(r => r.data),
  getChat: (projectId: string) =>
    api.get<ChatMessage[]>(`/api/model/${projectId}/chat`).then(r => r.data),
  sendChat: (projectId: string, content: string) =>
    api.post<ChatMessage>(`/api/model/${projectId}/chat`, { content }).then(r => r.data),
}

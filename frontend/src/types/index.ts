export interface Project {
  id: string
  company_name: string
  ticker: string | null
  sector: string | null
  base_currency: string | null
  fiscal_year_end: string | null
  created_at: string
  updated_at: string
  document_count: number
}

export interface ProjectCreate {
  company_name: string
  ticker?: string
  sector?: string
  base_currency?: string
  fiscal_year_end?: string
}

export interface Document {
  id: string
  project_id: string
  file_name: string
  file_size: number | null
  page_count: number | null
  detected_year: number | null
  detected_currency: string | null
  detected_scale: string | null
  status: 'pending' | 'processing' | 'extracted' | 'failed'
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface ExtractedTable {
  id: string
  document_id: string
  page_number: number | null
  table_type: 'income_statement' | 'balance_sheet' | 'cash_flow' | 'note' | 'unknown'
  detection_confidence: number | null
  detected_periods: string[] | null
  headers: string[] | null
  raw_data: Record<string, string>[] | null
  extraction_confidence: number | null
  user_confirmed: boolean
}

export interface LineItem {
  id: string
  project_id: string
  table_id: string | null
  statement_type: string
  source_label: string
  standard_id: string | null
  standard_label: string | null
  period: string | null
  raw_value: string | null
  normalized_value: number | null
  currency: string | null
  scale: string | null
  sign_convention: string
  mapping_confidence: number | null
  review_status: 'pending' | 'approved' | 'rejected' | 'edited'
  source_page: number | null
  source_document_id: string | null
}

export interface AuditLog {
  id: string
  project_id: string
  action: string
  detail: Record<string, unknown> | null
  created_at: string
}

export type StatementType = 'income_statement' | 'balance_sheet' | 'cash_flow'

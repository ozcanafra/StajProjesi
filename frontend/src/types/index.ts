export interface User {
  id: number
  email: string
  created_at: string
}

export interface Target {
  id: number
  domain: string
  is_verified: boolean
  verification_token: string
  created_at: string
}

export interface VerifyInstructions {
  record_name: string
  record_value: string
  instructions: string
}

export type Severity = 'info' | 'low' | 'medium' | 'high' | 'critical'

export interface Finding {
  id: number
  module: string
  severity: Severity
  title: string
  description: string
  evidence: Record<string, unknown>
  created_at: string
}

export interface PrioritizedFinding {
  title: string
  severity: Severity
  business_impact: string
  remediation: string
}

export interface Report {
  id: number
  risk_score: number
  executive_summary: string
  technical_summary: string
  prioritized_findings: PrioritizedFinding[]
  created_at: string
}

export type ScanStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface Scan {
  id: number
  target_id: number
  status: ScanStatus
  modules: string[]
  risk_score: number | null
  error_message: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
}

export interface ScanDetail extends Scan {
  findings: Finding[]
  report: Report | null
}

export interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface ScanDiff {
  previous_scan_id: number | null
  previous_created_at: string | null
  risk_score_delta: number | null
  new_findings: Finding[]
  resolved_findings: Finding[]
  persisting_count: number
}

export const AVAILABLE_MODULES = ['recon', 'headers_tls', 'webvuln'] as const

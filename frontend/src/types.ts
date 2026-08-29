export type Severity = 'pass' | 'log' | 'block'

export interface CheckResult {
  score: number
  flags: string[]
  [key: string]: unknown
}

export interface ScoredResponse {
  id: string
  session_id: string
  model: string
  use_case: string
  timestamp: string
  prompt: string
  response: string
  checks: {
    performance: CheckResult
    cost: CheckResult
    responsibility: CheckResult
  }
  correlation: {
    compound_flags: string[]
    correlation_score: number
  }
  severity: Severity
  decision_reason: string
  generated?: boolean
  llm_provider?: string | null
  override_status: string
  override_reason?: string | null
  feedback_text?: string | null
}

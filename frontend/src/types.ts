export type Severity = "pass" | "edit" | "log" | "block";

export interface CheckResult {
  score: number;
  flags: string[];
  [key: string]: unknown;
}

export interface ScoredResponse {
  id: string;
  session_id: string;
  model: string;
  use_case: string;
  geography: string;
  timestamp: string;
  prompt: string;
  response: string;
  checks: {
    performance: CheckResult;
    cost: CheckResult;
    responsibility: CheckResult;
    bias: CheckResult;
    hallucination: CheckResult;
  };
  correlation: {
    compound_flags: string[];
    correlation_score: number;
  };
  severity: Severity;
  decision_reason: string;
  original_severity?: Severity;
  original_decision_reason?: string;
  generated?: boolean;
  llm_provider?: string | null;
  override_status: string;
  override_reason?: string | null;
  feedback_text?: string | null;
  feedback?: Array<{
    id: string;
    override: "false_positive" | "false_negative" | "correct";
    note?: string | null;
    timestamp: string;
  }>;
}

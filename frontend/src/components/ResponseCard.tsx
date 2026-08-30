import { useState } from "react";
import type { ScoredResponse } from "../types";
import SeverityBadge from "./SeverityBadge";
import {
  ShieldAlert,
  MessageSquare,
  CornerDownRight,
  RefreshCw,
} from "lucide-react";

const GAUGE_COLOR = (score: number) =>
  score >= 70 ? "text-pass" : score >= 40 ? "text-log" : "text-block";
const GAUGE_BAR = (score: number) =>
  score >= 70 ? "bg-pass" : score >= 40 ? "bg-log" : "bg-block";

function Gauge({ label, score }: { label: string; score: number }) {
  return (
    <div className="flex flex-col gap-1.5 min-w-[80px]">
      <div className="flex items-baseline justify-between">
        <span className="text-[9px] uppercase tracking-widest text-muted">
          {label}
        </span>
        <span
          className={`font-mono text-xs font-semibold tabular-nums ${GAUGE_COLOR(score)}`}
        >
          {score}
        </span>
      </div>
      <div className="h-1 rounded-full bg-hairline overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${GAUGE_BAR(score)}`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}

export default function ResponseCard({ record }: { record: ScoredResponse }) {
  const [showAnalysis, setShowAnalysis] = useState(false);
  const [overrideReason, setOverrideReason] = useState("");
  const [showOverrideInput, setShowOverrideInput] = useState<
    "allow" | "block" | null
  >(null);
  const [feedbackInput, setFeedbackInput] = useState("");
  const [feedbackOverride, setFeedbackOverride] = useState<
    "false_positive" | "false_negative" | "correct"
  >("correct");
  const [submittingFeedback, setSubmittingFeedback] = useState(false);
  const [submittingOverride, setSubmittingOverride] = useState(false);

  const {
    id,
    checks,
    correlation,
    severity,
    decision_reason,
    original_severity,
    timestamp,
    model,
    generated,
    llm_provider,
    override_status,
    feedback_text,
  } = record;

  const time = new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  async function handleOverride(
    status: "override_allow" | "override_block" | "none",
    reason?: string,
  ) {
    setSubmittingOverride(true);
    try {
      const res = await fetch(`/api/score/${id}/override`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status, reason }),
      });
      if (res.ok) {
        setShowOverrideInput(null);
        setOverrideReason("");
      }
    } catch (err) {
      console.error(err);
    } finally {
      setSubmittingOverride(false);
    }
  }

  async function handleFeedback(e: React.FormEvent) {
    e.preventDefault();
    setSubmittingFeedback(true);
    try {
      const res = await fetch(`/api/feedback/${id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          override: feedbackOverride,
          note: feedbackInput || null,
        }),
      });
      if (res.ok) {
        setFeedbackInput("");
      }
    } catch (err) {
      console.error(err);
    } finally {
      setSubmittingFeedback(false);
    }
  }

  return (
    <div className="space-y-4 py-4 border-b border-hairline/40 w-full max-w-3xl mx-auto px-4">
      {/* 1. User Message (Prompt) */}
      <div className="flex flex-col items-end gap-1.5 w-full">
        <div className="flex items-center gap-2 font-mono text-[9px] text-muted">
          <span>User</span>
          <span>•</span>
          <span>{time}</span>
        </div>
        <div className="bg-panel border border-hairline/60 text-paper px-4 py-2.5 rounded-2xl max-w-[85%] text-sm select-text">
          {record.prompt}
        </div>
      </div>

      {/* 2. Assistant Message (Response) */}
      <div className="flex flex-col items-start gap-1.5 w-full">
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-2 font-mono text-[9px] text-muted">
            <span className="text-brass font-bold">ControlPlane</span>
            <span>•</span>
            <span className="uppercase">{model}</span>
            {generated && (
              <>
                <span>•</span>
                <span className="text-brass-soft">
                  generated ({llm_provider})
                </span>
              </>
            )}
          </div>
          <div className="flex items-center gap-2">
            {override_status !== "none" && (
              <span
                className={`text-[9px] px-1.5 py-0.5 rounded font-mono uppercase tracking-wider font-semibold ${
                  override_status === "override_allow"
                    ? "bg-pass-soft text-pass border border-pass/30"
                    : "bg-block-soft text-block border border-block/30"
                }`}
              >
                Human Override:{" "}
                {override_status === "override_allow" ? "Allowed" : "Blocked"}
              </span>
            )}
            <SeverityBadge severity={severity} />
          </div>
        </div>

        <div
          className={`px-4 py-3 rounded-2xl max-w-[85%] text-sm relative select-text w-full ${
            severity === "block"
              ? "bg-block-soft/20 border border-block/30 text-block-soft"
              : "bg-panel/40 border border-hairline/40 text-paper/90"
          }`}
        >
          {severity === "block" ? (
            <div className="space-y-2">
              <p className="font-semibold text-block flex items-center gap-1.5 text-xs font-mono">
                <ShieldAlert size={14} />
                <span>RESPONSE BLOCKED BY SAFETY GATEWAY</span>
              </p>
              <p className="text-muted/80 text-xs italic">
                The original model response was withheld because of compliance
                violations.
              </p>
              {override_status === "override_allow" && (
                <p className="text-paper/80 pt-2 border-t border-hairline/20 mt-2 font-mono text-xs">
                  Original Response: &ldquo;{record.response}&rdquo;
                </p>
              )}
            </div>
          ) : (
            <p className="whitespace-pre-wrap">{record.response}</p>
          )}

          {feedback_text && (
            <div className="mt-3 bg-panel/75 border border-hairline/50 p-2.5 rounded-xl text-xs space-y-1">
              <div className="text-brass-soft font-mono text-[9px] uppercase tracking-wider flex items-center gap-1">
                <MessageSquare size={10} />
                <span>Human Feedback Notes</span>
              </div>
              <p className="text-muted italic">&ldquo;{feedback_text}&rdquo;</p>
            </div>
          )}
        </div>

        {/* 3. Action Buttons & Analysis Toggle */}
        <div className="flex flex-wrap items-center gap-3 mt-1 w-full pl-1">
          <button
            type="button"
            onClick={() => setShowAnalysis((v) => !v)}
            className={`font-mono text-[10px] uppercase tracking-wider flex items-center gap-1 ${
              showAnalysis
                ? "text-brass font-bold"
                : "text-muted hover:text-paper"
            }`}
          >
            <span>{showAnalysis ? "Hide Analysis" : "Compliance Report"}</span>
            <CornerDownRight size={10} />
          </button>

          {/* Override Action Buttons */}
          {override_status === "none" ? (
            <>
              {severity === "block" && (
                <button
                  type="button"
                  onClick={() =>
                    setShowOverrideInput(
                      showOverrideInput === "allow" ? null : "allow",
                    )
                  }
                  className="font-mono text-[10px] text-pass hover:underline uppercase tracking-wider"
                >
                  Override: Allow Response
                </button>
              )}
              {severity === "pass" && (
                <button
                  type="button"
                  onClick={() =>
                    setShowOverrideInput(
                      showOverrideInput === "block" ? null : "block",
                    )
                  }
                  className="font-mono text-[10px] text-block hover:underline uppercase tracking-wider"
                >
                  Override: Block Response
                </button>
              )}
            </>
          ) : (
            <button
              type="button"
              onClick={() => handleOverride("none")}
              disabled={submittingOverride}
              className="font-mono text-[10px] text-brass hover:underline uppercase tracking-wider flex items-center gap-1"
            >
              <RefreshCw
                size={10}
                className={submittingOverride ? "animate-spin" : ""}
              />
              <span>Reset Override</span>
            </button>
          )}
        </div>

        {/* 4. Analysis & Forms Panel */}
        {showAnalysis && (
          <div className="w-full bg-panel/30 border border-hairline/30 rounded-xl p-4 mt-2 space-y-4 animate-fade-in">
            {/* Readouts / Gauges */}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
              <Gauge label="Performance" score={checks.performance.score} />
              <Gauge label="Cost" score={checks.cost.score} />
              <Gauge
                label="Responsibility"
                score={checks.responsibility.score}
              />
              {checks.bias && <Gauge label="Bias" score={checks.bias.score} />}
              {checks.hallucination && (
                <Gauge
                  label="Hallucination"
                  score={checks.hallucination.score}
                />
              )}
              <Gauge
                label="Correlation"
                score={correlation.correlation_score}
              />
            </div>

            {/* Diagnostic Details */}
            <div className="space-y-1.5 pt-2 border-t border-hairline/20">
              <div className="flex items-start gap-1 text-[11px]">
                <span className="font-mono text-muted uppercase tracking-wider">
                  Gateway Decision:
                </span>
                <span className="font-mono text-paper font-semibold uppercase">
                  {severity}
                </span>
              </div>
              <div className="flex items-start gap-1 text-[11px]">
                <span className="font-mono text-muted uppercase tracking-wider">
                  Reason:
                </span>
                <span className="text-muted italic">{decision_reason}</span>
              </div>
              {override_status !== "none" && original_severity && (
                <div className="flex items-start gap-1 text-[11px]">
                  <span className="font-mono text-muted uppercase tracking-wider">
                    Originally:
                  </span>
                  <span className="text-muted italic">
                    {original_severity}, overridden to {severity}
                  </span>
                </div>
              )}

              {/* Correlation Flags */}
              {correlation.compound_flags.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {correlation.compound_flags.map((flag) => (
                    <span
                      key={flag}
                      className="rounded border border-signal/20 bg-signal/5 px-1.5 py-0.5 font-mono text-[9px] text-signal-soft"
                    >
                      {flag}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Human Override Forms */}
            {showOverrideInput && (
              <div className="bg-ink/60 border border-hairline p-3 rounded-lg space-y-2">
                <p className="font-mono text-[10px] uppercase text-brass-soft">
                  Provide a Reason for Human{" "}
                  {showOverrideInput === "allow" ? "Approval" : "Blocking"}
                </p>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={overrideReason}
                    onChange={(e) => setOverrideReason(e.target.value)}
                    placeholder="Enter reason (e.g. False positive PII, urgent customer fix)..."
                    className="flex-1 rounded bg-panel border border-hairline px-3 py-1 text-xs text-paper focus:outline-none focus:border-brass"
                  />
                  <button
                    type="button"
                    onClick={() =>
                      handleOverride(
                        showOverrideInput === "allow"
                          ? "override_allow"
                          : "override_block",
                        overrideReason,
                      )
                    }
                    disabled={submittingOverride}
                    className="bg-brass text-ink font-semibold px-3 py-1 rounded text-xs hover:brightness-105"
                  >
                    Confirm
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowOverrideInput(null);
                      setOverrideReason("");
                    }}
                    className="bg-panel border border-hairline px-2 py-1 rounded text-xs hover:text-paper"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {/* Feedback Loop Form */}
            <form
              onSubmit={handleFeedback}
              className="flex gap-2 pt-2 border-t border-hairline/20"
            >
              <select
                value={feedbackOverride}
                onChange={(e) =>
                  setFeedbackOverride(e.target.value as typeof feedbackOverride)
                }
                className="rounded bg-panel border border-hairline/60 px-2 py-1.5 text-xs text-paper focus:outline-none focus:border-brass/60"
              >
                <option value="correct">Correct</option>
                <option value="false_positive">False positive</option>
                <option value="false_negative">False negative</option>
              </select>
              <input
                type="text"
                value={feedbackInput}
                onChange={(e) => setFeedbackInput(e.target.value)}
                placeholder="Optional note for future threshold tuning..."
                className="flex-1 rounded bg-panel border border-hairline/60 px-3 py-1.5 text-xs text-paper focus:outline-none focus:border-brass/60"
              />
              <button
                type="submit"
                disabled={submittingFeedback}
                className="bg-panel border border-hairline/60 px-4 py-1.5 rounded text-xs font-mono text-muted hover:border-brass/40 hover:text-paper transition-colors"
              >
                {submittingFeedback ? "Saving..." : "Record Feedback"}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}

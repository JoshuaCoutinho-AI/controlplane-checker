import { useState } from 'react'
import type { ScoredResponse } from '../types'
import SeverityBadge from './SeverityBadge'

const GAUGE_COLOR = (score: number) =>
  score >= 65 ? 'text-pass' : score >= 30 ? 'text-log' : 'text-block'
const GAUGE_BAR = (score: number) =>
  score >= 65 ? 'bg-pass' : score >= 30 ? 'bg-log' : 'bg-block'

const LONG_TEXT_THRESHOLD = 420

function Gauge({ label, score }: { label: string; score: number }) {
  return (
    <div className="flex flex-col gap-1.5 min-w-[100px]">
      <div className="flex items-baseline justify-between">
        <span className="text-[10px] uppercase tracking-widest text-muted">{label}</span>
        <span className={`font-mono text-base font-medium tabular-nums ${GAUGE_COLOR(score)}`}>{score}</span>
      </div>
      <div className="h-1.5 rounded-full bg-hairline overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${GAUGE_BAR(score)}`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  )
}

function ExpandableText({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false)
  const isLong = text.length > LONG_TEXT_THRESHOLD
  const shown = isLong && !expanded ? `${text.slice(0, LONG_TEXT_THRESHOLD)}…` : text

  return (
    <span>
      {shown}
      {isLong && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="ml-2 font-mono text-xs font-medium text-signal-soft underline decoration-dotted underline-offset-2 hover:text-signal"
        >
          {expanded ? 'show less' : 'show full response'}
        </button>
      )}
    </span>
  )
}

export default function ResponseCard({ record }: { record: ScoredResponse }) {
  const { checks, correlation, severity, decision_reason, timestamp, model, session_id, generated, llm_provider } =
    record
  const time = new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })

  return (
    <article className="animate-fade-slide-up rounded-2xl border border-hairline bg-panel/60 p-6 shadow-panel">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 font-mono text-xs text-muted tabular-nums">
          <span>{time}</span>
          <span className="text-hairline">/</span>
          <span className="text-signal-soft">{model}</span>
          <span className="text-hairline">/</span>
          <span>{session_id}</span>
          {generated && (
            <>
              <span className="text-hairline">/</span>
              <span className="text-brass-soft">generated via {llm_provider}</span>
            </>
          )}
        </div>
        <SeverityBadge severity={severity} />
      </div>

      <div className="mt-4 space-y-3 text-base leading-relaxed">
        <p>
          <span className="mr-2 font-mono text-[10px] uppercase tracking-widest text-muted">Prompt</span>
          <span className="text-paper/90">{record.prompt}</span>
        </p>
        <p>
          <span className="mr-2 font-mono text-[10px] uppercase tracking-widest text-muted">Response</span>
          <span className="text-paper/70">
            <ExpandableText text={record.response} />
          </span>
        </p>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-x-5 gap-y-4 sm:grid-cols-4">
        <Gauge label="Performance" score={checks.performance.score} />
        <Gauge label="Cost" score={checks.cost.score} />
        <Gauge label="Responsibility" score={checks.responsibility.score} />
        <Gauge label="Correlation" score={correlation.correlation_score} />
      </div>

      {correlation.compound_flags.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-1.5">
          {correlation.compound_flags.map((flag) => (
            <span
              key={flag}
              className="rounded-md border border-signal/30 bg-signal/10 px-2 py-0.5 font-mono text-[10px] font-medium text-signal-soft"
            >
              {flag}
            </span>
          ))}
        </div>
      )}

      <p className="mt-4 border-t border-hairline pt-3 text-sm italic text-muted">{decision_reason}</p>
    </article>
  )
}

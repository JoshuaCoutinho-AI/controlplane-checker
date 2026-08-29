import { useEffect, useState } from 'react'
import { ArrowUp, Loader2 } from 'lucide-react'

const API_BASE = '/api'

const PROVIDERS = ['ollama', 'gemini'] as const
type Provider = (typeof PROVIDERS)[number]

interface Props {
  onScored?: () => void
}

/**
 * The signature interaction of this panel: a physical-feeling rocker
 * switch between the two real providers this app can call, rather than
 * a generic dropdown. It's the one choice that changes which real
 * model answers, so it earns a control that feels deliberate to use.
 */
function ProviderSwitch({ value, onChange }: { value: Provider; onChange: (p: Provider) => void }) {
  return (
    <div
      role="radiogroup"
      aria-label="Generation provider"
      className="relative inline-flex rounded-full border border-hairline bg-ink p-1 font-mono text-xs font-medium uppercase tracking-wide"
    >
      <div
        className="absolute inset-y-1 w-[calc(50%-4px)] rounded-full bg-brass shadow-glow transition-transform duration-300 ease-out"
        style={{ transform: value === 'gemini' ? 'translateX(100%)' : 'translateX(0)' }}
      />
      {PROVIDERS.map((p) => (
        <button
          key={p}
          type="button"
          role="radio"
          aria-checked={value === p}
          onClick={() => onChange(p)}
          className={`relative z-10 w-24 rounded-full py-2 transition-colors duration-300 ${
            value === p ? 'text-ink' : 'text-muted hover:text-paper'
          }`}
        >
          {p}
        </button>
      ))}
    </div>
  )
}

export default function ScoreForm({ onScored }: Props) {
  const [prompt, setPrompt] = useState('')
  const [response, setResponse] = useState('')
  const [model, setModel] = useState<Provider>(PROVIDERS[0])
  const [sessionId, setSessionId] = useState('manual-session')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastResult, setLastResult] = useState<{
    severity: string
    decision_reason: string
    generated: boolean
    llm_provider: string | null
    response: string
  } | null>(null)

  // Default the switch to the server's fallback provider on load. From
  // here, switching is just flipping the toggle — no .env edit or
  // restart, since the choice travels with each request.
  useEffect(() => {
    fetch(`${API_BASE}/llm/status`)
      .then((r) => r.json())
      .then((data) => {
        if (PROVIDERS.includes(data.default_provider)) setModel(data.default_provider)
      })
      .catch(() => {})
  }, [])

  const willGenerate = response.trim() === ''

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!prompt.trim()) {
      setError('A prompt is required.')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/score`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          response: response.trim() === '' ? null : response,
          model,
          session_id: sessionId || 'manual-session',
        }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail || `Server returned ${res.status}`)
      }
      const data = await res.json()
      setLastResult({
        severity: data.severity,
        decision_reason: data.decision_reason,
        generated: data.generated,
        llm_provider: data.llm_provider,
        response: data.response,
      })
      setPrompt('')
      setResponse('')
      onScored?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-3xl border border-hairline bg-panel p-3 shadow-float transition-shadow focus-within:shadow-glow"
    >
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Ask something — leave the response blank and a real model will answer it"
        rows={2}
        className="w-full resize-none bg-transparent px-3 py-2 text-lg text-paper placeholder:text-muted/70 focus:outline-none"
      />

      {showAdvanced && (
        <textarea
          value={response}
          onChange={(e) => setResponse(e.target.value)}
          placeholder="Or paste your own response here to test a specific scenario — e.g. one with an email address, to see it redacted and blocked"
          rows={2}
          className="mt-1 w-full resize-none rounded-2xl border border-hairline bg-ink px-3 py-2.5 text-sm text-paper placeholder:text-muted/70 focus:border-brass/60 focus:outline-none"
        />
      )}

      <div className="mt-2 flex flex-wrap items-center gap-2.5 px-1">
        <ProviderSwitch value={model} onChange={setModel} />

        <button
          type="button"
          onClick={() => setShowAdvanced((v) => !v)}
          className="rounded-full border border-hairline px-3 py-1.5 font-mono text-xs text-muted transition-colors hover:border-brass/40 hover:text-paper"
        >
          {showAdvanced ? 'hide custom response' : 'paste a response instead'}
        </button>

        {showAdvanced && (
          <input
            value={sessionId}
            onChange={(e) => setSessionId(e.target.value)}
            placeholder="session id"
            className="w-36 rounded-full border border-hairline bg-ink px-3 py-1.5 font-mono text-xs text-paper placeholder:text-muted/70 focus:border-brass/60 focus:outline-none"
          />
        )}

        <button
          type="submit"
          disabled={submitting}
          className="group ml-auto inline-flex h-11 w-11 items-center justify-center rounded-full bg-brass text-ink shadow-glow transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
          aria-label={willGenerate ? 'Generate and score' : 'Score it'}
          title={willGenerate ? 'Generate and score' : 'Score it'}
        >
          {submitting ? (
            <Loader2 size={18} className="animate-spin" />
          ) : (
            <ArrowUp size={18} className="transition-transform group-hover:-translate-y-0.5" />
          )}
        </button>
      </div>

      {error && <p className="mt-3 px-2 text-sm text-block">{error}</p>}
      {lastResult && !error && (
        <div className="mt-3 space-y-1 border-t border-hairline px-2 pt-3 text-sm">
          <p className="text-muted">
            <span className="font-mono font-semibold text-paper">{lastResult.severity}</span>
            {' — '}
            {lastResult.decision_reason}
            {lastResult.generated && <span className="text-brass-soft"> (via {lastResult.llm_provider})</span>}
          </p>
          {lastResult.generated && <p className="italic text-muted/80">&ldquo;{lastResult.response}&rdquo;</p>}
        </div>
      )}
    </form>
  )
}

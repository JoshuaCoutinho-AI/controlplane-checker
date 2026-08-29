import { useEffect, useState } from 'react'
import { ArrowUp, Loader2, SlidersHorizontal } from 'lucide-react'

const API_BASE = '/api'

const PROVIDERS = ['ollama', 'gemini'] as const
type Provider = (typeof PROVIDERS)[number]

interface Props {
  useCase: string
  onScored?: () => void
}

export default function ScoreForm({ useCase, onScored }: Props) {
  const [prompt, setPrompt] = useState('')
  const [response, setResponse] = useState('')
  const [model, setModel] = useState<Provider>(PROVIDERS[0])
  const [sessionId, setSessionId] = useState('demo-session')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${API_BASE}/llm/status`)
      .then((r) => r.json())
      .then((data) => {
        if (PROVIDERS.includes(data.default_provider)) setModel(data.default_provider)
      })
      .catch(() => {})
  }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!prompt.trim() || submitting) return
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
          use_case: useCase,
          session_id: sessionId || 'demo-session',
        }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail || `Server returned ${res.status}`)
      }
      setPrompt('')
      setResponse('')
      onScored?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit')
    } finally {
      setSubmitting(false)
    }
  }

  // Handle Enter to submit (Shift+Enter for newline)
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="w-full max-w-3xl mx-auto px-4 mt-auto">
      <form
        onSubmit={handleSubmit}
        className="relative bg-panel border border-hairline rounded-2xl shadow-lg p-3 transition-all focus-within:ring-1 focus-within:ring-brass/30 focus-within:border-brass/50"
      >
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Message ControlPlane Checker... (Press Enter to send)"
          rows={2}
          className="w-full resize-none bg-transparent px-3 py-1.5 text-base text-paper placeholder:text-muted/60 focus:outline-none pr-12"
        />

        {showAdvanced && (
          <div className="mt-3 border-t border-hairline pt-3 space-y-3">
            <div>
              <label className="block text-[10px] uppercase tracking-widest text-muted mb-1.5 font-mono">
                Paste Custom Response (Optional)
              </label>
              <textarea
                value={response}
                onChange={(e) => setResponse(e.target.value)}
                placeholder="Paste response text to bypass live generation (useful for PII / toxicity testing)..."
                rows={2}
                className="w-full resize-none rounded-xl border border-hairline bg-ink px-3 py-2 text-sm text-paper placeholder:text-muted/50 focus:border-brass/60 focus:outline-none"
              />
            </div>
            
            <div className="flex gap-4">
              <div className="flex-1">
                <label className="block text-[10px] uppercase tracking-widest text-muted mb-1.5 font-mono">
                  Session ID
                </label>
                <input
                  type="text"
                  value={sessionId}
                  onChange={(e) => setSessionId(e.target.value)}
                  placeholder="session id"
                  className="w-full rounded-xl border border-hairline bg-ink px-3 py-1.5 font-mono text-xs text-paper placeholder:text-muted/50 focus:border-brass/60 focus:outline-none"
                />
              </div>
            </div>
          </div>
        )}

        <div className="mt-2.5 flex items-center justify-between gap-3 border-t border-hairline/50 pt-2 px-1">
          <div className="flex items-center gap-3">
            {/* Model Select */}
            <div className="flex items-center rounded-full bg-ink border border-hairline p-0.5 font-mono text-[10px]">
              {PROVIDERS.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setModel(p)}
                  className={`rounded-full px-3 py-1 uppercase tracking-wider transition-colors ${
                    model === p ? 'bg-brass text-ink font-semibold' : 'text-muted hover:text-paper'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>

            {/* Advanced Toggle */}
            <button
              type="button"
              onClick={() => setShowAdvanced((v) => !v)}
              className={`flex items-center gap-1.5 rounded-full border px-3 py-1 font-mono text-[10px] transition-colors ${
                showAdvanced 
                  ? 'border-brass bg-brass/10 text-brass' 
                  : 'border-hairline text-muted hover:border-brass/40 hover:text-paper'
              }`}
            >
              <SlidersHorizontal size={10} />
              <span>Advanced</span>
            </button>
          </div>

          <button
            type="submit"
            disabled={submitting || !prompt.trim()}
            className="flex h-8 w-8 items-center justify-center rounded-full bg-paper text-ink transition-all hover:bg-brass hover:text-ink disabled:bg-hairline disabled:text-muted disabled:cursor-not-allowed"
          >
            {submitting ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <ArrowUp size={14} />
            )}
          </button>
        </div>
      </form>
      {error && <p className="mt-2 px-2 text-xs text-block font-mono">{error}</p>}
      <p className="mt-2 text-center text-[10px] text-muted/40">
        ControlPlane Checker can monitor, audit, and override LLM outputs in real-time.
      </p>
    </div>
  )
}

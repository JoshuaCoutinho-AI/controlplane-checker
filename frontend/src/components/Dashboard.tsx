import { useLiveFeed } from '../hooks/useLiveFeed'
import ResponseCard from './ResponseCard'
import ScoreForm from './ScoreForm'
import Pulseline from './Pulseline'
import ThemeToggle from './ThemeToggle'

export default function Dashboard() {
  const { records, connected } = useLiveFeed(100)
  const isEmpty = records.length === 0

  const counts = records.reduce(
    (acc, r) => {
      acc[r.severity] += 1
      return acc
    },
    { pass: 0, log: 0, block: 0 } as Record<'pass' | 'log' | 'block', number>,
  )

  return (
    <div className="min-h-screen bg-ink text-paper">
      <div className={`mx-auto max-w-3xl px-6 ${isEmpty ? 'flex min-h-screen flex-col justify-center py-10' : 'py-10'}`}>
        <header className={`flex flex-wrap items-start justify-between gap-4 ${isEmpty ? 'mb-10' : 'mb-8'}`}>
          <div>
            <div className="flex items-center gap-2.5">
              <span
                className={`h-2 w-2 rounded-full ${connected ? 'bg-pass animate-pulse-dot' : 'bg-block'}`}
                aria-hidden="true"
              />
              <h1 className="font-display text-2xl font-medium tracking-tight text-paper">
                ControlPlane <span className="text-brass">Checker</span>
              </h1>
            </div>
            <p className="mt-1.5 text-base text-muted">Live LLM response scoring &amp; severity routing</p>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex flex-col items-end gap-1.5">
              <div className="flex items-center gap-3 font-mono text-xs tabular-nums">
                <span className="text-pass">{counts.pass} pass</span>
                <span className="text-log">{counts.log} log</span>
                <span className="text-block">{counts.block} block</span>
                <span
                  className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-wide ${
                    connected
                      ? 'border-pass/40 bg-pass-soft text-pass'
                      : 'border-block/40 bg-block-soft text-block'
                  }`}
                >
                  {connected ? 'live' : 'reconnecting'}
                </span>
              </div>
              <Pulseline severities={records.map((r) => r.severity)} />
            </div>
            <ThemeToggle />
          </div>
        </header>

        {isEmpty && (
          <div className="mb-8 animate-fade-in text-center">
            <h2 className="font-display text-hero font-medium tracking-tight text-paper">
              What should we <span className="text-brass">check</span> today?
            </h2>
            <p className="mx-auto mt-3 max-w-md text-base text-muted">
              Type a prompt below. Leave the response blank to generate one live, or paste your own to test a
              specific scenario.
            </p>
          </div>
        )}

        <ScoreForm />

        {!isEmpty && (
          <div className="mt-8 grid gap-4">
            {records.map((record) => (
              <ResponseCard key={record.id} record={record} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

import type { Severity } from '../types'

const TICK_COLOR: Record<Severity, string> = {
  pass: 'bg-pass',
  log: 'bg-log',
  block: 'bg-block',
}

const GLOW: Record<Severity, string> = {
  pass: 'shadow-[0_0_8px_1px_rgb(var(--c-pass)/0.7)]',
  log: 'shadow-[0_0_8px_1px_rgb(var(--c-log)/0.7)]',
  block: 'shadow-[0_0_8px_1px_rgb(var(--c-block)/0.7)]',
}

/**
 * The one signature, memorable element of this design: a live strip of
 * recent severities, oldest to newest left-to-right, that grows as
 * scored responses arrive over the WebSocket. It's not decoration —
 * it's the same severity data as the feed below, just compressed into
 * an at-a-glance "systems nominal" readout, the way an instrument
 * panel would show a running trend rather than only the latest value.
 */
export default function Pulseline({ severities }: { severities: Severity[] }) {
  const visible = severities.slice(0, 28).reverse() // oldest -> newest, left -> right

  return (
    <div className="flex items-center gap-[3px] h-5 px-1" aria-hidden="true">
      {visible.length === 0 ? (
        <span className="text-[10px] text-muted font-mono tracking-wide">awaiting signal</span>
      ) : (
        visible.map((sev, i) => {
          const isNewest = i === visible.length - 1
          return (
            <span
              key={i}
              className={`w-[3px] rounded-full transition-all duration-300 ${TICK_COLOR[sev]} ${
                isNewest ? `h-4 ${GLOW[sev]} animate-pulse-dot` : 'h-2.5 opacity-70'
              }`}
            />
          )
        })
      )}
    </div>
  )
}

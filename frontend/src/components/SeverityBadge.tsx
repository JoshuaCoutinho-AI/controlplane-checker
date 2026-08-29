import { CheckCircle2, AlertTriangle, XCircle } from 'lucide-react'
import type { Severity } from '../types'

const STYLES: Record<Severity, string> = {
  pass: 'bg-pass-soft text-pass border-pass/40',
  log: 'bg-log-soft text-log border-log/40',
  block: 'bg-block-soft text-block border-block/40',
}

const LABELS: Record<Severity, string> = {
  pass: 'Pass',
  log: 'Log',
  block: 'Block',
}

const ICONS: Record<Severity, typeof CheckCircle2> = {
  pass: CheckCircle2,
  log: AlertTriangle,
  block: XCircle,
}

export default function SeverityBadge({ severity }: { severity: Severity }) {
  const Icon = ICONS[severity]
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold font-mono tracking-wide uppercase border ${STYLES[severity]}`}
    >
      <Icon size={13} strokeWidth={2.5} />
      {LABELS[severity]}
    </span>
  )
}

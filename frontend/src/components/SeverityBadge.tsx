import type { Severity } from '../types'

const STYLES: Record<Severity, string> = {
  critical: 'bg-red-950 text-red-300 border-red-800',
  high: 'bg-orange-950 text-orange-300 border-orange-800',
  medium: 'bg-yellow-950 text-yellow-300 border-yellow-800',
  low: 'bg-blue-950 text-blue-300 border-blue-800',
  info: 'bg-slate-800 text-slate-300 border-slate-700',
}

const LABELS: Record<Severity, string> = {
  critical: 'Kritik',
  high: 'Yuksek',
  medium: 'Orta',
  low: 'Dusuk',
  info: 'Bilgi',
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-medium ${STYLES[severity]}`}>
      {LABELS[severity]}
    </span>
  )
}

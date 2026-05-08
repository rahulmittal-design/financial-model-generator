interface Props { value: number | null }

export default function ConfidenceBadge({ value }: Props) {
  if (value === null || value === undefined) return <span className="text-gray-400 text-xs">—</span>
  const pct = Math.round(value * 100)
  const cls = pct >= 85 ? 'text-green-600' : pct >= 60 ? 'text-yellow-600' : 'text-red-500'
  return <span className={`text-xs font-medium ${cls}`}>{pct}%</span>
}

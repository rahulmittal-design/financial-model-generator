interface Props {
  status: string
  size?: 'sm' | 'md'
}

const STATUS_STYLES: Record<string, string> = {
  pending:    'bg-gray-100 text-gray-600',
  processing: 'bg-yellow-100 text-yellow-700 animate-pulse',
  extracted:  'bg-green-100 text-green-700',
  failed:     'bg-red-100 text-red-700',
  approved:   'bg-green-100 text-green-700',
  rejected:   'bg-red-100 text-red-700',
  edited:     'bg-blue-100 text-blue-700',
  unknown:    'bg-gray-100 text-gray-500',
  income_statement: 'bg-blue-100 text-blue-700',
  balance_sheet:    'bg-purple-100 text-purple-700',
  cash_flow:        'bg-teal-100 text-teal-700',
  note:             'bg-orange-100 text-orange-600',
}

const STATUS_LABELS: Record<string, string> = {
  pending:    'Pending',
  processing: 'Processing…',
  extracted:  'Extracted',
  failed:     'Failed',
  approved:   'Approved',
  rejected:   'Rejected',
  edited:     'Edited',
  unknown:    'Unknown',
  income_statement: 'Income Stmt',
  balance_sheet:    'Balance Sheet',
  cash_flow:        'Cash Flow',
  note:             'Note',
}

export default function StatusBadge({ status, size = 'sm' }: Props) {
  const cls = STATUS_STYLES[status] ?? 'bg-gray-100 text-gray-500'
  const label = STATUS_LABELS[status] ?? status
  return (
    <span className={`inline-flex items-center rounded-full font-medium ${size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm'} ${cls}`}>
      {label}
    </span>
  )
}

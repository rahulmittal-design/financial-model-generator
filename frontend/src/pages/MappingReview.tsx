import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, CheckCircle2, XCircle, AlertCircle, Filter, ThumbsUp, Loader2 } from 'lucide-react'
import { mappingApi } from '../api/client'
import type { LineItem, StatementType } from '../types'
import StatusBadge from '../components/StatusBadge'
import ConfidenceBadge from '../components/ConfidenceBadge'

const STMT_TABS: { key: StatementType | 'all'; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'income_statement', label: 'Income Statement' },
  { key: 'balance_sheet', label: 'Balance Sheet' },
  { key: 'cash_flow', label: 'Cash Flow' },
]

const REVIEW_FILTER = ['all', 'pending', 'approved', 'rejected']

export default function MappingReview() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [stmtTab, setStmtTab] = useState<string>('all')
  const [reviewFilter, setReviewFilter] = useState('all')

  const { data: items = [], isLoading } = useQuery({
    queryKey: ['line-items', projectId],
    queryFn: () => mappingApi.listLineItems(projectId!),
    enabled: !!projectId,
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: object }) =>
      mappingApi.updateLineItem(projectId!, id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['line-items', projectId] }),
  })

  const bulkApproveMutation = useMutation({
    mutationFn: () => mappingApi.bulkApprove(projectId!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['line-items', projectId] }),
  })

  const filtered = items.filter(item => {
    if (stmtTab !== 'all' && item.statement_type !== stmtTab) return false
    if (reviewFilter !== 'all' && item.review_status !== reviewFilter) return false
    return true
  })

  // Group by period
  const periods = [...new Set(items.map(i => i.period).filter(Boolean))].sort()
  const pendingCount = items.filter(i => i.review_status === 'pending').length

  const setStatus = (item: LineItem, status: string) =>
    updateMutation.mutate({ id: item.id, data: { review_status: status } })

  return (
    <div>
      <div className="flex items-center gap-2 text-sm text-gray-500 mb-6">
        <button onClick={() => navigate(`/projects/${projectId}`)} className="hover:text-blue-600 flex items-center gap-1">
          <ArrowLeft className="w-4 h-4" /> Back to Project
        </button>
        <span>/</span>
        <span className="text-gray-900 font-medium">Line-Item Mapping Review</span>
      </div>

      {/* Stats bar */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6 flex flex-wrap gap-6 items-center">
        <div className="text-center">
          <p className="text-2xl font-bold text-gray-900">{items.length}</p>
          <p className="text-xs text-gray-500">Total items</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-yellow-600">{pendingCount}</p>
          <p className="text-xs text-gray-500">Pending review</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-green-600">{items.filter(i => i.review_status === 'approved').length}</p>
          <p className="text-xs text-gray-500">Approved</p>
        </div>
        <div className="ml-auto">
          <button
            onClick={() => bulkApproveMutation.mutate()}
            disabled={bulkApproveMutation.isPending || pendingCount === 0}
            className="bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white text-sm font-medium px-4 py-2 rounded-lg flex items-center gap-2"
          >
            {bulkApproveMutation.isPending
              ? <><Loader2 className="w-4 h-4 animate-spin" /> Approving…</>
              : <><ThumbsUp className="w-4 h-4" /> Bulk Approve High-Confidence</>}
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <div className="flex bg-gray-100 rounded-lg p-1 gap-1">
          {STMT_TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => setStmtTab(tab.key)}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                stmtTab === tab.key ? 'bg-white shadow text-blue-700' : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 ml-auto">
          <Filter className="w-4 h-4 text-gray-400" />
          <select
            value={reviewFilter}
            onChange={e => setReviewFilter(e.target.value)}
            className="text-sm border border-gray-300 rounded-lg px-2 py-1.5 focus:ring-2 focus:ring-blue-500 outline-none"
          >
            {REVIEW_FILTER.map(f => (
              <option key={f} value={f}>{f === 'all' ? 'All statuses' : f.charAt(0).toUpperCase() + f.slice(1)}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="text-center py-16 text-gray-400">Loading line items…</div>
        ) : filtered.length === 0 ? (
          <div className="flex items-center justify-center gap-2 text-gray-400 py-16">
            <AlertCircle className="w-5 h-5" />
            <span>No items match the current filters.</span>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">Source Label</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">Mapped To</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">Period</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wide">Value</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase tracking-wide">Confidence</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase tracking-wide">Status</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase tracking-wide">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.map(item => (
                  <tr key={item.id} className={`hover:bg-gray-50 ${item.review_status === 'pending' && (item.mapping_confidence ?? 0) < 0.6 ? 'bg-yellow-50' : ''}`}>
                    <td className="px-4 py-2.5">
                      <span className="text-gray-800 font-medium">{item.source_label}</span>
                      {item.source_page && (
                        <span className="ml-2 text-xs text-gray-400">p.{item.source_page}</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      {item.standard_label ? (
                        <div>
                          <span className="text-gray-800">{item.standard_label}</span>
                          <span className="ml-2 text-xs text-gray-400 font-mono">{item.standard_id}</span>
                        </div>
                      ) : (
                        <span className="text-gray-400 italic text-xs">No match</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-gray-600">{item.period ?? '—'}</td>
                    <td className="px-4 py-2.5 text-right font-mono text-gray-700 text-xs">
                      {item.normalized_value !== null
                        ? item.normalized_value.toLocaleString()
                        : item.raw_value ?? '—'}
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      <ConfidenceBadge value={item.mapping_confidence} />
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      <StatusBadge status={item.review_status} />
                    </td>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center justify-center gap-1">
                        <button
                          title="Approve"
                          onClick={() => setStatus(item, 'approved')}
                          disabled={item.review_status === 'approved'}
                          className="p-1 rounded text-gray-400 hover:text-green-600 disabled:opacity-30"
                        >
                          <CheckCircle2 className="w-4 h-4" />
                        </button>
                        <button
                          title="Reject"
                          onClick={() => setStatus(item, 'rejected')}
                          disabled={item.review_status === 'rejected'}
                          className="p-1 rounded text-gray-400 hover:text-red-500 disabled:opacity-30"
                        >
                          <XCircle className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Period summary */}
      {periods.length > 0 && (
        <div className="mt-4 text-xs text-gray-400 text-right">
          Detected periods: {periods.join(', ')}
        </div>
      )}
    </div>
  )
}

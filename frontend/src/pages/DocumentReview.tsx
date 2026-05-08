import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Table2, AlertCircle } from 'lucide-react'
import { documentsApi } from '../api/client'
import StatusBadge from '../components/StatusBadge'
import ConfidenceBadge from '../components/ConfidenceBadge'

const TABLE_TYPES = ['income_statement', 'balance_sheet', 'cash_flow', 'note', 'unknown']

export default function DocumentReview() {
  const { projectId, docId } = useParams<{ projectId: string; docId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: doc } = useQuery({
    queryKey: ['document', projectId, docId],
    queryFn: () => documentsApi.list(projectId!).then(docs => docs.find(d => d.id === docId)),
    enabled: !!(projectId && docId),
  })

  const { data: tables = [], isLoading } = useQuery({
    queryKey: ['tables', projectId, docId],
    queryFn: () => documentsApi.getTables(projectId!, docId!),
    enabled: !!(projectId && docId),
  })

  const updateTypeMutation = useMutation({
    mutationFn: ({ tableId, table_type }: { tableId: string; table_type: string }) =>
      documentsApi.updateTableType(projectId!, docId!, tableId, table_type),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tables', projectId, docId] }),
  })

  return (
    <div>
      <div className="flex items-center gap-2 text-sm text-gray-500 mb-6">
        <button onClick={() => navigate(`/projects/${projectId}`)} className="hover:text-blue-600 flex items-center gap-1">
          <ArrowLeft className="w-4 h-4" /> Back to Project
        </button>
        {doc && <><span>/</span><span className="text-gray-900 font-medium">{doc.file_name}</span></>}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h1 className="text-xl font-bold text-gray-900 mb-1">Document Review</h1>
        {doc && (
          <div className="flex flex-wrap gap-4 text-sm text-gray-500 mt-2">
            <span>{doc.file_name}</span>
            {doc.page_count && <span>{doc.page_count} pages</span>}
            {doc.detected_year && <span>FY{doc.detected_year}</span>}
            {doc.detected_currency && <span>{doc.detected_currency}</span>}
            {doc.detected_scale && <span>{doc.detected_scale}</span>}
            <StatusBadge status={doc.status} />
          </div>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Table2 className="w-4 h-4 text-blue-500" />
          Extracted Tables ({tables.length})
        </h2>

        {isLoading ? (
          <div className="text-center py-10 text-gray-400">Loading tables…</div>
        ) : tables.length === 0 ? (
          <div className="flex items-center gap-2 text-gray-400 py-8 justify-center">
            <AlertCircle className="w-5 h-5" />
            <span>No tables extracted from this document.</span>
          </div>
        ) : (
          <div className="space-y-6">
            {tables.map(tbl => (
              <div key={tbl.id} className="border border-gray-200 rounded-xl overflow-hidden">
                {/* Table header */}
                <div className="bg-gray-50 px-4 py-3 flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-gray-700">
                      Page {tbl.page_number ?? '?'}
                    </span>
                    <ConfidenceBadge value={tbl.detection_confidence} />
                    {tbl.detected_periods && tbl.detected_periods.length > 0 && (
                      <span className="text-xs text-gray-500">
                        {tbl.detected_periods.join(', ')}
                      </span>
                    )}
                    {tbl.user_confirmed && (
                      <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                        Confirmed
                      </span>
                    )}
                  </div>
                  <select
                    value={tbl.table_type}
                    onChange={e => updateTypeMutation.mutate({ tableId: tbl.id, table_type: e.target.value })}
                    className="text-sm border border-gray-300 rounded-lg px-2 py-1 focus:ring-2 focus:ring-blue-500 outline-none"
                  >
                    {TABLE_TYPES.map(t => (
                      <option key={t} value={t}>
                        {t.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Table data */}
                {tbl.headers && tbl.headers.length > 0 && (
                  <div className="overflow-x-auto">
                    <table className="min-w-full text-xs">
                      <thead>
                        <tr className="bg-blue-50">
                          {tbl.headers.map((h, i) => (
                            <th key={i} className="px-3 py-2 text-left font-medium text-blue-800 whitespace-nowrap">
                              {h || '—'}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {(tbl.raw_data ?? []).slice(0, 20).map((row, ri) => (
                          <tr key={ri} className="hover:bg-gray-50">
                            {(tbl.headers ?? []).map((h, ci) => (
                              <td key={ci} className="px-3 py-1.5 text-gray-700 whitespace-nowrap">
                                {row[h] ?? ''}
                              </td>
                            ))}
                          </tr>
                        ))}
                        {(tbl.raw_data ?? []).length > 20 && (
                          <tr>
                            <td colSpan={(tbl.headers ?? []).length} className="px-3 py-2 text-center text-gray-400 text-xs">
                              … {(tbl.raw_data ?? []).length - 20} more rows
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

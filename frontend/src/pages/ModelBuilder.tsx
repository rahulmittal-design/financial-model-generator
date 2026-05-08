import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { modelApi, type StatementTable, type FinancialModel } from '../api/client'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts'
import { BarChart2, RefreshCw, Download, ChevronDown, ChevronUp, Sparkles } from 'lucide-react'

const fmt = (v: number | null | undefined): string =>
  v == null ? '—' : v >= 1e9 ? `${(v / 1e9).toFixed(1)}B` : v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : v.toFixed(1)

function StatementSection({ table }: { table: StatementTable }) {
  const [collapsed, setCollapsed] = useState(false)

  const chartData = table.periods.map((p: string) => {
    const obj: Record<string, string | number> = { period: p }
    table.rows
      .filter((r) => r.is_derived)
      .forEach((r) => { obj[r.standard_label] = r.values[p] ?? 0 })
    return obj
  })
  const derivedKeys = table.rows.filter((r) => r.is_derived).map((r) => r.standard_label).slice(0, 5)
  const COLORS = ['#4f46e5', '#0891b2', '#059669', '#d97706', '#dc2626']

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center justify-between px-5 py-3 hover:bg-gray-50"
      >
        <h3 className="font-semibold text-gray-800 capitalize">
          {table.statement_type.replace(/_/g, ' ')}
        </h3>
        {collapsed ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronUp className="w-4 h-4 text-gray-400" />}
      </button>

      {!collapsed && (
        <div className="px-5 pb-5 space-y-4">
          {derivedKeys.length > 0 && (
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => fmt(v)} />
                  <Tooltip formatter={(v: number) => fmt(v)} />
                  <Legend />
                  {derivedKeys.map((k: string, i: number) => (
                    <Bar key={k} dataKey={k} fill={COLORS[i % COLORS.length]} radius={[3, 3, 0, 0]} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-2 font-medium text-gray-600 pr-4 min-w-[200px]">Line Item</th>
                  {table.periods.map((p: string) => (
                    <th key={p} className="text-right py-2 font-medium text-gray-600 px-3 whitespace-nowrap">{p}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {table.rows.map((row) => (
                  <tr
                    key={row.standard_id}
                    className={`border-b border-gray-100 ${row.is_derived ? 'bg-blue-50 font-semibold' : 'hover:bg-gray-50'}`}
                  >
                    <td className="py-1.5 pr-4 text-gray-700">
                      {row.standard_label}
                      {row.source === 'llm' && (
                        <span className="ml-1 text-xs text-indigo-500">✦ LLM</span>
                      )}
                    </td>
                    {table.periods.map((p: string) => (
                      <td key={p} className="py-1.5 px-3 text-right text-gray-700 tabular-nums">
                        {fmt(row.values[p])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

function RatiosSection({ ratios, periods }: { ratios: FinancialModel['key_ratios']; periods: string[] }) {
  const RATIO_LABELS: Record<string, string> = {
    gross_margin: 'Gross Margin (%)',
    operating_margin: 'Operating Margin (%)',
    net_margin: 'Net Margin (%)',
    ebitda_margin: 'EBITDA Margin (%)',
    return_on_assets: 'Return on Assets (%)',
    return_on_equity: 'Return on Equity (%)',
    debt_to_equity: 'Debt / Equity (×)',
    fcf_margin: 'FCF Margin (%)',
    capex_to_revenue: 'CapEx / Revenue (%)',
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-100">
        <h3 className="font-semibold text-gray-800">Key Ratios</h3>
      </div>
      <div className="overflow-x-auto px-5 pb-5">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-2 font-medium text-gray-600 pr-4 min-w-[200px]">Ratio</th>
              {periods.map((p: string) => (
                <th key={p} className="text-right py-2 font-medium text-gray-600 px-3 whitespace-nowrap">{p}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Object.entries(RATIO_LABELS).map(([key, label]) => {
              const row = ratios[key]
              if (!row) return null
              return (
                <tr key={key} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-1.5 pr-4 text-gray-700">{label}</td>
                  {periods.map((p: string) => (
                    <td key={p} className="py-1.5 px-3 text-right tabular-nums text-gray-700">
                      {row[p] != null ? row[p]!.toFixed(1) : '—'}
                    </td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function ModelBuilder() {
  const { projectId } = useParams<{ projectId: string }>()
  const qc = useQueryClient()
  const [useLlm, setUseLlm] = useState(true)

  const { data: model, isLoading, error } = useQuery({
    queryKey: ['model', projectId],
    queryFn: () => modelApi.getModel(projectId!),
    retry: false,
  })

  const buildMut = useMutation({
    mutationFn: () => modelApi.buildModel(projectId!, useLlm),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['model', projectId] }),
  })

  const exportMut = useMutation({
    mutationFn: () => modelApi.exportExcel(projectId!),
    onSuccess: (blob: Blob) => {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'FinancialModel.xlsx'
      a.click()
      URL.revokeObjectURL(url)
    },
  })

  const periods = model?.income_statement.periods ?? []

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <BarChart2 className="w-8 h-8 text-indigo-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Financial Model</h1>
            <p className="text-sm text-gray-500">Historical 3-statement model assembled from extracted data</p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
            <input type="checkbox" checked={useLlm} onChange={e => setUseLlm(e.target.checked)} className="rounded" />
            <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
            Use LLM enhancement
          </label>
          <button
            onClick={() => buildMut.mutate()}
            disabled={buildMut.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${buildMut.isPending ? 'animate-spin' : ''}`} />
            {model ? 'Rebuild Model' : 'Build Model'}
          </button>
          {model && (
            <button
              onClick={() => exportMut.mutate()}
              disabled={exportMut.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition-colors"
            >
              <Download className="w-4 h-4" />
              Export Excel
            </button>
          )}
        </div>
      </div>

      {buildMut.isError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
          {(buildMut.error as Error)?.message}
        </div>
      )}

      {isLoading && <div className="text-center py-20 text-gray-400">Loading model…</div>}

      {!isLoading && !model && !error && (
        <div className="text-center py-20 space-y-3">
          <BarChart2 className="w-12 h-12 text-gray-300 mx-auto" />
          <p className="text-gray-500">No model built yet.</p>
          <p className="text-sm text-gray-400">Click "Build Model" to assemble the 3-statement model from approved line items.</p>
        </div>
      )}

      {model && (
        <div className="space-y-4">
          <StatementSection table={model.income_statement} />
          <StatementSection table={model.balance_sheet} />
          <StatementSection table={model.cash_flow} />
          {Object.keys(model.key_ratios).length > 0 && (
            <RatiosSection ratios={model.key_ratios} periods={periods} />
          )}
        </div>
      )}
    </div>
  )
}

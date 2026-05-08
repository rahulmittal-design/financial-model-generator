import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { modelApi } from '../api/client'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Legend, ReferenceLine,
} from 'recharts'
import { TrendingUp, RefreshCw, Download, Sparkles } from 'lucide-react'

const fmt = (v: number | null | undefined): string =>
  v == null ? '—' : v >= 1e9 ? `${(v / 1e9).toFixed(2)}B` : v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : v.toFixed(1)

const KEY_ITEMS = ['revenue', 'gross_profit', 'operating_income', 'net_income', 'ebitda', 'free_cash_flow']
const COLORS = ['#4f46e5', '#0891b2', '#059669', '#d97706', '#dc2626', '#7c3aed']

export default function ForecastView() {
  const { projectId } = useParams<{ projectId: string }>()
  const qc = useQueryClient()
  const [forecastYears, setForecastYears] = useState(3)
  const [useLlm, setUseLlm] = useState(true)

  const { data: model } = useQuery({
    queryKey: ['model', projectId],
    queryFn: () => modelApi.getModel(projectId!),
    retry: false,
  })

  const { data: forecast, isLoading, error } = useQuery({
    queryKey: ['forecast', projectId],
    queryFn: () => modelApi.getForecast(projectId!),
    retry: false,
  })

  const runMut = useMutation({
    mutationFn: () => modelApi.runForecast(projectId!, forecastYears, useLlm),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['forecast', projectId] }),
  })

  const exportMut = useMutation({
    mutationFn: () => modelApi.exportExcel(projectId!, true),
    onSuccess: (blob: Blob) => {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'FinancialModel_WithForecast.xlsx'
      a.click()
      URL.revokeObjectURL(url)
    },
  })

  const histPeriods = model?.income_statement.periods ?? []
  const fcPeriods = forecast?.forecast_periods ?? []
  const allPeriods = [...new Set([...histPeriods, ...fcPeriods])].sort()
  const lastHistPeriod = histPeriods[histPeriods.length - 1]

  const chartData = allPeriods.map((p: string) => {
    const obj: Record<string, string | number | null> = { period: p }
    KEY_ITEMS.forEach((sid: string) => {
      const histRow = model?.income_statement.rows.find((r) => r.standard_id === sid)
        ?? model?.cash_flow.rows.find((r) => r.standard_id === sid)
      if (histRow?.values[p] != null) {
        obj[sid] = histRow.values[p]
      } else if (forecast?.forecast[sid]?.[p] != null) {
        obj[sid] = forecast.forecast[sid][p]
      } else {
        obj[sid] = null
      }
    })
    return obj
  })

  const getAssumption = (sid: string): string | null => {
    const a = forecast?.assumptions?.[sid]
    if (!a) return null
    if (typeof a === 'string') return a
    const typed = a as { growth_rate: number; rationale: string }
    return `${(typed.growth_rate * 100).toFixed(1)}% growth — ${typed.rationale}`
  }

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <TrendingUp className="w-8 h-8 text-green-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Forecast</h1>
            <p className="text-sm text-gray-500">LLM-driven projections with growth assumptions</p>
          </div>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <label className="flex items-center gap-2 text-sm text-gray-600">
            Years:
            <select
              value={forecastYears}
              onChange={e => setForecastYears(Number(e.target.value))}
              className="border border-gray-300 rounded px-2 py-1 text-sm"
            >
              {[1, 2, 3, 4, 5].map(y => <option key={y} value={y}>{y}</option>)}
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
            <input type="checkbox" checked={useLlm} onChange={e => setUseLlm(e.target.checked)} className="rounded" />
            <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
            LLM assumptions
          </label>
          <button
            onClick={() => runMut.mutate()}
            disabled={runMut.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${runMut.isPending ? 'animate-spin' : ''}`} />
            {forecast ? 'Re-run Forecast' : 'Run Forecast'}
          </button>
          {forecast && (
            <button
              onClick={() => exportMut.mutate()}
              disabled={exportMut.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              <Download className="w-4 h-4" />
              Export Excel
            </button>
          )}
        </div>
      </div>

      {runMut.isError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
          {(runMut.error as Error)?.message}
        </div>
      )}

      {!isLoading && !forecast && !error && (
        <div className="text-center py-20 space-y-3">
          <TrendingUp className="w-12 h-12 text-gray-300 mx-auto" />
          <p className="text-gray-500">No forecast yet. Click "Run Forecast" to generate projections.</p>
        </div>
      )}

      {forecast && (
        <>
          <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
            <h3 className="font-semibold text-gray-800">Key Metrics — Historical + Forecast</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => fmt(v)} />
                  <Tooltip formatter={(v: number) => fmt(v)} />
                  <Legend />
                  {lastHistPeriod && (
                    <ReferenceLine
                      x={lastHistPeriod}
                      stroke="#94a3b8"
                      strokeDasharray="4 4"
                      label={{ value: 'Forecast →', position: 'top', fontSize: 11 }}
                    />
                  )}
                  {KEY_ITEMS.map((sid: string, i: number) => (
                    <Line
                      key={sid}
                      type="monotone"
                      dataKey={sid}
                      name={sid.replace(/_/g, ' ')}
                      stroke={COLORS[i % COLORS.length]}
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      connectNulls
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-800 mb-3">Forecast Assumptions</h3>
            <div className="space-y-2">
              {KEY_ITEMS.map((sid: string) => {
                const assumption = getAssumption(sid)
                if (!assumption) return null
                return (
                  <div key={sid} className="flex gap-3 text-sm">
                    <span className="font-medium text-gray-700 w-40 shrink-0">{sid.replace(/_/g, ' ')}</span>
                    <span className="text-gray-500">{assumption}</span>
                  </div>
                )
              })}
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-100">
              <h3 className="font-semibold text-gray-800">Forecast Values</h3>
            </div>
            <div className="overflow-x-auto px-5 pb-5">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-2 font-medium text-gray-600 pr-4 min-w-[200px]">Line Item</th>
                    {fcPeriods.map((p: string) => (
                      <th key={p} className="text-right py-2 px-3 font-medium text-green-700 whitespace-nowrap">{p}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {KEY_ITEMS.map((sid: string) => {
                    const vals = forecast.forecast[sid]
                    if (!vals) return null
                    return (
                      <tr key={sid} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="py-1.5 pr-4 text-gray-700">
                          {sid.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())}
                        </td>
                        {fcPeriods.map((p: string) => (
                          <td key={p} className="py-1.5 px-3 text-right tabular-nums text-green-700">
                            {fmt(vals[p])}
                          </td>
                        ))}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

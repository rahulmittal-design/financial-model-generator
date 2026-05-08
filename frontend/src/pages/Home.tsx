import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Building2, FileText, Trash2, ChevronRight, AlertCircle } from 'lucide-react'
import { projectsApi } from '../api/client'
import type { ProjectCreate } from '../types'

export default function Home() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [showNew, setShowNew] = useState(false)
  const [form, setForm] = useState<ProjectCreate>({ company_name: '', ticker: '', sector: '', base_currency: 'USD' })
  const [error, setError] = useState<string | null>(null)

  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  })

  const createMutation = useMutation({
    mutationFn: projectsApi.create,
    onSuccess: (p) => {
      qc.invalidateQueries({ queryKey: ['projects'] })
      setShowNew(false)
      setForm({ company_name: '', ticker: '', sector: '', base_currency: 'USD' })
      navigate(`/projects/${p.id}`)
    },
    onError: (e: Error) => setError(e.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => projectsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  })

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.company_name.trim()) { setError('Company name is required'); return }
    setError(null)
    createMutation.mutate(form)
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Projects</h1>
          <p className="text-sm text-gray-500 mt-1">Each project holds annual reports for one company.</p>
        </div>
        <button
          onClick={() => setShowNew(true)}
          className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" /> New Project
        </button>
      </div>

      {/* New project form */}
      {showNew && (
        <div className="bg-white border border-blue-200 rounded-xl p-6 mb-6 shadow-sm">
          <h2 className="font-semibold text-gray-900 mb-4">New Project</h2>
          {error && (
            <div className="flex items-center gap-2 text-red-600 text-sm mb-3 bg-red-50 rounded-lg p-3">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />{error}
            </div>
          )}
          <form onSubmit={handleCreate} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Company Name *</label>
              <input
                type="text" required
                value={form.company_name}
                onChange={e => setForm(f => ({ ...f, company_name: e.target.value }))}
                placeholder="e.g. Reliance Industries"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Ticker</label>
              <input
                type="text"
                value={form.ticker ?? ''}
                onChange={e => setForm(f => ({ ...f, ticker: e.target.value }))}
                placeholder="e.g. RELIANCE"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Sector</label>
              <input
                type="text"
                value={form.sector ?? ''}
                onChange={e => setForm(f => ({ ...f, sector: e.target.value }))}
                placeholder="e.g. Energy"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Base Currency</label>
              <select
                value={form.base_currency ?? 'USD'}
                onChange={e => setForm(f => ({ ...f, base_currency: e.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              >
                {['USD', 'GBP', 'EUR', 'INR', 'JPY', 'SGD', 'AUD', 'HKD'].map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div className="sm:col-span-2 flex gap-3 pt-2">
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium px-5 py-2 rounded-lg transition-colors"
              >
                {createMutation.isPending ? 'Creating…' : 'Create Project'}
              </button>
              <button
                type="button"
                onClick={() => { setShowNew(false); setError(null) }}
                className="text-gray-600 hover:text-gray-800 text-sm px-4 py-2 rounded-lg border border-gray-300 transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Project list */}
      {isLoading ? (
        <div className="text-center py-20 text-gray-400">Loading projects…</div>
      ) : projects.length === 0 ? (
        <div className="text-center py-20">
          <Building2 className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">No projects yet</p>
          <p className="text-gray-400 text-sm mt-1">Create one to get started.</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map(p => (
            <div
              key={p.id}
              className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md hover:border-blue-300 transition-all cursor-pointer group"
              onClick={() => navigate(`/projects/${p.id}`)}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="bg-blue-100 rounded-lg p-2 flex-shrink-0">
                    <Building2 className="w-5 h-5 text-blue-600" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-semibold text-gray-900 truncate">{p.company_name}</h3>
                    {p.ticker && <p className="text-xs text-gray-500">{p.ticker}</p>}
                  </div>
                </div>
                <button
                  onClick={e => { e.stopPropagation(); if (confirm('Delete this project?')) deleteMutation.mutate(p.id) }}
                  className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-all p-1 rounded"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              <div className="mt-4 flex items-center justify-between text-sm text-gray-500">
                <span className="flex items-center gap-1">
                  <FileText className="w-4 h-4" />
                  {p.document_count} {p.document_count === 1 ? 'report' : 'reports'}
                </span>
                <span className="flex items-center gap-1 text-blue-600 font-medium text-xs group-hover:gap-2 transition-all">
                  Open <ChevronRight className="w-3 h-3" />
                </span>
              </div>
              {p.sector && <p className="text-xs text-gray-400 mt-1">{p.sector} · {p.base_currency}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

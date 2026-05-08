import { useCallback, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useDropzone } from 'react-dropzone'
import {
  ArrowLeft, Upload, FileText, Loader2, AlertCircle,
  CheckCircle2, Zap, Map, ChevronRight, RefreshCw, Trash2,
  BarChart2, TrendingUp, MessageCircle,
} from 'lucide-react'
import { projectsApi, documentsApi, mappingApi } from '../api/client'
import StatusBadge from '../components/StatusBadge'

export default function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [mappingMsg, setMappingMsg] = useState<string | null>(null)

  const { data: project, isLoading: projLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId!),
    enabled: !!projectId,
  })

  const { data: documents = [], isLoading: docsLoading, refetch: refetchDocs } = useQuery({
    queryKey: ['documents', projectId],
    queryFn: () => documentsApi.list(projectId!),
    enabled: !!projectId,
    refetchInterval: (data) => {
      const hasProcessing = (data?.state?.data ?? []).some((d: { status: string }) => d.status === 'processing')
      return hasProcessing ? 2000 : false
    },
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => documentsApi.upload(projectId!, file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents', projectId] })
      setUploadError(null)
    },
    onError: (e: Error) => setUploadError(e.message),
  })

  const extractMutation = useMutation({
    mutationFn: (docId: string) => documentsApi.extract(projectId!, docId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['documents', projectId] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (docId: string) => documentsApi.delete(projectId!, docId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['documents', projectId] }),
  })

  const mappingMutation = useMutation({
    mutationFn: () => mappingApi.runMapping(projectId!),
    onSuccess: (res) => {
      setMappingMsg(res.message)
      qc.invalidateQueries({ queryKey: ['line-items', projectId] })
    },
    onError: (e: Error) => setMappingMsg(`Error: ${e.message}`),
  })

  const onDrop = useCallback((accepted: File[]) => {
    setUploadError(null)
    accepted.forEach(f => uploadMutation.mutate(f))
  }, [uploadMutation])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: true,
  })

  const extractedDocs = documents.filter(d => d.status === 'extracted')

  if (projLoading) return <div className="text-center py-20 text-gray-400">Loading…</div>
  if (!project) return <div className="text-center py-20 text-red-500">Project not found</div>

  return (
    <div>
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-500 mb-6">
        <button onClick={() => navigate('/')} className="hover:text-blue-600 flex items-center gap-1">
          <ArrowLeft className="w-4 h-4" /> Projects
        </button>
        <span>/</span>
        <span className="text-gray-900 font-medium">{project.company_name}</span>
      </div>

      {/* Project header */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{project.company_name}</h1>
            <div className="flex flex-wrap gap-3 mt-2 text-sm text-gray-500">
              {project.ticker && <span className="font-mono bg-gray-100 px-2 py-0.5 rounded">{project.ticker}</span>}
              {project.sector && <span>{project.sector}</span>}
              {project.base_currency && <span>{project.base_currency}</span>}
              {project.fiscal_year_end && <span>FYE: {project.fiscal_year_end}</span>}
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <CheckCircle2 className="w-4 h-4 text-green-500" />
            <span className="text-gray-500">{project.document_count} document{project.document_count !== 1 ? 's' : ''}</span>
          </div>
        </div>
      </div>

      {/* Upload */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Upload className="w-4 h-4 text-blue-500" /> Upload Annual Reports
        </h2>
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            isDragActive ? 'border-blue-400 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
          }`}
        >
          <input {...getInputProps()} />
          <Upload className="w-8 h-8 text-gray-300 mx-auto mb-2" />
          {isDragActive ? (
            <p className="text-blue-600 font-medium">Drop PDF files here</p>
          ) : (
            <>
              <p className="text-gray-600 font-medium">Drag &amp; drop PDF files here</p>
              <p className="text-sm text-gray-400 mt-1">or click to browse · PDF only · up to 100 MB each</p>
            </>
          )}
        </div>
        {uploadError && (
          <div className="mt-3 flex items-center gap-2 text-sm text-red-600 bg-red-50 rounded-lg p-3">
            <AlertCircle className="w-4 h-4 shrink-0" /> {uploadError}
          </div>
        )}
        {uploadMutation.isPending && (
          <div className="mt-3 flex items-center gap-2 text-sm text-blue-600">
            <Loader2 className="w-4 h-4 animate-spin" /> Uploading…
          </div>
        )}
      </div>

      {/* Documents */}
      {(docsLoading || documents.length > 0) && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
              <FileText className="w-4 h-4 text-blue-500" /> Documents
            </h2>
            <button onClick={() => refetchDocs()} className="text-gray-400 hover:text-gray-600">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          <div className="divide-y divide-gray-100">
            {documents.map(doc => (
              <div key={doc.id} className="py-3 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3 min-w-0">
                  <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">{doc.file_name}</p>
                    <p className="text-xs text-gray-400">
                      {doc.file_size ? `${(doc.file_size / 1024 / 1024).toFixed(1)} MB` : ''}
                      {doc.page_count ? ` · ${doc.page_count} pages` : ''}
                      {doc.detected_year ? ` · FY${doc.detected_year}` : ''}
                      {doc.detected_currency ? ` · ${doc.detected_currency}` : ''}
                    </p>
                    {doc.error_message && (
                      <p className="text-xs text-red-500 mt-0.5">{doc.error_message}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <StatusBadge status={doc.status} />
                  {doc.status === 'extracted' && (
                    <Link
                      to={`/projects/${projectId}/documents/${doc.id}`}
                      className="text-xs text-blue-600 hover:underline"
                    >
                      Review
                    </Link>
                  )}
                  {(doc.status === 'pending' || doc.status === 'failed') && (
                    <button
                      onClick={() => extractMutation.mutate(doc.id)}
                      disabled={extractMutation.isPending}
                      className="text-xs bg-blue-600 text-white px-3 py-1 rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1"
                    >
                      {extractMutation.isPending
                        ? <><Loader2 className="w-3 h-3 animate-spin" /> Extracting</>
                        : <><Zap className="w-3 h-3" /> Extract</>}
                    </button>
                  )}
                  <button
                    onClick={() => { if (confirm('Delete this document?')) deleteMutation.mutate(doc.id) }}
                    className="text-gray-400 hover:text-red-500 p-1 rounded"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Mapping */}
      {extractedDocs.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
            <Map className="w-4 h-4 text-blue-500" /> Line-Item Mapping
          </h2>
          <p className="text-sm text-gray-500 mb-4">
            Run the mapper to classify extracted tables and map line items to the standard financial schema.
          </p>
          {mappingMsg && (
            <div className="mb-3 text-sm bg-green-50 text-green-700 rounded-lg p-3">{mappingMsg}</div>
          )}
          <div className="flex gap-3">
            <button
              onClick={() => mappingMutation.mutate()}
              disabled={mappingMutation.isPending}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium px-5 py-2 rounded-lg flex items-center gap-2 transition-colors"
            >
              {mappingMutation.isPending
                ? <><Loader2 className="w-4 h-4 animate-spin" /> Running…</>
                : <><Zap className="w-4 h-4" /> Run Mapping</>}
            </button>
            <Link
              to={`/projects/${projectId}/mapping`}
              className="text-sm text-blue-600 hover:underline flex items-center gap-1 px-2"
            >
              Review Mappings <ChevronRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      )}

      {/* Phase 4-6: Model / Forecast / Chat navigation cards */}
      {extractedDocs.length > 0 && (
        <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Link
            to={`/projects/${projectId}/model`}
            className="flex items-start gap-3 bg-white border border-gray-200 hover:border-indigo-400 hover:shadow-sm rounded-xl p-4 transition-all group"
          >
            <div className="w-9 h-9 rounded-lg bg-indigo-100 flex items-center justify-center shrink-0">
              <BarChart2 className="w-5 h-5 text-indigo-600" />
            </div>
            <div>
              <p className="font-semibold text-gray-800 group-hover:text-indigo-700">Financial Model</p>
              <p className="text-xs text-gray-500 mt-0.5">Build IS / BS / CF + key ratios</p>
            </div>
            <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-indigo-500 ml-auto mt-1" />
          </Link>

          <Link
            to={`/projects/${projectId}/forecast`}
            className="flex items-start gap-3 bg-white border border-gray-200 hover:border-green-400 hover:shadow-sm rounded-xl p-4 transition-all group"
          >
            <div className="w-9 h-9 rounded-lg bg-green-100 flex items-center justify-center shrink-0">
              <TrendingUp className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="font-semibold text-gray-800 group-hover:text-green-700">Forecast</p>
              <p className="text-xs text-gray-500 mt-0.5">LLM-driven 3–5 year projections</p>
            </div>
            <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-green-500 ml-auto mt-1" />
          </Link>

          <Link
            to={`/projects/${projectId}/chat`}
            className="flex items-start gap-3 bg-white border border-gray-200 hover:border-purple-400 hover:shadow-sm rounded-xl p-4 transition-all group"
          >
            <div className="w-9 h-9 rounded-lg bg-purple-100 flex items-center justify-center shrink-0">
              <MessageCircle className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="font-semibold text-gray-800 group-hover:text-purple-700">Chat Assistant</p>
              <p className="text-xs text-gray-500 mt-0.5">Ask questions about the financials</p>
            </div>
            <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-purple-500 ml-auto mt-1" />
          </Link>
        </div>
      )}
    </div>
  )
}

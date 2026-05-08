import { useState, useEffect } from 'react'
import { modelApi, type LLMStatus } from '../api/client'
import { Cpu, Download, CheckCircle, XCircle, Loader2, ChevronDown, ChevronUp } from 'lucide-react'

const MODELS = [
  {
    id: 'Qwen/Qwen2.5-7B-Instruct',
    label: 'Qwen 2.5 — 7B (Recommended)',
    desc: 'Best quality. Requires ~14 GB VRAM (GPU) or ~28 GB RAM (CPU).',
  },
  {
    id: 'Qwen/Qwen2.5-3B-Instruct',
    label: 'Qwen 2.5 — 3B (Balanced)',
    desc: 'Good quality. Requires ~6 GB VRAM or ~12 GB RAM.',
  },
  {
    id: 'Qwen/Qwen2.5-1.5B-Instruct',
    label: 'Qwen 2.5 — 1.5B (CPU-friendly)',
    desc: 'Faster on CPU. Requires ~4 GB RAM. Reduced accuracy.',
  },
]

export default function LLMSetup() {
  const [status, setStatus] = useState<LLMStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [polling, setPolling] = useState(false)
  const [selectedModel, setSelectedModel] = useState(MODELS[1].id)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchStatus = async (): Promise<LLMStatus | null> => {
    try {
      const s = await modelApi.llmStatus()
      setStatus(s)
      return s
    } catch {
      return null
    }
  }

  useEffect(() => {
    fetchStatus()
  }, [])

  useEffect(() => {
    if (!polling) return
    const id = setInterval(async () => {
      const s = await fetchStatus()
      if (s?.loaded || s?.error) {
        setPolling(false)
        setLoading(false)
      }
    }, 3000)
    return () => clearInterval(id)
  }, [polling])

  const handleLoad = async () => {
    setLoading(true)
    setError(null)
    try {
      await modelApi.llmLoad(selectedModel)
      setPolling(true)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to start loading')
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Cpu className="w-8 h-8 text-indigo-600" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900">LLM Setup</h1>
          <p className="text-sm text-gray-500">Download and configure a local HuggingFace language model</p>
        </div>
      </div>

      <div className={`rounded-xl border-2 p-5 ${status?.loaded ? 'border-green-400 bg-green-50' : status?.error ? 'border-red-400 bg-red-50' : 'border-gray-200 bg-gray-50'}`}>
        <div className="flex items-center gap-3">
          {status?.loaded ? (
            <CheckCircle className="w-6 h-6 text-green-600" />
          ) : status?.error ? (
            <XCircle className="w-6 h-6 text-red-600" />
          ) : polling ? (
            <Loader2 className="w-6 h-6 text-indigo-600 animate-spin" />
          ) : (
            <Cpu className="w-6 h-6 text-gray-400" />
          )}
          <div>
            <p className="font-semibold text-gray-800">
              {status?.loaded
                ? `Model loaded: ${status.model_name}`
                : polling
                ? 'Downloading and loading model… this may take several minutes'
                : status?.error
                ? 'Load failed'
                : 'No model loaded'}
            </p>
            {status?.loaded && (
              <p className="text-sm text-gray-500">
                Device: {status.device?.toUpperCase()} · {status.quantized ? '4-bit quantized' : 'Full precision'}
              </p>
            )}
            {status?.error && <p className="text-sm text-red-600">{status.error}</p>}
          </div>
        </div>
      </div>

      {!status?.loaded && (
        <div className="space-y-3">
          <p className="font-medium text-gray-700">Select model to download:</p>
          {MODELS.map(m => (
            <label
              key={m.id}
              className={`flex gap-3 p-4 rounded-lg border-2 cursor-pointer transition-colors ${selectedModel === m.id ? 'border-indigo-500 bg-indigo-50' : 'border-gray-200 hover:border-gray-300'}`}
            >
              <input
                type="radio"
                name="model"
                value={m.id}
                checked={selectedModel === m.id}
                onChange={() => setSelectedModel(m.id)}
                className="mt-1"
              />
              <div>
                <p className="font-medium text-gray-800">{m.label}</p>
                <p className="text-sm text-gray-500">{m.desc}</p>
              </div>
            </label>
          ))}

          <button
            onClick={handleLoad}
            disabled={loading || polling}
            className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg font-semibold hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {polling ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> Loading…</>
            ) : (
              <><Download className="w-4 h-4" /> Download &amp; Load Model</>
            )}
          </button>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>
      )}

      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          <span>Technical Details &amp; Requirements</span>
          {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
        {showAdvanced && (
          <div className="px-4 pb-4 text-sm text-gray-600 space-y-2 border-t border-gray-200 pt-3">
            <p><strong>GPU (CUDA):</strong> 4-bit NF4 quantisation via bitsandbytes. Much faster inference.</p>
            <p><strong>CPU:</strong> float32. Expect 30–120 seconds per response depending on model size.</p>
            <p><strong>First load:</strong> Downloads model weights from HuggingFace Hub (~1.5–14 GB). Cached locally afterward.</p>
            <p><strong>Cache:</strong> <code className="bg-gray-100 px-1 rounded">backend/llm_cache/</code></p>
            <p><strong>Dependencies:</strong> torch, transformers, accelerate, bitsandbytes</p>
          </div>
        )}
      </div>
    </div>
  )
}

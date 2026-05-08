import { useState, useRef, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { modelApi, type ChatMessage, type LLMStatus } from '../api/client'
import { MessageCircle, Send, Bot, User, Loader2, AlertCircle } from 'lucide-react'

const SUGGESTIONS = [
  'What was the revenue growth trend?',
  'How has the gross margin changed over time?',
  'What is the net income for the latest year?',
  'Summarise the cash flow position',
  'What are the key financial risks based on this data?',
  'Compare EBITDA margins across reported years',
]

export default function ChatAssistant() {
  const { projectId } = useParams<{ projectId: string }>()
  const qc = useQueryClient()
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const { data: llmStatus } = useQuery<LLMStatus>({
    queryKey: ['llm-status'],
    queryFn: modelApi.llmStatus,
    refetchInterval: 5000,
  })

  const { data: messages = [], isLoading } = useQuery<ChatMessage[]>({
    queryKey: ['chat', projectId],
    queryFn: () => modelApi.getChat(projectId!),
  })

  const sendMut = useMutation({
    mutationFn: (content: string) => modelApi.sendChat(projectId!, content),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['chat', projectId] }),
  })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sendMut.isPending])

  const send = () => {
    const content = input.trim()
    if (!content || sendMut.isPending) return
    setInput('')
    sendMut.mutate(content)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="max-w-3xl mx-auto flex flex-col h-[calc(100vh-120px)] p-6 gap-4">
      <div className="flex items-center gap-3">
        <MessageCircle className="w-8 h-8 text-indigo-600" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Financial Assistant</h1>
          <p className="text-sm text-gray-500">Ask questions about this company's financials</p>
        </div>
        {llmStatus && (
          <div className={`ml-auto flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full ${llmStatus.loaded ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${llmStatus.loaded ? 'bg-green-500' : 'bg-amber-500'}`} />
            {llmStatus.loaded ? `${llmStatus.model_name?.split('/')[1] ?? 'LLM'} ready` : 'LLM not loaded'}
          </div>
        )}
      </div>

      {llmStatus && !llmStatus.loaded && (
        <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-700">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
          <span>LLM is not loaded. Go to <strong>LLM Setup</strong> to load a model for intelligent answers.</span>
        </div>
      )}

      <div className="flex-1 overflow-y-auto space-y-4 pr-1">
        {isLoading && <div className="text-center py-8 text-gray-400">Loading conversation…</div>}

        {!isLoading && messages.length === 0 && (
          <div className="space-y-4 py-4">
            <p className="text-center text-gray-500 text-sm">No messages yet. Try one of these:</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {SUGGESTIONS.map((s: string) => (
                <button
                  key={s}
                  onClick={() => { setInput(s); textareaRef.current?.focus() }}
                  className="text-left text-sm text-gray-600 bg-gray-50 hover:bg-indigo-50 hover:text-indigo-700 border border-gray-200 hover:border-indigo-300 rounded-lg px-3 py-2 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg: ChatMessage) => (
          <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className="w-7 h-7 rounded-full bg-indigo-100 flex items-center justify-center shrink-0 mt-1">
                <Bot className="w-4 h-4 text-indigo-600" />
              </div>
            )}
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-indigo-600 text-white rounded-tr-sm'
                  : 'bg-gray-100 text-gray-800 rounded-tl-sm'
              }`}
            >
              {msg.content}
            </div>
            {msg.role === 'user' && (
              <div className="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center shrink-0 mt-1">
                <User className="w-4 h-4 text-white" />
              </div>
            )}
          </div>
        ))}

        {sendMut.isPending && (
          <div className="flex gap-3 justify-start">
            <div className="w-7 h-7 rounded-full bg-indigo-100 flex items-center justify-center shrink-0 mt-1">
              <Bot className="w-4 h-4 text-indigo-600" />
            </div>
            <div className="bg-gray-100 rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-2">
              <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />
              <span className="text-sm text-gray-400">Thinking…</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="flex gap-2 items-end border border-gray-300 rounded-xl p-2 bg-white shadow-sm focus-within:border-indigo-400 focus-within:ring-1 focus-within:ring-indigo-400">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about revenue, margins, cash flow…"
          rows={1}
          className="flex-1 resize-none outline-none text-sm text-gray-800 placeholder-gray-400 px-2 py-1 max-h-32"
        />
        <button
          onClick={send}
          disabled={!input.trim() || sendMut.isPending}
          className="w-8 h-8 flex items-center justify-center bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shrink-0"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
      <p className="text-xs text-center text-gray-400">Press Enter to send · Shift+Enter for new line</p>
    </div>
  )
}

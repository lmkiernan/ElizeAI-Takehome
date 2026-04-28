import { useState } from 'react'
import { Copy, Check, RefreshCw } from 'lucide-react'

export default function EmailDraft({ lead }) {
  const [subject, setSubject] = useState(lead.emailDraft?.subject ?? '')
  const [body, setBody] = useState(lead.emailDraft?.body ?? '')
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    await navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!lead.emailDraft) {
    return (
      <div className="px-6 py-12 text-center">
        <p className="text-sm text-slate-400">Email draft not yet generated for this lead.</p>
      </div>
    )
  }

  return (
    <div className="px-6 py-5 space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">AI-Generated Draft</p>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 text-xs text-slate-600 border border-slate-200 rounded-lg px-2.5 py-1.5 hover:bg-slate-50 transition-colors"
          >
            {copied
              ? <><Check className="h-3.5 w-3.5 text-emerald-500" /> Copied</>
              : <><Copy className="h-3.5 w-3.5" /> Copy</>
            }
          </button>
          <button
            title="Regenerate requires the backend"
            className="flex items-center gap-1.5 text-xs text-slate-400 border border-slate-200 rounded-lg px-2.5 py-1.5 hover:bg-slate-50 transition-colors cursor-not-allowed"
          >
            <RefreshCw className="h-3.5 w-3.5" /> Regenerate
          </button>
        </div>
      </div>

      {/* Subject */}
      <div>
        <label className="block text-xs font-medium text-slate-500 mb-1.5">Subject Line</label>
        <input
          type="text"
          value={subject}
          onChange={e => setSubject(e.target.value)}
          className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      {/* Body */}
      <div>
        <label className="block text-xs font-medium text-slate-500 mb-1.5">Email Body</label>
        <textarea
          value={body}
          onChange={e => setBody(e.target.value)}
          rows={16}
          className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none leading-relaxed"
        />
      </div>

      <p className="text-xs text-slate-400 bg-slate-50 rounded-lg px-3 py-2">
        Personalized using live market data for {lead.city}, {lead.state}. Edit freely before sending.
      </p>
    </div>
  )
}

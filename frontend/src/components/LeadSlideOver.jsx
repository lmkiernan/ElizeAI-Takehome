import { useState, useEffect } from 'react'
import { X, Mail, MapPin } from 'lucide-react'
import ScoreBadge from './ScoreBadge'
import InsightPanel from './InsightPanel'
import EmailDraft from './EmailDraft'

const TABS = [
  { key: 'insights', label: 'Insights' },
  { key: 'email',    label: 'Email Draft' },
]

export default function LeadSlideOver({ lead, onClose }) {
  const [tab, setTab] = useState('insights')

  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  // Reset to insights tab when lead changes
  useEffect(() => { setTab('insights') }, [lead.id])

  return (
    <>
      {/* Overlay */}
      <div className="fixed inset-0 bg-black/25 z-20" onClick={onClose} />

      {/* Panel */}
      <div className="fixed inset-y-0 right-0 z-30 w-full max-w-lg bg-white shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between px-6 py-5 border-b border-slate-200">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-3 mb-1">
              <h2 className="text-lg font-semibold text-slate-900 truncate">{lead.name}</h2>
              {lead.score != null && <ScoreBadge score={lead.score} tier={lead.tier} size="sm" />}
            </div>
            <p className="text-sm font-medium text-slate-600">{lead.company}</p>
            <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
              <span className="flex items-center gap-1">
                <MapPin className="h-3 w-3" />
                {lead.city}, {lead.state}
              </span>
              <span className="flex items-center gap-1">
                <Mail className="h-3 w-3" />
                {lead.email}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="ml-3 p-1.5 hover:bg-slate-100 rounded-lg transition-colors text-slate-400 flex-shrink-0"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-200 px-6">
          {TABS.map(t => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`py-3 mr-6 text-sm font-medium border-b-2 transition-colors ${
                tab === t.key
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {tab === 'insights' ? <InsightPanel lead={lead} /> : <EmailDraft lead={lead} />}
        </div>
      </div>
    </>
  )
}

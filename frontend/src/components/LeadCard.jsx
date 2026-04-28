import { ArrowRight } from 'lucide-react'

const TIER_BORDER = {
  Hot:  'border-l-rose-400',
  Warm: 'border-l-amber-400',
  Cool: 'border-l-sky-400',
  Pass: 'border-l-slate-300',
}

const SCORE_STYLE = {
  Hot:  'bg-rose-100 text-rose-700',
  Warm: 'bg-amber-100 text-amber-700',
  Cool: 'bg-sky-100 text-sky-700',
  Pass: 'bg-slate-100 text-slate-500',
}

function timeAgo(iso) {
  if (!iso) return null
  const diff = Math.floor((Date.now() - new Date(iso)) / 86400000)
  if (diff === 0) return 'Today'
  if (diff === 1) return 'Yesterday'
  return `${diff}d ago`
}

export default function LeadCard({ lead, onClick }) {
  const borderClass = TIER_BORDER[lead.tier] ?? 'border-l-slate-200'
  const scoreStyle = SCORE_STYLE[lead.tier] ?? 'bg-slate-100 text-slate-400'
  const firstInsight = lead.insights?.[0]?.replace(/^\*\*[^*]+\*\*:\s*/, '') ?? ''

  if (lead.status === 'pending' || lead.status === 'processing') {
    return (
      <div className="bg-white border border-dashed border-slate-200 rounded-xl p-4 animate-pulse">
        <div className="flex items-center justify-between mb-2">
          <div className="h-4 bg-slate-100 rounded w-2/3" />
          <div className="h-5 w-12 bg-slate-100 rounded-full" />
        </div>
        <div className="h-3 bg-slate-100 rounded w-1/2 mb-3" />
        <div className="h-3 bg-slate-100 rounded w-full mb-1" />
        <div className="h-3 bg-slate-100 rounded w-4/5" />
        <p className="text-xs text-slate-400 mt-3">Processing…</p>
      </div>
    )
  }

  if (lead.status === 'failed') {
    return (
      <div className="bg-white border border-dashed border-rose-200 rounded-xl p-4">
        <div className="flex items-start justify-between gap-2 mb-1">
          <p className="font-semibold text-slate-900 text-sm leading-tight">{lead.company || lead.name}</p>
          <span className="text-xs font-semibold px-2 py-0.5 rounded-lg bg-rose-100 text-rose-700">
            Failed
          </span>
        </div>
        <p className="text-xs text-slate-500 mb-3">{lead.city}, {lead.state}</p>
        <p className="text-xs text-rose-700">Processing failed. Fix the row or retry from the backend.</p>
      </div>
    )
  }

  if (lead.status === 'unprocessed') {
    return (
      <div className="bg-white border border-dashed border-amber-200 rounded-xl p-4">
        <div className="flex items-start justify-between gap-2 mb-1">
          <p className="font-semibold text-slate-900 text-sm leading-tight">{lead.company || lead.name}</p>
          <span className="text-xs font-semibold px-2 py-0.5 rounded-lg bg-amber-100 text-amber-700">
            New
          </span>
        </div>
        <p className="text-xs text-slate-500 mb-3">{lead.city}, {lead.state}</p>
        <div className="mb-3 pb-3 border-b border-slate-100">
          <p className="text-xs font-medium text-slate-700">{lead.name}</p>
          <p className="text-xs text-slate-400 truncate">{lead.email}</p>
        </div>
        <p className="text-xs text-amber-700">Ready to process. Click Process All to score this lead.</p>
      </div>
    )
  }

  return (
    <div
      onClick={onClick}
      className={`bg-white border border-slate-200 border-l-4 ${borderClass} rounded-xl p-4 cursor-pointer hover:shadow-md hover:-translate-y-0.5 transition-all group`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-1">
        <p className="font-semibold text-slate-900 text-sm leading-tight">{lead.company}</p>
        <span className={`text-sm font-bold px-2 py-0.5 rounded-lg flex-shrink-0 ${scoreStyle}`}>
          {lead.score}
        </span>
      </div>

      <p className="text-xs text-slate-500 mb-3">{lead.city}, {lead.state}</p>

      {/* Contact */}
      <div className="mb-3 pb-3 border-b border-slate-100">
        <p className="text-xs font-medium text-slate-700">{lead.name}</p>
        <p className="text-xs text-slate-400 truncate">{lead.email}</p>
      </div>

      {/* Top insight */}
      {firstInsight && (
        <p className="text-xs text-slate-600 line-clamp-2 mb-3">"{firstInsight}"</p>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-400">
          {lead.status === 'duplicate' ? 'Already processed' : timeAgo(lead.processed_at)}
        </span>
        <ArrowRight className="h-3.5 w-3.5 text-slate-300 group-hover:text-slate-500 transition-colors" />
      </div>
    </div>
  )
}

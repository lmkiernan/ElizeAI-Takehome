import LeadCard from './LeadCard'

const COLUMNS = [
  { tier: 'Hot',  label: '🔥 Hot',  bg: 'bg-rose-50',   header: 'border-t-rose-400' },
  { tier: 'Warm', label: '🟡 Warm', bg: 'bg-amber-50',  header: 'border-t-amber-400' },
  { tier: 'Cool', label: '🔵 Cool', bg: 'bg-sky-50',    header: 'border-t-sky-400' },
  { tier: 'Pass', label: '⬜ Pass', bg: 'bg-slate-50',  header: 'border-t-slate-300' },
]

function EmptyColumn({ tier }) {
  const messages = {
    Hot:  'No hot leads yet.',
    Warm: 'No warm leads yet.',
    Cool: 'No cool leads yet.',
    Pass: 'No leads below threshold.',
  }
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <p className="text-sm text-slate-400">{messages[tier]}</p>
    </div>
  )
}

export default function KanbanBoard({ leads, pendingLeads, onSelectLead }) {
  const byTier = Object.fromEntries(
    COLUMNS.map(col => [col.tier, leads.filter(l => l.tier === col.tier)])
  )

  return (
    <div className="grid grid-cols-4 gap-4 min-h-0">
      {COLUMNS.map(col => {
        const cards = byTier[col.tier] ?? []
        const isPending = col.tier === 'Hot' // pending cards sit above Hot column
        return (
          <div key={col.tier} className={`${col.bg} rounded-xl border border-t-4 ${col.header} border-slate-200 flex flex-col`}>
            {/* Column header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
              <span className="text-sm font-semibold text-slate-700">{col.label}</span>
              <span className="text-xs font-medium bg-white border border-slate-200 text-slate-500 rounded-full px-2 py-0.5">
                {cards.length}
              </span>
            </div>

            {/* Cards */}
            <div className="flex-1 overflow-y-auto p-3 space-y-3">
              {/* Pending cards shown in Hot column */}
              {isPending && pendingLeads.map(lead => (
                <LeadCard key={lead.id} lead={lead} onClick={() => {}} />
              ))}

              {cards.length === 0 && pendingLeads.length === 0 ? (
                <EmptyColumn tier={col.tier} />
              ) : (
                cards.map(lead => (
                  <LeadCard key={lead.id} lead={lead} onClick={() => onSelectLead(lead)} />
                ))
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

import { Users, DollarSign, Home, Building2, Activity } from 'lucide-react'
import ScoreBadge from './ScoreBadge'

function ScoreBar({ label, score, max }) {
  const pct = Math.round((score / max) * 100)
  const barColor = pct >= 80 ? 'bg-emerald-500' : pct >= 60 ? 'bg-amber-400' : 'bg-rose-400'
  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-xs text-slate-600">{label}</span>
        <span className="text-xs font-semibold text-slate-700">{score}/{max}</span>
      </div>
      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function Metric({ icon: Icon, label, value, sub }) {
  return (
    <div className="bg-slate-50 rounded-lg p-3">
      <Icon className="h-4 w-4 text-slate-400 mb-1.5" />
      <p className="text-sm font-semibold text-slate-900">{value ?? '—'}</p>
      <p className="text-xs text-slate-500 mt-0.5">{label}</p>
      {sub && <p className="text-xs text-slate-400">{sub}</p>}
    </div>
  )
}

function fmt(n, prefix = '', suffix = '') {
  if (n == null) return null
  return `${prefix}${Number(n).toLocaleString()}${suffix}`
}

export default function InsightPanel({ lead }) {
  return (
    <div className="px-6 py-5 space-y-7">
      {/* Score overview */}
      <section>
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Score Breakdown</h3>
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="flex items-center gap-4 pb-4 mb-4 border-b border-slate-100">
            <ScoreBadge score={lead.score} tier={lead.tier} size="lg" />
            <div>
              <p className="text-sm text-slate-500">Lead Score</p>
              <p className="text-xs text-slate-400 mt-0.5">Based on Census, FRED & market data</p>
            </div>
          </div>
          {lead.scoreBreakdown ? (
            <div className="space-y-3">
              {Object.values(lead.scoreBreakdown).map(dim => (
                <ScoreBar key={dim.label} {...dim} />
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400 italic">
              Detailed breakdown available for leads processed via the dashboard.
            </p>
          )}
        </div>
      </section>

      {/* Demographics */}
      <section>
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
          Demographics
          <span className="ml-2 normal-case font-normal text-slate-300">· U.S. Census API</span>
        </h3>
        <div className="grid grid-cols-2 gap-2">
          <Metric icon={Users} label="Population" value={fmt(lead.population)} />
          <Metric icon={DollarSign} label="Median HH Income" value={fmt(lead.median_income, '$')} />
          <Metric icon={Home} label="Renter-Occupied" value={lead.renter_pct != null ? `${lead.renter_pct}%` : null} />
          <Metric icon={Building2} label="Median Rent" value={fmt(lead.median_rent, '$', '/mo')} />
          <Metric icon={Building2} label="Housing Units" value={fmt(lead.total_housing_units)} />
          <Metric icon={Activity} label="Unemployment" value={lead.unemployment_rate != null ? `${lead.unemployment_rate}%` : null} sub="· FRED API" />
        </div>
      </section>

      {/* Sales insights */}
      <section>
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
          Sales Insights
          <span className="ml-2 normal-case font-normal text-slate-300">· Gemini AI</span>
        </h3>
        {lead.insights?.length > 0 ? (
          <ul className="space-y-2.5">
            {lead.insights.map((ins, i) => {
              const clean = ins.replace(/^\*\*[^*]+\*\*:\s*/, '')
              const label = ins.match(/^\*\*([^*]+)\*\*/)?.[1]
              return (
                <li key={i} className="flex gap-2.5 text-sm text-slate-700">
                  <span className="mt-0.5 text-indigo-400 font-bold flex-shrink-0 text-xs">→</span>
                  <span>
                    {label && <span className="font-semibold text-slate-800">{label}: </span>}
                    {clean}
                  </span>
                </li>
              )
            })}
          </ul>
        ) : (
          <p className="text-sm text-slate-400 italic">No insights available.</p>
        )}
      </section>
    </div>
  )
}

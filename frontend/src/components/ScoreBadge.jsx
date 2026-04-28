const TIER_STYLES = {
  Hot:  'bg-rose-100 text-rose-700 ring-rose-200',
  Warm: 'bg-amber-100 text-amber-700 ring-amber-200',
  Cool: 'bg-sky-100 text-sky-700 ring-sky-200',
  Pass: 'bg-slate-100 text-slate-500 ring-slate-200',
}

export default function ScoreBadge({ score, tier, size = 'md' }) {
  const style = TIER_STYLES[tier] ?? 'bg-slate-100 text-slate-400 ring-slate-200'

  if (size === 'lg') {
    return (
      <div className={`inline-flex flex-col items-center justify-center rounded-2xl px-5 py-3 ring-2 ${style}`}>
        <span className="text-4xl font-bold leading-none">{score}</span>
        <span className="text-xs font-semibold uppercase tracking-widest mt-1">{tier}</span>
      </div>
    )
  }

  if (size === 'sm') {
    return (
      <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ${style}`}>
        {score}
      </span>
    )
  }

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-sm font-semibold ring-1 ${style}`}>
      {score} <span className="opacity-60 text-xs">/ 100</span>
    </span>
  )
}

import { useState, useEffect, useMemo, useRef } from 'react'
import { AlertCircle, ArrowUpDown, RefreshCw, Plus } from 'lucide-react'
import KanbanBoard from './components/KanbanBoard'
import LeadSlideOver from './components/LeadSlideOver'
import LeadForm from './components/LeadForm'
import { fetchLeads, processAll } from './api'

const TIME_FILTERS = [
  { label: 'All time', value: 'all' },
  { label: 'Last 7d',  value: '7'   },
  { label: 'Last 14d', value: '14'  },
  { label: 'Last 30d', value: '30'  },
]

export default function App() {
  const [leads, setLeads] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedLead, setSelectedLead] = useState(null)
  const [view, setView] = useState('kanban')       // 'kanban' | 'add'
  const [timeFilter, setTimeFilter] = useState('all')
  const [sortDir, setSortDir] = useState('desc')   // 'desc' = highest first
  const [syncing, setSyncing] = useState(false)
  const [connectionError, setConnectionError] = useState(null)
  const autoProcessKeyRef = useRef(null)

  useEffect(() => {
    loadLeads({ showLoading: true })
  }, [])

  // Poll for new leads processed via the sheet webhook.
  useEffect(() => {
    const id = setInterval(() => {
      loadLeads()
    }, 60_000)
    return () => clearInterval(id)
  }, [])

  async function loadLeads({ showLoading = false } = {}) {
    if (showLoading) setLoading(true)
    try {
      const data = await fetchLeads()
      setLeads(data)
      setConnectionError(null)
    } catch (e) {
      setConnectionError('Could not connect to the backend. Start the Flask server and try again.')
    } finally {
      if (showLoading) setLoading(false)
    }
  }

  const processedLeads = useMemo(() => {
    let filtered = leads.filter(l => ['processed', 'duplicate'].includes(l.status) && l.score != null)

    if (timeFilter !== 'all') {
      const cutoff = new Date(Date.now() - Number(timeFilter) * 86_400_000)
      filtered = filtered.filter(l => l.processed_at && new Date(l.processed_at) >= cutoff)
    }

    filtered.sort((a, b) =>
      sortDir === 'desc' ? b.score - a.score : a.score - b.score
    )

    return filtered
  }, [leads, timeFilter, sortDir])

  const pendingLeads = useMemo(
    () => leads.filter(l => ['pending', 'processing', 'unprocessed', 'failed'].includes(l.status)),
    [leads]
  )

  const unprocessedKey = useMemo(() => {
    return leads
      .filter(l => l.status === 'unprocessed')
      .map(l => l.lead_key || `${l.property_address}|${l.city}|${l.state}`.toLowerCase())
      .sort()
      .join('::')
  }, [leads])

  useEffect(() => {
    if (!unprocessedKey || syncing || autoProcessKeyRef.current === unprocessedKey) return
    autoProcessKeyRef.current = unprocessedKey
    handleProcessAll({ automatic: true })
  }, [unprocessedKey, syncing])

  // Stats for the header bar
  const hotCount  = processedLeads.filter(l => l.tier === 'Hot').length
  const avgScore  = processedLeads.length
    ? Math.round(processedLeads.reduce((s, l) => s + l.score, 0) / processedLeads.length)
    : null

  async function handleProcessAll({ automatic = false } = {}) {
    setSyncing(true)
    try {
      const results = await processAll()
      if (results.length > 0) {
        setLeads(prev => {
          const updated = [...prev]
          results.forEach(r => {
            const idx = updated.findIndex(l => l.id === r.id)
            if (idx >= 0) updated[idx] = r
            else updated.push(r)
          })
          return updated
        })
      }
      await loadLeads()
    } catch {
      setConnectionError(
        automatic
          ? 'Auto-processing failed. Check that the backend is running.'
          : 'Could not process leads. Check that the backend is running.'
      )
    } finally {
      setSyncing(false)
    }
  }

  function handleLeadsProcessed(newLeads) {
    setLeads(prev => {
      const updated = [...prev]
      newLeads.forEach(r => {
        const idx = updated.findIndex(l => l.id === r.id)
        if (idx >= 0) updated[idx] = r
        else updated.push(r)
      })
      return updated
    })
    setView('kanban')
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-sm text-slate-400">Loading leads…</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* ── Navbar ── */}
      <nav className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-screen-xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="font-bold text-lg tracking-tight">
              <span className="text-indigo-600">Elise</span>
              <span className="text-slate-900">AI</span>
            </span>
            <span className="h-4 w-px bg-slate-200" />
            <span className="text-sm text-slate-400 font-medium">Lead Intelligence</span>
          </div>
          <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
            <button
              onClick={() => setView('kanban')}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                view === 'kanban' ? 'bg-white shadow-sm text-slate-900' : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              Leads
            </button>
            <button
              onClick={() => setView('add')}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                view === 'add' ? 'bg-white shadow-sm text-slate-900' : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              + Add Leads
            </button>
          </div>
        </div>
      </nav>

      {view === 'add' ? (
        <main className="flex-1 max-w-screen-xl mx-auto w-full px-6 py-8">
          <LeadForm onLeadsProcessed={handleLeadsProcessed} onCancel={() => setView('kanban')} />
        </main>
      ) : (
        <>
          {/* ── Stats + controls bar ── */}
          <div className="bg-white border-b border-slate-100">
            <div className="max-w-screen-xl mx-auto px-6 py-3 flex items-center justify-between gap-4 flex-wrap">
              {/* Stats */}
              <div className="flex items-center gap-6">
                <Stat label="Total" value={processedLeads.length + pendingLeads.length} />
                <Stat label="Hot leads" value={hotCount} accent />
                {avgScore != null && <Stat label="Avg score" value={avgScore} />}
                {pendingLeads.length > 0 && (
                  <span className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-full px-2.5 py-0.5 font-medium">
                    {pendingLeads.length} ready to process
                  </span>
                )}
              </div>

              {/* Controls */}
              <div className="flex items-center gap-2">
                {/* Sort toggle */}
                <button
                  onClick={() => setSortDir(d => d === 'desc' ? 'asc' : 'desc')}
                  className="flex items-center gap-1.5 text-xs font-medium text-slate-600 border border-slate-200 rounded-lg px-3 py-1.5 hover:bg-slate-50 transition-colors"
                >
                  <ArrowUpDown className="h-3.5 w-3.5" />
                  Score {sortDir === 'desc' ? '↓ High first' : '↑ Low first'}
                </button>

                {/* Time filter */}
                <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
                  {TIME_FILTERS.map(f => (
                    <button
                      key={f.value}
                      onClick={() => setTimeFilter(f.value)}
                      className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                        timeFilter === f.value
                          ? 'bg-white shadow-sm text-slate-900'
                          : 'text-slate-500 hover:text-slate-700'
                      }`}
                    >
                      {f.label}
                    </button>
                  ))}
                </div>

                {/* Process all */}
                <button
                  onClick={handleProcessAll}
                  disabled={syncing}
                  className="flex items-center gap-1.5 text-xs font-medium text-indigo-600 border border-indigo-200 rounded-lg px-3 py-1.5 hover:bg-indigo-50 transition-colors disabled:opacity-50"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${syncing ? 'animate-spin' : ''}`} />
                  {syncing ? 'Syncing…' : 'Process All'}
                </button>

                {/* Add leads shortcut */}
                <button
                  onClick={() => setView('add')}
                  className="flex items-center gap-1.5 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg px-3 py-1.5 transition-colors"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Add Leads
                </button>
              </div>
            </div>
          </div>

          {connectionError && (
            <div className="bg-amber-50 border-b border-amber-200">
              <div className="max-w-screen-xl mx-auto px-6 py-2 flex items-center justify-between gap-3">
                <p className="flex items-center gap-2 text-sm text-amber-700">
                  <AlertCircle className="h-4 w-4" />
                  {connectionError}
                </p>
                <button
                  onClick={() => loadLeads({ showLoading: true })}
                  className="text-xs font-medium text-amber-700 border border-amber-300 rounded-lg px-2.5 py-1 hover:bg-amber-100 transition-colors"
                >
                  Retry
                </button>
              </div>
            </div>
          )}

          {/* ── Kanban board ── */}
          <main className="flex-1 max-w-screen-xl mx-auto w-full px-6 py-5 overflow-hidden">
            <KanbanBoard
              leads={processedLeads}
              pendingLeads={pendingLeads}
              onSelectLead={setSelectedLead}
            />
          </main>
        </>
      )}

      {/* ── Lead detail slide-over ── */}
      {selectedLead && (
        <LeadSlideOver
          lead={selectedLead}
          onClose={() => setSelectedLead(null)}
        />
      )}
    </div>
  )
}

function Stat({ label, value, accent }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <span className={`text-xl font-bold ${accent ? 'text-rose-600' : 'text-slate-900'}`}>{value}</span>
      <span className="text-xs text-slate-400">{label}</span>
    </div>
  )
}

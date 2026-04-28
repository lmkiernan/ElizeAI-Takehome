import { useState, useRef } from 'react'
import { Upload, Plus, X, FileText, Loader2 } from 'lucide-react'
import { processLead } from '../api'

const EMPTY = { name: '', email: '', company: '', property_address: '', city: '', state: '' }

function parseCSV(text) {
  const lines = text.trim().split('\n').filter(Boolean)
  if (lines.length < 2) return []
  const headers = lines[0].split(',').map(h => h.trim().toLowerCase().replace(/\s+/g, '_').replace(/['"]/g, ''))
  return lines.slice(1).map((line, i) => {
    const vals = line.split(',').map(v => v.trim().replace(/^["']|["']$/g, ''))
    const obj = Object.fromEntries(headers.map((h, idx) => [h, vals[idx] ?? '']))
    return {
      id: Date.now() + i,
      name: obj.name ?? '',
      email: obj.email ?? '',
      company: obj.company ?? '',
      property_address: obj.property_address ?? obj.address ?? '',
      city: obj.city ?? '',
      state: obj.state ?? '',
      status: 'pending',
    }
  })
}

export default function LeadForm({ onLeadsProcessed, onCancel }) {
  const [csvLeads, setCsvLeads] = useState([])
  const [manualLeads, setManualLeads] = useState([])
  const [form, setForm] = useState(EMPTY)
  const [dragOver, setDragOver] = useState(false)
  const [fileName, setFileName] = useState('')
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState(null)
  const fileRef = useRef()

  function handleFile(file) {
    if (!file) return
    setFileName(file.name)
    const reader = new FileReader()
    reader.onload = e => setCsvLeads(parseCSV(e.target.result))
    reader.readAsText(file)
  }

  function addManual() {
    if (!form.name || !form.email) return
    setManualLeads(prev => [...prev, { ...form, id: Date.now(), status: 'pending' }])
    setForm(EMPTY)
  }

  const queue = [...csvLeads, ...manualLeads]

  async function handleProcess() {
    setProcessing(true)
    setError(null)
    try {
      const results = await Promise.all(queue.map(l => processLead(l)))
      onLeadsProcessed(results)
    } catch (e) {
      setError('Processing failed — is the backend running?')
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Add Leads</h1>
          <p className="text-sm text-slate-500 mt-0.5">Upload a CSV or enter leads manually, then process to enrich and score.</p>
        </div>
        <button onClick={onCancel} className="text-sm text-slate-400 hover:text-slate-600 flex items-center gap-1.5">
          <X className="h-4 w-4" /> Cancel
        </button>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* CSV Upload */}
        <div>
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Upload CSV</h2>
          <div
            onDrop={e => { e.preventDefault(); setDragOver(false); handleFile(e.dataTransfer.files[0]) }}
            onDragOver={e => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onClick={() => fileRef.current.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
              dragOver ? 'border-indigo-400 bg-indigo-50' : 'border-slate-200 hover:border-indigo-300 hover:bg-slate-50'
            }`}
          >
            {fileName ? (
              <div className="flex items-center justify-center gap-2 text-sm text-slate-700">
                <FileText className="h-4 w-4 text-indigo-500" />
                {fileName}
              </div>
            ) : (
              <>
                <Upload className="h-7 w-7 text-slate-300 mx-auto mb-2" />
                <p className="text-sm text-slate-600 font-medium">Drop CSV or click to upload</p>
                <p className="text-xs text-slate-400 mt-1">name, email, company, address, city, state</p>
              </>
            )}
            <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={e => handleFile(e.target.files[0])} />
          </div>

          {csvLeads.length > 0 && (
            <div className="mt-3 bg-white border border-slate-200 rounded-xl overflow-hidden">
              <div className="px-4 py-2 bg-slate-50 border-b border-slate-100 flex justify-between">
                <span className="text-xs font-semibold text-slate-600">{csvLeads.length} rows from CSV</span>
                <button onClick={() => { setCsvLeads([]); setFileName('') }} className="text-xs text-slate-400 hover:text-rose-500">Clear</button>
              </div>
              <div className="max-h-40 overflow-y-auto divide-y divide-slate-50">
                {csvLeads.map((l, i) => (
                  <div key={i} className="px-4 py-2 text-xs flex justify-between">
                    <span className="font-medium text-slate-800">{l.name || '—'}</span>
                    <span className="text-slate-400">{l.company} · {l.city}, {l.state}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Manual Entry */}
        <div>
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Manual Entry</h2>
          <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-3">
            {[
              { key: 'name',             label: 'Full Name',        placeholder: 'Sarah Kim' },
              { key: 'email',            label: 'Email',            placeholder: 'skim@example.com' },
              { key: 'company',          label: 'Company',          placeholder: 'UrbanEdge Apartments' },
              { key: 'property_address', label: 'Property Address', placeholder: '1200 S Congress Ave' },
              { key: 'city',             label: 'City',             placeholder: 'Austin' },
              { key: 'state',            label: 'State',            placeholder: 'TX' },
            ].map(f => (
              <div key={f.key}>
                <label className="block text-xs font-medium text-slate-500 mb-1">{f.label}</label>
                <input
                  type={f.key === 'email' ? 'email' : 'text'}
                  value={form[f.key]}
                  onChange={e => setForm(p => ({ ...p, [f.key]: e.target.value }))}
                  onKeyDown={e => e.key === 'Enter' && addManual()}
                  placeholder={f.placeholder}
                  className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            ))}
            <button
              onClick={addManual}
              disabled={!form.name || !form.email}
              className="w-full flex items-center justify-center gap-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium py-2 rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Plus className="h-4 w-4" /> Add to Queue
            </button>
          </div>

          {manualLeads.length > 0 && (
            <div className="mt-3 bg-white border border-slate-200 rounded-xl overflow-hidden">
              <div className="px-4 py-2 bg-slate-50 border-b border-slate-100">
                <span className="text-xs font-semibold text-slate-600">{manualLeads.length} manually added</span>
              </div>
              {manualLeads.map((l, i) => (
                <div key={i} className="px-4 py-2 text-xs border-b border-slate-50 flex justify-between items-center">
                  <span className="font-medium text-slate-800">{l.name}</span>
                  <button onClick={() => setManualLeads(p => p.filter((_, j) => j !== i))} className="text-slate-300 hover:text-rose-400">
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Process button */}
      {queue.length > 0 && (
        <div className="mt-6">
          {error && <p className="text-sm text-rose-500 mb-3">{error}</p>}
          <div className="flex justify-end">
            <button
              onClick={handleProcess}
              disabled={processing}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white font-medium px-6 py-2.5 rounded-xl transition-colors text-sm"
            >
              {processing
                ? <><Loader2 className="h-4 w-4 animate-spin" /> Processing {queue.length} leads…</>
                : <>Process {queue.length} Lead{queue.length !== 1 ? 's' : ''} →</>
              }
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

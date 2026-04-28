import { useState } from 'react'
import { Plus, X, Loader2 } from 'lucide-react'
import { createLead, fetchLeads, processAll } from '../api'

const EMPTY = {
  name: '',
  email: '',
  company: '',
  property_address: '',
  city: '',
  state: '',
  country: 'US',
}

const FIELDS = [
  { key: 'name', label: 'Name', placeholder: 'Sarah Kim', required: true },
  { key: 'email', label: 'Email', placeholder: 'skim@example.com', type: 'email', required: true },
  { key: 'company', label: 'Company', placeholder: 'UrbanEdge Apartments', required: true },
  { key: 'property_address', label: 'Property Address', placeholder: '1200 S Congress Ave', required: true },
  { key: 'city', label: 'City', placeholder: 'Austin', required: true },
  { key: 'state', label: 'State', placeholder: 'TX', required: true },
  { key: 'country', label: 'Country', placeholder: 'US', required: true },
]

export default function LeadForm({ onLeadsProcessed, onCancel }) {
  const [form, setForm] = useState(EMPTY)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const canSubmit = FIELDS.every(f => !f.required || form[f.key].trim())

  async function handleSubmit(e) {
    e.preventDefault()
    if (!canSubmit || saving) return

    setSaving(true)
    setError(null)
    try {
      await createLead(form)
      await processAll()
      onLeadsProcessed(await fetchLeads())
      setForm(EMPTY)
    } catch {
      setError('Could not add and process lead. Check that the backend is running.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Add Lead</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Add a row to Google Sheets. New rows are enriched and scored automatically.
          </p>
        </div>
        <button onClick={onCancel} className="text-sm text-slate-400 hover:text-slate-600 flex items-center gap-1.5">
          <X className="h-4 w-4" /> Cancel
        </button>
      </div>

      <form onSubmit={handleSubmit} className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          {FIELDS.map(f => (
            <div key={f.key} className={f.key === 'property_address' ? 'col-span-2' : ''}>
              <label className="block text-xs font-medium text-slate-500 mb-1">
                {f.label}
              </label>
              <input
                type={f.type ?? 'text'}
                value={form[f.key]}
                onChange={e => setForm(p => ({ ...p, [f.key]: e.target.value }))}
                placeholder={f.placeholder}
                required={f.required}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          ))}
        </div>

        {error && <p className="text-sm text-rose-500">{error}</p>}

        <div className="flex justify-end pt-2">
          <button
            type="submit"
            disabled={!canSubmit || saving}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium px-5 py-2.5 rounded-xl transition-colors text-sm"
          >
            {saving
              ? <><Loader2 className="h-4 w-4 animate-spin" /> Adding and Processing…</>
              : <><Plus className="h-4 w-4" /> Add and Process</>
            }
          </button>
        </div>
      </form>
    </div>
  )
}

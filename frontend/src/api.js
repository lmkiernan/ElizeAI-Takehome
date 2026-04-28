const BASE = '/api'

function toNum(v) {
  const n = parseFloat(v)
  return isNaN(n) ? null : n
}

function normalizeLead(raw, index) {
  const insights = Array.isArray(raw.insights)
    ? raw.insights
    : typeof raw.insights === 'string'
      ? raw.insights.split('|').map(s => s.trim()).filter(Boolean)
      : []

  const score = toNum(raw.score)
  const rawStatus = String(raw.status || '').toLowerCase()

  return {
    id: raw.lead_key || raw.id || `${raw.property_address ?? ''}|${raw.city ?? ''}|${raw.state ?? ''}` || index,
    lead_key: raw.lead_key ?? '',
    name: raw.name ?? '',
    email: raw.email ?? '',
    company: raw.company ?? '',
    property_address: raw.property_address ?? '',
    city: raw.city ?? '',
    state: raw.state ?? '',
    score,
    tier: raw.tier ?? null,
    scoreBreakdown: raw.scoreBreakdown ?? null,
    population: toNum(raw.population),
    median_income: toNum(raw.median_income),
    renter_pct: toNum(raw.renter_pct),
    median_rent: toNum(raw.median_rent),
    total_housing_units: toNum(raw.total_housing_units),
    unemployment_rate: toNum(raw.unemployment_rate),
    emailDraft: raw.emailDraft ?? {
      subject: raw.email_subject ?? '',
      body: raw.email_body ?? '',
    },
    insights,
    processed_at: raw.processed_at ?? null,
    status: rawStatus || (score != null ? 'processed' : 'unprocessed'),
  }
}

export async function fetchLeads() {
  const res = await fetch(`${BASE}/leads`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const data = await res.json()
  return (data.leads ?? []).map(normalizeLead)
}

export async function processLead(lead) {
  const res = await fetch(`${BASE}/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(lead),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return normalizeLead(await res.json())
}

export async function processAll() {
  const res = await fetch(`${BASE}/process-all`, { method: 'POST' })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const data = await res.json()
  return (data.leads ?? []).map(normalizeLead)
}

import { useState } from 'react'
import { apiPost } from '../api/client'
import PageHeader from '../components/layout/PageHeader'
import Section from '../components/layout/Section'
import KPICard from '../components/data/KPICard'
import { fmt } from '../components/data/CurrencyDisplay'

interface AffordResult {
  ok: boolean
  amount: number
  verdict: 'green' | 'yellow' | 'red'
  liquid_cash_before: number
  liquid_cash_after: number
  monthly_outflow_avg: number
  emergency_months_after: number | null
  min_months_required: number
  goal_impact: { goal: string; extra_months_to_target: number | null }[]
}

const verdictLabel = { green: 'Yes', yellow: 'Maybe', red: 'Not recommended' }
const verdictColor = { green: 'green' as const, yellow: 'yellow' as const, red: 'red' as const }

export default function AffordPage() {
  const [amount, setAmount] = useState(1000)
  const [result, setResult] = useState<AffordResult | null>(null)
  const [loading, setLoading] = useState(false)

  const check = async () => {
    setLoading(true)
    try {
      const r = await apiPost<AffordResult>('/afford', { amount, min_months: 3.0 })
      setResult(r)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <PageHeader title="Can I Afford This?" />

      <div className="flex gap-4 items-end mb-6">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Purchase amount ($)</label>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(Number(e.target.value))}
            className="border rounded px-3 py-1.5 text-sm w-32"
            min={0}
          />
        </div>
        <button
          onClick={check}
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Checking...' : 'Check'}
        </button>
      </div>

      {result && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <KPICard
              label="Verdict"
              value={verdictLabel[result.verdict]}
              color={verdictColor[result.verdict]}
            />
            <KPICard label="Cash Before" value={fmt(result.liquid_cash_before)} />
            <KPICard label="Cash After" value={fmt(result.liquid_cash_after)} />
            <KPICard
              label="Emergency Months After"
              value={result.emergency_months_after !== null ? `${result.emergency_months_after}` : '--'}
              color={
                result.emergency_months_after !== null && result.emergency_months_after >= 3
                  ? 'green'
                  : 'red'
              }
            />
          </div>

          {result.goal_impact.length > 0 && (
            <Section title="Goal Impact">
              <ul className="space-y-1 text-sm">
                {result.goal_impact.map((g) => (
                  <li key={g.goal}>
                    <strong>{g.goal}</strong>
                    {g.extra_months_to_target !== null
                      ? ` — adds ~${g.extra_months_to_target} months`
                      : ' — minimal impact'}
                  </li>
                ))}
              </ul>
            </Section>
          )}
        </>
      )}
    </div>
  )
}

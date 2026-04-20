import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { apiPost } from '../api/client'
import type { DebtData } from '../api/types'
import PageHeader from '../components/layout/PageHeader'
import Section from '../components/layout/Section'
import DataTable from '../components/data/DataTable'
import KPICard from '../components/data/KPICard'
import EmptyState from '../components/layout/EmptyState'
import { fmt, fmtFull } from '../components/data/CurrencyDisplay'

interface SimResult {
  ok: boolean
  strategy: string
  converged: boolean
  months: number
  total_interest: number
  total_paid: number
  by_debt: { name: string; months_to_zero: number | null; interest_paid: number }[]
  warnings: string[]
}

export default function DebtPage() {
  const { data } = useApi<DebtData>('/debt')
  const [strategy, setStrategy] = useState('avalanche')
  const [extra, setExtra] = useState(100)
  const [sim, setSim] = useState<SimResult | null>(null)
  const [simLoading, setSimLoading] = useState(false)

  const runSim = async () => {
    setSimLoading(true)
    try {
      const result = await apiPost<SimResult>('/debt/simulate', {
        strategy,
        extra_monthly: extra,
      })
      setSim(result)
    } finally {
      setSimLoading(false)
    }
  }

  if (!data || data.debts.length === 0) {
    return (
      <div>
        <PageHeader title="Debt" />
        <EmptyState message="No debt accounts." />
      </div>
    )
  }

  return (
    <div>
      <PageHeader title="Debt" sub={`Total: ${fmt(data.total)}`} />

      <DataTable
        columns={[
          { key: 'name', header: 'Account', render: (r) => r.name },
          { key: 'type', header: 'Type', render: (r) => r.account_type },
          { key: 'balance', header: 'Balance', align: 'right', render: (r) => fmtFull(r.balance) },
          { key: 'apr', header: 'APR', align: 'right', render: (r) => r.apr !== null ? `${r.apr}%` : '--' },
          { key: 'min', header: 'Min Payment', align: 'right', render: (r) => r.min_payment !== null ? fmtFull(r.min_payment) : '--' },
        ]}
        rows={data.debts}
      />

      <Section title="Payoff Simulator">
        <div className="flex gap-4 items-end mb-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Strategy</label>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              className="border rounded px-2 py-1 text-sm"
            >
              <option value="avalanche">Avalanche (highest APR first)</option>
              <option value="snowball">Snowball (smallest balance first)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Extra monthly ($)</label>
            <input
              type="number"
              value={extra}
              onChange={(e) => setExtra(Number(e.target.value))}
              className="border rounded px-2 py-1 text-sm w-24"
              min={0}
            />
          </div>
          <button
            onClick={runSim}
            disabled={simLoading}
            className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {simLoading ? 'Running...' : 'Simulate'}
          </button>
        </div>

        {sim && (
          <div>
            <div className="grid grid-cols-3 gap-4 mb-4">
              <KPICard label="Months to Freedom" value={String(sim.months)} />
              <KPICard label="Total Interest" value={fmt(sim.total_interest)} color="red" />
              <KPICard label="Total Paid" value={fmt(sim.total_paid)} />
            </div>
            <DataTable
              columns={[
                { key: 'name', header: 'Debt', render: (r) => r.name },
                { key: 'months', header: 'Months', align: 'right', render: (r) => r.months_to_zero ?? '--' },
                { key: 'interest', header: 'Interest', align: 'right', render: (r) => fmtFull(r.interest_paid) },
              ]}
              rows={sim.by_debt}
            />
            {sim.warnings.length > 0 && (
              <div className="mt-3 text-xs text-yellow-600">
                {sim.warnings.map((w, i) => <div key={i}>{w}</div>)}
              </div>
            )}
          </div>
        )}
      </Section>
    </div>
  )
}

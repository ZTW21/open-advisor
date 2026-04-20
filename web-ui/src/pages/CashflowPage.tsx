import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import type { CashflowData } from '../api/types'
import PageHeader from '../components/layout/PageHeader'
import Section from '../components/layout/Section'
import KPICard from '../components/data/KPICard'
import CashflowBar from '../components/charts/CashflowBar'
import DataTable from '../components/data/DataTable'
import { fmt, fmtFull } from '../components/data/CurrencyDisplay'

const windows = ['7d', '30d', '3m', '6m', '1y']
const groupBys = ['category', 'merchant', 'account'] as const

export default function CashflowPage() {
  const [window, setWindow] = useState('30d')
  const [by, setBy] = useState<string>('category')
  const { data } = useApi<CashflowData>(`/cashflow?window=${window}&by=${by}`)

  return (
    <div>
      <PageHeader title="Cashflow" />

      <div className="flex gap-2 mb-4">
        {windows.map((w) => (
          <button
            key={w}
            onClick={() => setWindow(w)}
            className={`px-2 py-1 text-xs rounded ${
              window === w ? 'bg-blue-600 text-white' : 'bg-white border text-gray-600'
            }`}
          >
            {w}
          </button>
        ))}
        <span className="mx-2 text-gray-300">|</span>
        {groupBys.map((g) => (
          <button
            key={g}
            onClick={() => setBy(g)}
            className={`px-2 py-1 text-xs rounded ${
              by === g ? 'bg-blue-600 text-white' : 'bg-white border text-gray-600'
            }`}
          >
            {g}
          </button>
        ))}
      </div>

      {data && (
        <>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <KPICard label="Inflow" value={fmt(data.totals.inflow)} color="green" />
            <KPICard label="Outflow" value={fmt(data.totals.outflow)} color="red" />
            <KPICard
              label="Net"
              value={fmt(data.totals.net)}
              color={data.totals.net >= 0 ? 'green' : 'red'}
            />
          </div>

          <Section title={`By ${by}`}>
            <CashflowBar data={data.buckets} limit={12} />
          </Section>

          <Section title="Detail">
            <DataTable
              columns={[
                { key: 'key', header: by, render: (r) => r.key },
                { key: 'inflow', header: 'Inflow', align: 'right', render: (r) => fmtFull(r.inflow) },
                { key: 'outflow', header: 'Outflow', align: 'right', render: (r) => fmtFull(r.outflow) },
                { key: 'net', header: 'Net', align: 'right', render: (r) => fmtFull(r.net) },
                { key: 'count', header: 'Txns', align: 'right', render: (r) => r.count },
              ]}
              rows={data.buckets}
            />
          </Section>
        </>
      )}
    </div>
  )
}

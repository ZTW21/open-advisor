import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import PageHeader from '../components/layout/PageHeader'
import Section from '../components/layout/Section'
import EmptyState from '../components/layout/EmptyState'

type Cadence = 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'annual'

export default function ReportsPage() {
  const [cadence, setCadence] = useState<Cadence>('monthly')
  const { data, loading } = useApi<Record<string, unknown>>(`/reports/${cadence}`)

  return (
    <div>
      <PageHeader title="Reports" />

      <div className="flex gap-2 mb-4">
        {(['daily', 'weekly', 'monthly', 'quarterly', 'annual'] as Cadence[]).map((c) => (
          <button
            key={c}
            onClick={() => setCadence(c)}
            className={`px-2 py-1 text-xs rounded capitalize ${
              cadence === c ? 'bg-blue-600 text-white' : 'bg-white border text-gray-600'
            }`}
          >
            {c}
          </button>
        ))}
      </div>

      {loading && <div className="text-sm text-gray-400">Loading...</div>}

      {data && (
        <Section title={`${cadence} report`}>
          <pre className="text-xs text-gray-700 overflow-x-auto whitespace-pre-wrap">
            {JSON.stringify(data, null, 2)}
          </pre>
        </Section>
      )}

      {!loading && !data && <EmptyState message="No data for this report." />}
    </div>
  )
}

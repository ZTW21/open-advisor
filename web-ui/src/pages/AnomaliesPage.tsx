import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import type { Anomaly } from '../api/types'
import PageHeader from '../components/layout/PageHeader'
import StatusDot from '../components/data/StatusDot'
import EmptyState from '../components/layout/EmptyState'
import { fmtFull } from '../components/data/CurrencyDisplay'

interface AnomaliesData {
  ok: boolean
  window: string
  anomalies: Anomaly[]
  count: number
}

const windows = ['7d', '30d', '3m', '6m']

export default function AnomaliesPage() {
  const [window, setWindow] = useState('30d')
  const { data } = useApi<AnomaliesData>(`/anomalies?window=${window}`)

  return (
    <div>
      <PageHeader title="Anomalies" sub={data ? `${data.count} flags` : undefined} />

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
      </div>

      {data && data.anomalies.length > 0 ? (
        <ul className="space-y-3">
          {data.anomalies.map((a, i) => (
            <li key={i} className="bg-white border rounded-lg p-3">
              <div className="flex items-start gap-2">
                <StatusDot status={a.severity === 'alert' ? 'red' : a.severity === 'warn' ? 'yellow' : 'info'} />
                <div>
                  <div className="text-sm font-medium">{a.subject}</div>
                  <div className="text-sm text-gray-600">{a.detail}</div>
                  <div className="text-xs text-gray-400 mt-1">
                    {a.kind} {a.date && `| ${a.date}`} {a.amount !== null && `| ${fmtFull(a.amount)}`}
                  </div>
                </div>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState message="No anomalies detected." />
      )}
    </div>
  )
}

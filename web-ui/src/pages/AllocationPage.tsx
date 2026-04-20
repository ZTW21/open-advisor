import { useApi } from '../hooks/useApi'
import type { AllocationData } from '../api/types'
import PageHeader from '../components/layout/PageHeader'
import Section from '../components/layout/Section'
import AllocationPie from '../components/charts/AllocationPie'
import DataTable from '../components/data/DataTable'
import EmptyState from '../components/layout/EmptyState'
import { fmt } from '../components/data/CurrencyDisplay'

export default function AllocationPage() {
  const { data } = useApi<AllocationData>('/allocation')

  if (!data) return null

  return (
    <div>
      <PageHeader title="Allocation" sub={`Total assets: ${fmt(data.assets_total)}`} />

      {data.by_class.length > 0 ? (
        <>
          <Section title="Current Allocation">
            <AllocationPie data={data.by_class} />
          </Section>

          {data.targets_set && (
            <Section title="Drift vs. Targets">
              <DataTable
                columns={[
                  { key: 'class', header: 'Asset Class', render: (r) => r.asset_class },
                  { key: 'current', header: 'Current', align: 'right', render: (r) => `${r.current_pct.toFixed(1)}%` },
                  {
                    key: 'target',
                    header: 'Target',
                    align: 'right',
                    render: (r) => r.target_pct !== null ? `${r.target_pct.toFixed(1)}%` : '--',
                  },
                  {
                    key: 'drift',
                    header: 'Drift',
                    align: 'right',
                    render: (r) =>
                      r.drift_pp !== null ? (
                        <span className={Math.abs(r.drift_pp) > 5 ? 'text-red-600 font-medium' : ''}>
                          {r.drift_pp > 0 ? '+' : ''}{r.drift_pp.toFixed(1)}pp
                        </span>
                      ) : '--',
                  },
                ]}
                rows={data.drift}
              />
            </Section>
          )}
        </>
      ) : (
        <EmptyState message="No asset balances recorded." hint="Add balances via: finance balance set" />
      )}
    </div>
  )
}

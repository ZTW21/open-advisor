import { useApi } from '../hooks/useApi'
import type { RecurringItem } from '../api/types'
import PageHeader from '../components/layout/PageHeader'
import DataTable from '../components/data/DataTable'
import EmptyState from '../components/layout/EmptyState'
import { fmt, fmtFull } from '../components/data/CurrencyDisplay'

interface RecurringData {
  ok: boolean
  recurring: RecurringItem[]
  count: number
  total_estimated_annual: number
}

export default function RecurringPage() {
  const { data } = useApi<RecurringData>('/recurring')

  return (
    <div>
      <PageHeader
        title="Recurring Charges"
        sub={data ? `${data.count} detected | Est. annual: ${fmt(data.total_estimated_annual)}` : undefined}
      />

      {data && data.recurring.length > 0 ? (
        <DataTable
          columns={[
            { key: 'merchant', header: 'Merchant', render: (r) => r.merchant },
            { key: 'category', header: 'Category', render: (r) => r.category },
            { key: 'monthly', header: 'Monthly', align: 'right', render: (r) => fmtFull(r.estimated_monthly) },
            { key: 'annual', header: 'Annual', align: 'right', render: (r) => fmtFull(r.estimated_annual) },
            { key: 'hits', header: 'Hits', align: 'right', render: (r) => r.hits },
            { key: 'last', header: 'Last Charge', render: (r) => r.last_date },
          ]}
          rows={data.recurring}
        />
      ) : (
        <EmptyState message="No recurring charges detected." hint="Need 3+ months of data." />
      )}
    </div>
  )
}

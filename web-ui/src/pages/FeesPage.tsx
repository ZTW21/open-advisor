import { useApi } from '../hooks/useApi'
import type { FeeData } from '../api/types'
import PageHeader from '../components/layout/PageHeader'
import Section from '../components/layout/Section'
import DataTable from '../components/data/DataTable'
import EmptyState from '../components/layout/EmptyState'
import { fmt, fmtFull } from '../components/data/CurrencyDisplay'

export default function FeesPage() {
  const { data } = useApi<FeeData>('/fees')

  if (!data) return null

  return (
    <div>
      <PageHeader
        title="Fee Audit"
        sub={`Est. annual cost: ${fmt(data.total_annual_cost)} | Threshold: ${data.threshold_pct}%`}
      />

      {data.accounts.length > 0 ? (
        <Section title="Accounts with Fee Info">
          <DataTable
            columns={[
              { key: 'account', header: 'Account', render: (r) => r.account },
              { key: 'type', header: 'Type', render: (r) => r.account_type },
              { key: 'er', header: 'Expense Ratio', align: 'right', render: (r) => r.expense_ratio_pct !== null ? `${r.expense_ratio_pct}%` : '--' },
              { key: 'fee', header: 'Annual Fee', align: 'right', render: (r) => r.annual_fee !== null ? fmtFull(r.annual_fee) : '--' },
              { key: 'cost', header: 'Est. Annual Cost', align: 'right', render: (r) => fmtFull(r.total_annual_cost) },
            ]}
            rows={data.accounts}
          />
        </Section>
      ) : (
        <EmptyState
          message="No fee info recorded."
          hint="Run: finance account edit --expense-ratio 0.03"
        />
      )}

      {data.missing_fee_info.length > 0 && (
        <Section title="Missing Fee Info">
          <p className="text-sm text-gray-500">
            These investment accounts have no expense ratio or annual fee recorded:{' '}
            {data.missing_fee_info.join(', ')}
          </p>
        </Section>
      )}
    </div>
  )
}

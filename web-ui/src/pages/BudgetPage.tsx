import { useApi } from '../hooks/useApi'
import PageHeader from '../components/layout/PageHeader'
import DataTable from '../components/data/DataTable'
import EmptyState from '../components/layout/EmptyState'
import { fmtFull } from '../components/data/CurrencyDisplay'

interface BudgetData {
  ok: boolean
  month: string
  budgets: { category: string; planned: number; actual: number; variance: number; variance_pct: number | null }[]
}

export default function BudgetPage() {
  const { data } = useApi<BudgetData>('/budget')

  return (
    <div>
      <PageHeader title="Budget vs. Actual" sub={data ? data.month : undefined} />
      {data && data.budgets.length > 0 ? (
        <DataTable
          columns={[
            { key: 'category', header: 'Category', render: (r) => r.category },
            { key: 'planned', header: 'Planned', align: 'right', render: (r) => fmtFull(r.planned) },
            { key: 'actual', header: 'Actual', align: 'right', render: (r) => fmtFull(r.actual) },
            {
              key: 'variance',
              header: 'Variance',
              align: 'right',
              render: (r) => (
                <span className={r.variance > 0 ? 'text-red-600' : 'text-green-600'}>
                  {r.variance > 0 ? '+' : ''}{fmtFull(r.variance)}
                </span>
              ),
            },
          ]}
          rows={data.budgets}
        />
      ) : (
        <EmptyState
          message="No budgets set."
          hint="Set budgets via the CLI to see comparisons here."
        />
      )}
    </div>
  )
}

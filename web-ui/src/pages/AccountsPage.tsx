import { useApi } from '../hooks/useApi'
import type { AccountListData } from '../api/types'
import PageHeader from '../components/layout/PageHeader'
import DataTable from '../components/data/DataTable'
import EmptyState from '../components/layout/EmptyState'
import { fmtFull } from '../components/data/CurrencyDisplay'

export default function AccountsPage() {
  const { data } = useApi<AccountListData>('/accounts')

  return (
    <div>
      <PageHeader title="Accounts" sub={data ? `${data.count} active` : undefined} />
      {data && data.accounts.length > 0 ? (
        <DataTable
          columns={[
            { key: 'name', header: 'Name', render: (r) => r.name },
            { key: 'type', header: 'Type', render: (r) => r.account_type },
            {
              key: 'balance',
              header: 'Balance',
              align: 'right',
              render: (r) => r.balance !== null ? fmtFull(r.balance) : '--',
            },
            { key: 'as_of', header: 'As Of', render: (r) => r.balance_as_of || '--' },
          ]}
          rows={data.accounts}
        />
      ) : (
        <EmptyState message="No accounts yet." hint="Run: finance account add" />
      )}
    </div>
  )
}

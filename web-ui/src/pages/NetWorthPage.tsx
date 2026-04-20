import { useApi } from '../hooks/useApi'
import type { NetWorthData, NetWorthHistory } from '../api/types'
import PageHeader from '../components/layout/PageHeader'
import Section from '../components/layout/Section'
import NetWorthChart from '../components/charts/NetWorthChart'
import DataTable from '../components/data/DataTable'
import { fmtFull } from '../components/data/CurrencyDisplay'

export default function NetWorthPage() {
  const { data } = useApi<NetWorthData>('/networth')
  const { data: hist } = useApi<NetWorthHistory>('/networth/history?months=24')

  return (
    <div>
      <PageHeader title="Net Worth" sub={data ? `As of ${data.as_of}` : undefined} />

      {hist && hist.history.length > 0 && (
        <Section title="History (24 months)">
          <NetWorthChart data={hist.history} />
        </Section>
      )}

      {data && (
        <Section title="Breakdown">
          <DataTable
            columns={[
              { key: 'account', header: 'Account', render: (r) => r.account },
              { key: 'type', header: 'Type', render: (r) => r.account_type },
              {
                key: 'balance',
                header: 'Balance',
                align: 'right',
                render: (r) => r.balance !== null ? fmtFull(r.balance) : '--',
              },
              { key: 'as_of', header: 'As Of', render: (r) => r.as_of_date || '--' },
            ]}
            rows={data.breakdown}
            emptyMessage="No accounts with balances."
          />
        </Section>
      )}
    </div>
  )
}

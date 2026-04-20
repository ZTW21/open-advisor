import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import type { TransactionsData } from '../api/types'
import PageHeader from '../components/layout/PageHeader'
import DataTable from '../components/data/DataTable'
import EmptyState from '../components/layout/EmptyState'
import { fmtFull } from '../components/data/CurrencyDisplay'

export default function TransactionsPage() {
  const [search, setSearch] = useState('')
  const [offset, setOffset] = useState(0)
  const limit = 50
  const qParam = search ? `&q=${encodeURIComponent(search)}` : ''
  const { data } = useApi<TransactionsData>(
    `/transactions?limit=${limit}&offset=${offset}${qParam}`
  )

  return (
    <div>
      <PageHeader title="Transactions" sub={data ? `${data.total} total` : undefined} />

      <div className="mb-4">
        <input
          type="text"
          placeholder="Search description..."
          className="border border-gray-300 rounded px-3 py-1.5 text-sm w-64"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setOffset(0) }}
        />
      </div>

      {data && data.transactions.length > 0 ? (
        <>
          <DataTable
            columns={[
              { key: 'date', header: 'Date', render: (r) => r.date },
              { key: 'description', header: 'Description', render: (r) => r.merchant || r.description },
              { key: 'account', header: 'Account', render: (r) => r.account },
              { key: 'category', header: 'Category', render: (r) => r.category || '--' },
              {
                key: 'amount',
                header: 'Amount',
                align: 'right',
                render: (r) => (
                  <span className={r.amount >= 0 ? 'text-green-600' : 'text-red-600'}>
                    {fmtFull(r.amount)}
                  </span>
                ),
              },
            ]}
            rows={data.transactions}
          />
          <div className="flex justify-between items-center mt-4 text-sm text-gray-500">
            <button
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - limit))}
              className="px-3 py-1 border rounded disabled:opacity-30"
            >
              Previous
            </button>
            <span>
              {offset + 1}–{Math.min(offset + limit, data.total)} of {data.total}
            </span>
            <button
              disabled={offset + limit >= data.total}
              onClick={() => setOffset(offset + limit)}
              className="px-3 py-1 border rounded disabled:opacity-30"
            >
              Next
            </button>
          </div>
        </>
      ) : (
        <EmptyState message="No transactions." hint="Run: finance import" />
      )}
    </div>
  )
}

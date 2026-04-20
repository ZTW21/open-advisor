import { useApi } from '../hooks/useApi'
import { fmt } from '../components/data/CurrencyDisplay'
import type { DashboardData } from '../api/types'

const modeBadge = {
  debt: 'bg-red-100 text-red-700',
  invest: 'bg-green-100 text-green-700',
  balanced: 'bg-blue-100 text-blue-700',
}

export default function TopBar() {
  const { data } = useApi<DashboardData>('/dashboard')

  return (
    <header className="h-10 bg-white border-b border-gray-200 flex items-center px-4 gap-4 text-sm shrink-0">
      {data && (
        <>
          <span className="font-medium">{fmt(data.net_worth.total)}</span>
          <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${modeBadge[data.mode.mode]}`}>
            {data.mode.mode}
          </span>
          {data.net_worth.oldest_balance_as_of && (
            <span className="text-gray-400 text-xs ml-auto">
              data as of {data.net_worth.oldest_balance_as_of}
            </span>
          )}
        </>
      )}
    </header>
  )
}

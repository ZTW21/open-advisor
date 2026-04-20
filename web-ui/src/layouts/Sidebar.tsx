import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', label: 'Overview' },
  { to: '/net-worth', label: 'Net Worth' },
  { to: '/accounts', label: 'Accounts' },
  { to: '/cashflow', label: 'Cashflow' },
  { to: '/transactions', label: 'Transactions' },
  { to: '/budget', label: 'Budget' },
  { to: '/goals', label: 'Goals' },
  { to: '/debt', label: 'Debt' },
  { to: '/allocation', label: 'Allocation' },
  { to: '/fees', label: 'Fees' },
  { to: '/anomalies', label: 'Anomalies' },
  { to: '/recurring', label: 'Recurring' },
  { to: '/categories', label: 'Categories' },
  { to: '/afford', label: 'Afford' },
  { to: '/reports', label: 'Reports' },
]

export default function Sidebar() {
  return (
    <aside className="w-48 bg-white border-r border-gray-200 flex flex-col py-4 shrink-0">
      <div className="px-4 mb-4">
        <h1 className="text-sm font-bold text-gray-800 tracking-tight">open-advisor</h1>
      </div>
      <nav className="flex-1 overflow-y-auto">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            className={({ isActive }) =>
              `block px-4 py-1.5 text-sm ${
                isActive
                  ? 'text-blue-600 bg-blue-50 font-medium'
                  : 'text-gray-600 hover:bg-gray-50'
              }`
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}

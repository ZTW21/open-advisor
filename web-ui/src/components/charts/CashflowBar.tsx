import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { fmt } from '../data/CurrencyDisplay'
import type { CashflowBucket } from '../../api/types'

interface CashflowBarProps {
  data: CashflowBucket[]
  limit?: number
}

export default function CashflowBar({ data, limit = 8 }: CashflowBarProps) {
  const items = data.slice(0, limit).map((b) => ({
    name: b.key.length > 16 ? b.key.slice(0, 14) + '...' : b.key,
    outflow: b.outflow,
    inflow: b.inflow,
  }))
  if (items.length === 0) return null
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={items} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} angle={-30} textAnchor="end" height={60} />
        <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => fmt(v)} width={60} />
        <Tooltip formatter={(v: number) => fmt(v)} />
        <Bar dataKey="outflow" fill="#f87171" name="Outflow" />
        <Bar dataKey="inflow" fill="#34d399" name="Inflow" />
      </BarChart>
    </ResponsiveContainer>
  )
}

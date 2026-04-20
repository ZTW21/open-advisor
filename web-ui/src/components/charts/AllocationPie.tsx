import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { fmt } from '../data/CurrencyDisplay'

interface Slice {
  asset_class: string
  balance: number
  pct: number
}

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#6366f1', '#14b8a6']

interface AllocationPieProps {
  data: Slice[]
}

export default function AllocationPie({ data }: AllocationPieProps) {
  if (data.length === 0) return null
  return (
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie
          data={data}
          dataKey="balance"
          nameKey="asset_class"
          cx="50%"
          cy="50%"
          outerRadius={80}
          label={({ asset_class, pct }: Slice) => `${asset_class} ${pct.toFixed(0)}%`}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip formatter={(v: number) => fmt(v)} />
      </PieChart>
    </ResponsiveContainer>
  )
}

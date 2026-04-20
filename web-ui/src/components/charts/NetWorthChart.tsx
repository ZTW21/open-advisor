import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { fmt } from '../data/CurrencyDisplay'

interface Point {
  date: string
  net_worth: number
}

interface NetWorthChartProps {
  data: Point[]
}

export default function NetWorthChart({ data }: NetWorthChartProps) {
  if (data.length === 0) return null
  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 11 }}
          tickFormatter={(v: string) => v.slice(5)}
        />
        <YAxis
          tick={{ fontSize: 11 }}
          tickFormatter={(v: number) => fmt(v)}
          width={70}
        />
        <Tooltip formatter={(v: number) => fmt(v)} />
        <Area
          type="monotone"
          dataKey="net_worth"
          stroke="#3b82f6"
          fill="#dbeafe"
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}

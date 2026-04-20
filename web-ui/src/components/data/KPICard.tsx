interface KPICardProps {
  label: string
  value: string
  sub?: string
  color?: 'green' | 'yellow' | 'red' | 'gray'
}

const colorMap = {
  green: 'text-green-600',
  yellow: 'text-yellow-600',
  red: 'text-red-600',
  gray: 'text-gray-600',
}

export default function KPICard({ label, value, sub, color = 'gray' }: KPICardProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</div>
      <div className={`text-2xl font-semibold mt-1 ${colorMap[color]}`}>{value}</div>
      {sub && <div className="text-xs text-gray-400 mt-1">{sub}</div>}
    </div>
  )
}

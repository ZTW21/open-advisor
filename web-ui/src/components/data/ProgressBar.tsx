interface ProgressBarProps {
  current: number
  target: number
  status: 'green' | 'yellow' | 'red' | 'info'
}

const barColors = {
  green: 'bg-green-400',
  yellow: 'bg-yellow-400',
  red: 'bg-red-400',
  info: 'bg-gray-300',
}

export default function ProgressBar({ current, target, status }: ProgressBarProps) {
  const pct = target > 0 ? Math.min(100, (current / target) * 100) : 0
  return (
    <div className="w-full bg-gray-100 rounded-full h-2">
      <div
        className={`h-2 rounded-full ${barColors[status]}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

interface StatusDotProps {
  status: 'green' | 'yellow' | 'red' | 'info'
  label?: string
}

const dotColors = {
  green: 'bg-green-400',
  yellow: 'bg-yellow-400',
  red: 'bg-red-400',
  info: 'bg-gray-300',
}

export default function StatusDot({ status, label }: StatusDotProps) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`inline-block w-2 h-2 rounded-full ${dotColors[status]}`} />
      {label && <span className="text-sm text-gray-600">{label}</span>}
    </span>
  )
}

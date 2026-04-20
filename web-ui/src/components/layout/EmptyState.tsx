interface EmptyStateProps {
  message: string
  hint?: string
}

export default function EmptyState({ message, hint }: EmptyStateProps) {
  return (
    <div className="text-center py-12">
      <p className="text-gray-500 text-sm">{message}</p>
      {hint && (
        <p className="text-gray-400 text-xs mt-2 font-mono">{hint}</p>
      )}
    </div>
  )
}

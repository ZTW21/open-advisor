import { useApi } from '../hooks/useApi'
import type { GoalProgress } from '../api/types'
import PageHeader from '../components/layout/PageHeader'
import Section from '../components/layout/Section'
import StatusDot from '../components/data/StatusDot'
import ProgressBar from '../components/data/ProgressBar'
import EmptyState from '../components/layout/EmptyState'
import { fmt } from '../components/data/CurrencyDisplay'

interface GoalsData {
  ok: boolean
  as_of: string
  goals: GoalProgress[]
}

export default function GoalsPage() {
  const { data } = useApi<GoalsData>('/goals')

  if (!data || data.goals.length === 0) {
    return (
      <div>
        <PageHeader title="Goals" />
        <EmptyState message="No active goals." hint="Create goals via the CLI." />
      </div>
    )
  }

  return (
    <div>
      <PageHeader title="Goals" sub={`As of ${data.as_of}`} />
      {data.goals.map((g) => (
        <Section key={g.id} title={g.name}>
          <div className="flex items-center justify-between text-sm mb-2">
            <StatusDot status={g.status} label={g.status} />
            <span className="text-gray-500">
              {fmt(g.current)}
              {g.target_amount && <> / {fmt(g.target_amount)}</>}
            </span>
          </div>
          {g.target_amount && (
            <ProgressBar current={g.current} target={g.target_amount} status={g.status} />
          )}
          {g.target_date && (
            <div className="text-xs text-gray-400 mt-2">Target: {g.target_date}</div>
          )}
          {g.expected_at_pace !== null && (
            <div className="text-xs text-gray-400">
              Expected at pace: {fmt(g.expected_at_pace)}
            </div>
          )}
        </Section>
      ))}
    </div>
  )
}

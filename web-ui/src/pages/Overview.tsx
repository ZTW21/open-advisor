import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { apiFetch } from '../api/client'
import type { DashboardData, NetWorthHistory, CashflowData, InsightsData } from '../api/types'
import KPICard from '../components/data/KPICard'
import Section from '../components/layout/Section'
import EmptyState from '../components/layout/EmptyState'
import NetWorthChart from '../components/charts/NetWorthChart'
import CashflowBar from '../components/charts/CashflowBar'
import StatusDot from '../components/data/StatusDot'
import ProgressBar from '../components/data/ProgressBar'
import { fmt, fmtPct } from '../components/data/CurrencyDisplay'

const severityStyles: Record<string, { border: string; bg: string; icon: string }> = {
  alert:    { border: 'border-red-400',    bg: 'bg-red-50',    icon: '!' },
  warn:     { border: 'border-yellow-400', bg: 'bg-yellow-50', icon: '~' },
  info:     { border: 'border-blue-400',   bg: 'bg-blue-50',   icon: 'i' },
  positive: { border: 'border-green-400',  bg: 'bg-green-50',  icon: '+' },
}

const severityIconColors: Record<string, string> = {
  alert:    'bg-red-400 text-white',
  warn:     'bg-yellow-400 text-white',
  info:     'bg-blue-400 text-white',
  positive: 'bg-green-400 text-white',
}

export default function Overview() {
  const { data, loading } = useApi<DashboardData>('/dashboard')
  const { data: nwHist } = useApi<NetWorthHistory>('/networth/history?months=12')
  const { data: cf } = useApi<CashflowData>('/cashflow?window=30d&by=category')
  const { data: insightsData, refetch: refetchInsights } = useApi<InsightsData>('/insights')

  const [dismissing, setDismissing] = useState<Set<number>>(new Set())

  if (loading) return <div className="text-gray-400 text-sm">Loading...</div>
  if (!data) return <EmptyState message="Could not load dashboard." />

  const sr = data.savings_rate
  const srColor = sr.rate === null ? 'gray' : sr.rate >= 0.1 ? 'green' : sr.rate >= 0 ? 'yellow' : 'red'

  const insights = (insightsData?.insights ?? []).filter(i => !dismissing.has(i.id))

  const handleDismiss = async (id: number) => {
    setDismissing(prev => new Set(prev).add(id))
    try {
      await apiFetch(`/insights/${id}/dismiss`, { method: 'POST' })
      refetchInsights()
    } catch {
      setDismissing(prev => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    }
  }

  return (
    <div>
      {/* Advisor Insights */}
      {insights.length > 0 && (
        <div className="mb-6 space-y-2">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Your Advisor
          </h2>
          {insights.map((insight) => {
            const style = severityStyles[insight.severity] || severityStyles.info
            const iconColor = severityIconColors[insight.severity] || severityIconColors.info
            return (
              <div
                key={insight.id}
                className={`border-l-4 ${style.border} ${style.bg} rounded-r-lg px-4 py-3 flex items-start gap-3`}
              >
                <span
                  className={`flex-shrink-0 w-5 h-5 rounded-full ${iconColor} flex items-center justify-center text-xs font-bold mt-0.5`}
                >
                  {style.icon}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900">{insight.title}</p>
                  <p className="text-sm text-gray-600 mt-0.5">{insight.body}</p>
                </div>
                <button
                  onClick={() => handleDismiss(insight.id)}
                  className="flex-shrink-0 text-gray-400 hover:text-gray-600 p-1 -mr-1"
                  title="Dismiss"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            )
          })}
        </div>
      )}

      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KPICard label="Net Worth" value={fmt(data.net_worth.total)} />
        <KPICard
          label="Savings Rate (30d)"
          value={sr.rate !== null ? fmtPct(sr.rate * 100) : '--'}
          color={srColor}
        />
        <KPICard
          label="Cashflow (30d)"
          value={fmt(data.cashflow_30d.net)}
          sub={`${fmt(data.cashflow_30d.inflow)} in / ${fmt(data.cashflow_30d.outflow)} out`}
          color={data.cashflow_30d.net >= 0 ? 'green' : 'red'}
        />
        <KPICard label="Accounts" value={String(data.net_worth.account_count)} />
      </div>

      {/* Net worth chart */}
      {nwHist && nwHist.history.length > 0 && (
        <Section title="Net Worth (12 months)">
          <NetWorthChart data={nwHist.history} />
        </Section>
      )}

      {/* Cashflow by category */}
      {cf && cf.buckets.length > 0 && (
        <Section title="Spending by Category (30 days)">
          <CashflowBar data={cf.buckets} />
        </Section>
      )}

      {/* Goals */}
      {data.goals.length > 0 && (
        <Section title="Goals">
          <div className="space-y-3">
            {data.goals.map((g) => (
              <div key={g.id}>
                <div className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2">
                    <StatusDot status={g.status} />
                    {g.name}
                  </span>
                  <span className="text-gray-500">
                    {fmt(g.current)}
                    {g.target_amount && <> / {fmt(g.target_amount)}</>}
                  </span>
                </div>
                {g.target_amount && (
                  <ProgressBar current={g.current} target={g.target_amount} status={g.status} />
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Anomalies */}
      {data.anomalies.length > 0 && (
        <Section title="Recent Flags">
          <ul className="space-y-1">
            {data.anomalies.map((a, i) => (
              <li key={i} className="text-sm flex items-start gap-2">
                <StatusDot status={a.severity === 'alert' ? 'red' : a.severity === 'warn' ? 'yellow' : 'info'} />
                <span>{a.detail}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* Budget */}
      {data.budget_vs_actual.length > 0 && (
        <Section title="Budget vs. Actual (this month)">
          <div className="space-y-2">
            {data.budget_vs_actual.map((b) => (
              <div key={b.category} className="flex items-center justify-between text-sm">
                <span>{b.category}</span>
                <span className={b.variance > 0 ? 'text-red-600' : 'text-green-600'}>
                  {fmt(b.actual)} / {fmt(b.planned)}
                  {b.variance > 0 && <span className="ml-1">(+{fmt(b.variance)})</span>}
                </span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {data.net_worth.account_count === 0 && (
        <EmptyState
          message="No accounts yet."
          hint="Run: finance account add"
        />
      )}
    </div>
  )
}

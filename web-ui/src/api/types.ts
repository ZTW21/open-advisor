// Shared API response types

export interface ApiResponse {
  ok: boolean
  error?: string
  message?: string
}

export interface DashboardData extends ApiResponse {
  as_of: string
  net_worth: {
    total: number
    assets: number
    liabilities: number
    oldest_balance_as_of: string | null
    account_count: number
  }
  mode: {
    mode: 'debt' | 'invest' | 'balanced'
    reasons: string[]
  }
  cashflow_30d: {
    start: string
    end: string
    inflow: number
    outflow: number
    net: number
    count: number
  }
  savings_rate: {
    income: number
    spent: number
    saved: number
    rate: number | null
  }
  goals: GoalProgress[]
  budget_vs_actual: BudgetLine[]
  anomalies: Anomaly[]
}

export interface NetWorthData extends ApiResponse {
  as_of: string
  assets_total: number
  liabilities_total: number
  net_worth: number
  oldest_balance_as_of: string | null
  breakdown: AccountBalance[]
}

export interface NetWorthHistory extends ApiResponse {
  months: number
  history: { date: string; net_worth: number; assets: number; liabilities: number }[]
}

export interface AccountBalance {
  account: string
  account_type: string
  balance: number | null
  as_of_date: string | null
}

export interface AccountListData extends ApiResponse {
  accounts: {
    id: number
    name: string
    account_type: string
    active: boolean
    asset_class: string | null
    balance: number | null
    balance_as_of: string | null
  }[]
  count: number
}

export interface GoalProgress {
  id: number
  name: string
  target_amount: number | null
  target_date: string | null
  priority: number
  current: number
  current_as_of: string | null
  expected_at_pace: number | null
  status: 'green' | 'yellow' | 'red' | 'info'
}

export interface BudgetLine {
  category: string
  planned: number
  actual: number
  variance: number
  variance_pct: number | null
}

export interface Anomaly {
  kind: string
  severity: 'info' | 'warn' | 'alert'
  subject: string
  detail: string
  amount: number | null
  txn_id: number | null
  date: string | null
}

export interface CashflowBucket {
  key: string
  inflow: number
  outflow: number
  net: number
  count: number
}

export interface CashflowData extends ApiResponse {
  window: string
  start: string
  end: string
  totals: { inflow: number; outflow: number; net: number; count: number }
  by: string
  buckets: CashflowBucket[]
}

export interface TransactionItem {
  id: number
  date: string
  amount: number
  description: string
  merchant: string | null
  account: string
  category: string
  is_transfer: boolean
}

export interface TransactionsData extends ApiResponse {
  transactions: TransactionItem[]
  total: number
  limit: number
  offset: number
}

export interface DebtItem {
  account_id: number
  name: string
  account_type: string
  balance: number
  apr: number | null
  min_payment: number | null
  as_of_date: string | null
}

export interface DebtData extends ApiResponse {
  as_of: string
  debts: DebtItem[]
  total: number
}

export interface AllocationData extends ApiResponse {
  as_of: string
  assets_total: number
  by_class: { asset_class: string; balance: number; pct: number; accounts: string[] }[]
  targets: Record<string, number>
  targets_set: boolean
  drift: { asset_class: string; current_pct: number; target_pct: number | null; drift_pp: number | null }[]
  missing_balance: string[]
}

export interface FeeData extends ApiResponse {
  as_of: string
  threshold_pct: number
  accounts: {
    account: string
    account_type: string
    balance: number | null
    expense_ratio_pct: number | null
    annual_fee: number | null
    expense_cost: number | null
    total_annual_cost: number
  }[]
  flagged: unknown[]
  total_annual_cost: number
  missing_fee_info: string[]
}

export interface RecurringItem {
  merchant: string
  category: string
  hits: number
  median_amount: number
  last_amount: number
  last_date: string
  estimated_monthly: number
  estimated_annual: number
}

export interface ModeData extends ApiResponse {
  as_of: string
  mode: 'debt' | 'invest' | 'balanced'
  reasons: string[]
  inputs: Record<string, unknown>
}

export interface Insight {
  id: number
  insight_key: string
  type: string
  severity: 'positive' | 'info' | 'warn' | 'alert'
  title: string
  body: string
  source: string
  created_at: string
  updated_at: string
}

export interface InsightsData extends ApiResponse {
  as_of: string
  insights: Insight[]
  count: number
}

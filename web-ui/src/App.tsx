import { BrowserRouter, Route, Routes } from 'react-router-dom'
import DashboardLayout from './layouts/DashboardLayout'
import Overview from './pages/Overview'
import NetWorthPage from './pages/NetWorthPage'
import AccountsPage from './pages/AccountsPage'
import CashflowPage from './pages/CashflowPage'
import TransactionsPage from './pages/TransactionsPage'
import BudgetPage from './pages/BudgetPage'
import GoalsPage from './pages/GoalsPage'
import DebtPage from './pages/DebtPage'
import AllocationPage from './pages/AllocationPage'
import FeesPage from './pages/FeesPage'
import AnomaliesPage from './pages/AnomaliesPage'
import RecurringPage from './pages/RecurringPage'
import CategoriesPage from './pages/CategoriesPage'
import AffordPage from './pages/AffordPage'
import ReportsPage from './pages/ReportsPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<DashboardLayout />}>
          <Route path="/" element={<Overview />} />
          <Route path="/net-worth" element={<NetWorthPage />} />
          <Route path="/accounts" element={<AccountsPage />} />
          <Route path="/cashflow" element={<CashflowPage />} />
          <Route path="/transactions" element={<TransactionsPage />} />
          <Route path="/budget" element={<BudgetPage />} />
          <Route path="/goals" element={<GoalsPage />} />
          <Route path="/debt" element={<DebtPage />} />
          <Route path="/allocation" element={<AllocationPage />} />
          <Route path="/fees" element={<FeesPage />} />
          <Route path="/anomalies" element={<AnomaliesPage />} />
          <Route path="/recurring" element={<RecurringPage />} />
          <Route path="/categories" element={<CategoriesPage />} />
          <Route path="/afford" element={<AffordPage />} />
          <Route path="/reports" element={<ReportsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

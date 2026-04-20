import { useApi } from '../hooks/useApi'
import PageHeader from '../components/layout/PageHeader'
import DataTable from '../components/data/DataTable'
import Section from '../components/layout/Section'
import EmptyState from '../components/layout/EmptyState'

interface Category {
  id: number
  name: string
  parent_id: number | null
  is_income: boolean
  is_transfer: boolean
}

interface CatRule {
  id: number
  pattern: string
  match_type: string
  category_name: string
  priority: number
}

interface CatData {
  ok: boolean
  categories: Category[]
  count: number
}

interface RulesData {
  ok: boolean
  rules: CatRule[]
  count: number
}

export default function CategoriesPage() {
  const { data: cats } = useApi<CatData>('/categories')
  const { data: rules } = useApi<RulesData>('/categories/rules')

  return (
    <div>
      <PageHeader title="Categories" sub={cats ? `${cats.count} categories` : undefined} />

      {cats && cats.categories.length > 0 ? (
        <Section title="Categories">
          <DataTable
            columns={[
              { key: 'name', header: 'Name', render: (r) => r.name },
              { key: 'income', header: 'Income', render: (r) => r.is_income ? 'Yes' : '' },
              { key: 'transfer', header: 'Transfer', render: (r) => r.is_transfer ? 'Yes' : '' },
            ]}
            rows={cats.categories}
          />
        </Section>
      ) : (
        <EmptyState message="No categories yet." hint="Run: finance categorize" />
      )}

      {rules && rules.rules.length > 0 && (
        <Section title="Categorization Rules">
          <DataTable
            columns={[
              { key: 'pattern', header: 'Pattern', render: (r) => r.pattern },
              { key: 'type', header: 'Match', render: (r) => r.match_type },
              { key: 'category', header: 'Category', render: (r) => r.category_name },
              { key: 'priority', header: 'Priority', align: 'right', render: (r) => r.priority },
            ]}
            rows={rules.rules}
          />
        </Section>
      )}
    </div>
  )
}

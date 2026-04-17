---
name: Category Taxonomy
description: The user's spending categories. User-editable. The CLI references this when categorizing. Changes here affect reports immediately.
type: taxonomy
updated: 2026-04-17
stale_after: 365d
related:
  - transactions/rules.md
sources: []
---

# Spending Categories

*Default taxonomy below. User can add/remove/rename during onboarding or any time.*

## Structure

Each category has a **name**, an optional **parent** (for subcategories), and flags:
- `is_transfer` — true for self-transfers and paying credit card balances (excluded from income/spend aggregates)
- `is_income` — true for income categories

## Income

- **Salary** — regular W-2 paychecks
- **Bonus** — discretionary, annual, signing
- **Self-employment** — 1099, business income
- **Interest** — HYSA, CD, bond interest
- **Dividends** — stock/fund dividends
- **Capital gains** — realized gains from sales
- **Refunds & reimbursements** — tax refunds, expense reimbursements
- **Gifts received**
- **Other income**

## Fixed expenses

- **Housing**
  - Rent / Mortgage
  - Property tax
  - HOA
  - Home insurance
- **Utilities**
  - Electric
  - Gas
  - Water / sewer
  - Internet
  - Phone
- **Insurance**
  - Health premium
  - Auto insurance
  - Life insurance
  - Disability insurance
  - Umbrella
- **Debt service**
  - Student loans
  - Car payment
  - Personal loan
  - Credit card interest (only the interest, not the principal)

## Variable essentials

- **Groceries**
- **Transportation**
  - Gas
  - Public transit
  - Parking
  - Rideshare
  - Car maintenance
- **Medical**
  - Copays
  - Prescriptions
  - Dental
  - Vision
- **Childcare & education**

## Discretionary

- **Dining out**
- **Entertainment**
- **Shopping — clothing**
- **Shopping — household**
- **Travel**
- **Gifts given**
- **Subscriptions** (streaming, apps, memberships)
- **Personal care**
- **Hobbies**

## Savings & investing

- **Emergency fund contribution**
- **Retirement contribution** (401k, IRA)
- **Taxable brokerage contribution**
- **HSA contribution**
- **529 contribution**
- **Goal savings** (by goal name)

## Taxes

- **Federal income tax**
- **State income tax**
- **FICA / Medicare**
- **Estimated payments**
- **Property tax** (if itemized separately)

## Transfers (excluded from income/spend aggregates)

- **Internal transfer**
- **Credit card payment**
- **Loan payment** (principal portion)

## One-time / other

- **Major purchase** (flag for review)
- **Unusual** (flag for review)
- **Uncategorized** (flagged — must be resolved)

## Naming convention

Use **title case**. Keep names short. Use `/` to nest when a quick look-up matters (e.g., `Transportation / Gas`). The CLI stores these as `parent:child` internally.

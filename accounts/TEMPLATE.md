---
name: <Account display name, e.g. "Chase Checking">
description: <One-line purpose, e.g. "Primary operating checking account">
type: account
account_type: <checking|savings|credit_card|brokerage|retirement|loan|mortgage|cash|other>
institution: <e.g. Chase, Fidelity, Ally>
account_nickname_in_db: <the short `name` used with `finance account` — e.g. chase_checking>
opened_on: <YYYY-MM-DD or "unknown">
updated: <YYYY-MM-DD — date you last touched this file>
stale_after: 180d
related: [state/net-worth.md, state/debts.md]
sources: [data/finance.sqlite, manual entry]
---

# <Account display name>

> Copy this file to `accounts/<nickname>.md` (matching `account_nickname_in_db`) when registering a real account.
> Balances and transactions live in the database — **do not** write dollar amounts here. This file is narrative only.

## Purpose

<Why does this account exist? What role does it play in the plan?
 Examples:
  - "Operating account — paycheck lands here, bills leave here, target balance ~1 month expenses."
  - "Emergency fund — 6 months of expenses. Don't touch unless emergency."
  - "Roth IRA — retirement, Boglehead three-fund tilt, max out annually.">

## Features & terms

<Whatever is relevant to the account type. Leave out what doesn't apply.

 Checking / savings:
  - APY, minimum balance, monthly fees, ATM network, overdraft behavior

 Credit card:
  - APR (purchase, cash advance, penalty), statement close date, due date
  - Rewards structure (cashback %, category bonuses, annual fee)
  - Credit limit

 Brokerage / retirement:
  - Expense ratios of default holdings
  - Trading fees / commissions
  - Match % (for 401k), vesting schedule
  - Contribution limit for current year

 Loan / mortgage:
  - APR (fixed/variable), term (years remaining), monthly payment
  - Prepayment penalty, recast rules, escrow details>

## Rules & reminders

<Anything specific to how this account should (or should not) be used.
 Examples:
  - "Keep balance between $2k–$5k. Sweep anything over $5k to HYSA on the 15th."
  - "Designated for down payment — don't touch until 2028."
  - "Autopay in full every month. Never carry a balance."
  - "Annual fee hits in March — decide by Feb whether to downgrade.">

## Beneficiaries

<For retirement, life insurance, and brokerage accounts. Keep current — beneficiary designations
 override the will. Review after marriage, divorce, birth, death.

 Examples:
  - "Primary: <spouse name>, 100%. Contingent: <child name>, 100%."
  - "Primary: <name>, 50%; <name>, 50%. Contingent: estate.">

## Historical notes

<When opened, why, any significant events.
 Examples:
  - "Opened 2019-03 when I started at Acme — needed direct deposit account."
  - "2024-02: Rolled over old 401k from previous employer.">

## Links

<Login URL, customer service phone, mobile app. **No credentials, no full account numbers, no SSN.**

 Examples:
  - Login: https://chase.com
  - Customer service: 1-800-xxx-xxxx
  - Mobile app: Chase (iOS/Android)>

---

## What does NOT go in this file

- **Balances** — the database holds those. Use `finance balance set --account <name> --balance <n>`.
- **Transactions** — imported via `finance import`. Query with `finance cashflow`.
- **Holdings** (shares, cost basis) — stored in the `holdings` table.
- **Credentials, full account numbers, routing numbers, SSN** — never written anywhere.

If you need a dollar figure in narrative ("HYSA should hold ~6 months expenses"), that's fine.
But actual current balances come from the database, not from here.

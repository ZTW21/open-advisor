---
name: Accounts Folder Guide
description: Guide for account markdown files. Not loaded into context by default.
type: folder-readme
---

# Accounts — one markdown file per account

Each account gets its own markdown file. **Narrative and metadata only** — balances and transactions live in the database.

## Filename convention

`<institution>-<account-type>.md` or `<institution>-<nickname>.md`

- `chase-checking.md`
- `hysa-ally.md`
- `401k-fidelity.md`
- `roth-ira-vanguard.md`
- `brokerage-schwab.md`
- `mortgage-wells-fargo.md`
- `cc-amex-gold.md`
- `cc-chase-sapphire.md`

## Frontmatter template

```yaml
---
name: <account name>
description: <one-line purpose>
type: account
account_type: <checking|savings|credit_card|brokerage|retirement|loan|mortgage|cash|other>
institution: <name>
account_id_in_db: <stable id used by the CLI>
updated: <ISO date>
stale_after: 90d
related: [state/net-worth.md]
sources: [data/finance.sqlite, manual entry]
---
```

## Body sections

Use these sections (omit any that don't apply):

- **Purpose** — why the account exists, what role it plays in the overall plan
- **Beneficiaries** — who's named (keep current — this overrides the will)
- **Fees** — maintenance fees, trading fees, expense ratios of default holdings
- **Features** — relevant features (match %, interest rate, rewards categories, APR)
- **Rules & reminders** — anything specific (e.g., "don't touch — designated for down payment")
- **Historical notes** — when opened, why, significant events
- **Links** — login URL (not credentials), customer service, app

## What doesn't go here

- Balances (DB)
- Transactions (DB)
- Holdings (DB — snapshot table)
- Credentials, full account numbers, routing numbers — never written anywhere automated

## Accounts populate in Phase 4.

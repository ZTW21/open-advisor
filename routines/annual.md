---
name: Annual Review
description: Mid-December full-year review. Tax prep handoff, insurance and beneficiary check, goal reset, philosophy check, strategy refresh from the Long arc down.
type: routine
cadence: annual (mid-December, covering the current calendar year; early-January tax-pack follow-up allowed)
output_length: full review (~2–4 pages)
updated: 2026-04-17
stale_after: never
related:
  - reports/
  - STRATEGY.md
  - routines/strategy-refresh.md
  - routines/life-event.md
  - routines/consolidate-memory.md
  - state/tax.md
  - state/insurance.md
  - state/estate.md
  - principles.md
  - rules.md
sources:
  - finance_advisor/commands/report.py (annual)
  - finance_advisor/commands/taxpack.py
  - finance_advisor/commands/fees.py
  - finance_advisor/commands/rebalance.py
---

# Annual Review

Once a year — mid-December covers the current year early enough to act on year-end tax moves; early January is a valid fallback for a cleaner finalize. This is the one routine that rewrites `STRATEGY.md` top-to-bottom, including the Long arc.

## Trigger

- On demand: user says "run the annual" / "year-end review" / "close out 2026."
- Life-event hygiene can also call this routine at year-end.
- This advisor is pull-based. Mid-December is a good moment for tax-year moves — a calendar reminder is the right nudge.

## Flow

### 1. Pull the payload

```
finance --json report annual --year YYYY
```

Default (no flag) is `today.year - 1` — the last complete calendar year. If the user is running this in mid-December, pass `--year <current year>` explicitly to get the in-progress year; the payload will honor Jan 1 → Dec 31 and note where balances are stale.

The payload returns:

- `totals` — full-year inflow, outflow, net.
- `savings_rate` — annual rate.
- `net_worth` — Jan 1 and Dec 31, delta, percent.
- `year_over_year` — outflow delta vs. prior year.
- `by_category` / `by_merchant` — top 15 / top 10.
- `goals` — year-end status per goal.
- `tax_pack` — the nested tax-handoff bundle (same numbers as `finance tax-pack --year YYYY`): income, spend by category, net-worth anchors, "notable" matches (charitable, medical, mortgage, tax, HSA, retirement, student-loan).
- `allocation` — year-end allocation plus drift vs. targets.
- `fees` — flagged accounts and `missing_fee_info`.
- `anomalies` — top events from the year.

### 2. Compose the review

Target length: ~2–4 pages. Ten sections, cite-grounded.

1. **The year in review** — one paragraph. Financially and in life. Pull from `memory/facts/` and `memory/decisions/` — this is the one time per year you read those folders end-to-end.
2. **Net worth trajectory** — annual delta, plus 3- and 5-year context if `reports/` history is available. Cite the oldest anchor date; flag any stale-data gaps.
3. **Cash flow totals** — income, spend, saved, rate. Y/Y comparison. One paragraph.
4. **Goal progress** — status dot per goal. For each, state: where it started the year, where it ended, what it needs in year N+1. Propose a new target or timeline if the current one doesn't fit the data.
5. **Tax prep handoff** — read `tax_pack.income`, `tax_pack.spend_by_category`, and `tax_pack.notable`. Name the totals the user will need at filing time:
   - Gross income (tagged): per category.
   - Potentially deductible spend: each category in `notable` with the total and the txn count.
   - Net-worth anchors for the year.
   Append the CLI disclaimer verbatim (`pack.disclaimer`). Do not compute liability. Refer to a CPA or filing software for any move above ordinary deductions.
6. **Insurance review** — walk through `state/insurance.md`. For each policy (life, disability, health, auto, home, umbrella, LTC): premium paid this year, coverage amount, gap check against rules of thumb (e.g., 10× income for term life). Flag any policy that hasn't been updated since a life event. This is a read-through; do not edit the file.
7. **Beneficiary review** — read `state/estate.md`. For each account and policy: confirm primary and contingent beneficiaries are still the right names. Flag any "tbd," "???," missing contingent, or a name that's no longer relevant (post-divorce, ex-employer, etc.). Per CLAUDE.md §7, refer actual changes to a licensed estate attorney or the custodian's beneficiary form.
8. **Fee audit year-end** — summarize `fees.total_annual_cost`. For each `flagged` account, translate into a y/y dollar cost and propose a swap at the asset-class level.
9. **Philosophy check** — is `principles.md` still right? Did any position shift this year (e.g., "I'm willing to hold bonds now," "I'm done with individual stocks")? Is `rules.md` still what the user wants to follow? Propose at most 2–3 concrete edits; let the user accept or decline.
10. **Next year strategy** — three to five actions for the first quarter of the new year. Pull from `STRATEGY.md § Next 12 months` and shape by what the year revealed.

Close with: **"Life-event hygiene — anything that should have triggered a `life-event.md` run but didn't?"** If the answer is yes, run that routine *after* the annual review (separate session).

### 3. Save the report

```
finance --json report annual --year YYYY --write
```

Writes `reports/YYYY-annual.md`. The CLI's default body is factual prose; the advisor's message is canonical.

### 4. Refresh STRATEGY.md

Run `routines/strategy-refresh.md` at **annual depth**. That routine owns the rewrite protocol — citation rules, History row, memory pass. Annual depth means:

- Rewrite **everything**: Current stance, Next 30 days, Next 90 days, Next 12 months, **Long arc** (the one time per year this gets touched), Dependencies, Open gaps, Open questions, What I'm not doing.
- Bump the **major** version (e.g., 0.4 → 1.0 for the first annual; 1.3 → 2.0 thereafter).
- Append one row to the History table.

### 5. Memory consolidation pass

Run `routines/consolidate-memory.md` in annual mode:

- Retire any memory older than 2 years unless it's still load-bearing.
- Compress `memory/patterns/` — if a pattern has held for a year, fold it into `principles.md` or `rules.md` as an explicit rule. Write `memory/decisions/` for the promotion.
- Re-confirm every `memory/watchlist/` item.
- Keep `memory/MEMORY.md` under 50 lines.

### 6. Tax-pack follow-up (early January)

If the review runs in December, schedule an explicit follow-up in early January once final-year data has settled. The follow-up runs:

```
finance --json tax-pack --year YYYY
```

...and delivers the refined numbers to the user as the CPA handoff bundle.

## Content rules

- Cite every number. Every figure traces to the payload or a file.
- No tickers (CLAUDE.md §2). Asset-class and criteria only.
- No tax-liability estimate. No withholding-adequacy verdict. Numbers handed to a pro.
- Flag stale data (CLAUDE.md §6). Balances older than 15 days at year-end are suspect; surface them.
- Honest about a bad year. If net worth dropped or savings rate was negative, say so plainly before the next-year planning.

## Voice example (opening shape)

> **2026 — the year in review.** Net worth $228,400 → $289,700 (+$61,300, +26.8% — driven by continued 401k contributions, equity recovery, and one $8k bonus in March). Cash flow: $94,200 income, $62,400 spent, 33.8% savings rate — up from 27.1% in 2025 and ahead of the 25% target in `rules.md`.
>
> **Goals.** 🟢 Emergency fund held at 5 months of expenses all year. 🟢 Roth 2026 fully funded at the $7,000 cap. 🟡 Down payment fund ($54k of $60k) — on pace for a 2027-Q3 finish; target was 2027-06, close enough to not reset.
>
> **Tax prep handoff.** Gross income (tagged): $94,200. Potentially deductible, per `finance tax-pack`: charitable $3,200 across 11 txns, medical $1,440, HSA contributions $4,150. Not computed as a liability — that's your CPA / filing software. Net-worth anchors for form entry: Jan 1 $228,400; Dec 31 $289,700.
>
> **Insurance.** Term life $500k still in place, premium $480/yr. Rule-of-thumb 10× income says $940k — the gap has grown as income climbed; consider bumping coverage at renewal. Umbrella policy unchanged; auto and home renewed at +8% (inflation tracks). Nothing actionable immediately but worth discussing.
>
> **Beneficiaries.** 401k primary still listed as sibling — you mentioned last July you wanted to revisit this after the marriage; flagging it again. The custodian's form takes 10 minutes; no attorney needed for the designation itself.
>
> **Fees.** Total cost of ownership ~$310/yr after last Q2's Wealthfront swap — down from $560/yr at the start of the year. No new flags. Fidelity 401k blended ER still not recorded — if you can grab the number off the annual disclosure, we'll update.
>
> **Philosophy check.** `principles.md` line "bonds in tax-advantaged only" held across the year. `rules.md` savings floor was 15%; you cleared 33% — consider bumping the floor to 20% for 2027 as a soft target. That's a discussion, not a this-minute edit.
>
> **Next year (top 5):**
> 1. Bump term life at March renewal to $900k+.
> 2. Update 401k beneficiary to spouse.
> 3. Finish down-payment fund by Q3; decide between house hunt and delaying a year.
> 4. Pull Fidelity 401k ER into `accounts/fidelity-401k.md`.
> 5. Revisit `rules.md` savings floor after the Q1 monthly cycle lands.

## What this routine does NOT do

- **Never executes trades, transfers, contributions, or beneficiary changes** (CLAUDE.md §1). The user acts.
- **Never computes tax liability, withholding adequacy, or filing-ready numbers.** Surface the aggregates; hand off.
- **Never endorses or declines specific insurance products.** Name the coverage gap and the rule of thumb; let the user and their broker decide.
- **Never revises `principles.md` or `rules.md` unilaterally.** Propose edits; user approves and writes.

## Safety

- Every dollar figure cites the CLI or a state file.
- Insurance adequacy and estate changes are licensed-professional territory (CLAUDE.md §7). The advisor writes the checklist; the pro signs off.
- If the year surfaces a life event that wasn't processed in the moment, run `routines/life-event.md` separately — don't fold it into the annual.

## Timing

- **December 15 target.** Early enough for year-end tax moves (Roth conversions, TLH, HSA catch-up, charitable bunching); late enough that most of the year's data is in.
- **January follow-up** — refined `tax-pack` once final-year balances settle, delivered as a CPA handoff.
- **Annual routine does not run mid-year.** If the user asks for a "half-year checkpoint," that's a quarterly, not an annual.

## Useful sub-commands

| Task | Command |
|---|---|
| Last complete year | `finance --json report annual` |
| Specific year | `finance --json report annual --year YYYY` |
| Save to reports/ | `finance --json report annual --year YYYY --write` |
| Tax-pack only | `finance --json tax-pack --year YYYY` |
| Fee audit only | `finance --json fees` |
| Rebalance payload | `finance --json rebalance` |

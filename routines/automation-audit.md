---
name: Automation Audit
description: Semiannual review of every recurring charge and auto-debit. Keep, cancel, negotiate, or consolidate. The "subscription creep" sweep.
type: routine
cadence: semiannual (April and October; falls out of the Q2 and Q4 routines)
output_length: one page
updated: 2026-04-17
stale_after: 200d
related:
  - CLAUDE.md
  - principles.md
  - rules.md
  - routines/quarterly.md
  - memory/decisions/
sources:
  - finance_advisor/commands/automation.py
  - finance_advisor/commands/cashflow.py
  - finance_advisor/analytics.py (detect_recurring)
---

# Automation Audit

Money leaks through things you signed up for once and forgot about. This
routine catches the leak. Twice a year, we list every recurring outflow,
price it annualized, and make a keep/cancel/negotiate decision per line.

The goal isn't frugality for its own sake — it's alignment. Every recurring
charge should be a deliberate choice, not inertia.

## Trigger

- User-initiated: "audit my subscriptions" / "where's my money going?" /
  "what am I paying for monthly?"
- Also triggered when `finance cashflow --by merchant` surfaces a surprising
  monthly recurring pattern during a weekly or monthly routine.
- This advisor is pull-based. April 1 and October 1 are sensible semiannual
  checkpoints — if the user wants the nudge, a recurring calendar event is
  the right tool.

## Flow

### 1. Pull the payload

```
finance --json automation --lookback-months 6
```

Returns a list of merchants that charged at least 3 distinct months in the
lookback window with stable amounts (within ±15% of the median). Each row:
merchant, category, monthly, annual, hits, months seen.

If the user wants a wider net, try:

```
finance --json automation --lookback-months 12 --min-hits 4 --tolerance 0.25
```

### 2. Group the list

Three buckets — print them as plain prose groups in the output, not a table:

- **Utilities and required bills** (electric, water, internet, phone, rent,
  mortgage, insurance premiums). These are either needed or negotiable;
  rarely cancelable. Focus on whether the price is still competitive
  (phone/internet especially).
- **Productivity and work** (software, cloud storage, LLM subscriptions,
  pro memberships). Keep if actively used; evaluate consolidation (one
  cloud drive instead of three).
- **Lifestyle and discretionary** (streaming, gym, meal kits, apps, box
  subscriptions). The meaty bucket — most subscription creep lives here.

### 3. For each row, one question

> "Have you used [merchant] in the last 30 days?"

That's the only question. It short-circuits rationalization ("but I *might*
watch it"). If the answer is no, it's a cancel unless the user wants to
actively defend it.

Don't list them one at a time unless there are fewer than five. For longer
lists, print them grouped (per step 2) and ask the user to flag anything
they want to keep. The default disposition for everything not flagged is
"cancel."

### 4. Translate to dollar terms

For any charge the user is hesitating on, translate:

- Monthly cost × 12 = annual cost.
- Annual cost ÷ hourly wage = hours of work to pay for it.
- Annual cost × 30 years at 7% real return = the "keep" cost in a
  retirement number.

The last translation is the most motivating. $20/month for something
unused is $24,000 in foregone retirement dollars over 30 years.

### 5. Honor the `rules.md` line

If `rules.md` has the classic rule *"no subscriptions I haven't used in
the last 60 days"* — quote it verbatim and apply it mechanically. The
user wrote that rule during a calm moment; the audit is where it earns
its keep.

### 6. Make the plan

Three kinds of actions — the user executes each themselves (no command
here moves money):

- **Cancel.** Walk through each cancellation path. Some are one-click;
  some require phone calls; some require writing a letter. If the path is
  painful, surface that ("this one requires calling AT&T during business
  hours; budget 20 minutes").
- **Negotiate.** For utilities and insurance, "call and ask for a
  retention discount" saves more per hour than almost anything. Mention
  the last negotiated price if recorded in `memory/decisions/`.
- **Consolidate.** If there are three cloud drives, two streaming services
  of the same type, or overlapping gym memberships, recommend picking one.

### 7. Log the decisions

Write `memory/decisions/YYYY-MM-DD-automation-audit.md`:

```markdown
# Automation audit: 2026-04-17

## Cancellations (approved)
- Adobe Photoshop — $20.99/mo — unused for 4 months. Saves $251.88/yr.
- Meal kit X — $80/mo — switching to groceries. Saves $960/yr.

## Negotiations planned
- Verizon — currently $95/mo. Last negotiation: 2025-03 at $80/mo (expired).
  User to call by 2026-04-25 for retention.

## Kept (actively used and approved)
- Netflix, Spotify, Google One, gym.

## Total saved (if all cancellations follow through)
- $1,211.88/yr  (~$101/mo)

## Next audit: 2026-10
```

### 8. Set the follow-up

Write a reminder entry in `memory/watchlist/automation-audit-followup.md`
with the cancellations the user committed to. The next monthly routine
checks whether those charges disappeared from `finance cashflow --by merchant`.

## Output shape

One page of prose. Grouped bullet lists are fine here — this is one of the
few routines where a list is genuinely the right format. Keep each item
to one line. End with the total annual savings and the follow-up date.

Example ending:

> If you cancel Adobe, the meal kit, and two of the three cloud drives,
> you'll save ~$1,260/yr — about $38,000 over 30 years at a 7% real
> return. The phone call for Verizon is worth ~$180/yr on its own. I'll
> check in during the May monthly to confirm the charges dropped off.

## What this routine does NOT do

- **Never cancels on the user's behalf.** We list; they act.
- **Never judges the keep decisions.** If the user wants to pay $80/mo for
  a service you find useless, that's their call — note the cost, move on.
- **Never extrapolates rules** ("you kept this one, so keep all similar
  ones"). Each subscription stands on its own.

## Safety

- Every number cites `finance automation` or a prior decision entry.
- If `rules.md` is empty (no spending rules stated), don't manufacture one
  — offer to add one during the next onboarding refresh.
- Essential services (utilities, insurance, rent/mortgage) get scrutinized
  for price, not for existence. Don't suggest canceling electricity.

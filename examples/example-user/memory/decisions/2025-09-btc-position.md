---
name: BTC position — drift-down, not sell-down
description: Alex holds 6% of portfolio in BTC, above the 5% single-asset ceiling in rules.md. Decision: don't sell; let it drift down via new-money allocation.
type: decision
updated: 2025-09-18
stale_after: 365d
related:
  - rules.md
  - principles.md
  - accounts/fidelity-roth.md
---

# BTC position — drift-down, not sell-down

**Date:** 2025-09-18.

**Decision:** keep the existing BTC position (~6% of total portfolio). Don't sell to bring it to 5%. Do not add to it with new money. Let new contributions flow into index funds per `principles.md`, which will mechanically drift the BTC % down over time.

**The rule being nudged:** `rules.md § Concentration` — "no single holding over 5% of total portfolio."

**Why we chose the drift-down path:**
1. Selling would realize a long-term capital gain. In Alex's federal bracket (24%), plus the position's cost basis from 2019, the tax cost of forcing the position to 5% now was ~$1,400. Not catastrophic, but not free.
2. The rule exists to manage concentration risk going forward, not to require an immediate sell to the line. Drift-down achieves the same endpoint on a ~24 month horizon given projected contribution volume.
3. Alex was explicit: "I don't want to sell BTC I'm comfortable with just to satisfy a spreadsheet rule. I do want to stop it growing as a share."

**How this is logged as an override:**
- This is a technical violation of `rules.md` at the moment — the position is 6%, not ≤5%. The rule's intent is honored by the glide path; the letter of it is not.
- Monthly reports will note the position percentage until it's under 5%. When it crosses 5%, close this out in `decisions/` as resolved.
- If BTC price spikes materially (position crosses 8%), revisit — at that point the tax cost of a partial sale may be worth it.

**Status (as of 2026-04):** position is ~5.9% per `finance net-worth`. Trending in the right direction, slowly. On pace to drop under 5% in Q4 2026 if BTC stays range-bound.

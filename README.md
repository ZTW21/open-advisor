# Financial Advisor

An open-source, **local-first** personal financial advisor. It lives in a directory on your own machine. Narrative lives in markdown files you can read and edit. Numbers live in a local SQLite database. An AI assistant — paired with a deterministic CLI — onboards you, ingests your financial reality, and delivers short, honest, cited advice on a cadence you control.

Opinionated by default (Boglehead investing philosophy). Editable spine. Never executes trades or moves money — it advises; you act.

---

## Why this exists

Personal finance tools split roughly into three camps:

1. **Bank-linked aggregators** (Mint, Monarch, Copilot) that auto-categorize transactions but live on someone else's servers and usually lock you in.
2. **Spreadsheet/plain-text setups** (Beancount, YNAB) that put you in control but require hours of discipline to extract insights.
3. **Robo-advisors** (Betterment, Wealthfront) that automate the investing side but treat everything else as out of scope.

This project is a fourth option: your data stays local, the files are human-readable, the advisor is opinionated enough to be useful on day one, and it gets smarter about *you* specifically over time through a structured memory system. It uses an AI assistant for reasoning and a deterministic CLI for math — the assistant never does arithmetic on your money.

## What you get

- **A guided onboarding routine.** The advisor walks you through who you are, what you own, what you owe, what you want, and what rules you want to live by. Everything it learns goes into editable markdown files.
- **A deterministic CLI (`finance`)** that owns every number: imports, dedup, categorization, net worth, cash flow, rebalance drift, debt payoff schedules, budget vs. actual, fees audit, tax-pack generation, subscription detection, behavioral-mode classification.
- **Scheduled briefs.** A one-sentence daily, a ~150-word weekly every Sunday evening, a monthly report, quarterly review, annual review. All observational — the advisor flags; you decide.
- **A structured memory system.** The advisor remembers your stated preferences, corrections, decisions, and observed patterns — and cites them when it advises.
- **A master strategy (`STRATEGY.md`)** it maintains on your behalf, broken into Long arc / Next 12 months / Next 30 days. You never write this by hand.
- **Advisory routines** for the hard moments: "can I afford this?", "should I sell in a crash?", "how do I pay down this debt?", "what should I do with this bonus?", "we just had a kid — what changes?"

## The hard rules it won't violate

These apply regardless of what you ask:

1. No trades, transfers, or payments — it advises; you execute.
2. No specific ticker recommendations — advice lives at the category level ("a total-market index fund with an expense ratio under 0.10%"), not the security level.
3. No arithmetic done in its head — every number comes from the CLI, cited.
4. No writes to the database without a dry-run preview and your explicit confirmation.
5. No credentials, SSNs, or full account numbers written to any file.
6. Stale data is flagged, not hidden.
7. Licensed-professional territory (estate law, complex state tax, divorce, bankruptcy) is routed to a real professional.
8. Distress triage: if you're in imminent financial crisis, free resources (211, nonprofit credit counseling) come before generic advice.

## Architecture at a glance

```
your-finance-dir/
  CLAUDE.md            Router + persona + hard rules (loaded every turn)
  STRATEGY.md          Advisor's living master plan
  profile.md           Who you are
  principles.md        Investing philosophy (Boglehead default)
  rules.md             Your personal guardrails
  goals.md             What you're working toward

  bin/finance          CLI entry point
  src/finance_advisor/ Python source: importers, dedup, analytics, routines
  tests/               Fixtures and unit tests

  data/
    finance.sqlite     Working database (git-ignored)
    exports/           JSON snapshots (committed to git for history)
    backups/           Dated DB snapshots (git-ignored)
    secrets/           Sync tokens (git-ignored; 0600)

  memory/              Structured memory system
    MEMORY.md          Index, always loaded

  accounts/            One markdown file per real account
  state/               Net worth, income, debts, insurance, tax, estate snapshots
  transactions/
    inbox/             Where you drop CSV/OFX statements for import
    processed/         Files the importer has already consumed

  routines/            Specs for daily/weekly/monthly/quarterly/annual flows
                       plus on-demand flows (afford, windfall, life-event, ...)
  reports/             Generated outputs, dated
  decisions/           Journal of meaningful moves, with reasoning
  scenarios/           What-if analyses
```

## Quickstart

Requirements: Python 3.10+.

```bash
# 1. Clone the framework
git clone https://github.com/<your-username>/open-advisor.git my-money
cd my-money

# 2. Install dependencies
pip install -e .

# 3. Initialize the database
bin/finance init

# 4. Ask your AI assistant to run onboarding
#    (see routines/onboarding.md — any Claude-capable assistant can follow it)
```

After onboarding you'll have populated `profile.md`, `goals.md`, `rules.md`, `state/*`, one `accounts/*.md` per real account, and a first pass at `STRATEGY.md`. The advisor will offer to register the seven scheduled jobs (daily/weekly/monthly/quarterly/annual briefs, semiannual automation audit, nightly sync).

For a worked example of what a populated directory looks like, see [`examples/example-user/`](examples/example-user/).

## Day-to-day usage

You interact through your AI assistant, not the CLI directly. Typical turns:

- "What's my net worth?" → runs `finance net-worth`, cites the DB.
- "Where did my money go this month?" → runs `finance cashflow --last 30d`.
- "I got a $5k bonus. What should I do with it?" → follows `routines/windfall.md`, honoring any preferences in `memory/preferences/`.
- "Can I afford a $2,400 laptop?" → follows `routines/afford.md`, checks your cushion / pace / goal impact.
- "The market is down 15% — should I sell?" → follows `routines/loss-aversion.md`, quotes your own `rules.md` back at you verbatim.
- "Give me the weekly" → runs the weekly routine; the scheduled version fires Sundays at 6pm local.

If you want to poke the CLI directly, everything supports `--json` and has stable error codes. See `bin/finance --help`.

## Privacy

Short version: everything stays local by default. Nothing leaves your machine unless you explicitly share it with an AI assistant (which you control), a CPA, or a partner. The full statement is [`PRIVACY.md`](PRIVACY.md).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). The framework is deliberately small — adding a new "routine" is usually a single markdown file; adding a new CLI command is a single Python file. Tests live in `tests/`.

## License

MIT. See [`LICENSE`](LICENSE).

## Status

**v1.0.0** — feature-complete for single-user US usage. The default `csv_inbox` sync adapter (drop a statement into `transactions/inbox/`, run `finance import`) is fully supported. SimpleFIN and Plaid adapters are scaffolded with a stable adapter contract but not wired to the network — they return a structured `not_configured` / `not_implemented` error until someone ships the client code.

Known deferred work: multi-household finances, non-US tax regimes, investment holdings snapshots (brokerage positions vs. cash balances). See [`CHANGELOG.md`](CHANGELOG.md) for what shipped in v1.0.0 and [`CONTRIBUTING.md`](CONTRIBUTING.md) for how to help.

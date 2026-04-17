# Upgrading

You'll spend a lot of time populating this directory — onboarding produces a `STRATEGY.md`, memory files, state snapshots, account narratives, decision journals. None of that should be at risk when you pull in a framework update.

This project is built so that upgrading is a `git pull` away, and your populated data is never in the blast radius. Here's how.

## The split

The repo is cleanly divided into two halves:

**Framework** — code, routines, scaffolds, docs. Versioned in git. Safe to overwrite on every upgrade.

- `CLAUDE.md`, `README.md`, `CONTRIBUTING.md`, `PRIVACY.md`, `UPGRADING.md`, `LICENSE`, `CHANGELOG.md`
- `pyproject.toml`, `bin/`, `src/`, `tests/`
- `routines/` — how the advisor behaves
- `examples/` — a reference user directory
- `templates/` — the scaffolds that seed fresh installs (more on this below)
- Folder READMEs: `accounts/README.md`, `accounts/TEMPLATE.md`, `decisions/README.md`, `reports/README.md`, `scenarios/README.md`, `state/README.md`, `memory/README.md`, `memory/onboarding.md`, `memory/*/README.md`

**User data** — the answers you gave, the plan the advisor built, the numbers in your database. Lives on your machine only; `.gitignore` keeps it out of the repo.

- `STRATEGY.md`, `profile.md`, `principles.md`, `rules.md`, `goals.md`
- `state/*.md` (except the README)
- `memory/MEMORY.md` and everything under `memory/*/` except the per-folder READMEs
- `accounts/*.md` (except README and TEMPLATE)
- `decisions/*.md`, `scenarios/*.md`, `reports/*`
- `data/finance.sqlite`, `data/backups/`, `data/secrets/`, `transactions/inbox/*`, `transactions/processed/*`

The distinction is enforced by `.gitignore` at the repo root. When you stage, commit, or push, Git will never include your user data.

## First install

```bash
git clone https://github.com/<owner>/open-advisor.git my-money
cd my-money
pip install -e .
finance init
```

`finance init` creates `data/finance.sqlite`, runs schema migrations, and **hydrates templates** — it copies every file in `templates/` into the corresponding location in your finance directory, but only if the destination doesn't exist yet. After that, your assistant can run `routines/onboarding.md` to populate the files with your real life.

`finance init` is idempotent. Re-run it any time; it only copies what's missing.

## Upgrading to a new release

The workflow is a standard git-upstream-remote pattern. You only set up the remote once.

```bash
# One-time: point at the canonical repo
git remote add upstream https://github.com/<owner>/open-advisor.git

# Every upgrade
git fetch upstream
git merge upstream/main          # or: git rebase upstream/main

# Pick up any new templates that shipped
finance init

# Run the test suite to confirm nothing's broken
pytest
```

### Why this works

Your populated files are gitignored at the repo root, so they never appear in `git status`, never participate in a merge, and never collide with upstream changes. Git's only job on `merge upstream/main` is to update framework paths — the code under `src/`, the markdown routines, the scaffolds under `templates/`, the top-level docs. Your actual `STRATEGY.md`, memory entries, state snapshots, and database are untouched.

### If you forked and edited framework files

If you've customized `CLAUDE.md` or added a new routine, `git merge upstream/main` may report real conflicts in those framework files. Resolve them the usual git way. Your user data is still safe — it's not in the merge.

### If `finance init` reports a "Skipped" count

That's the non-destructive guarantee working. `init` won't touch a file that already exists on your disk. If upstream shipped a newer version of a template and you want to see what changed, diff the file against `templates/<same path>`:

```bash
diff STRATEGY.md templates/STRATEGY.md
```

Cherry-pick any structural changes you want; leave your content in place.

## What counts as a "breaking" upgrade

The advisor's contract aims to be stable across minor and patch releases:

- **Patch (`1.0.x`)** — bug fixes only. `git pull` → `finance init` is always safe.
- **Minor (`1.x.0`)** — new features, new templates, additive CLI commands, new routines. Your existing data continues to work; hydrated templates fill in new files.
- **Major (`x.0.0`)** — may introduce database migrations that touch existing rows, renamed templates, or removed routines. `finance init` still runs the migrations; the CHANGELOG will call out any manual steps required.

## Backing up before an upgrade

The framework already takes a timestamped DB snapshot at every write. Before a major upgrade, take one manually for peace of mind:

```bash
finance backup
```

This writes `data/backups/finance-YYYY-MM-DDTHHMMSS.sqlite`, which you can restore with `finance rollback` if needed.

## Rolling back a bad upgrade

```bash
# Check what you pulled
git log --oneline upstream/main ^HEAD

# Undo the merge; your working tree is still clean
git reset --hard ORIG_HEAD

# Restore a DB snapshot if a migration ran
finance rollback --snapshot data/backups/finance-<timestamp>.sqlite
```

Framework state is fully reversible via git; database state is reversible via the snapshots `finance` writes automatically.

## If something doesn't fit

This is all by convention, not by force. If you want a different layout — say, your user data in a sibling directory with the framework as a pip-installed package — you can do that; `finance` resolves the finance directory via `find_finance_dir` (walks up looking for `CLAUDE.md`) and honors `FINANCE_DB` for the database path. Open an issue if you'd like a first-class separate-directory mode baked in.

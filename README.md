# FlakeIQ

Flake tracking + LLM-based failure classification for mobilewright E2E tests.

## How It Works

```
mobilewright_repo/                     FlakeIQ/
================                       ========

npx mobilewright test
  │
  ▼  (FlakeReporter captures last 10 pw:api steps)
flake-results.jsonl  ───────────────►  classify.py ──► Ollama llama3.2 (on failures)
                                            │
                                            ▼
                                        flake.db  ◄── seed.py (synthetic data)
                                            │
                                            ▼
                                    dashboard.py ──► browser (Chart.js)
```

## Step-by-Step

### 1. Run Tests

In `mobilewright_repo/`, config already has `reporter: [['html'], ['../FlakeIQ/flake-reporter.js']]`:

```bash
cd /path/to/mobilewright_repo
npx mobilewright test --project ios
```

Output: `flake-results.jsonl` (one JSON line per test, with last 10 actions + screen name + platform + session ID)

### 2. Classify Failures

```bash
cd /path/to/mobilewright_repo
python3 ../FlakeIQ/classify.py flake-results.jsonl
```

For each **failed** test → sends `error_message` + `last_actions` to Ollama at `localhost:11434` → returns category (`REAL_BUG` / `TIMEOUT_FLAKE` / `DEVICE_FLAKE` / `LOCATOR_FLAKE` / `UNKNOWN`) + reason → upserts SQLite.

**Passed** tests stored as-is, no Ollama call.

Output: `flake.db`

### 3. View Dashboard

```bash
# Real data (from flake.db in current directory)
python3 ../FlakeIQ/dashboard.py --open

# Custom database path
python3 ../FlakeIQ/dashboard.py --db /path/to/flake.db --open

# Seed demo (5100 synthetic records)
cd /path/to/FlakeIQ
python3 dashboard.py --seed --open
```

Opens browser at http://127.0.0.1:8080 with:

- **Stats cards** — total runs, flake rate, real bug count, avg duration
- **Flake rate 7d moving average** — line chart
- **Failure breakdown** — doughnut chart by classification category
- **Flake rate by action type** — bar chart (fill/tap/swipe/scrollIntoView)
- **Platform comparison** — pass/fail stacked bar per platform
- **Daily test volume** — stacked bar (pass/fail per day)
- **Failure duration distribution** — histogram (0-5s through 120s+)
- **Classification trend over time** — stacked area chart
- **Flake heatmap** — screen × day grid with color-coded flake rate
- **Top flaky tests** — ranked table with fail rate bar
- **Device health** — per-device pass/fail table
- **Latest session** — per-test pass/fail badges with durations
- **Sessions** — all test sessions with pass rate, platform, time range

### One-Shot Pipeline

```bash
cd /path/to/mobilewright_repo
../FlakeIQ/run.sh flake-results.jsonl
```

Runs classify then dashboard with `--open`.

## Seed Data

For demo without real test runs:

```bash
cd /path/to/FlakeIQ
python3 seed.py
# Creates flake-seed.db with 5100 records (30 days, 91.5% pass rate, 4 devices, 11 screens)

python3 dashboard.py --seed --open
```

## Dashboard Options

| Flag | Description |
|---|---|
| `--db PATH` | SQLite database path (default: `flake.db`) |
| `--port NUM` | HTTP port (default: `8080`) |
| `--host ADDR` | Bind address (default: `127.0.0.1`) |
| `--seed` | Use `flake-seed.db` instead of real data |
| `--open` | Auto-launch browser on start |

## Requirements

- **Node 18+** — for `flake-reporter.js` (Playwright reporter)
- **Python 3.13+** — stdlib only, no pip packages needed
- **Ollama** (optional) — only needed for LLM failure classification:
  ```bash
  brew install ollama
  ollama pull llama3.2
  ollama serve
  ```
  If Ollama is not running, `classify.py` skips LLM calls and stores failures as unclassified.

## API Endpoints

All endpoints return JSON. Used by the dashboard's Chart.js frontend.

| Endpoint | Description |
|---|---|
| `/api/stats` | Total runs, failures, flake rate, avg duration, date range |
| `/api/sessions` | All test sessions with pass/fail counts, avg duration, time range |
| `/api/latest-session` | Latest session + per-test results |
| `/api/flake-rate` | Daily flake rate trend (last 60 days) |
| `/api/breakdown` | Classification category counts for failed tests |
| `/api/by-action` | Flake rate grouped by last action type |
| `/api/by-platform` | Pass/fail counts per platform |
| `/api/volume` | Daily pass/fail test volume |
| `/api/duration-dist` | Failure duration bucketed histogram |
| `/api/classification-trend` | Classification counts per day over time |
| `/api/heatmap` | Screen × day flake rate grid |
| `/api/top-flakes` | Flakiest tests ranked by fail rate |
| `/api/devices` | Device-level pass/fail stats |

## Files

| File | Purpose |
|---|---|
| `flake-reporter.js` | Playwright reporter — captures last 10 `pw:api` steps, writes JSONL |
| `classify.py` | Reads JSONL, calls Ollama, upserts SQLite |
| `dashboard.py` | HTTP server with Chart.js dashboard |
| `seed.py` | Generates 5100 synthetic records for demo |
| `run.sh` | One-shot pipeline: classify + dashboard |
| `flake.db` | SQLite database (real test results) |
| `flake-seed.db` | SQLite database (synthetic demo data) |

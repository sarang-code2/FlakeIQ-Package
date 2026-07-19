# FlakeIQ

Test flake tracking + LLM failure classification for Playwright/mobilewright E2E tests.

## Prerequisites

| Requirement | Required For | Install |
|---|---|---|
| **Node.js 18+** | Reporter, CLI | [nodejs.org](https://nodejs.org/) |
| **Python 3.11+** | Dashboard, Classifier | [python.org](https://www.python.org/downloads/) |
| **Ollama** | AI failure classification | See below |

### Install Python

```bash
# Check if installed
python --version

# If not installed, download from:
# https://www.python.org/downloads/
```

**Windows users:** Check "Add Python to PATH" during installation.

### Install Ollama

Ollama runs a local LLM to classify test failures as real bugs vs flakes.

**macOS / Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
```bash
# Download from https://ollama.com/download
# Or use winget:
winget install Ollama.Ollama
```

**After install, pull the model and start the server:**
```bash
ollama pull llama3.2
ollama serve
```

**Verify it's running:**
```bash
curl http://localhost:11434/api/tags
```

> **Note:** If Ollama is not running, FlakeIQ still works but failures are stored as "unclassified". Install Ollama to get AI-powered classification.

## Quick Start

```bash
npm install flakeiq --save-dev
```

Add to your `playwright.config.ts`:
```js
reporter: [['html'], ['flakeiq/reporter']]
```

Run your tests:
```bash
npx playwright test
```

View dashboard:
```bash
npx flakeiq serve
```

## Daily Workflow

### Developer (Every PR)

```bash
# 1. Run your Playwright tests (reporter auto-captures results)
npx playwright test

# 2. Import results into FlakeIQ database
npx flakeiq classify flake-results.jsonl

# 3. View dashboard to see flake analysis
npx flakeiq serve
```

### CI Pipeline (GitHub Actions)

```yaml
# .github/workflows/test.yml
name: E2E Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - run: npm ci
      - run: npx playwright install --with-deps chromium
      - run: npx playwright test
      # Import results into FlakeIQ
      - run: npx flakeiq classify flake-results.jsonl
      # Upload results as artifact
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: flakeiq-results
          path: |
            flake-results.jsonl
            flakeiq-data/flake.db
```

### Weekly Team Review

```bash
# View accumulated flake data over time
npx flakeiq serve

# Check flake rate trends
# Check top flaky tests
# Check device health
# Make decisions on what to fix vs ignore
```

## How It Works

```
your-repo/                            FlakeIQ
==========                            =======

npx playwright test
  |
  v  (FlakeReporter captures last 10 pw:api steps)
flake-results.jsonl  ---------------> classify.py --> Ollama llama3.2 (on failures)
                                           |
                                           v
                                       flake.db
                                           |
                                           v
                                   dashboard.py --> browser (Chart.js)
```

## Commands

| Command | Requires | Description |
|---|---|---|
| `npx flakeiq serve` | Python | Start the dashboard server |
| `npx flakeiq serve --port 3000` | Python | Start on a custom port |
| `npx flakeiq serve --seed` | Python | Dashboard with demo data |
| `npx flakeiq serve --open` | Python | Auto-open browser |
| `npx flakeiq classify results.jsonl` | Python + Ollama | Classify failures from JSONL |
| `npx flakeiq seed` | Python | Generate synthetic seed data |
| `npx flakeiq status` | — | Show environment status |
| `npx flakeiq reporter` | — | Show reporter setup instructions |

## Dashboard Options

| Flag | Description |
|---|---|
| `--db PATH` | SQLite database path (default: `flakeiq-data/flake.db`) |
| `--port NUM` | HTTP port (default: `8080`) |
| `--host ADDR` | Bind address (default: `127.0.0.1`) |
| `--seed` | Generate and use demo data |
| `--open` | Auto-launch browser on start |

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
| `/api/heatmap` | Screen x day flake rate grid |
| `/api/top-flakes` | Flakiest tests ranked by fail rate |
| `/api/devices` | Device-level pass/fail stats |

## Seed Data

For demo without real test runs:

```bash
npx flakeiq seed
npx flakeiq serve --seed
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `FLAKE_DB` | `./flakeiq-data/flake.db` | SQLite database path |
| `FLAKE_PORT` | `8080` | Dashboard port |
| `FLAKE_HOST` | `127.0.0.1` | Dashboard bind address |
| `OLLAMA_URL` | `http://localhost:11434/api/generate` | Ollama API URL |
| `OLLAMA_MODEL` | `llama3.2` | Ollama model name |
| `FLAKE_DATA_DIR` | `./flakeiq-data` | Data directory |

## Files

| File | Purpose |
|---|---|
| `reporter/flake-reporter.js` | Playwright reporter — captures last 10 `pw:api` steps, writes JSONL |
| `python/classify.py` | Reads JSONL, calls Ollama, upserts SQLite |
| `python/dashboard.py` | HTTP server with Chart.js dashboard |
| `python/seed.py` | Generates 5100 synthetic records for demo |
| `python/web/static/` | Dashboard HTML/CSS/JS assets |

## License

MIT

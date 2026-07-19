# FlakeIQ

Test flake tracking + LLM failure classification for Playwright/mobilewright E2E tests.

## Prerequisites

| Requirement | Required For | Install |
|---|---|---|
| **Node.js 18+** | Reporter, CLI | [nodejs.org](https://nodejs.org/) |
| **Python 3.11+** | Dashboard, Classifier | [python.org](https://www.python.org/downloads/) |
| **Ollama** (optional) | AI failure classification | [ollama.com](https://ollama.com/) |

> **Note:** The flake-reporter works without Python. Python is only needed for the dashboard and failure classifier.

### Check if you have Python installed

```bash
python --version
# or
python3 --version
```

If you see `Python 3.11.x` or higher, you're good. If not, install from [python.org](https://www.python.org/downloads/).

**Windows users:** Make sure to check "Add Python to PATH" during installation.

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

## How It Works

```
mobilewright_repo/                     FlakeIQ (npm package)
================                        =====================

npx mobilewright test
  |
  v  (FlakeReporter captures last 10 pw:api steps)
flake-results.jsonl  -----------------> classify.py --> Ollama llama3.2 (on failures)
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
| `--db PATH` | SQLite database path (default: `flake.db`) |
| `--port NUM` | HTTP port (default: `8080`) |
| `--host ADDR` | Bind address (default: `127.0.0.1`) |
| `--seed` | Use `flake-seed.db` instead of real data |
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

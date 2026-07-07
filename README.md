# FlakeIQ

Flake tracking + LLM-based failure classification for mobilewright/Playwright tests.

## Usage

```bash
# 1. Run tests with the flake reporter
cd /path/to/mobilewright_repo
npx playwright test --reporter=./path/to/FlakeIQ/flake-reporter.ts,html

# 2. Classify failures and store in SQLite
python3 /path/to/FlakeIQ/classify.py flake-results.jsonl

# 3. Launch dashboard
python3 /path/to/FlakeIQ/dashboard.py --port 8080
# Open http://127.0.0.1:8080

# Or run both at once:
./FlakeIQ/run.sh flake-results.jsonl
```

## Pipeline

```
mobilewright test run
  ↓ (flake-reporter.ts)
flake-results.jsonl  ← one JSON line per test
  ↓ (classify.py)
flake.db  ← SQLite (Ollama classifies failures)
  ↓ (dashboard.py)
HTTP server at :8080  ← Chart.js dashboard
```

## Requirements

- Python 3.13+ (stdlib only — no pip packages needed)
- Ollama (optional, for failure classification):
  ```bash
  brew install ollama
  ollama pull llama3.2
  ```

# FlakeIQ

Test flake tracking + LLM failure classification for E2E tests. Works with **Playwright**, **Detox**, **Appium**, **Selenium**, and any framework that can output test results as JSON.

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

**Playwright** has a built-in reporter — zero config required. **All other frameworks** (Detox, Appium, Selenium, etc.) need a small custom reporter to output test results as JSONL. Once you have the JSONL file, `npx flakeiq classify` and `npx flakeiq serve` work identically regardless of framework.

### Playwright (Built-in Reporter)

```bash
npm install flakeiq --save-dev
```

Add to your `playwright.config.ts`:
```js
reporter: [
    ['html'],
    ['flakeiq/reporter', { outputFile: 'flake-results.jsonl' }],
  ],
```

Run your tests:
```bash
npx playwright test
```

View dashboard:
```bash
npx flakeiq serve
```

### Detox (React Native)

Output test results as JSONL in this format:

```json
{
  "test_file": "src/__tests__/login.test.js",
  "test_name": "login with valid credentials",
  "platform": "ios",
  "device_id": "iPhone 15",
  "duration_ms": 4500,
  "result": "passed",
  "error_message": "",
  "last_actions": ["tap login button", "enter email", "enter password", "tap submit"],
  "classification": null,
  "classification_reason": null,
  "screen_name": "login",
  "session_id": "detox_run_123",
  "run_at": "2026-01-15T10:30:00Z"
}
```

**Detox reporter example:**

```javascript
// detox.config.js
module.exports = {
  // ... your config
  reporters: [
    ['jest-html-reporter', { outputPath: 'test-results.html' }],
    // Custom JSONL reporter
    ['custom', {
      onComplete: (results) => {
        const fs = require('fs');
        const lines = results.testResults.map(test => ({
          test_file: test.testFilePath,
          test_name: test.testTitle,
          platform: process.platform,
          device_id: process.env.DEVICE_ID || 'unknown',
          duration_ms: test.duration,
          result: test.status,
          error_message: test.failureMessages.join('\n'),
          last_actions: [],
          classification: null,
          classification_reason: null,
          screen_name: test.testFilePath.split('/').pop().replace('.test.js', ''),
          session_id: `detox_${Date.now()}`,
          run_at: new Date().toISOString()
        }));
        fs.writeFileSync('flake-results.jsonl', lines.map(l => JSON.stringify(l)).join('\n'));
      }
    }]
  ]
};
```

### Appium

Output test results as JSONL:

```json
{
  "test_file": "tests/android/login.js",
  "test_name": "Android login flow",
  "platform": "android",
  "device_id": "emulator-5554",
  "duration_ms": 8200,
  "result": "timedOut",
  "error_message": "An unknown server-side error occurred while processing the command",
  "last_actions": ["findElement", "click", "sendKeys", "waitForElement"],
  "classification": null,
  "classification_reason": null,
  "screen_name": "login",
  "session_id": "appium_session_abc123",
  "run_at": "2026-01-15T11:00:00Z"
}
```

**Appium integration example:**

```javascript
// wdio.conf.js
exports.config = {
  // ... your config
  onComplete: function(results) {
    const fs = require('fs');
    const lines = results.tests.map(test => ({
      test_file: test.file,
      test_name: test.title,
      platform: this.capabilities.platformName,
      device_id: this.capabilities.deviceName,
      duration_ms: test.duration,
      result: test.passed ? 'passed' : 'failed',
      error_message: test.error || '',
      last_actions: test.commands || [],
      classification: null,
      classification_reason: null,
      screen_name: test.file.split('/').pop().replace('.js', ''),
      session_id: `appium_${Date.now()}`,
      run_at: new Date().toISOString()
    }));
    fs.writeFileSync('flake-results.jsonl', lines.map(l => JSON.stringify(l)).join('\n'));
  }
};
```

### Selenium

Output test results as JSONL:

```json
{
  "test_file": "tests/selenium/login_test.py",
  "test_name": "Selenium login test",
  "platform": "chrome",
  "device_id": "Chrome 120",
  "duration_ms": 3400,
  "result": "passed",
  "error_message": "",
  "last_actions": ["find_element", "send_keys", "click", "assert"],
  "classification": null,
  "classification_reason": null,
  "screen_name": "login",
  "session_id": "selenium_run_456",
  "run_at": "2026-01-15T12:00:00Z"
}
```

**Python Selenium integration:**

```python
# conftest.py (pytest)
import json
import os
from datetime import datetime

def pytest_runtest_makereport(item, call):
    if call.when == 'call':
        result = {
            'test_file': str(item.fspath),
            'test_name': item.name,
            'platform': 'selenium',
            'device_id': os.environ.get('BROWSER', 'chrome'),
            'duration_ms': int(call.duration * 1000),
            'result': 'passed' if call.excinfo is None else 'failed',
            'error_message': str(call.excinfo.value) if call.excinfo else '',
            'last_actions': [],
            'classification': None,
            'classification_reason': None,
            'screen_name': item.name,
            'session_id': f'selenium_{int(datetime.now().timestamp())}',
            'run_at': datetime.now().isoformat() + 'Z'
        }
        
        with open('flake-results.jsonl', 'a') as f:
            f.write(json.dumps(result) + '\n')
```

### Any Framework

For any testing framework, output results as JSONL with this schema:

```json
{
  "test_file": "string",
  "test_name": "string",
  "platform": "string",
  "device_id": "string",
  "duration_ms": 0,
  "result": "passed|failed|timedOut|skipped",
  "error_message": "string",
  "last_actions": ["string"],
  "classification": null,
  "classification_reason": null,
  "screen_name": "string",
  "session_id": "string",
  "run_at": "ISO8601"
}
```

Then run:
```bash
npx flakeiq classify flake-results.jsonl
npx flakeiq serve
```

## Every Test Run (QA / CI / Local)

### Local / QA

```bash
# 1. Run your Playwright tests (reporter auto-captures results)
npx playwright test

# 2. Import results into FlakeIQ database
npx flakeiq classify flake-results.jsonl

# 3. View dashboard to see flake analysis
npx flakeiq serve
```

### CI (GitHub Actions)

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

Your tests (Playwright/Detox/Appium/Selenium/any framework)
  |
  v  (Reporter captures test results)
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
| `reporter/index.js` | Re-export for `flakeiq/reporter` import |
| `python/classify.py` | Reads JSONL, calls Ollama, upserts SQLite |
| `python/dashboard.py` | HTTP server with Chart.js dashboard |
| `python/seed.py` | Generates 5100 synthetic records for demo |
| `python/web/static/` | Dashboard HTML/CSS/JS assets |
| `lib/*.js` | CLI commands (serve, classify, seed, status, reporter, setup) |
| `bin/flakeiq.js` | CLI entry point |

## License

MIT

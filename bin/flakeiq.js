#!/usr/bin/env node

const { getConfig, isVenvReady } = require('../lib/config');
const { setup } = require('../lib/setup');
const { serve } = require('../lib/serve');
const { classify } = require('../lib/classify');
const { seed } = require('../lib/seed');
const { getPythonVersion } = require('../lib/utils');
const path = require('path');

const VERSION = require('../package.json').version;

const HELP = `
  FlakeIQ v${VERSION} — Test flake tracking + LLM failure classification

  Usage:
    npx flakeiq <command> [options]

  Commands:
    serve       Start the dashboard server
    classify    Classify test failures from a JSONL file
    seed        Generate synthetic seed data
    setup       (Re)run Python environment setup
    status      Show FlakeIQ status and configuration
    reporter    Show reporter setup instructions
    help        Show this help message

  Examples:
    npx flakeiq serve                    Start dashboard at localhost:8080
    npx flakeiq serve --port 3000        Start on port 3000
    npx flakeiq serve --seed             Dashboard with demo data
    npx flakeiq serve --open             Auto-open browser
    npx flakeiq classify results.jsonl   Classify failures from JSONL
    npx flakeiq seed                     Create seed database
    npx flakeiq status                   Check environment
`;

function parseArgs(args) {
  const parsed = { _: [] };
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg.startsWith('--')) {
      const key = arg.slice(2);
      const next = args[i + 1];
      if (next && !next.startsWith('--')) {
        parsed[key] = next;
        i++;
      } else {
        parsed[key] = true;
      }
    } else {
      parsed._.push(arg);
    }
  }
  return parsed;
}

function ensurePython() {
  if (!isVenvReady()) {
    console.log('Python environment not set up. Running setup...');
    setup();
    if (!isVenvReady()) {
      console.error('\nCannot continue without Python. Install Python 3.11+ and retry.');
      process.exit(1);
    }
  }
}

function showStatus() {
  const config = getConfig();
  const pythonVer = getPythonVersion(config.venvPython);
  const sysPython = getPythonVersion('python3') || getPythonVersion('python');

  console.log('');
  console.log(`  FlakeIQ v${VERSION}`);
  console.log('  ─────────────────────────────────');
  console.log(`  Node.js:     ${process.version}`);
  console.log(`  Python (system): ${sysPython ? sysPython.raw : 'NOT FOUND'}`);
  console.log(`  Python (venv):   ${pythonVer ? pythonVer.raw : 'NOT SET UP'}`);
  console.log(`  Venv ready:  ${isVenvReady() ? 'Yes' : 'No'}`);
  console.log(`  Database:    ${config.dbPath}`);
  console.log(`  Data dir:    ${config.dataDir}`);
  console.log(`  Ollama URL:  ${config.ollamaUrl}`);
  console.log(`  Ollama model: ${config.ollamaModel}`);
  console.log(`  Default port: ${config.port}`);
  console.log(`  Reporter:    ${config.reporterPath}`);
  console.log('');
}

function showReporterSetup() {
  console.log('');
  console.log('  Reporter Setup');
  console.log('  ─────────────────────────────────');
  console.log('');
  console.log('  1. Add to your playwright.config.ts:');
  console.log('');
  console.log('     export default {');
  console.log("       reporter: [['html'], ['flakeiq/reporter']],");
  console.log('       // ...');
  console.log('     }');
  console.log('');
  console.log('  2. Run your tests:');
  console.log('     npx playwright test');
  console.log('');
  console.log('  3. View results:');
  console.log('     npx flakeiq serve');
  console.log('');
  console.log('  Output: flake-results.jsonl (auto-generated)');
  console.log('');
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const command = args._[0] || 'help';

  switch (command) {
    case 'serve':
      ensurePython();
      await serve({
        port: args.port ? parseInt(args.port) : undefined,
        host: args.host,
        seed: args.seed || false,
        open: args.open !== undefined ? args.open : true,
        db: args.db,
      });
      break;

    case 'classify':
      ensurePython();
      classify(args._[1], {
        db: args.db,
        ollamaUrl: args['ollama-url'],
        model: args.model,
      });
      break;

    case 'seed':
      ensurePython();
      seed(args._[1]);
      break;

    case 'setup':
      setup();
      break;

    case 'status':
      showStatus();
      break;

    case 'reporter':
    case 'init':
      showReporterSetup();
      break;

    case 'help':
    case '--help':
    case '-h':
      console.log(HELP);
      break;

    case '--version':
    case '-v':
      console.log(`flakeiq v${VERSION}`);
      break;

    default:
      console.error(`  Unknown command: ${command}`);
      console.log('  Run "npx flakeiq help" for usage.');
      process.exit(1);
  }
}

main();

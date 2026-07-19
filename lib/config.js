const path = require('path');
const fs = require('fs');

const PACKAGE_DIR = path.resolve(__dirname, '..');
const PYTHON_DIR = path.join(PACKAGE_DIR, 'python');
const REPORTER_PATH = path.join(PACKAGE_DIR, 'reporter', 'flake-reporter.js');

function getVenvDir() {
  return path.join(PACKAGE_DIR, '.flakeiq');
}

function getVenvPython() {
  const venvDir = getVenvDir();
  if (process.platform === 'win32') {
    return path.join(venvDir, 'Scripts', 'python.exe');
  }
  return path.join(venvDir, 'bin', 'python3');
}

function getDataDir() {
  const dir = process.env.FLAKE_DATA_DIR || path.join(process.cwd(), 'flakeiq-data');
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  return dir;
}

function getDbPath() {
  if (process.env.FLAKE_DB) return process.env.FLAKE_DB;
  return path.join(getDataDir(), 'flake.db');
}

function getConfig() {
  return {
    packageDir: PACKAGE_DIR,
    pythonDir: PYTHON_DIR,
    reporterPath: REPORTER_PATH,
    venvDir: getVenvDir(),
    venvPython: getVenvPython(),
    dataDir: getDataDir(),
    dbPath: getDbPath(),
    port: parseInt(process.env.FLAKE_PORT || '8080', 10),
    host: process.env.FLAKE_HOST || '127.0.0.1',
    ollamaUrl: process.env.OLLAMA_URL || 'http://localhost:11434/api/generate',
    ollamaModel: process.env.OLLAMA_MODEL || 'llama3.2',
  };
}

function isVenvReady() {
  return fs.existsSync(getVenvPython());
}

module.exports = { getVenvDir, getVenvPython, getDataDir, getDbPath, getConfig, isVenvReady, PACKAGE_DIR, PYTHON_DIR, REPORTER_PATH };

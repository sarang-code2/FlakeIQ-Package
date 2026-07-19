const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const { getVenvDir, getVenvPython, PYTHON_DIR } = require('./config');
const { getPythonVersion } = require('./utils');

const REQUIREMENTS = path.join(PYTHON_DIR, 'requirements.txt');

function findSystemPython() {
  const candidates = process.platform === 'win32'
    ? ['python', 'python3', 'py -3']
    : ['python3', 'python'];

  for (const cmd of candidates) {
    const ver = getPythonVersion(cmd);
    if (ver && (ver.major > 3 || (ver.major === 3 && ver.minor >= 11))) {
      return cmd;
    }
  }
  return null;
}

function createVenv(pythonCmd) {
  const venvDir = getVenvDir();
  if (fs.existsSync(getVenvPython())) return true;

  console.log('  Creating Python virtual environment...');
  try {
    execSync(`"${pythonCmd}" -m venv "${venvDir}"`, { stdio: 'pipe', timeout: 60000 });
    return true;
  } catch (e) {
    console.error('  Failed to create venv:', e.message);
    return false;
  }
}

function installDeps() {
  const pip = process.platform === 'win32'
    ? path.join(getVenvDir(), 'Scripts', 'pip.exe')
    : path.join(getVenvDir(), 'bin', 'pip3');

  if (!fs.existsSync(pip)) {
    console.error('  pip not found in venv');
    return false;
  }

  console.log('  Installing Python dependencies...');
  try {
    execSync(`"${pip}" install -r "${REQUIREMENTS}" --quiet`, { stdio: 'pipe', timeout: 120000 });
    return true;
  } catch (e) {
    console.error('  Failed to install deps:', e.message);
    return false;
  }
}

function setup() {
  const python = findSystemPython();
  if (!python) {
    console.log('');
    console.log('  WARNING: Python 3.11+ not found on your system.');
    console.log('  FlakeIQ dashboard requires Python. Install it from:');
    console.log('    https://www.python.org/downloads/');
    console.log('');
    console.log('  The flake-reporter will still work without Python.');
    console.log('');
    return false;
  }

  console.log(`  Found Python: ${python}`);

  if (!createVenv(python)) return false;
  if (!installDeps()) return false;

  console.log('  Python environment ready.');
  return true;
}

module.exports = { setup, findSystemPython };

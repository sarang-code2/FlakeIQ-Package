const { spawn } = require('child_process');
const path = require('path');
const { getConfig } = require('./config');

function seed(dbPath, options = {}) {
  const config = getConfig();
  const python = config.venvPython;
  const seedScript = path.join(config.pythonDir, 'seed.py');

  const args = [seedScript];
  if (dbPath) args.push(dbPath);

  const child = spawn(python, args, {
    stdio: 'inherit',
    env: { ...process.env, FLAKE_DB: dbPath || config.dbPath },
  });

  child.on('error', (err) => {
    if (err.code === 'ENOENT') {
      console.error('Python not found. Run "npx flakeiq setup" or install Python 3.11+.');
    } else {
      console.error('Seed error:', err.message);
    }
    process.exit(1);
  });

  child.on('exit', (code) => { process.exit(code || 0); });
}

module.exports = { seed };

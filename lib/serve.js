const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const { getConfig } = require('./config');
const { findAvailablePort } = require('./utils');

async function serve(options = {}) {
  const config = getConfig();
  const python = config.venvPython;
  const dashboardScript = path.join(config.pythonDir, 'dashboard.py');
  const seedScript = path.join(config.pythonDir, 'seed.py');

  const port = options.port || config.port;
  const host = options.host || config.host;
  const actualPort = await findAvailablePort(port, host);
  const useSeed = options.seed || false;
  const dbPath = options.db || config.dbPath;

  if (useSeed && !fs.existsSync(dbPath)) {
    console.log('Seed database not found. Generating...');
    await new Promise((resolve, reject) => {
      const seedChild = spawn(python, [seedScript, dbPath], {
        stdio: 'inherit',
        env: { ...process.env, FLAKE_DB: dbPath },
      });
      seedChild.on('exit', (code) => code === 0 ? resolve() : reject(new Error('Seed failed')));
      seedChild.on('error', reject);
    });
  }

  const args = [dashboardScript, '--port', String(actualPort), '--host', host, '--db', dbPath];
  if (options.open !== false) args.push('--open');

  console.log(`Starting FlakeIQ dashboard on http://${host}:${actualPort}`);
  if (useSeed) console.log('Using seed database...');

  const child = spawn(python, args, {
    stdio: 'inherit',
    env: { ...process.env, FLAKE_DB: dbPath },
  });

  child.on('error', (err) => {
    if (err.code === 'ENOENT') {
      console.error('Python not found. Run "npx flakeiq setup" or install Python 3.11+.');
    } else {
      console.error('Dashboard error:', err.message);
    }
    process.exit(1);
  });

  child.on('exit', (code) => {
    process.exit(code || 0);
  });

  process.on('SIGINT', () => { child.kill('SIGINT'); });
  process.on('SIGTERM', () => { child.kill('SIGTERM'); });
}

module.exports = { serve };

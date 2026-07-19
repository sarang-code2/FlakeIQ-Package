const { spawn } = require('child_process');
const path = require('path');
const { getConfig } = require('./config');

function classify(jsonlPath, options = {}) {
  const config = getConfig();
  const python = config.venvPython;
  const classifyScript = path.join(config.pythonDir, 'classify.py');

  const args = [classifyScript];
  if (jsonlPath) args.push(jsonlPath);
  if (options.db) args.push('--db', options.db);
  if (options.ollamaUrl) args.push('--ollama-url', options.ollamaUrl);
  if (options.model) args.push('--model', options.model);

  const child = spawn(python, args, {
    stdio: 'inherit',
    env: {
      ...process.env,
      FLAKE_DB: options.db || config.dbPath,
      OLLAMA_URL: options.ollamaUrl || config.ollamaUrl,
      OLLAMA_MODEL: options.model || config.ollamaModel,
    },
  });

  child.on('error', (err) => {
    if (err.code === 'ENOENT') {
      console.error('Python not found. Run "npx flakeiq setup" or install Python 3.11+.');
    } else {
      console.error('Classify error:', err.message);
    }
    process.exit(1);
  });

  child.on('exit', (code) => { process.exit(code || 0); });
}

module.exports = { classify };

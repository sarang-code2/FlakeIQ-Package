const net = require('net');
const { execSync } = require('child_process');

function isPortAvailable(port, host = '127.0.0.1') {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once('error', () => resolve(false));
    server.once('listening', () => { server.close(() => resolve(true)); });
    server.listen(port, host);
  });
}

function findAvailablePort(startPort, host = '127.0.0.1') {
  return new Promise(async (resolve) => {
    for (let port = startPort; port < startPort + 100; port++) {
      if (await isPortAvailable(port, host)) { resolve(port); return; }
    }
    resolve(startPort);
  });
}

function openBrowser(url) {
  const cmd = process.platform === 'win32'
    ? `start "" "${url}"`
    : process.platform === 'darwin'
      ? `open "${url}"`
      : `xdg-open "${url}"`;
  try { execSync(cmd, { stdio: 'ignore' }); } catch {}
}

function getPythonVersion(pythonPath) {
  try {
    const out = execSync(`"${pythonPath}" --version`, { encoding: 'utf8', timeout: 5000 }).trim();
    const match = out.match(/Python (\d+)\.(\d+)/);
    if (match) return { major: parseInt(match[1]), minor: parseInt(match[2]), raw: out };
  } catch {}
  return null;
}

module.exports = { isPortAvailable, findAvailablePort, openBrowser, getPythonVersion };

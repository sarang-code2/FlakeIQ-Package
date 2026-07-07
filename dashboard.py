#!/usr/bin/env python3
import json
import sqlite3
import os
import argparse
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

DB_PATH = os.environ.get("FLAKE_DB", "flake.db")
PORT = int(os.environ.get("FLAKE_PORT", "8080"))


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FlakeIQ Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px; }
h1 { color: #58a6ff; margin-bottom: 8px; }
.subtitle { color: #8b949e; margin-bottom: 24px; }
.dashboard { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; max-width: 1400px; margin: 0 auto; }
.card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; }
.card.full { grid-column: 1 / -1; }
.card h2 { font-size: 16px; color: #58a6ff; margin-bottom: 16px; }
canvas { max-height: 300px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; padding: 8px 12px; border-bottom: 2px solid #30363d; color: #8b949e; font-weight: 600; }
td { padding: 8px 12px; border-bottom: 1px solid #21262d; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }
.badge-pass { background: #1b3a2d; color: #3fb950; }
.badge-fail { background: #3d1f1f; color: #f85149; }
.badge-REAL_BUG { background: #3d1f1f; color: #f85149; }
.badge-TIMEOUT_FLAKE { background: #3d2e1a; color: #d29922; }
.badge-DEVICE_FLAKE { background: #1f2d3d; color: #58a6ff; }
.badge-LOCATOR_FLAKE { background: #2d1f3d; color: #bc8cff; }
.badge-UNKNOWN { background: #21262d; color: #8b949e; }
.flake-bar { height: 8px; border-radius: 4px; background: #21262d; overflow: hidden; min-width: 60px; }
.flake-bar-fill { height: 100%; border-radius: 4px; transition: width 0.3s; }
.metric { display: inline-flex; align-items: center; gap: 8px; margin-right: 24px; }
.metric-value { font-size: 28px; font-weight: 700; }
.metric-label { color: #8b949e; font-size: 12px; }
.stats-row { display: flex; flex-wrap: wrap; gap: 16px; margin-bottom: 20px; }
@media (max-width: 800px) { .dashboard { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<h1>FlakeIQ</h1>
<p class="subtitle">Test flake tracker &mdash; <span id="recordCount">0</span> records</p>
<div class="stats-row" id="statsRow"></div>
<div class="dashboard">
  <div class="card"><h2>Flake Rate (7d MA)</h2><canvas id="trendChart"></canvas></div>
  <div class="card"><h2>Flake Breakdown by Classification</h2><canvas id="pieChart"></canvas></div>
  <div class="card full"><h2>Flake Heatmap (Screen × Day)</h2><div style="overflow-x:auto;font-size:12px" id="heatmapContainer"></div></div>
  <div class="card full"><h2>Top Flaky Tests</h2><table><thead><tr><th>Test</th><th>Platform</th><th>Screen</th><th>Flake Rate</th><th>Runs</th><th>Flake Bar</th><th>Common Classification</th></tr></thead><tbody id="flakeTableBody"></tbody></table></div>
  <div class="card full"><h2>Device Health</h2><table><thead><tr><th>Device ID</th><th>Platform</th><th>Runs</th><th>Flake Rate</th><th>Flake Bar</th><th>Common Issue</th></tr></thead><tbody id="deviceTableBody"></tbody></table></div>
</div>
<script>
async function loadData() {
  const [stats, flakeRate, breakdown, heatmap, topFlakes, devices] = await Promise.all([
    fetch('/api/stats').then(r=>r.json()),
    fetch('/api/flake-rate').then(r=>r.json()),
    fetch('/api/breakdown').then(r=>r.json()),
    fetch('/api/heatmap').then(r=>r.json()),
    fetch('/api/top-flakes').then(r=>r.json()),
    fetch('/api/devices').then(r=>r.json()),
  ]);
  document.getElementById('recordCount').textContent = stats.total_runs;
  document.getElementById('statsRow').innerHTML = `
    <div class="metric"><span class="metric-value">${stats.total_runs}</span><span class="metric-label">Total Runs</span></div>
    <div class="metric"><span class="metric-value">${stats.fail_count}</span><span class="metric-label">Failures</span></div>
    <div class="metric"><span class="metric-value">${stats.flake_rate}%</span><span class="metric-label">Flake Rate</span></div>
    <div class="metric"><span class="metric-value">${stats.classified_count}</span><span class="metric-label">Classified</span></div>
    <div class="metric"><span class="metric-value">${stats.real_bug_count}</span><span class="metric-label">Real Bugs</span></div>
  `;
  renderTrend(flakeRate);
  renderPie(breakdown);
  renderHeatmap(heatmap);
  renderTable('flakeTableBody', topFlakes, true);
  renderTable('deviceTableBody', devices, false);
}
function renderTrend(data) {
  new Chart(document.getElementById('trendChart'), {
    type: 'line', data: {
      labels: data.map(d=>d.day),
      datasets: [{
        label: 'Flake Rate %', data: data.map(d=>d.rate),
        borderColor: '#58a6ff', backgroundColor: 'rgba(88,166,255,0.1)',
        fill: true, tension: 0.3, pointRadius: 3
      }]
    }, options: {
      responsive: true, maintainAspectRatio: false,
      scales: { x: { ticks: { color: '#8b949e', maxTicksLimit: 14 } }, y: { ticks: { color: '#8b949e' }, beginAtZero: true } },
      plugins: { legend: { labels: { color: '#c9d1d9' } } }
    }
  });
}
function renderPie(data) {
  const colors = { REAL_BUG: '#f85149', TIMEOUT_FLAKE: '#d29922', DEVICE_FLAKE: '#58a6ff', LOCATOR_FLAKE: '#bc8cff', UNKNOWN: '#8b949e' };
  new Chart(document.getElementById('pieChart'), {
    type: 'doughnut', data: {
      labels: data.map(d=>d.classification),
      datasets: [{
        data: data.map(d=>d.count),
        backgroundColor: data.map(d=>colors[d.classification]||'#8b949e'),
        borderWidth: 0
      }]
    }, options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'right', labels: { color: '#c9d1d9' } } }
    }
  });
}
function renderHeatmap(data) {
  const container = document.getElementById('heatmapContainer');
  if (!data.length) { container.innerHTML = '<span style="color:#8b949e">Not enough data — need at least 3 runs per screen-day.</span>'; return; }
  const screens = [...new Set(data.map(d=>d.screen))].sort();
  const days = [...new Set(data.map(d=>d.day))].sort();
  const lookup = {};
  data.forEach(d => { lookup[d.screen+'|'+d.day] = d.rate; });
  const heatColor = v => { if (v === 0) return '#1b3a2d'; if (v < 10) return '#2d4a1a'; if (v < 25) return '#4a3a1a'; if (v < 50) return '#5a2a1a'; return '#6a1a1a'; };
  let html = '<table style="border-collapse:collapse"><tr><th style="padding:4px 8px;color:#8b949e;font-weight:600">Screen</th>';
  days.forEach(d => { html += `<th style="padding:4px 8px;color:#8b949e;font-weight:600;font-size:11px">${d.slice(5)}</th>`; });
  html += '<th style="padding:4px 8px;color:#8b949e;font-weight:600">Avg</th></tr>';
  screens.forEach(s => {
    html += `<tr><td style="padding:4px 8px;color:#c9d1d9;font-size:11px">${s}</td>`;
    let sum = 0, cnt = 0;
    days.forEach(d => {
      const v = lookup[s+'|'+d];
      if (v !== undefined) { sum += v; cnt++; }
      const bg = v !== undefined ? heatColor(v) : '#161b22';
      const txt = v !== undefined ? v.toFixed(0) + '%' : '—';
      html += `<td style="padding:4px 8px;text-align:center;background:${bg};color:${v > 25 ? '#f0f0f0' : '#c9d1d9'};border-radius:4px;font-size:12px">${txt}</td>`;
    });
    const avg = cnt > 0 ? (sum / cnt).toFixed(0) + '%' : '—';
    html += `<td style="padding:4px 8px;text-align:center;color:#8b949e;font-size:12px">${avg}</td>`;
    html += '</tr>';
  });
  html += '</table>';
  container.innerHTML = html;
}
function renderTable(tbodyId, rows, isTest) {
  const tbody = document.getElementById(tbodyId);
  if (!rows.length) { tbody.innerHTML = '<tr><td colspan="7" style="color:#8b949e;text-align:center;padding:20px">No data yet. Run tests first.</td></tr>'; return; }
  tbody.innerHTML = rows.map(r => {
    const rate = (r.fail_count / r.total * 100).toFixed(1);
    const pct = Math.min(100, Math.round(r.fail_count / r.total * 100));
    const cls = r.common_classification || 'UNKNOWN';
    const name = isTest ? r.test_name : r.device_id;
    const platform = r.platform || '';
    const subtitle = isTest ? (r.screen_name || '') : '';
    return `<tr>
      <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${name}</td>
      <td>${platform ? `<span class="badge">${platform}</span>` : ''}</td>
      <td>${subtitle ? `<span class="badge">${subtitle}</span>` : ''}</td>
      <td>${rate}%</td>
      <td>${r.total}</td>
      <td><div class="flake-bar"><div class="flake-bar-fill" style="width:${pct}%;background:${pct>50?'#f85149':pct>25?'#d29922':'#3fb950'}"></div></div></td>
      <td><span class="badge badge-${cls}">${cls}</span></td>
    </tr>`;
  }).join('');
}
loadData();
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(HTML.encode())
            return

        handlers = {
            "/api/stats": self.api_stats,
            "/api/flake-rate": self.api_flake_rate,
            "/api/breakdown": self.api_breakdown,
            "/api/heatmap": self.api_heatmap,
            "/api/top-flakes": self.api_top_flakes,
            "/api/devices": self.api_devices,
        }
        handler = handlers.get(path)
        if handler:
            handler()
        else:
            self.send_response(404)
            self.end_headers()

    def _json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _query(self, sql, params=()):
        db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        try:
            cur = db.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
        finally:
            db.close()

    def api_stats(self):
        rows = self._query("""
            SELECT
                COUNT(*) as total_runs,
                SUM(CASE WHEN result != 'passed' THEN 1 ELSE 0 END) as fail_count,
                SUM(CASE WHEN classification IS NOT NULL THEN 1 ELSE 0 END) as classified_count,
                SUM(CASE WHEN classification = 'REAL_BUG' THEN 1 ELSE 0 END) as real_bug_count
            FROM test_runs
        """)
        s = rows[0]
        s["flake_rate"] = round(s["fail_count"] / s["total_runs"] * 100, 1) if s["total_runs"] else 0
        self._json(s)

    def api_flake_rate(self):
        rows = self._query("""
            SELECT DATE(run_at) as day,
                   ROUND(SUM(CASE WHEN result != 'passed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as rate
            FROM test_runs
            GROUP BY day
            ORDER BY day
            LIMIT 30
        """)
        self._json(rows)

    def api_breakdown(self):
        rows = self._query("""
            SELECT COALESCE(classification, 'UNCLASSIFIED') as classification, COUNT(*) as count
            FROM test_runs WHERE result != 'passed'
            GROUP BY classification
            ORDER BY count DESC
        """)
        self._json(rows)

    def api_heatmap(self):
        rows = self._query("""
            SELECT DATE(run_at) as day, screen_name as screen,
                   ROUND(SUM(CASE WHEN result != 'passed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as rate
            FROM test_runs
            WHERE screen_name IS NOT NULL AND screen_name != ''
            GROUP BY day, screen
            HAVING COUNT(*) >= 3
            ORDER BY day, screen
        """)
        self._json(rows)

    def api_top_flakes(self):
        rows = self._query("""
            SELECT test_name, platform, screen_name, COUNT(*) as total,
                   SUM(CASE WHEN result != 'passed' THEN 1 ELSE 0 END) as fail_count,
                   (SELECT classification FROM test_runs t2
                    WHERE t2.test_name = t1.test_name AND t2.result != 'passed'
                    GROUP BY classification ORDER BY COUNT(*) DESC LIMIT 1
                   ) as common_classification
            FROM test_runs t1
            GROUP BY test_name, platform
            HAVING total >= 3
            ORDER BY fail_count * 1.0 / total DESC
            LIMIT 20
        """)
        self._json(rows)

    def api_devices(self):
        rows = self._query("""
            SELECT device_id, platform, COUNT(*) as total,
                   SUM(CASE WHEN result != 'passed' THEN 1 ELSE 0 END) as fail_count,
                   (SELECT classification FROM test_runs t2
                    WHERE t2.device_id = t1.device_id AND t2.result != 'passed'
                    GROUP BY classification ORDER BY COUNT(*) DESC LIMIT 1
                   ) as common_classification
            FROM test_runs t1
            GROUP BY device_id
            HAVING total >= 2
            ORDER BY fail_count * 1.0 / total DESC
        """)
        self._json(rows)

    def log_message(self, format, *args):
        pass


def main():
    global DB_PATH, PORT
    parser = argparse.ArgumentParser(description="FlakeIQ dashboard")
    parser.add_argument("--db", default=None, help="SQLite database path")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address")
    args = parser.parse_args()
    if args.db:
        DB_PATH = args.db
    if args.port:
        PORT = args.port
    os.environ["FLAKE_DB"] = DB_PATH

    if not os.path.exists(DB_PATH):
        print(f"Database not found: {DB_PATH}")
        print("Run classify.py first to create it.")
        sys.exit(1)

    server = HTTPServer((args.host, PORT), Handler)
    print(f"FlakeIQ dashboard at http://{args.host}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import json
import sqlite3
import os
import argparse
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

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
:root {
  --bg: #0d1117; --card: #161b22; --border: #30363d;
  --text: #c9d1d9; --muted: #8b949e; --accent: #58a6ff;
  --green: #3fb950; --red: #f85149; --yellow: #d29922;
  --purple: #bc8cff; --orange: #f0883e;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); padding: 24px; }
h1 { font-size: 24px; font-weight: 700; background: linear-gradient(135deg, var(--accent), var(--purple)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 4px; }
.subtitle { color: var(--muted); font-size: 14px; margin-bottom: 24px; }
.dashboard { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; max-width: 1500px; margin: 0 auto; }
.card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 20px; transition: border-color 0.2s; }
.card:hover { border-color: #484f58; }
.card.full { grid-column: 1 / -1; }
.card h2 { font-size: 13px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 16px; }
.card h3 { font-size: 14px; font-weight: 600; color: var(--text); margin-bottom: 12px; }
canvas { max-height: 260px; width: 100% !important; }
.stats-row { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 20px; grid-column: 1 / -1; }
.stat-card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px 20px; flex: 1; min-width: 140px; }
.stat-card .value { font-size: 28px; font-weight: 700; line-height: 1.2; }
.stat-card .label { font-size: 12px; color: var(--muted); margin-top: 4px; }
.stat-card .trend { font-size: 11px; margin-top: 4px; }
.stat-card.up { border-left: 3px solid var(--green); }
.stat-card.down { border-left: 3px solid var(--red); }
.stat-card.warn { border-left: 3px solid var(--yellow); }
.stat-card.info { border-left: 3px solid var(--accent); }
.stat-card.purple { border-left: 3px solid var(--purple); }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; padding: 8px 10px; border-bottom: 2px solid var(--border); color: var(--muted); font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.3px; white-space: nowrap; }
td { padding: 8px 10px; border-bottom: 1px solid #21262d; white-space: nowrap; }
tr:hover td { background: rgba(255,255,255,0.02); }
.badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.badge-pass { background: #1b3a2d; color: var(--green); }
.badge-fail { background: #3d1f1f; color: var(--red); }
.badge-REAL_BUG { background: #3d1f1f; color: var(--red); }
.badge-TIMEOUT_FLAKE { background: #3d2e1a; color: var(--yellow); }
.badge-DEVICE_FLAKE { background: #1f2d3d; color: var(--accent); }
.badge-LOCATOR_FLAKE { background: #2d1f3d; color: var(--purple); }
.badge-UNKNOWN { background: #21262d; color: var(--muted); }
.flake-bar { height: 6px; border-radius: 3px; background: #21262d; overflow: hidden; min-width: 80px; }
.flake-bar-fill { height: 100%; border-radius: 3px; transition: width 0.5s ease; }
.chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; grid-column: 1 / -1; }
.session-row { display: flex; flex-wrap: wrap; gap: 8px; }
.session-row .test-badge { padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 500; border: 1px solid var(--border); }
.detail-toggle { cursor: pointer; color: var(--accent); font-size: 11px; }
@media (max-width: 1000px) { .dashboard { grid-template-columns: 1fr; } .chart-grid { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<h1>FlakeIQ</h1>
<p class="subtitle">Test flake tracker &mdash; <span id="recordCount">0</span> records &middot; <span id="dateRange"></span></p>
<div class="dashboard">
<div class="stats-row" id="statsRow"></div>

<div class="card"><h2>Flake Rate (7d Moving Avg)</h2><canvas id="trendChart"></canvas></div>
<div class="card"><h2>Failure Breakdown</h2><canvas id="pieChart"></canvas></div>

<div class="card"><h2>Flake Rate by Action Type</h2><canvas id="actionChart"></canvas></div>
<div class="card"><h2>Platform Comparison</h2><canvas id="platformChart"></canvas></div>

<div class="card"><h2>Daily Test Volume</h2><canvas id="volumeChart"></canvas></div>
<div class="card"><h2>Failure Duration Distribution</h2><canvas id="durationChart"></canvas></div>

<div class="card full"><h2>Classification Trend Over Time</h2><canvas id="classificationTrendChart" style="max-height:200px"></canvas></div>

<div class="card full"><h2>Flake Heatmap (Screen × Day)</h2><div style="overflow-x:auto;font-size:12px" id="heatmapContainer"></div></div>

<div class="card full"><h2>Top Flaky Tests</h2>
<table><thead><tr><th>Test</th><th>Platform</th><th>Screen</th><th>Fail Rate</th><th>Runs</th><th>Flake Bar</th><th>Common Issue</th></tr></thead><tbody id="flakeTableBody"></tbody></table></div>

<div class="card full"><h2>Device Health</h2>
<table><thead><tr><th>Device</th><th>Platform</th><th>Runs</th><th>Fail Rate</th><th>Flake Bar</th><th>Common Issue</th></tr></thead><tbody id="deviceTableBody"></tbody></table></div>

<div class="card full"><h2>Latest Session</h2>
<div id="latestSessionContainer"><span style="color:var(--muted)">Loading...</span></div></div>

<div class="card full"><h2>Sessions</h2>
<div style="overflow-x:auto"><table><thead><tr><th>Session</th><th>Platform</th><th>Device</th><th>Runs</th><th>Passed</th><th>Failed</th><th>Pass Rate</th><th>Avg Duration</th><th>First Run</th><th>Last Run</th></tr></thead><tbody id="sessionsTableBody"></tbody></table></div></div>
</div>

<script>
const COLORS = { REAL_BUG: '#f85149', TIMEOUT_FLAKE: '#d29922', DEVICE_FLAKE: '#58a6ff', LOCATOR_FLAKE: '#bc8cff', UNKNOWN: '#8b949e', UNCLASSIFIED: '#484f58' };

async function loadData() {
  const [stats, trend, pie, action, platform, volume, duration, clsTrend, heatmap, topFlakes, devices, latestSession, sessions] = await Promise.all([
    fetch('/api/stats').then(r=>r.json()),
    fetch('/api/flake-rate').then(r=>r.json()),
    fetch('/api/breakdown').then(r=>r.json()),
    fetch('/api/by-action').then(r=>r.json()),
    fetch('/api/by-platform').then(r=>r.json()),
    fetch('/api/volume').then(r=>r.json()),
    fetch('/api/duration-dist').then(r=>r.json()),
    fetch('/api/classification-trend').then(r=>r.json()),
    fetch('/api/heatmap').then(r=>r.json()),
    fetch('/api/top-flakes').then(r=>r.json()),
    fetch('/api/devices').then(r=>r.json()),
    fetch('/api/latest-session').then(r=>r.json()),
    fetch('/api/sessions').then(r=>r.json()),
  ]);
  document.getElementById('recordCount').textContent = stats.total_runs;
  document.getElementById('dateRange').textContent = stats.date_range || '';
  renderStats(stats);
  renderTrend(trend);
  renderPie(pie);
  renderActionChart(action);
  renderPlatformChart(platform);
  renderVolumeChart(volume);
  renderDurationChart(duration);
  renderClassificationTrend(clsTrend);
  renderHeatmap(heatmap);
  renderTable('flakeTableBody', topFlakes, true);
  renderTable('deviceTableBody', devices, false);
  renderLatestSession(latestSession);
  renderSessions(sessions);
}

function renderStats(s) {
  const flakeColor = s.flake_rate > 20 ? 'down' : s.flake_rate > 10 ? 'warn' : 'up';
  document.getElementById('statsRow').innerHTML = `
    <div class="stat-card info"><div class="value">${s.total_runs}</div><div class="label">Total Runs</div></div>
    <div class="stat-card down"><div class="value">${s.fail_count}</div><div class="label">Failures</div><div class="trend">${(s.fail_count/s.total_runs*100).toFixed(1)}% fail rate</div></div>
    <div class="stat-card ${flakeColor}"><div class="value">${s.flake_rate}%</div><div class="label">Flake Rate</div></div>
    <div class="stat-card warn"><div class="value">${s.real_bug_count}</div><div class="label">Real Bugs</div></div>
    <div class="stat-card purple"><div class="value">${s.classified_count}</div><div class="label">Classified</div><div class="trend">${s.classified_count > 0 ? (s.real_bug_count/s.classified_count*100).toFixed(0)+'% are bugs' : ''}</div></div>
    <div class="stat-card info"><div class="value">${s.avg_duration}s</div><div class="label">Avg Duration</div></div>
  `;
}

function renderTrend(data) {
  const ctx = document.getElementById('trendChart').getContext('2d');
  new Chart(ctx, {
    type: 'line', data: {
      labels: data.map(d=>d.day),
      datasets: [{
        label: 'Flake Rate %', data: data.map(d=>d.rate),
        borderColor: '#58a6ff', backgroundColor: 'rgba(88,166,255,0.08)',
        fill: true, tension: 0.3, pointRadius: 2, pointHoverRadius: 5,
      }]
    }, options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        x: { ticks: { color: '#8b949e', maxTicksLimit: 14, font: {size: 10} }, grid: {color: '#21262d'} },
        y: { ticks: { color: '#8b949e', font: {size: 10} }, beginAtZero: true, grid: {color: '#21262d'} }
      },
      plugins: { legend: { labels: { color: '#c9d1d9', font: {size: 11} } } }
    }
  });
}

function renderPie(data) {
  const ctx = document.getElementById('pieChart').getContext('2d');
  new Chart(ctx, {
    type: 'doughnut', data: {
      labels: data.map(d=>d.classification),
      datasets: [{ data: data.map(d=>d.count), backgroundColor: data.map(d=>COLORS[d.classification]||'#484f58'), borderWidth: 0 }]
    }, options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'right', labels: { color: '#c9d1d9', font: {size: 11}, padding: 12 } } }
    }
  });
}

function renderActionChart(data) {
  if (!data.length) return;
  const ctx = document.getElementById('actionChart').getContext('2d');
  const colors = { fill: '#58a6ff', swipe: '#d29922', tap: '#3fb950', press: '#bc8cff', scrollIntoView: '#f0883e', other: '#8b949e' };
  new Chart(ctx, {
    type: 'bar', data: {
      labels: data.map(d=>d.action_type),
      datasets: [{
        label: 'Flake Rate %', data: data.map(d=>d.rate),
        backgroundColor: data.map(d=>colors[d.action_type]||'#8b949e'),
        borderRadius: 4, borderSkipped: false,
      }]
    }, options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        x: { ticks: { color: '#8b949e', font: {size: 10} }, grid: {display: false} },
        y: { ticks: { color: '#8b949e', font: {size: 10} }, beginAtZero: true, grid: {color: '#21262d'} }
      },
      plugins: { legend: { display: false } }
    }
  });
}

function renderPlatformChart(data) {
  const ctx = document.getElementById('platformChart').getContext('2d');
  new Chart(ctx, {
    type: 'bar', data: {
      labels: data.map(d=>d.platform),
      datasets: [
        { label: 'Pass', data: data.map(d=>d.pass_count), backgroundColor: '#1b3a2d', borderRadius: 4 },
        { label: 'Fail', data: data.map(d=>d.fail_count), backgroundColor: '#3d1f1f', borderRadius: 4 },
      ]
    }, options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        x: { stacked: true, ticks: { color: '#8b949e', font: {size: 10} }, grid: {display: false} },
        y: { stacked: true, ticks: { color: '#8b949e', font: {size: 10} }, beginAtZero: true, grid: {color: '#21262d'} }
      },
      plugins: { legend: { labels: { color: '#c9d1d9', font: {size: 11} } } }
    }
  });
}

function renderVolumeChart(data) {
  const ctx = document.getElementById('volumeChart').getContext('2d');
  new Chart(ctx, {
    type: 'bar', data: {
      labels: data.map(d=>d.day),
      datasets: [
        { label: 'Pass', data: data.map(d=>d.pass_count), backgroundColor: '#1b3a2d', borderRadius: 2 },
        { label: 'Fail', data: data.map(d=>d.fail_count), backgroundColor: '#3d1f1f', borderRadius: 2 },
      ]
    }, options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        x: { ticks: { color: '#8b949e', maxTicksLimit: 10, font: {size: 9} }, grid: {display: false}, stacked: true },
        y: { ticks: { color: '#8b949e', font: {size: 10} }, beginAtZero: true, grid: {color: '#21262d'}, stacked: true }
      },
      plugins: { legend: { labels: { color: '#c9d1d9', font: {size: 11} } } }
    }
  });
}

function renderDurationChart(data) {
  const ctx = document.getElementById('durationChart').getContext('2d');
  new Chart(ctx, {
    type: 'bar', data: {
      labels: data.map(d=>d.bucket),
      datasets: [{
        label: 'Failures', data: data.map(d=>d.count),
        backgroundColor: '#f8514944', borderColor: '#f85149', borderWidth: 1,
        borderRadius: 3,
      }]
    }, options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        x: { ticks: { color: '#8b949e', font: {size: 9} }, grid: {display: false} },
        y: { ticks: { color: '#8b949e', font: {size: 10} }, beginAtZero: true, grid: {color: '#21262d'} }
      },
      plugins: { legend: { display: false } }
    }
  });
}

function renderClassificationTrend(data) {
  if (!data.length) return;
  const categories = [...new Set(data.map(d=>d.classification))].filter(Boolean);
  const days = [...new Set(data.map(d=>d.day))].sort();
  const datasets = categories.map(cat => ({
    label: cat,
    data: days.map(day => { const f = data.find(d=>d.day===day&&d.classification===cat); return f ? f.count : 0; }),
    backgroundColor: COLORS[cat] + '66',
    borderColor: COLORS[cat],
    borderWidth: 1,
    fill: true,
    tension: 0.3,
    pointRadius: 0,
  }));
  const ctx = document.getElementById('classificationTrendChart').getContext('2d');
  new Chart(ctx, {
    type: 'line', data: { labels: days, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        x: { ticks: { color: '#8b949e', maxTicksLimit: 10, font: {size: 9} }, grid: {color: '#21262d'} },
        y: { stacked: true, ticks: { color: '#8b949e', font: {size: 10} }, beginAtZero: true, grid: {color: '#21262d'} }
      },
      plugins: {
        legend: { labels: { color: '#c9d1d9', font: {size: 10} } },
        tooltip: { mode: 'index', intersect: false }
      },
      interaction: { mode: 'nearest', axis: 'x', intersect: false }
    }
  });
}

function renderHeatmap(data) {
  const container = document.getElementById('heatmapContainer');
  if (!data.length) { container.innerHTML = '<span style="color:var(--muted)">Not enough data.</span>'; return; }
  const screens = [...new Set(data.map(d=>d.screen))].sort();
  const days = [...new Set(data.map(d=>d.day))].sort();
  const lookup = {}; data.forEach(d => { lookup[d.screen+'|'+d.day] = d.rate; });
  const heatColor = v => { if (v === 0) return '#1b3a2d'; if (v < 10) return '#2d4a1a'; if (v < 20) return '#3d3a1a'; if (v < 35) return '#4a2a1a'; if (v < 50) return '#5a1a1a'; return '#6a0a0a'; };
  let html = '<table style="border-collapse:collapse"><tr><th style="padding:3px 8px;color:var(--muted);font-size:10px;font-weight:600">Screen</th>';
  days.forEach(d => { html += `<th style="padding:3px 4px;color:var(--muted);font-size:9px;font-weight:600;text-align:center">${d.slice(5)}</th>`; });
  html += '<th style="padding:3px 8px;color:var(--muted);font-size:10px;font-weight:600;text-align:center">Avg</th></tr>';
  screens.forEach(s => {
    html += `<tr><td style="padding:3px 8px;color:var(--text);font-size:11px">${s}</td>`;
    let sum = 0, cnt = 0;
    days.forEach(d => {
      const v = lookup[s+'|'+d];
      if (v !== undefined) { sum += v; cnt++; }
      const bg = v !== undefined ? heatColor(v) : '#161b22';
      const txt = v !== undefined ? v.toFixed(0) + '%' : '—';
      html += `<td style="padding:3px 4px;text-align:center;background:${bg};color:${v > 30 ? '#fff' : 'var(--text)'};border-radius:3px;font-size:11px;font-weight:${v !== undefined ? '600' : '400'}">${txt}</td>`;
    });
    const avg = cnt > 0 ? (sum / cnt).toFixed(0) + '%' : '—';
    html += `<td style="padding:3px 8px;text-align:center;color:var(--muted);font-size:11px;font-weight:600">${avg}</td></tr>`;
  });
  html += '</table>';
  container.innerHTML = html;
}

function renderTable(tbodyId, rows, isTest) {
  const tbody = document.getElementById(tbodyId);
  if (!rows.length) { tbody.innerHTML = '<tr><td colspan="7" style="color:var(--muted);text-align:center;padding:20px;font-size:13px">No data yet. Run tests first.</td></tr>'; return; }
  tbody.innerHTML = rows.map(r => {
    const rate = (r.fail_count / r.total * 100);
    const pct = Math.min(100, Math.round(rate));
    const cls = r.common_classification || 'UNKNOWN';
    const name = isTest ? r.test_name : r.device_id;
    const platform = r.platform || '';
    const subtitle = isTest ? (r.screen_name || '') : '';
    const barColor = pct > 50 ? 'var(--red)' : pct > 25 ? 'var(--yellow)' : pct > 10 ? 'var(--orange)' : 'var(--green)';
    return `<tr>
      <td style="max-width:280px;overflow:hidden;text-overflow:ellipsis">${name}</td>
      <td>${platform ? `<span class="badge badge-${platform}">${platform}</span>` : ''}</td>
      <td>${subtitle ? `<span class="badge">${subtitle}</span>` : ''}</td>
      <td style="font-weight:600">${rate.toFixed(1)}%</td>
      <td>${r.total}</td>
      <td><div class="flake-bar"><div class="flake-bar-fill" style="width:${pct}%;background:${barColor}"></div></div></td>
      <td><span class="badge badge-${cls}">${cls}</span></td>
    </tr>`;
  }).join('');
}

function renderLatestSession(s) {
  const container = document.getElementById('latestSessionContainer');
  if (!s || !s.total_runs) {
    container.innerHTML = '<span style="color:var(--muted)">No sessions recorded yet.</span>';
    return;
  }
  const rate = s.total_runs > 0 ? (s.passed / s.total_runs * 100).toFixed(0) : 0;
  let testsHtml = s.tests.map(t => {
    const cls = t.result === 'passed' ? 'badge-pass' : 'badge-fail';
    return `<span class="test-badge badge ${cls}" title="${t.test_name} (${t.duration_ms}ms)">${t.test_name}</span>`;
  }).join('');
  container.innerHTML = `
    <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:12px">
      <div><span style="font-size:24px;font-weight:700">${s.total_runs}</span><span style="color:var(--muted);margin-left:6px;font-size:12px">tests</span></div>
      <div><span style="font-size:24px;font-weight:700;color:var(--green)">${s.passed}</span><span style="color:var(--muted);margin-left:6px;font-size:12px">passed</span></div>
      <div><span style="font-size:24px;font-weight:700;color:var(--red)">${s.failed}</span><span style="color:var(--muted);margin-left:6px;font-size:12px">failed</span></div>
      <div><span style="font-size:24px;font-weight:700">${rate}%</span><span style="color:var(--muted);margin-left:6px;font-size:12px">pass rate</span></div>
      <div><span style="font-size:20px;font-weight:600;color:var(--accent)">${s.platform || '—'}</span><span style="color:var(--muted);margin-left:6px;font-size:12px">platform</span></div>
      <div><span style="font-size:14px;color:var(--muted)">${s.avg_duration_s || 0}s avg</span></div>
    </div>
    <div class="session-row">${testsHtml}</div>
  `;
}

function renderSessions(sessions) {
  const tbody = document.getElementById('sessionsTableBody');
  if (!sessions.length) {
    tbody.innerHTML = '<tr><td colspan="10" style="color:var(--muted);text-align:center;padding:20px">No sessions recorded.</td></tr>';
    return;
  }
  tbody.innerHTML = sessions.map(s => {
    const rate = s.total_runs > 0 ? (s.passed / s.total_runs * 100).toFixed(0) : 0;
    const passColor = rate >= 90 ? 'var(--green)' : rate >= 70 ? 'var(--yellow)' : 'var(--red)';
    return `<tr>
      <td style="font-family:monospace;font-size:12px;max-width:200px;overflow:hidden;text-overflow:ellipsis" title="${s.session_id}">${s.session_id.slice(0, 30)}</td>
      <td>${s.platform || '—'}</td>
      <td style="font-size:12px;max-width:160px;overflow:hidden;text-overflow:ellipsis" title="${s.device_id || ''}">${s.device_id ? s.device_id.slice(0, 25) : '—'}</td>
      <td>${s.total_runs}</td>
      <td style="color:var(--green)">${s.passed}</td>
      <td style="color:var(--red)">${s.failed}</td>
      <td style="font-weight:600;color:${passColor}">${rate}%</td>
      <td>${s.avg_duration_s || 0}s</td>
      <td style="font-size:11px;color:var(--muted)">${s.first_run ? s.first_run.slice(0, 16).replace('T', ' ') : '—'}</td>
      <td style="font-size:11px;color:var(--muted)">${s.last_run ? s.last_run.slice(0, 16).replace('T', ' ') : '—'}</td>
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
        if path in ("/", "/index.html"):
            self._html()
            return
        handlers = {
            "/api/stats": self.api_stats,
            "/api/flake-rate": self.api_flake_rate,
            "/api/breakdown": self.api_breakdown,
            "/api/heatmap": self.api_heatmap,
            "/api/top-flakes": self.api_top_flakes,
            "/api/devices": self.api_devices,
            "/api/by-action": self.api_by_action,
            "/api/by-platform": self.api_by_platform,
            "/api/volume": self.api_volume,
            "/api/duration-dist": self.api_duration_dist,
            "/api/classification-trend": self.api_classification_trend,
            "/api/sessions": self.api_sessions,
            "/api/latest-session": self.api_latest_session,
        }
        h = handlers.get(path)
        if h:
            h()
        else:
            self.send_response(404); self.end_headers()

    def _html(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(HTML.encode())

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
            return [dict(r) for r in db.execute(sql, params).fetchall()]
        finally:
            db.close()

    def _scalar(self, sql, params=()):
        rows = self._query(sql, params)
        if rows:
            return list(rows[0].values())[0]
        return 0

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
        avg_dur = self._scalar("SELECT CAST(ROUND(AVG(duration_ms / 1000.0)) AS INTEGER) FROM test_runs")
        s["avg_duration"] = avg_dur or 0
        dr = self._query("SELECT MIN(DATE(run_at)) as first, MAX(DATE(run_at)) as last FROM test_runs")
        if dr and dr[0]["first"] and dr[0]["last"]:
            s["date_range"] = f"{dr[0]['first']} to {dr[0]['last']}"
        else:
            s["date_range"] = ""
        self._json(s)

    def api_flake_rate(self):
        rows = self._query("""
            SELECT DATE(run_at) as day,
                   ROUND(SUM(CASE WHEN result != 'passed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as rate
            FROM test_runs
            GROUP BY day ORDER BY day LIMIT 60
        """)
        self._json(rows)

    def api_breakdown(self):
        rows = self._query("""
            SELECT COALESCE(classification, 'UNCLASSIFIED') as classification, COUNT(*) as count
            FROM test_runs WHERE result != 'passed'
            GROUP BY classification ORDER BY count DESC
        """)
        self._json(rows)

    def api_heatmap(self):
        rows = self._query("""
            SELECT DATE(run_at) as day, screen_name as screen,
                   ROUND(SUM(CASE WHEN result != 'passed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as rate
            FROM test_runs
            WHERE screen_name IS NOT NULL AND screen_name != ''
            GROUP BY day, screen
            HAVING COUNT(*) >= 2
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
            HAVING total >= 2
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

    def api_by_action(self):
        rows = self._query("""
            SELECT action_type,
                   COUNT(*) as total,
                   SUM(CASE WHEN result != 'passed' THEN 1 ELSE 0 END) as fail_count,
                   ROUND(SUM(CASE WHEN result != 'passed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as rate
            FROM test_runs
            WHERE action_type IS NOT NULL AND action_type != ''
            GROUP BY action_type
            ORDER BY rate DESC
        """)
        self._json(rows)

    def api_by_platform(self):
        rows = self._query("""
            SELECT platform,
                   COUNT(*) as total,
                   SUM(CASE WHEN result = 'passed' THEN 1 ELSE 0 END) as pass_count,
                   SUM(CASE WHEN result != 'passed' THEN 1 ELSE 0 END) as fail_count,
                   ROUND(SUM(CASE WHEN result != 'passed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as fail_rate
            FROM test_runs
            WHERE platform IS NOT NULL AND platform != ''
            GROUP BY platform
            ORDER BY fail_rate DESC
        """)
        self._json(rows)

    def api_volume(self):
        rows = self._query("""
            SELECT DATE(run_at) as day,
                   SUM(CASE WHEN result = 'passed' THEN 1 ELSE 0 END) as pass_count,
                   SUM(CASE WHEN result != 'passed' THEN 1 ELSE 0 END) as fail_count
            FROM test_runs
            GROUP BY day ORDER BY day
        """)
        self._json(rows)

    def api_duration_dist(self):
        rows = self._query("""
            SELECT
                CASE
                    WHEN duration_ms < 5000 THEN '0-5s'
                    WHEN duration_ms < 15000 THEN '5-15s'
                    WHEN duration_ms < 30000 THEN '15-30s'
                    WHEN duration_ms < 60000 THEN '30-60s'
                    WHEN duration_ms < 120000 THEN '60-120s'
                    ELSE '120s+'
                END as bucket,
                COUNT(*) as count
            FROM test_runs
            WHERE result != 'passed'
            GROUP BY bucket
            ORDER BY MIN(duration_ms)
        """)
        self._json(rows)

    def api_classification_trend(self):
        rows = self._query("""
            SELECT DATE(run_at) as day, classification, COUNT(*) as count
            FROM test_runs
            WHERE result != 'passed' AND classification IS NOT NULL
            GROUP BY day, classification
            ORDER BY day
        """)
        self._json(rows)

    def api_sessions(self):
        rows = self._query("""
            SELECT session_id, platform, device_id,
                   COUNT(*) as total_runs,
                   SUM(CASE WHEN result = 'passed' THEN 1 ELSE 0 END) as passed,
                   SUM(CASE WHEN result != 'passed' THEN 1 ELSE 0 END) as failed,
                   CAST(ROUND(AVG(duration_ms / 1000.0)) AS INTEGER) as avg_duration_s,
                   MIN(run_at) as first_run,
                   MAX(run_at) as last_run
            FROM test_runs
            WHERE session_id IS NOT NULL AND session_id != ''
            GROUP BY session_id
            ORDER BY last_run DESC
            LIMIT 20
        """)
        self._json(rows)

    def api_latest_session(self):
        session = self._query("""
            SELECT session_id, platform, device_id,
                   COUNT(*) as total_runs,
                   SUM(CASE WHEN result = 'passed' THEN 1 ELSE 0 END) as passed,
                   SUM(CASE WHEN result != 'passed' THEN 1 ELSE 0 END) as failed,
                   CAST(ROUND(AVG(duration_ms / 1000.0)) AS INTEGER) as avg_duration_s
            FROM test_runs
            WHERE session_id IS NOT NULL AND session_id != ''
            GROUP BY session_id
            ORDER BY MAX(run_at) DESC
            LIMIT 1
        """)
        if not session:
            self._json({"total_runs": 0, "passed": 0, "failed": 0})
            return
        s = session[0]
        tests = self._query("""
            SELECT test_name, result, duration_ms, platform, screen_name, classification
            FROM test_runs
            WHERE session_id = ?
            ORDER BY run_at
        """, (s["session_id"],))
        s["tests"] = tests
        self._json(s)

    def log_message(self, format, *args):
        pass


def main():
    global DB_PATH, PORT
    parser = argparse.ArgumentParser(description="FlakeIQ dashboard")
    parser.add_argument("--db", default=None, help="SQLite database path")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address")
    parser.add_argument("--seed", action="store_true", help="Use the seed database (flake-seed.db) instead of real data")
    parser.add_argument("--open", action="store_true", help="Open browser on start")
    args = parser.parse_args()
    if args.seed:
        seed_path = os.path.join(os.path.dirname(__file__), "flake-seed.db")
        if os.path.exists(seed_path):
            DB_PATH = seed_path
            print(f"Using seed database: {seed_path}")
        else:
            print("Seed database not found. Run 'python3 seed.py' first.")
            sys.exit(1)
    elif args.db:
        DB_PATH = args.db
    PORT = args.port
    os.environ["FLAKE_DB"] = DB_PATH

    if not os.path.exists(DB_PATH):
        print(f"Database not found: {DB_PATH}")
        print("Run 'python3 classify.py flake-results.jsonl' or 'python3 seed.py' first.")
        sys.exit(1)

    server = HTTPServer((args.host, PORT), Handler)
    url = f"http://{args.host}:{PORT}"
    print(f"FlakeIQ dashboard at {url}")
    if args.open:
        import webbrowser
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()

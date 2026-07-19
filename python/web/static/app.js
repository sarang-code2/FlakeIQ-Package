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

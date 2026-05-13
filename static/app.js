// FugginNAS — SPA router + wizard screens

const _routes = {};
const _state = {};

function register(hash, fn) { _routes[hash] = fn; }
function navigate(hash) { location.hash = hash; }
function app() { return document.getElementById('app'); }

function render() {
  const hash = location.hash.replace(/^#/, '') || 'welcome';
  const fn = _routes[hash];
  if (fn) fn(); else _routes['welcome']();
}

window.addEventListener('hashchange', render);
window.addEventListener('DOMContentLoaded', render);

function formatBytes(bytes) {
  if (bytes >= 1e12) return (bytes / 1e12).toFixed(1) + ' TB';
  if (bytes >= 1e9)  return (bytes / 1e9).toFixed(1)  + ' GB';
  if (bytes >= 1e6)  return (bytes / 1e6).toFixed(1)  + ' MB';
  return bytes + ' B';
}

async function post(url, data) {
  return fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

// ── Screen: Welcome ──────────────────────────────────────────────────────────

register('welcome', () => {
  app().innerHTML = `
    <h1>FugginNAS</h1>
    <p>Browser-based wizard for configuring a home NAS on fresh Debian.</p>
    <div class="actions">
      <button id="btn-start">Start Setup →</button>
    </div>
  `;
  document.getElementById('btn-start').addEventListener('click', () => navigate('#backend'));
});

// ── Screen: Storage Backend ──────────────────────────────────────────────────

register('backend', () => {
  app().innerHTML = `
    <h1>FugginNAS</h1>
    <h2>Step 2 — Storage Backend</h2>
    <div class="option-group">
      <label class="option">
        <input type="radio" name="backend" value="snapraid" checked>
        <span>SnapRAID + MergerFS</span>
        <small>Scheduled parity — lower write overhead, recovery via sync</small>
      </label>
      <label class="option">
        <input type="radio" name="backend" value="nonraid">
        <span>NonRAID + MergerFS</span>
        <small>Live real-time parity — unRAID-style kernel driver</small>
      </label>
      <label class="option">
        <input type="radio" name="backend" value="mergerfs">
        <span>MergerFS only</span>
        <small>Pooling only — no parity protection</small>
      </label>
    </div>
    <div class="actions">
      <button id="btn-next">Next →</button>
    </div>
  `;

  document.getElementById('btn-next').addEventListener('click', async () => {
    const selected = document.querySelector('input[name="backend"]:checked').value;
    const resp = await post('/api/backend', { backend: selected });
    if (resp.ok) {
      _state.backend = selected;
      navigate(selected === 'nonraid' ? '#nonraid' : '#drives');
    }
  });
});

// ── Screen: Drive Selection ──────────────────────────────────────────────────

register('drives', async () => {
  app().innerHTML = '<p>Loading drives…</p>';

  const resp = await fetch('/api/drives');
  if (!resp.ok) {
    app().innerHTML = '<p class="error">Failed to load drives from server.</p>';
    return;
  }
  const { drives } = await resp.json();

  const rows = drives.map(d => `
    <tr>
      <td>/dev/${d.name}</td>
      <td>${formatBytes(d.size)}</td>
      <td>${d.model || '—'}</td>
      <td>${d.mountpoint || '—'}</td>
      <td>${d.fstype || '—'}</td>
      <td>
        <select data-drive="${d.name}">
          <option value="ignore">Ignore</option>
          <option value="cache">Cache</option>
          <option value="data">Data</option>
          <option value="parity">Parity</option>
        </select>
      </td>
    </tr>
  `).join('');

  app().innerHTML = `
    <h1>FugginNAS</h1>
    <h2>Step 3 — Drive Selection</h2>
    <table>
      <thead>
        <tr>
          <th>Device</th><th>Size</th><th>Model</th>
          <th>Mount</th><th>Filesystem</th><th>Role</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
    <div class="actions">
      <button class="secondary" id="btn-back">← Back</button>
      <button id="btn-next">Next →</button>
    </div>
  `;

  document.getElementById('btn-back').addEventListener('click', () => navigate('#backend'));

  document.getElementById('btn-next').addEventListener('click', () => {
    const tagged = {};
    document.querySelectorAll('select[data-drive]').forEach(sel => {
      tagged[sel.dataset.drive] = sel.value;
    });
    _state.drives = tagged;
    navigate('#pool');
  });
});

// ── Screen: NonRAID (mdadm) Configuration ────────────────────────────────────

register('nonraid', () => {
  app().innerHTML = `
    <h1>FugginNAS</h1>
    <h2>NonRAID — RAID Array Configuration</h2>
    <div class="form-group">
      <label>Devices (comma-separated)
        <input id="nonraid-devices" type="text" placeholder="/dev/sdb,/dev/sdc">
      </label>
      <label>RAID level
        <select id="nonraid-level">
          <option value="1">RAID 1 — Mirroring</option>
          <option value="5">RAID 5 — Striping with parity</option>
          <option value="6">RAID 6 — Double parity</option>
          <option value="10">RAID 10 — Mirroring + Striping</option>
          <option value="0">RAID 0 — Striping (no redundancy)</option>
        </select>
      </label>
    </div>
    <div class="actions">
      <button class="secondary" id="btn-back">← Back</button>
      <button id="btn-next">Next →</button>
    </div>
  `;

  document.getElementById('btn-back').addEventListener('click', () => navigate('#backend'));
  document.getElementById('btn-next').addEventListener('click', async () => {
    const devices = document.getElementById('nonraid-devices').value
      .split(',').map(d => d.trim()).filter(Boolean);
    const level = parseInt(document.getElementById('nonraid-level').value, 10);
    const r = await post('/api/nonraid', { devices, level });
    if (r.ok) navigate('#drives');
  });
});

// ── Screen: Pool Configuration ────────────────────────────────────────────────

register('pool', () => {
  const tagged = _state.drives || {};
  const dataDisks = Object.keys(tagged).filter(k => tagged[k] === 'data');
  const cacheDisks = Object.keys(tagged).filter(k => tagged[k] === 'cache');

  app().innerHTML = `
    <h1>FugginNAS</h1>
    <h2>Step 4 — Pool Configuration</h2>
    <div class="form-group">
      <label>Pool mount point
        <input id="pool-mount" type="text" value="/mnt/pool">
      </label>
      <label>Cache mount point
        <input id="cache-mount" type="text" value="/mnt/cache">
      </label>
      <label>Write policy
        <select id="write-policy">
          <option value="mfs">MFS — most free space</option>
          <option value="lfs">LFS — least free space</option>
          <option value="existing">Existing path first</option>
        </select>
      </label>
    </div>
    <p>${dataDisks.length} data disk(s), ${cacheDisks.length} cache disk(s) selected.</p>
    <div class="actions">
      <button class="secondary" id="btn-back">← Back</button>
      <button id="btn-next">Next →</button>
    </div>
  `;

  document.getElementById('btn-back').addEventListener('click', () => navigate('#drives'));
  document.getElementById('btn-next').addEventListener('click', async () => {
    const r = await post('/api/pool', {
      pool_mount: document.getElementById('pool-mount').value,
      cache_mount: document.getElementById('cache-mount').value,
      data_mounts: dataDisks.map((_, i) => `/mnt/disk${i + 1}`),
      write_policy: document.getElementById('write-policy').value,
    });
    if (r.ok) navigate(_state.backend === 'mergerfs' ? '#mover' : '#snapraid');
  });
});

// ── Screen: SnapRAID Configuration ───────────────────────────────────────────

register('snapraid', () => {
  const tagged = _state.drives || {};
  const parityDisks = Object.keys(tagged).filter(k => tagged[k] === 'parity');
  const dataDisks = Object.keys(tagged).filter(k => tagged[k] === 'data');

  app().innerHTML = `
    <h1>FugginNAS</h1>
    <h2>Step 5 — SnapRAID Configuration</h2>
    <div class="form-group">
      <label>Parity mode
        <select id="parity-mode">
          <option value="single">Single parity (1 parity disk)</option>
          <option value="dual">Dual parity (2 parity disks)</option>
        </select>
      </label>
      <label>Scrub schedule
        <select id="scrub-schedule">
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
          <option value="off">Off</option>
        </select>
      </label>
    </div>
    <p>${parityDisks.length} parity disk(s) selected.</p>
    <div class="actions">
      <button class="secondary" id="btn-back">← Back</button>
      <button id="btn-next">Next →</button>
    </div>
  `;

  document.getElementById('btn-back').addEventListener('click', () => navigate('#pool'));
  document.getElementById('btn-next').addEventListener('click', async () => {
    const r = await post('/api/snapraid', {
      parity_disks: parityDisks.map(d => `/dev/${d}`),
      data_mounts: dataDisks.map((_, i) => `/mnt/disk${i + 1}`),
      scrub_schedule: document.getElementById('scrub-schedule').value,
      parity_mode: document.getElementById('parity-mode').value,
    });
    if (r.ok) navigate('#mover');
  });
});

// ── Screen: Mover Configuration ──────────────────────────────────────────────

register('mover', () => {
  app().innerHTML = `
    <h1>FugginNAS</h1>
    <h2>Step 6 — Mover Configuration</h2>
    <div class="form-group">
      <label>Run time (HH:MM)
        <input id="schedule-time" type="text" value="03:00">
      </label>
      <label>Move files older than (hours)
        <input id="age-hours" type="number" value="24" min="0">
      </label>
      <label>Min cache free (%)
        <input id="min-free-pct" type="number" value="20" min="0" max="100">
      </label>
    </div>
    <div class="actions">
      <button class="secondary" id="btn-back">← Back</button>
      <button id="btn-next">Next →</button>
    </div>
  `;

  document.getElementById('btn-back').addEventListener('click', () => navigate('#snapraid'));
  document.getElementById('btn-next').addEventListener('click', async () => {
    const r = await post('/api/mover', {
      schedule_time: document.getElementById('schedule-time').value,
      age_hours: parseInt(document.getElementById('age-hours').value, 10),
      min_free_pct: parseInt(document.getElementById('min-free-pct').value, 10),
    });
    if (r.ok) navigate('#shares');
  });
});

// ── Screen: Share Setup ───────────────────────────────────────────────────────

register('shares', () => {
  app().innerHTML = `
    <h1>FugginNAS</h1>
    <h2>Step 7 — Share Setup</h2>
    <div class="form-group">
      <label>Share name
        <input id="share-name" type="text" placeholder="media">
      </label>
      <label>Path
        <input id="share-path" type="text" value="/mnt/pool">
      </label>
      <label>Protocol
        <select id="share-protocol">
          <option value="smb">SMB (Windows/macOS)</option>
          <option value="nfs">NFS (Linux)</option>
          <option value="both">Both SMB + NFS</option>
        </select>
      </label>
    </div>
    <div class="actions">
      <button class="secondary" id="btn-back">← Back</button>
      <button id="btn-next">Add share →</button>
      <button class="secondary" id="btn-skip">Skip →</button>
    </div>
  `;

  document.getElementById('btn-back').addEventListener('click', () => navigate('#mover'));
  document.getElementById('btn-skip').addEventListener('click', () => navigate('#summary'));
  document.getElementById('btn-next').addEventListener('click', async () => {
    const r = await post('/api/shares', {
      name: document.getElementById('share-name').value,
      path: document.getElementById('share-path').value,
      protocol: document.getElementById('share-protocol').value,
    });
    if (r.ok) navigate('#summary');
  });
});

// ── Screen: Summary + Apply ───────────────────────────────────────────────────

register('summary', async () => {
  app().innerHTML = '<p>Loading summary…</p>';

  const resp = await fetch('/api/summary');
  if (!resp.ok) {
    app().innerHTML = '<p class="error">Failed to load summary.</p>';
    return;
  }
  const { files } = await resp.json();

  const rows = (files || []).map(f => `
    <tr>
      <td>${f.path}</td>
      <td><pre>${(f.content || '').slice(0, 120)}…</pre></td>
    </tr>
  `).join('');

  app().innerHTML = `
    <h1>FugginNAS</h1>
    <h2>Step 8 — Summary + Apply</h2>
    <table>
      <thead><tr><th>File</th><th>Preview</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <div class="actions">
      <button class="secondary" id="btn-back">← Back</button>
      <button id="btn-apply">Apply Configuration</button>
    </div>
  `;

  document.getElementById('btn-back').addEventListener('click', () => navigate('#shares'));
  document.getElementById('btn-apply').addEventListener('click', async () => {
    const r = await post('/api/apply', {});
    if (r.ok) navigate('#status');
  });
});

// ── Screen: Status Dashboard ──────────────────────────────────────────────────

register('status', async () => {
  app().innerHTML = '<p>Loading status…</p>';

  const resp = await fetch('/api/status');
  if (!resp.ok) {
    app().innerHTML = '<p class="error">Failed to load status.</p>';
    return;
  }
  const data = await resp.json();

  app().innerHTML = `
    <h1>FugginNAS</h1>
    <h2>Status Dashboard</h2>
    <table>
      <tr><th>Backend</th><td>${data.backend || '—'}</td></tr>
      <tr><th>Pool mount</th><td>${data.pool ? data.pool.mount : '—'}</td></tr>
      <tr><th>Pool used</th><td>${data.pool ? (data.pool.used_pct || 0) + '%' : '—'}</td></tr>
      <tr><th>Pool available</th><td>${data.pool ? formatBytes(data.pool.available_bytes || 0) : '—'}</td></tr>
      <tr><th>Cache fill</th><td>${data.cache_fill_pct != null ? data.cache_fill_pct + '%' : '—'}</td></tr>
      <tr><th>Shares</th><td>${(data.shares || []).length}</td></tr>
    </table>
    <div class="actions">
      <button class="secondary" id="btn-reconfigure">← Reconfigure</button>
    </div>
  `;

  document.getElementById('btn-reconfigure').addEventListener('click', () => navigate('#backend'));
});

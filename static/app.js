// FugginNAS — SPA router + wizard screens

const _routes = {};
const _state = {};

const THEMES = [
  "default", "nord", "dracula", "solarized-dark", "gruvbox",
  "monokai", "catppuccin", "tokyo-night", "one-dark",
  "material", "github-dark", "synthwave",
  "tron-blue", "tron-red",
];

function applyTheme(name) {
  document.documentElement.dataset.theme = name === 'default' ? '' : name;
}

async function loadTheme() {
  try {
    const resp = await fetch('/api/theme');
    if (resp.ok) {
      const { theme } = await resp.json();
      applyTheme(theme);
      const sel = document.getElementById('theme-select');
      if (sel) sel.value = theme;
    }
  } catch (_) {}
}

function mountThemePicker() {
  const picker = document.createElement('div');
  picker.id = 'theme-picker';
  picker.innerHTML = `
    Theme:
    <select id="theme-select">
      ${THEMES.map(t => `<option value="${t}">${t}</option>`).join('')}
    </select>
  `;
  document.body.appendChild(picker);
  picker.querySelector('#theme-select').addEventListener('change', async (e) => {
    const name = e.target.value;
    applyTheme(name);
    await post('/api/theme', { theme: name });
  });
}

function register(hash, fn) { _routes[hash] = fn; }
function navigate(hash) { location.hash = hash; }
function app() { return document.getElementById('app'); }

function render() {
  const hash = location.hash.replace(/^#/, '') || 'welcome';
  const fn = _routes[hash];
  if (fn) fn(); else _routes['welcome']();
}

window.addEventListener('hashchange', render);
window.addEventListener('DOMContentLoaded', () => {
  mountThemePicker();
  loadTheme();
  render();
});

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

function showModal(message, onConfirm) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `
    <div class="modal">
      <p>${message}</p>
      <div class="actions">
        <button id="modal-cancel" class="secondary">Cancel</button>
        <button id="modal-confirm">Confirm</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);
  overlay.querySelector('#modal-cancel').addEventListener('click', () => overlay.remove());
  overlay.querySelector('#modal-confirm').addEventListener('click', () => {
    overlay.remove();
    onConfirm();
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
  const current = _state.backend;

  app().innerHTML = `
    <h1>FugginNAS</h1>
    <h2>Step 2 — Storage Backend</h2>
    <table class="comparison-table">
      <thead>
        <tr>
          <th></th>
          <th>NonRAID + MergerFS</th>
          <th>SnapRAID + MergerFS</th>
          <th>MergerFS only</th>
        </tr>
      </thead>
      <tbody>
        <tr><td>Parity timing</td><td>Live, every write</td><td>Scheduled (nightly)</td><td>None</td></tr>
        <tr><td>Write overhead</td><td>~1/3 disk speed</td><td>Full speed</td><td>Full speed</td></tr>
        <tr><td>Unsynced file risk</td><td>None</td><td>Until next sync</td><td>N/A</td></tr>
        <tr><td>Accidental delete</td><td>Not protected</td><td>Protected until sync</td><td>Not protected</td></tr>
        <tr><td>Recovery model</td><td>Drive rebuild</td><td>Per-file restore</td><td>None</td></tr>
        <tr><td>Uses MergerFS pool</td><td>Yes — required</td><td>Yes — required</td><td>Yes — only layer</td></tr>
      </tbody>
    </table>
    <p class="info-note">All three options use <strong>MergerFS</strong> to present your disks as a single pool mount.
    NonRAID and SnapRAID add a parity layer on top of that — they are not alternatives to MergerFS.</p>
    <div class="option-group">
      <label class="option">
        <input type="radio" name="backend" value="snapraid" ${current === 'snapraid' || !current ? 'checked' : ''}>
        <span>SnapRAID + MergerFS</span>
        <small>Scheduled parity — full write speed, recovery via nightly sync</small>
      </label>
      <label class="option">
        <input type="radio" name="backend" value="nonraid" ${current === 'nonraid' ? 'checked' : ''}>
        <span>NonRAID + MergerFS</span>
        <small>Live real-time parity — unRAID-style kernel driver, ~1/3 write penalty</small>
      </label>
      <label class="option">
        <input type="radio" name="backend" value="mergerfs" ${current === 'mergerfs' ? 'checked' : ''}>
        <span>MergerFS only</span>
        <small>Pooling with no parity — full speed, no drive failure protection</small>
      </label>
    </div>
    <div class="actions">
      <button id="btn-next">Next →</button>
    </div>
  `;

  document.getElementById('btn-next').addEventListener('click', async () => {
    const selected = document.querySelector('input[name="backend"]:checked').value;

    const doNavigate = async () => {
      const resp = await post('/api/backend', { backend: selected });
      if (resp.ok) {
        _state.backend = selected;
        navigate('#drives');
      }
    };

    if (current && current !== selected) {
      showModal(
        `Changing backend from <strong>${current}</strong> to <strong>${selected}</strong> will reset your pool, parity, and mover configuration. Continue?`,
        async () => {
          delete _state.pool;
          delete _state.snapraid;
          delete _state.nonraid;
          delete _state.mover;
          delete _state.shares;
          await doNavigate();
        }
      );
    } else {
      await doNavigate();
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
    if (r.ok) {
      if (_state.backend === 'mergerfs') navigate('#mover');
      else if (_state.backend === 'nonraid') navigate('#nonraid');
      else navigate('#snapraid');
    }
  });
});

// ── Screen: SnapRAID Configuration (5a) ──────────────────────────────────────

register('snapraid', () => {
  const tagged = _state.drives || {};
  const parityDisks = Object.keys(tagged).filter(k => tagged[k] === 'parity');
  const dataDisks = Object.keys(tagged).filter(k => tagged[k] === 'data');

  app().innerHTML = `
    <h1>FugginNAS</h1>
    <h2>Step 5a — SnapRAID Configuration</h2>
    <div class="form-group">
      <label>Parity mode
        <select id="parity-mode">
          <option value="single">Single parity (1 parity disk)</option>
          <option value="dual">Dual parity (2 parity disks)</option>
        </select>
      </label>
      <label>Sync schedule time (HH:MM)
        <input id="sync-time" type="text" value="02:00" placeholder="02:00">
      </label>
      <label>Scrub schedule
        <select id="scrub-schedule">
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
          <option value="off">Off</option>
        </select>
      </label>
    </div>
    <p class="hint">Content files will be auto-placed on each data disk and the parity disk.</p>
    <p>${parityDisks.length} parity disk(s), ${dataDisks.length} data disk(s) selected.</p>
    <div class="actions">
      <button class="secondary" id="btn-back">← Back</button>
      <button id="btn-next">Next →</button>
    </div>
  `;

  document.getElementById('btn-back').addEventListener('click', () => navigate('#pool'));
  document.getElementById('btn-next').addEventListener('click', async () => {
    const r = await post('/api/snapraid', {
      parity_disks: parityDisks.map(d => `/mnt/${d}`),
      data_mounts: dataDisks.map((_, i) => `/mnt/disk${i + 1}`),
      parity_mode: document.getElementById('parity-mode').value,
      sync_time: document.getElementById('sync-time').value,
      scrub_schedule: document.getElementById('scrub-schedule').value,
    });
    if (r.ok) navigate('#mover');
  });
});

// ── Screen: NonRAID Configuration (5b) ───────────────────────────────────────

register('nonraid', async () => {
  const installResp = await fetch('/api/nonraid/install');
  const installData = installResp.ok ? await installResp.json() : { installed: false };
  const installed = installData.installed;

  app().innerHTML = `
    <h1>FugginNAS</h1>
    <h2>Step 5b — NonRAID Configuration</h2>
    <div class="notice warning">
      <strong>Early-stage project</strong> — data loss possible. Always maintain external backups.
      Write throughput is ~1/3 single-disk speed due to read-modify-write parity cycle.
    </div>
    <div class="form-group">
      <label>NonRAID status
        <span class="status-badge ${installed ? 'ok' : 'warn'}">${installed ? 'Installed' : 'Not installed'}</span>
        ${!installed ? '<button id="btn-install" class="inline">Install NonRAID</button>' : ''}
      </label>

      <h3>Array</h3>
      <label>Parity mode
        <select id="parity-mode">
          <option value="single">Single parity (1 parity disk)</option>
          <option value="dual">Dual parity (2 parity disks — slot 29)</option>
        </select>
      </label>
      <label>Per-disk filesystem
        <select id="filesystem">
          <option value="xfs">XFS (recommended)</option>
          <option value="btrfs">BTRFS</option>
          <option value="ext4">ext4</option>
          <option value="zfs">ZFS (requires cachefile=none)</option>
        </select>
      </label>

      <h3>Write Behavior</h3>
      <label>
        <input type="checkbox" id="turbo-write"> Turbo write mode
        <small>Reconstruct-write — faster writes, but keeps all disks spinning constantly</small>
      </label>

      <h3>Encryption</h3>
      <label>
        <input type="checkbox" id="luks"> LUKS encryption per disk
        <small>Keyfile stored at /etc/nonraid/luks-keyfile — back it up or lose all data</small>
      </label>

      <h3>Parity Check</h3>
      <label>Check schedule
        <select id="check-schedule">
          <option value="quarterly">Quarterly (recommended)</option>
          <option value="monthly">Monthly</option>
          <option value="off">Off</option>
        </select>
      </label>
      <label>Correction mode
        <select id="check-correct">
          <option value="nocorrect">NOCORRECT — report errors only (recommended)</option>
          <option value="correct">CORRECT — auto-repair mismatches</option>
        </select>
        <small>NOCORRECT is safer: review results before deciding to repair</small>
      </label>
      <label>Check speed limit
        <input type="number" id="check-speed" value="200" min="10" max="1000" step="10"> MB/s
        <small>Lower values reduce I/O impact during a check (default 200 MB/s)</small>
      </label>
    </div>
    <div id="install-terminal" class="terminal" style="display:none"></div>
    <div class="actions">
      <button class="secondary" id="btn-back">← Back</button>
      <button id="btn-next">Next →</button>
    </div>
  `;

  document.getElementById('btn-back').addEventListener('click', () => navigate('#pool'));

  const installBtn = document.getElementById('btn-install');
  if (installBtn) {
    installBtn.addEventListener('click', () => {
      const terminal = document.getElementById('install-terminal');
      terminal.style.display = 'block';
      terminal.textContent = '';
      fetch('/api/nonraid/install', { method: 'POST' }).then(r => {
        const reader = r.body.getReader();
        const decode = new TextDecoder();
        const read = () => reader.read().then(({ done, value }) => {
          if (done) return;
          terminal.textContent += decode.decode(value);
          terminal.scrollTop = terminal.scrollHeight;
          read();
        });
        read();
      });
    });
  }

  document.getElementById('btn-next').addEventListener('click', async () => {
    const parityMode = document.getElementById('parity-mode').value;
    const filesystem = document.getElementById('filesystem').value;
    const r = await post('/api/nonraid/config', {
      parity_mode: parityMode,
      filesystem,
      turbo_write: document.getElementById('turbo-write').checked,
      luks: document.getElementById('luks').checked,
      check_schedule: document.getElementById('check-schedule').value,
      check_correct: document.getElementById('check-correct').value === 'correct',
      check_speed_limit: parseInt(document.getElementById('check-speed').value, 10),
    });
    if (r.ok) {
      _state.nonraid_parity_mode = parityMode;
      _state.nonraid_filesystem = filesystem;
      navigate('#nonraid-roles');
    }
  });
});

// ── Screen: NonRAID Role Assignment (5c) ─────────────────────────────────────

register('nonraid-roles', async () => {
  const drivesResp = await fetch('/api/drives');
  const drives = drivesResp.ok ? await drivesResp.json() : [];
  const parityMode = _state.nonraid_parity_mode || 'single';
  const parityCount = parityMode === 'dual' ? 2 : 1;

  const rows = drives.map(d => `
    <tr>
      <td><code>/dev/${d.name}</code></td>
      <td>${d.model || '—'}</td>
      <td>${(d.size / 1e9).toFixed(0)} GB</td>
      <td>
        <select id="role-${d.name}">
          <option value="skip">Skip (not in array)</option>
          <option value="parity">Parity</option>
          <option value="data">Data</option>
        </select>
      </td>
    </tr>
  `).join('');

  app().innerHTML = `
    <h1>FugginNAS</h1>
    <h2>Step 5c — Assign Drive Roles</h2>
    <p>Assign each drive a role in the NonRAID array.
       Parity mode is <strong>${parityMode}</strong> — you must assign exactly
       <strong>${parityCount}</strong> parity drive(s).</p>
    <table>
      <thead><tr><th>Drive</th><th>Model</th><th>Size</th><th>Role</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <div id="role-error" class="error" style="display:none"></div>
    <div class="actions">
      <button class="secondary" id="btn-back">← Back</button>
      <button id="btn-next">Next →</button>
    </div>
  `;

  document.getElementById('btn-back').addEventListener('click', () => navigate('#nonraid'));

  document.getElementById('btn-next').addEventListener('click', async () => {
    const errEl = document.getElementById('role-error');
    errEl.style.display = 'none';
    const parity = drives
      .filter(d => document.getElementById(`role-${d.name}`).value === 'parity')
      .map(d => `/dev/${d.name}`);
    const data = drives
      .filter(d => document.getElementById(`role-${d.name}`).value === 'data')
      .map(d => `/dev/${d.name}`);

    if (parity.length !== parityCount) {
      errEl.textContent = `Select exactly ${parityCount} parity drive(s) (you selected ${parity.length}).`;
      errEl.style.display = 'block';
      return;
    }
    if (data.length === 0) {
      errEl.textContent = 'Select at least one data drive.';
      errEl.style.display = 'block';
      return;
    }

    const r = await post('/api/nonraid/roles', { parity_disks: parity, data_disks: data });
    if (r.ok) {
      _state.nonraid_parity_disks = parity;
      _state.nonraid_data_disks = data;
      navigate('#nonraid-prep');
    }
  });
});

// ── Screen: NonRAID Disk Preparation (5d) ────────────────────────────────────

function _mkfsCmd(fs, partition) {
  if (fs === 'xfs')   return `mkfs.xfs -f ${partition}`;
  if (fs === 'btrfs') return `mkfs.btrfs -f ${partition}`;
  if (fs === 'ext4')  return `mkfs.ext4 -F ${partition}`;
  if (fs === 'zfs')   return `zpool create disk${partition.replace(/[^0-9]/g, '')} ${partition}`;
  return `mkfs.${fs} ${partition}`;
}

register('nonraid-prep', () => {
  const parityDisks = _state.nonraid_parity_disks || [];
  const dataDisks = _state.nonraid_data_disks || [];
  const fs = _state.nonraid_filesystem || 'xfs';

  const parityBlocks = parityDisks.map(dev => `
    <div class="prep-block">
      <strong>${dev} — Parity</strong>
      <pre># WARNING: erases all data on ${dev}
sgdisk --zap-all ${dev}
sgdisk -n 1:0:0 -t 1:fd00 ${dev}</pre>
    </div>
  `).join('');

  const dataBlocks = dataDisks.map(dev => `
    <div class="prep-block">
      <strong>${dev} — Data</strong>
      <pre># WARNING: erases all data on ${dev}
sgdisk --zap-all ${dev}
sgdisk -n 1:0:0 -t 1:8300 ${dev}
${_mkfsCmd(fs, dev + '1')}</pre>
    </div>
  `).join('');

  app().innerHTML = `
    <h1>FugginNAS</h1>
    <h2>Step 5d — Prepare Disks</h2>
    <div class="notice warning">
      <strong>These commands permanently erase all data on the listed drives.</strong>
      Run them in a terminal on the NAS host before clicking Proceed.
    </div>
    ${parityBlocks}
    ${dataBlocks}
    <div class="prep-block">
      <strong>Create the array (interactive)</strong>
      <pre>nmdctl create</pre>
      <small>nmdctl create is interactive — it will prompt you to confirm disk assignments in the terminal.</small>
    </div>
    <label style="margin-top:1rem;display:flex;gap:.5rem;align-items:center">
      <input type="checkbox" id="prep-done">
      I have run all commands above and the array was created successfully.
    </label>
    <div class="actions">
      <button class="secondary" id="btn-back">← Back</button>
      <button id="btn-next" disabled>Proceed →</button>
    </div>
  `;

  document.getElementById('btn-back').addEventListener('click', () => navigate('#nonraid-roles'));

  const checkbox = document.getElementById('prep-done');
  const nextBtn = document.getElementById('btn-next');
  checkbox.addEventListener('change', () => { nextBtn.disabled = !checkbox.checked; });
  nextBtn.addEventListener('click', () => navigate('#mover'));
});

// ── Screen: Mover Configuration ──────────────────────────────────────────────

register('mover', () => {
  const backTarget = _state.backend === 'mergerfs' ? '#pool'
    : _state.backend === 'nonraid' ? '#nonraid-prep'
    : '#snapraid';

  app().innerHTML = `
    <h1>FugginNAS</h1>
    <h2>Step 6 — Cache Mover</h2>
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

  document.getElementById('btn-back').addEventListener('click', () => navigate(backTarget));
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
      <label>
        <input type="checkbox" id="smb-guest" checked> SMB guest access
      </label>
    </div>
    <div class="actions">
      <button class="secondary" id="btn-back">← Back</button>
      <button id="btn-add">Add Share →</button>
      <button class="secondary" id="btn-skip">Skip →</button>
    </div>
  `;

  document.getElementById('btn-back').addEventListener('click', () => navigate('#mover'));
  document.getElementById('btn-skip').addEventListener('click', () => navigate('#summary'));
  document.getElementById('btn-add').addEventListener('click', async () => {
    const r = await post('/api/shares', {
      name: document.getElementById('share-name').value,
      path: document.getElementById('share-path').value,
      protocol: document.getElementById('share-protocol').value,
      smb_guest_ok: document.getElementById('smb-guest').checked,
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
    <div id="apply-terminal" class="terminal" style="display:none"></div>
    <div class="actions">
      <button class="secondary" id="btn-back">← Back</button>
      <button id="btn-apply">Apply Configuration</button>
    </div>
  `;

  document.getElementById('btn-back').addEventListener('click', () => navigate('#shares'));

  document.getElementById('btn-apply').addEventListener('click', () => {
    const terminal = document.getElementById('apply-terminal');
    terminal.style.display = 'block';
    terminal.textContent = '';
    document.getElementById('btn-apply').disabled = true;

    fetch('/api/apply', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
      .then(r => {
        const reader = r.body.getReader();
        const decode = new TextDecoder();
        let buf = '';
        const read = () => reader.read().then(({ done, value }) => {
          if (done) { setTimeout(() => navigate('#status'), 1500); return; }
          buf += decode.decode(value, { stream: true });
          const lines = buf.split('\n');
          buf = lines.pop();
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              terminal.textContent += line.slice(6) + '\n';
              terminal.scrollTop = terminal.scrollHeight;
            }
          }
          read();
        });
        read();
      });
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

  const snapraidPanel = data.backend === 'snapraid' && data.snapraid ? `
    <section class="panel">
      <h3>SnapRAID</h3>
      <table>
        <tr><th>Last sync</th><td>${data.snapraid.sync.last_run || '—'}</td></tr>
        <tr><th>Sync result</th><td>${data.snapraid.sync.result || '—'}</td></tr>
        <tr><th>Sync errors</th><td>${data.snapraid.sync.errors ?? '—'}</td></tr>
        <tr><th>Last scrub</th><td>${data.snapraid.scrub.last_run || '—'}</td></tr>
        <tr><th>Scrub result</th><td>${data.snapraid.scrub.result || '—'}</td></tr>
        <tr><th>Dirty files</th><td>${data.snapraid.dirty_files ?? '—'}</td></tr>
      </table>
      <div class="actions">
        <button id="btn-sync-now">Run Sync Now</button>
        <button id="btn-scrub-now">Run Scrub Now</button>
      </div>
    </section>
  ` : '';

  app().innerHTML = `
    <h1>FugginNAS</h1>
    <h2>Status Dashboard</h2>
    <section class="panel">
      <h3>Pool</h3>
      <table>
        <tr><th>Backend</th><td>${data.backend || '—'}</td></tr>
        <tr><th>Mount</th><td>${data.pool ? data.pool.mount : '—'}</td></tr>
        <tr><th>Mounted</th><td>${data.pool ? (data.pool.mounted ? '✓ Yes' : '✗ No') : '—'}</td></tr>
        <tr><th>Used</th><td>${data.pool ? (data.pool.used_pct || 0) + '%' : '—'}</td></tr>
        <tr><th>Available</th><td>${data.pool ? formatBytes(data.pool.available_bytes || 0) : '—'}</td></tr>
        <tr><th>Cache fill</th><td>${data.cache_fill_pct != null ? data.cache_fill_pct + '%' : '—'}</td></tr>
      </table>
    </section>
    ${snapraidPanel}
    <section class="panel">
      <h3>Shares (${(data.shares || []).length})</h3>
      <ul>${(data.shares || []).map(s => `<li>${s.name} — ${s.path} (${s.protocol})</li>`).join('') || '<li>None configured</li>'}</ul>
    </section>
    <div class="actions">
      <button id="btn-mover-now">Run Mover Now</button>
      <button class="secondary" id="btn-reconfigure">← Reconfigure</button>
    </div>
  `;

  document.getElementById('btn-reconfigure').addEventListener('click', () => navigate('#backend'));
  document.getElementById('btn-mover-now').addEventListener('click', () => post('/api/mover/run', {}));

  const syncBtn = document.getElementById('btn-sync-now');
  if (syncBtn) syncBtn.addEventListener('click', () => post('/api/snapraid/sync', {}));

  const scrubBtn = document.getElementById('btn-scrub-now');
  if (scrubBtn) scrubBtn.addEventListener('click', () => post('/api/snapraid/scrub', {}));
});

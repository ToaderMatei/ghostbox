/* GhostBox — Main Dashboard JS */

// ── WebSocket live feed ────────────────────────────────────────────────────
let ws = null;
let wsReconnectTimer = null;

function connectWS() {
  ws = new WebSocket(`ws://${location.host}/ws`);

  ws.onopen = () => {
    setWsStatus(true);
    clearInterval(wsReconnectTimer);
    // Send keep-alive ping every 20s
    setInterval(() => ws.readyState === 1 && ws.send('ping'), 20_000);
  };

  ws.onmessage = (e) => {
    try {
      const event = JSON.parse(e.data);
      prependEvent(event);
      updateStatCounters();
    } catch (_) {}
  };

  ws.onclose = () => {
    setWsStatus(false);
    wsReconnectTimer = setTimeout(connectWS, 3000);
  };

  ws.onerror = () => ws.close();
}

function setWsStatus(connected) {
  const dot = document.querySelector('.ws-dot');
  const label = document.querySelector('.ws-label');
  if (!dot) return;
  dot.classList.toggle('connected', connected);
  if (label) label.textContent = connected ? 'Live' : 'Reconnecting…';
}

// ── Event feed ────────────────────────────────────────────────────────────

const EVENT_ICONS = {
  usb: '🔌', wifi: '📡', bluetooth: '🔵', evil_twin: '👻', system: '⚙️',
};

function prependEvent(event) {
  const feed = document.getElementById('eventFeed');
  if (!feed) return;

  const time = new Date(event.timestamp).toLocaleTimeString();
  const icon = EVENT_ICONS[event.type] || '🔔';

  const item = document.createElement('div');
  item.className = `event-item ${event.severity}`;
  item.innerHTML = `
    <span class="event-icon">${icon}</span>
    <div class="event-body">
      <div class="event-title">${escHtml(event.title)}</div>
      <div class="event-detail">${escHtml(event.detail)}</div>
    </div>
    <div class="event-time">${time}</div>
  `;

  feed.insertBefore(item, feed.firstChild);

  // Keep max 50 items
  while (feed.children.length > 50) feed.removeChild(feed.lastChild);
}

// ── Stats ─────────────────────────────────────────────────────────────────

async function updateStatCounters() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();
    const map = {
      'stat-wifi':   data.wifi_networks,
      'stat-bt':     data.bt_devices,
      'stat-creds':  data.credentials,
      'stat-events': data.events,
      'stat-payloads': data.payloads,
    };
    for (const [id, val] of Object.entries(map)) {
      const el = document.getElementById(id);
      if (el) animateCounter(el, parseInt(el.textContent) || 0, val);
    }
  } catch (_) {}
}

function animateCounter(el, from, to) {
  if (from === to) return;
  const step = Math.sign(to - from);
  const timer = setInterval(() => {
    from += step;
    el.textContent = from;
    if (from === to) clearInterval(timer);
  }, 30);
}

// ── Module control ────────────────────────────────────────────────────────

async function moduleAction(module, action) {
  let body = {};
  if (module === 'evil_twin' && action === 'start') {
    body = {
      ssid:    document.getElementById('etSsid')?.value    || 'FreeWiFi',
      channel: parseInt(document.getElementById('etChannel')?.value || '6'),
    };
  }

  try {
    const res = await fetch(`/api/${module.replace('_','-')}/${action}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    showToast(data.ok ? 'success' : 'error',
              data.ok ? `${module} ${action}ed` : 'Action failed');
    await refreshModuleStatus();
  } catch (e) {
    showToast('error', `Request failed: ${e.message}`);
  }
}

async function refreshModuleStatus() {
  try {
    const res = await fetch('/api/modules');
    const modules = await res.json();
    for (const [name, info] of Object.entries(modules)) {
      const badge = document.querySelector(`[data-module="${name}"] .badge`);
      if (badge) {
        badge.className = `badge badge-${info.status}`;
        badge.textContent = info.status;
      }
    }
  } catch (_) {}
}

// ── USB Arsenal ───────────────────────────────────────────────────────────

async function injectPayload() {
  const script = document.getElementById('duckyScript')?.value?.trim();
  const name   = document.getElementById('payloadName')?.value?.trim() || 'manual';

  if (!script) { showToast('error', 'No script to inject'); return; }

  const logEl = document.getElementById('injectionLog');
  if (logEl) logEl.innerHTML = '<span class="output">Injecting...</span>';

  try {
    const res  = await fetch('/api/usb/inject', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ script, payload_name: name }),
    });
    const data = await res.json();
    if (logEl) {
      logEl.innerHTML = data.log
        .map(l => `<span class="output">▶ ${escHtml(l)}</span>`)
        .join('\n');
    }
    showToast('success', `Injected ${data.log.length} commands`);
  } catch (e) {
    showToast('error', e.message);
  }
}

async function savePayload() {
  const name    = document.getElementById('payloadName')?.value?.trim();
  const content = document.getElementById('duckyScript')?.value?.trim();
  const desc    = document.getElementById('payloadDesc')?.value?.trim() || '';

  if (!name || !content) { showToast('error', 'Name and script required'); return; }

  try {
    await fetch('/api/usb/payloads', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description: desc, content }),
    });
    showToast('success', `Payload '${name}' saved`);
    await loadPayloads();
  } catch (e) {
    showToast('error', e.message);
  }
}

async function loadPayloads() {
  try {
    const res  = await fetch('/api/usb/payloads');
    const list = await res.json();
    const el   = document.getElementById('payloadList');
    if (!el) return;
    el.innerHTML = list.map(p => `
      <div class="event-item info" style="cursor:pointer" onclick="loadPayload(${escHtml(JSON.stringify(p))})">
        <span class="event-icon">📜</span>
        <div class="event-body">
          <div class="event-title">${escHtml(p.name)}</div>
          <div class="event-detail">${escHtml(p.description || 'No description')}</div>
        </div>
      </div>
    `).join('');
  } catch (_) {}
}

function loadPayload(p) {
  const nameEl   = document.getElementById('payloadName');
  const scriptEl = document.getElementById('duckyScript');
  const descEl   = document.getElementById('payloadDesc');
  if (nameEl)   nameEl.value   = p.name;
  if (scriptEl) scriptEl.value = p.content;
  if (descEl)   descEl.value   = p.description || '';
}

// ── WiFi Scanner ─────────────────────────────────────────────────────────

async function loadWifiNetworks() {
  try {
    const res  = await fetch('/api/wifi/networks');
    const nets = await res.json();
    const body = document.getElementById('wifiTableBody');
    if (!body) return;

    body.innerHTML = nets.map(n => {
      const bars = signalBars(n.signal);
      const enc  = encBadge(n.encryption);
      return `<tr>
        <td>${escHtml(n.ssid)}</td>
        <td style="color:var(--muted)">${escHtml(n.bssid)}</td>
        <td>CH ${n.channel}</td>
        <td>${bars} ${n.signal} dBm</td>
        <td>${enc}</td>
        <td style="color:var(--muted)">${escHtml(n.vendor)}</td>
      </tr>`;
    }).join('');
  } catch (_) {}
}

function signalBars(dbm) {
  const pct = Math.min(100, Math.max(0, (dbm + 100) * 2));
  const on  = Math.round(pct / 25);
  return `<span class="signal-bar">
    ${[1,2,3,4].map(i => `<span class="${i<=on?'on':''}" style="height:${i*3+2}px"></span>`).join('')}
  </span>`;
}

function encBadge(enc) {
  const cls = { OPEN:'enc-open', WPA2:'enc-wpa2', WPA:'enc-wpa', WEP:'enc-wep' };
  return `<span class="enc ${cls[enc]||'enc-open'}">${enc}</span>`;
}

// ── Bluetooth ─────────────────────────────────────────────────────────────

async function loadBtDevices() {
  try {
    const res  = await fetch('/api/bluetooth/devices');
    const devs = await res.json();
    const body = document.getElementById('btTableBody');
    if (!body) return;

    body.innerHTML = devs.map(d => {
      const typeClass = d.device_type === 'ble' ? 'dev-ble' : 'dev-classic';
      return `<tr>
        <td style="color:var(--cyan)">${escHtml(d.name || 'Unknown')}</td>
        <td style="color:var(--muted)">${escHtml(d.address)}</td>
        <td><span class="dev-type ${typeClass}">${d.device_type.toUpperCase()}</span></td>
        <td>${d.rssi} dBm</td>
        <td style="color:var(--muted)">${escHtml(d.manufacturer)}</td>
        <td style="color:var(--muted)">${escHtml(d.device_class)}</td>
      </tr>`;
    }).join('');
  } catch (_) {}
}

// ── Evil Twin ─────────────────────────────────────────────────────────────

async function loadCredentials() {
  try {
    const res   = await fetch('/api/evil-twin/credentials');
    const creds = await res.json();
    const body  = document.getElementById('credsTableBody');
    if (!body) return;

    body.innerHTML = creds.map(c => `<tr>
      <td style="color:var(--red)">${escHtml(c.username)}</td>
      <td style="color:var(--orange)">${escHtml(c.password)}</td>
      <td style="color:var(--muted)">${escHtml(c.ip_address)}</td>
      <td style="color:var(--muted)">${escHtml(c.source)}</td>
      <td style="color:var(--muted)">${new Date(c.timestamp).toLocaleString()}</td>
    </tr>`).join('');
  } catch (_) {}
}

// ── Tabs ──────────────────────────────────────────────────────────────────

function switchTab(tabId, btn) {
  document.querySelectorAll('.tab-pane').forEach(p => p.style.display = 'none');
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  const pane = document.getElementById(tabId);
  if (pane) pane.style.display = 'block';
  if (btn)  btn.classList.add('active');
}

// ── Toast ─────────────────────────────────────────────────────────────────

function showToast(type, msg) {
  const icons = { success:'✅', error:'❌', info:'ℹ️' };
  const c = document.getElementById('toasts') || (() => {
    const el = document.createElement('div');
    el.id = 'toasts';
    el.className = 'toast-container';
    document.body.appendChild(el);
    return el;
  })();

  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.innerHTML = `<span>${icons[type]||'🔔'}</span><span>${escHtml(msg)}</span>`;
  c.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

// ── Utility ───────────────────────────────────────────────────────────────

function escHtml(str) {
  return String(str)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}

// ── Init ──────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  connectWS();
  updateStatCounters();
  setInterval(updateStatCounters, 10_000);

  // Active nav link
  const path = location.pathname;
  document.querySelectorAll('.nav-item[data-path]').forEach(el => {
    el.classList.toggle('active', el.dataset.path === path);
  });
});

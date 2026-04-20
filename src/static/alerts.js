const REFRESH_INTERVAL_MS = 15000;
let autoRefreshEnabled = true;
let refreshTimer = null;

const chartColors = {
  critical: "#f85149",
  high: "#fb8500",
  medium: "#fbbf24",
  low: "#26a641",
  info: "#58a6ff",
  textColor: "#e6edf3",
};

const getDom = () => ({
  refreshButton: document.getElementById("refreshButton"),
  autoRefreshButton: document.getElementById("autoRefreshButton"),
  lastTime: document.getElementById("lastTime"),
  statusMessage: document.getElementById("statusMessage"),
  alertsBody: document.getElementById("alertsBody"),
});

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatTime(value) {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "-";
  const now = new Date();
  const diff = now - parsed;
  const hour = 3600000;
  const min = 60000;
  if (diff < min) return "just now";
  if (diff < hour) return Math.floor(diff / min) + "m ago";
  if (diff < 24 * hour) return Math.floor(diff / hour) + "h ago";
  return parsed.toLocaleDateString();
}

function setStatus(message, isError = false) {
  const dom = getDom();
  if (!dom.statusMessage) return;
  dom.statusMessage.textContent = message;
  dom.statusMessage.style.color = isError ? "#f85149" : "#8b949e";
}

async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${path} returned ${response.status}`);
  return response.json();
}

function renderAlerts(alerts) {
  const dom = getDom();
  if (!dom.alertsBody) return;
  if (!alerts.length) {
    dom.alertsBody.innerHTML = '<tr><td colspan="5" class="empty">No alerts found</td></tr>';
    return;
  }
  dom.alertsBody.innerHTML = alerts.map((alert) => `
    <tr>
      <td><span class="severity-dot ${alert.severity || 'low'}"></span></td>
      <td>${escapeHtml(alert.rule_name || 'Detection')}</td>
      <td>${escapeHtml(formatTime(alert.created_at))}</td>
      <td>HOST-${escapeHtml(alert.entity.substring(0, 4).toUpperCase())}</td>
      <td><span class="status-${alert.status || 'open'}">${escapeHtml(alert.status || 'open')}</span></td>
    </tr>
  `).join("");
}

async function refreshPage() {
  const dom = getDom();
  if (!dom.refreshButton || !dom.lastTime) return;
  
  dom.refreshButton.disabled = true;
  dom.refreshButton.textContent = "🔄";

  try {
    const alerts = await fetchJson("/alerts");
    renderAlerts(alerts);
    const now = new Date();
    dom.lastTime.textContent = now.toLocaleTimeString();
    setStatus("Alerts loaded successfully.");
  } catch (error) {
    setStatus(`Error: ${error.message}`, true);
  } finally {
    dom.refreshButton.disabled = false;
  }
}

function toggleAutoRefresh() {
  const dom = getDom();
  autoRefreshEnabled = !autoRefreshEnabled;
  if (dom.autoRefreshButton) {
    dom.autoRefreshButton.textContent = autoRefreshEnabled ? "⏱️ ON" : "⏱️ OFF";
  }
  setStatus(autoRefreshEnabled ? "Auto refresh enabled" : "Auto refresh disabled");
}

function startAutoRefresh() {
  if (refreshTimer !== null) clearInterval(refreshTimer);
  refreshTimer = setInterval(() => {
    if (autoRefreshEnabled) refreshPage();
  }, REFRESH_INTERVAL_MS);
}

const dom = getDom();
if (dom.refreshButton) dom.refreshButton.addEventListener("click", refreshPage);
if (dom.autoRefreshButton) dom.autoRefreshButton.addEventListener("click", toggleAutoRefresh);

startAutoRefresh();
refreshPage();

const REFRESH_INTERVAL_MS = 15000;
let autoRefreshEnabled = true;
let refreshTimer = null;

const getDom = () => ({
  refreshButton: document.getElementById("refreshButton"),
  autoRefreshButton: document.getElementById("autoRefreshButton"),
  lastTime: document.getElementById("lastTime"),
  statusMessage: document.getElementById("statusMessage"),
  iocsBody: document.getElementById("iocsBody"),
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

function renderIOCs(iocs) {
  const dom = getDom();
  if (!dom.iocsBody) return;
  if (!iocs.length) {
    dom.iocsBody.innerHTML = '<tr><td colspan="5" class="empty">No IOCs found</td></tr>';
    return;
  }
  dom.iocsBody.innerHTML = iocs.map((ioc) => `
    <tr>
      <td>${escapeHtml(formatTime(ioc.created_at))}</td>
      <td><span style="background: rgba(88, 166, 255, 0.2); padding: 2px 8px; border-radius: 4px; font-size: 11px; color: #58a6ff;">${escapeHtml(ioc.ioc_type)}</span></td>
      <td style="font-family: 'IBM Plex Mono'; font-size: 12px; word-break: break-all;">${escapeHtml(ioc.value)}</td>
      <td><span style="background: rgba(38, 166, 65, 0.2); padding: 2px 8px; border-radius: 4px; color: #26a641; font-size: 11px;">${ioc.confidence}%</span></td>
      <td style="text-align: center; color: #8b949e;">-</td>
    </tr>
  `).join("");
}

async function refreshPage() {
  const dom = getDom();
  if (!dom.refreshButton || !dom.lastTime) return;
  
  dom.refreshButton.disabled = true;
  dom.refreshButton.textContent = "🔄";

  try {
    const iocs = await fetchJson("/iocs");
    renderIOCs(iocs);
    const now = new Date();
    dom.lastTime.textContent = now.toLocaleTimeString();
    setStatus("IOCs loaded successfully.");
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

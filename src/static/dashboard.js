const REFRESH_INTERVAL_MS = 15000;
const MAX_ROWS = 8;

let autoRefreshEnabled = true;
let charts = {};
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
  metricNewDetections: document.getElementById("metricNewDetections"),
  metricPreventedAttacks: document.getElementById("metricPreventedAttacks"),
  metricHuntingLeads: document.getElementById("metricHuntingLeads"),
  metricHuntingLeadsInv: document.getElementById("metricHuntingLeadsInv"),
  metricRemediatedDetections: document.getElementById("metricRemediatedDetections"),
  metricCrowdScore: document.getElementById("metricCrowdScore"),
  alertsBody: document.getElementById("alertsBody"),
  eventsBody: document.getElementById("eventsBody"),
  responsesBody: document.getElementById("responsesBody"),
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

function numberWithCommas(value) {
  return Number(value || 0).toLocaleString();
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

function updateKPIs(summary) {
  const dom = getDom();
  if (dom.metricNewDetections) dom.metricNewDetections.textContent = numberWithCommas(summary.total_alerts);
  if (dom.metricPreventedAttacks) dom.metricPreventedAttacks.textContent = numberWithCommas(summary.queued_responses || 0);
  if (dom.metricHuntingLeads) dom.metricHuntingLeads.textContent = numberWithCommas(summary.total_events);
  if (dom.metricHuntingLeadsInv) dom.metricHuntingLeadsInv.textContent = numberWithCommas(summary.investigating_alerts || 0);
  if (dom.metricRemediatedDetections) dom.metricRemediatedDetections.textContent = numberWithCommas(summary.resolved_alerts || 0);
  if (dom.metricCrowdScore) dom.metricCrowdScore.textContent = Math.floor(50 + Math.random() * 50);
}

function createSeverityChart(summary) {
  const ctx = document.getElementById("severityChart");
  if (!ctx) return;
  
  const data = summary.alerts_by_severity || {};
  if (charts.severity) charts.severity.destroy();
  
  charts.severity = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: Object.keys(data),
      datasets: [{
        data: Object.values(data),
        backgroundColor: [chartColors.critical, chartColors.high, chartColors.medium, chartColors.low],
        borderColor: "#1c2128",
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          position: "bottom",
          labels: { color: chartColors.textColor, font: { size: 12 }, padding: 12 },
        },
      },
    },
  });
}

function createSourceChart(summary) {
  const ctx = document.getElementById("sourceChart");
  if (!ctx) return;
  
  const data = summary.events_by_source || {};
  const labels = Object.keys(data).slice(0, 5);
  const values = Object.values(data).slice(0, 5);
  
  if (charts.source) charts.source.destroy();
  
  charts.source = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        label: "Events",
        data: values,
        backgroundColor: chartColors.info,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      indexAxis: "y",
      plugins: { legend: { labels: { color: chartColors.textColor } } },
      scales: {
        x: { ticks: { color: chartColors.textColor }, grid: { color: "rgba(48, 54, 61, 0.3)" } },
        y: { ticks: { color: chartColors.textColor }, grid: { display: false } },
      },
    },
  });
}

function createDetectionChart(summary) {
  const ctx = document.getElementById("detectionChart");
  if (!ctx) return;
  
  if (charts.detection) charts.detection.destroy();
  
  const labels = Array.from({ length: 24 }, (_, i) => i + ":00");
  const data = Array.from({ length: 24 }, () => Math.floor(Math.random() * 100));
  
  charts.detection = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: "Detections",
        data: data,
        borderColor: chartColors.info,
        backgroundColor: "rgba(88, 166, 255, 0.1)",
        tension: 0.4,
        fill: true,
        pointRadius: 3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: { legend: { labels: { color: chartColors.textColor } } },
      scales: {
        x: { ticks: { color: chartColors.textColor }, grid: { color: "rgba(48, 54, 61, 0.3)" } },
        y: { ticks: { color: chartColors.textColor }, grid: { color: "rgba(48, 54, 61, 0.3)" } },
      },
    },
  });
}

function createStatusChart(summary) {
  const ctx = document.getElementById("statusChart");
  if (!ctx) return;
  
  if (charts.status) charts.status.destroy();
  
  const statuses = {
    open: summary.open_alerts || 0,
    investigating: summary.investigating_alerts || 0,
    resolved: summary.resolved_alerts || 0,
    false_positive: summary.false_positive_alerts || 0,
  };
  
  charts.status = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: Object.keys(statuses),
      datasets: [{
        data: Object.values(statuses),
        backgroundColor: [chartColors.critical, chartColors.medium, chartColors.low, chartColors.info],
        borderColor: "#1c2128",
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          position: "bottom",
          labels: { color: chartColors.textColor, font: { size: 12 }, padding: 12 },
        },
      },
    },
  });
}

function renderAlerts(alerts) {
  const dom = getDom();
  if (!dom.alertsBody) return;
  if (!alerts.length) {
    dom.alertsBody.innerHTML = '<tr><td colspan="5" class="empty">No alerts</td></tr>';
    return;
  }
  dom.alertsBody.innerHTML = alerts.slice(0, MAX_ROWS).map((alert) => `
    <tr>
      <td><span class="severity-dot ${alert.severity || 'low'}"></span></td>
      <td>Detection</td>
      <td>${escapeHtml(formatTime(alert.created_at))}</td>
      <td>HOST-${escapeHtml(alert.entity.substring(0, 4).toUpperCase())}</td>
      <td><a href="#" style="color: #58a6ff;">View</a></td>
    </tr>
  `).join("");
}

function renderEvents(events) {
  const dom = getDom();
  if (!dom.eventsBody) return;
  if (!events.length) {
    dom.eventsBody.innerHTML = '<tr><td colspan="5" class="empty">No events</td></tr>';
    return;
  }
  dom.eventsBody.innerHTML = events.slice(0, MAX_ROWS).map((event) => `
    <tr>
      <td>${escapeHtml(formatTime(event.timestamp))}</td>
      <td>${escapeHtml(event.source)}</td>
      <td>${escapeHtml(event.host)}</td>
      <td>${escapeHtml(event.event_type)}</td>
      <td class="severity-${event.severity || 'low'}">${escapeHtml(event.severity)}</td>
    </tr>
  `).join("");
}

function renderResponses(responses) {
  const dom = getDom();
  if (!dom.responsesBody) return;
  if (!responses.length) {
    dom.responsesBody.innerHTML = '<tr><td colspan="5" class="empty">No actions</td></tr>';
    return;
  }
  dom.responsesBody.innerHTML = responses.slice(0, MAX_ROWS).map((response) => `
    <tr>
      <td>${escapeHtml(formatTime(response.requested_at))}</td>
      <td>${escapeHtml(response.action_type)}</td>
      <td class="status-${response.status || 'queued'}">${escapeHtml(response.status)}</td>
      <td>${response.alert_id}</td>
      <td>${escapeHtml(response.notes || "-")}</td>
    </tr>
  `).join("");
}

function renderIOCs(iocs) {
  const dom = getDom();
  if (!dom.iocsBody) return;
  if (!iocs.length) {
    dom.iocsBody.innerHTML = '<tr><td colspan="4" class="empty">No IOCs</td></tr>';
    return;
  }
  dom.iocsBody.innerHTML = iocs.slice(0, MAX_ROWS).map((ioc) => `
    <tr>
      <td>${escapeHtml(formatTime(ioc.created_at))}</td>
      <td>${escapeHtml(ioc.ioc_type)}</td>
      <td>${escapeHtml(ioc.value)}</td>
      <td>${ioc.confidence}%</td>
    </tr>
  `).join("");
}

async function refreshDashboard() {
  const dom = getDom();
  if (!dom.refreshButton || !dom.lastTime) return;
  
  dom.refreshButton.disabled = true;
  dom.refreshButton.textContent = "🔄";

  try {
    const [summary, alerts, events, responses, iocs] = await Promise.all([
      fetchJson("/dashboard/summary"),
      fetchJson("/alerts"),
      fetchJson("/events?limit=120"),
      fetchJson("/responses"),
      fetchJson("/iocs"),
    ]);

    updateKPIs(summary);
    createSeverityChart(summary);
    createSourceChart(summary);
    createDetectionChart(summary);
    createStatusChart(summary);
    renderAlerts(alerts);
    renderEvents(events);
    renderResponses(responses);
    renderIOCs(iocs);

    const now = new Date();
    dom.lastTime.textContent = now.toLocaleTimeString();
    setStatus("Dashboard synced successfully.");
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
    if (autoRefreshEnabled) refreshDashboard();
  }, REFRESH_INTERVAL_MS);
}

function init() {
  const dom = getDom();
  if (dom.refreshButton) dom.refreshButton.addEventListener("click", refreshDashboard);
  if (dom.autoRefreshButton) dom.autoRefreshButton.addEventListener("click", toggleAutoRefresh);
  startAutoRefresh();
  refreshDashboard();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

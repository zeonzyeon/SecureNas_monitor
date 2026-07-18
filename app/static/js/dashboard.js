const eventLabels = {
  created: "생성",
  modified: "수정",
  deleted: "삭제",
  moved: "이동",
};

const elements = {
  apiState: document.querySelector("#apiState"),
  databasePath: document.querySelector("#databasePath"),
  deletedEvents: document.querySelector("#deletedEvents"),
  emptyState: document.querySelector("#emptyState"),
  eventsTable: document.querySelector("#eventsTable"),
  limitSelect: document.querySelector("#limitSelect"),
  modifiedEvents: document.querySelector("#modifiedEvents"),
  monitorConfigured: document.querySelector("#monitorConfigured"),
  monitorDot: document.querySelector("#monitorDot"),
  monitorPathState: document.querySelector("#monitorPathState"),
  monitorState: document.querySelector("#monitorState"),
  movedEvents: document.querySelector("#movedEvents"),
  refreshButton: document.querySelector("#refreshButton"),
  totalEvents: document.querySelector("#totalEvents"),
};

function formatDate(value) {
  if (!value) {
    return "-";
  }

  const normalized = value.includes("T") ? value : value.replace(" ", "T");
  const date = new Date(normalized);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "short",
    timeStyle: "medium",
  }).format(date);
}

function updateSummary(events) {
  elements.totalEvents.textContent = events.length;
  elements.modifiedEvents.textContent = events.filter((event) => event.event_type === "modified").length;
  elements.deletedEvents.textContent = events.filter((event) => event.event_type === "deleted").length;
  elements.movedEvents.textContent = events.filter((event) => event.event_type === "moved").length;
}

function renderEvents(events) {
  elements.eventsTable.innerHTML = events
    .map((event) => {
      const label = eventLabels[event.event_type] || event.event_type;
      return `
        <tr>
          <td><span class="badge ${event.event_type}">${label}</span></td>
          <td>${event.file_name || "-"}</td>
          <td>${event.file_path || "-"}</td>
          <td>${formatDate(event.created_at)}</td>
        </tr>
      `;
    })
    .join("");

  elements.emptyState.classList.toggle("visible", events.length === 0);
}

async function loadHealth() {
  const response = await fetch("/health");
  const health = await response.json();

  elements.apiState.textContent = health.status === "ok" ? "정상" : "점검 필요";
  elements.databasePath.textContent = health.database;
  elements.monitorConfigured.textContent = health.monitor_path_configured ? "설정됨" : "미설정";
  elements.monitorState.textContent = health.monitor_path_configured ? "감시 준비됨" : "감시 비활성";
  elements.monitorPathState.textContent = health.monitor_path_configured
    ? "NAS_MONITOR_PATH 설정 완료"
    : "NAS_MONITOR_PATH 미설정";
  elements.monitorDot.classList.toggle("ok", health.monitor_path_configured);
}

async function loadEvents() {
  const limit = elements.limitSelect.value;
  const response = await fetch(`/api/events?limit=${limit}`);
  const events = await response.json();

  updateSummary(events);
  renderEvents(events);
}

async function refreshDashboard() {
  elements.refreshButton.disabled = true;

  try {
    await Promise.all([loadHealth(), loadEvents()]);
  } catch (error) {
    elements.apiState.textContent = "연결 실패";
    elements.monitorState.textContent = "확인 실패";
    console.error(error);
  } finally {
    elements.refreshButton.disabled = false;
  }
}

elements.refreshButton.addEventListener("click", refreshDashboard);
elements.limitSelect.addEventListener("change", loadEvents);

refreshDashboard();
setInterval(refreshDashboard, 10000);

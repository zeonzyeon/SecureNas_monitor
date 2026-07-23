const eventLabels = {
  created: "생성",
  deleted: "삭제",
};

const roleLabels = {
  admin: "관리자",
  user: "사용자",
  viewer: "열람자",
};

const securityEventLabels = {
  login_success: "로그인 성공",
  login_failure: "로그인 실패",
  blocked_attempt: "차단 시도",
  ip_blocked: "자동 차단",
  manual_ip_blocked: "수동 차단",
  ip_unblocked: "차단 해제",
  login_attempt: "로그인",
};

const elements = {
  apiState: document.querySelector("#apiState"),
  blockedIps: document.querySelector("#blockedIps"),
  createdEvents: document.querySelector("#createdEvents"),
  databasePath: document.querySelector("#databasePath"),
  deletedEvents: document.querySelector("#deletedEvents"),
  emptyState: document.querySelector("#emptyState"),
  eventsTable: document.querySelector("#eventsTable"),
  ipBlocksEmptyState: document.querySelector("#ipBlocksEmptyState"),
  ipBlocksTable: document.querySelector("#ipBlocksTable"),
  ipBlockSaveState: document.querySelector("#ipBlockSaveState"),
  limitSelect: document.querySelector("#limitSelect"),
  manualBlockForm: document.querySelector("#manualBlockForm"),
  manualBlockIp: document.querySelector("#manualBlockIp"),
  manualBlockMinutes: document.querySelector("#manualBlockMinutes"),
  monitorConfigured: document.querySelector("#monitorConfigured"),
  monitorDot: document.querySelector("#monitorDot"),
  monitorPathState: document.querySelector("#monitorPathState"),
  monitorState: document.querySelector("#monitorState"),
  nasMonitorPath: document.querySelector("#nasMonitorPath"),
  pendingUsers: document.querySelector("#pendingUsers"),
  refreshButton: document.querySelector("#refreshButton"),
  securityLimitSelect: document.querySelector("#securityLimitSelect"),
  securityLogsEmptyState: document.querySelector("#securityLogsEmptyState"),
  securityLogsTable: document.querySelector("#securityLogsTable"),
  totalEvents: document.querySelector("#totalEvents"),
  userSaveState: document.querySelector("#userSaveState"),
  usersEmptyState: document.querySelector("#usersEmptyState"),
  usersTable: document.querySelector("#usersTable"),
};

let isRefreshing = false;
const pageMode = document.body.dataset.page || "dashboard";

function setText(element, value) {
  if (element) {
    element.textContent = value;
  }
}

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

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function getFileKind(event) {
  if (event.is_directory) {
    return { label: "폴더", className: "folder" };
  }

  const fileName = String(event.file_name || "").toLowerCase();
  const extension = fileName.includes(".") ? fileName.split(".").pop() : "";

  if (["jpg", "jpeg", "png", "gif", "bmp", "webp", "svg"].includes(extension)) {
    return { label: "이미지", className: "image" };
  }

  if (["txt", "md", "log", "csv"].includes(extension)) {
    return { label: "텍스트", className: "text" };
  }

  if (extension === "pdf") {
    return { label: "PDF", className: "pdf" };
  }

  if (["doc", "docx", "hwp", "hwpx"].includes(extension)) {
    return { label: "문서", className: "document" };
  }

  if (["xls", "xlsx"].includes(extension)) {
    return { label: "시트", className: "sheet" };
  }

  if (["mp4", "mov", "avi", "mkv", "mp3", "wav", "flac"].includes(extension)) {
    return { label: "미디어", className: "media" };
  }

  return { label: "파일", className: "file" };
}

function updateSummary(events, users, ipBlocks) {
  setText(elements.totalEvents, events.length);
  setText(elements.createdEvents, events.filter((event) => event.event_type === "created").length);
  setText(elements.deletedEvents, events.filter((event) => event.event_type === "deleted").length);
  setText(elements.pendingUsers, users.filter((user) => !user.is_active).length);
  setText(elements.blockedIps, ipBlocks.filter((block) => block.is_blocked).length);
}

function renderEvents(events) {
  if (!elements.eventsTable) {
    return;
  }

  elements.eventsTable.innerHTML = events
    .map((event) => {
      const label = eventLabels[event.event_type] || event.event_type;
      const kind = getFileKind(event);
      const fileName = escapeHtml(event.file_name || "-");
      const filePath = escapeHtml(event.file_path || "-");
      return `
        <tr>
          <td><span class="badge ${event.event_type}">${label}</span></td>
          <td>
            <span class="file-cell">
              <span class="kind-badge ${kind.className}">${kind.label}</span>
              <span class="truncate" title="${fileName}">${fileName}</span>
            </span>
          </td>
          <td><span class="truncate" title="${filePath}">${filePath}</span></td>
          <td>${formatDate(event.created_at)}</td>
        </tr>
      `;
    })
    .join("");

  elements.emptyState?.classList.toggle("visible", events.length === 0);
}

function renderUsers(users) {
  if (!elements.usersTable) {
    return;
  }

  const visibleUsers = pageMode === "dashboard" ? users.slice(0, Number(document.body.dataset.userLimit || 10)) : users;

  elements.usersTable.innerHTML = visibleUsers
    .map((user) => {
      const statusLabel = user.is_active ? "활성" : "승인 대기";
      const statusClass = user.is_active ? "active" : "pending";
      return `
        <tr>
          <td><strong>${escapeHtml(user.username)}</strong></td>
          <td>
            <select class="role-select" data-user-id="${user.id}" aria-label="${escapeHtml(user.username)} 역할">
              ${Object.entries(roleLabels)
                .map(([value, label]) => `<option value="${value}" ${user.role === value ? "selected" : ""}>${label}</option>`)
                .join("")}
            </select>
          </td>
          <td><span class="badge ${statusClass}">${statusLabel}</span></td>
          <td>${formatDate(user.created_at)}</td>
          <td>
            <div class="row-actions">
              ${
                user.is_active
                  ? `<button class="small-button danger" type="button" data-action="deactivate" data-user-id="${user.id}">비활성</button>`
                  : `<button class="small-button" type="button" data-action="approve" data-user-id="${user.id}">승인</button>`
              }
            </div>
          </td>
        </tr>
      `;
    })
    .join("");

  elements.usersEmptyState?.classList.toggle("visible", visibleUsers.length === 0);
}

function renderIpBlocks(blocks) {
  if (!elements.ipBlocksTable) {
    return;
  }

  elements.ipBlocksTable.innerHTML = blocks
    .map((block) => {
      const statusClass = block.is_blocked ? "blocked" : "pending";
      const statusLabel = block.is_blocked ? "차단" : "관찰";
      return `
        <tr>
          <td>
            <span class="file-cell">
              <span class="badge ${statusClass}">${statusLabel}</span>
              <strong class="truncate" title="${escapeHtml(block.ip_address)}">${escapeHtml(block.ip_address)}</strong>
            </span>
          </td>
          <td>${block.failed_attempts || 0}</td>
          <td>${formatDate(block.last_failed_at)}</td>
          <td>${formatDate(block.blocked_at)}</td>
          <td>${formatDate(block.blocked_until)}</td>
          <td>
            ${
              block.is_blocked
                ? `<button class="small-button danger" type="button" data-action="unblock-ip" data-ip="${escapeHtml(block.ip_address)}">해제</button>`
                : "-"
            }
          </td>
        </tr>
      `;
    })
    .join("");

  elements.ipBlocksEmptyState?.classList.toggle("visible", blocks.length === 0);
}

function renderSecurityLogs(logs) {
  if (!elements.securityLogsTable) {
    return;
  }

  elements.securityLogsTable.innerHTML = logs
    .map((log) => {
      const eventType = log.event_type || "login_attempt";
      const label = securityEventLabels[eventType] || eventType;
      return `
        <tr>
          <td><span class="badge ${escapeHtml(eventType)}">${escapeHtml(label)}</span></td>
          <td><span class="truncate" title="${escapeHtml(log.username || "-")}">${escapeHtml(log.username || "-")}</span></td>
          <td><span class="truncate" title="${escapeHtml(log.ip_address || "-")}">${escapeHtml(log.ip_address || "-")}</span></td>
          <td><span class="truncate" title="${escapeHtml(log.message || "-")}">${escapeHtml(log.message || "-")}</span></td>
          <td>${formatDate(log.created_at)}</td>
        </tr>
      `;
    })
    .join("");

  elements.securityLogsEmptyState?.classList.toggle("visible", logs.length === 0);
}

async function updateUser(userId, payload) {
  setText(elements.userSaveState, "저장 중");

  const response = await fetch(`/api/users/${userId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.error || "사용자 정보를 저장하지 못했습니다.");
  }

  setText(elements.userSaveState, "저장됨");
  await loadUsers();
}

async function loadHealth() {
  const response = await fetch("/health");
  const health = await response.json();

  setText(elements.apiState, health.status === "ok" ? "정상" : "확인 필요");
  setText(elements.databasePath, health.database);
  setText(elements.nasMonitorPath, health.nas_monitor_path || "미설정");
  setText(elements.monitorConfigured, health.monitor_path_configured ? "설정됨" : "미설정");
  setText(elements.monitorState, health.monitor_path_configured ? "감시 준비됨" : "감시 비활성");
  setText(
    elements.monitorPathState,
    health.monitor_path_configured ? "NAS_MONITOR_PATH 설정 완료" : "NAS_MONITOR_PATH 미설정",
  );
  elements.monitorDot?.classList.toggle("ok", health.monitor_path_configured);
}

async function loadEvents(options = {}) {
  const limit = options.limit || elements.limitSelect?.value || document.body.dataset.eventLimit || "10";
  const response = await fetch(`/api/events?limit=${limit}`);
  const events = await response.json();

  if (options.render !== false) {
    renderEvents(events);
  }

  return events;
}

async function loadUsers() {
  const response = await fetch("/api/users");
  const users = await response.json();

  renderUsers(users);
  return users;
}

async function loadIpBlocks() {
  const response = await fetch("/api/ip-blocks");
  const blocks = await response.json();

  renderIpBlocks(blocks);
  return blocks;
}

async function loadSecurityLogs() {
  const limit = elements.securityLimitSelect?.value || document.body.dataset.securityLimit || "10";
  const response = await fetch(`/api/security-logs?limit=${limit}`);
  const logs = await response.json();

  renderSecurityLogs(logs);
  return logs;
}

async function blockIp(ipAddress, minutes) {
  setText(elements.ipBlockSaveState, "차단 중");

  const response = await fetch("/api/ip-blocks", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ ip_address: ipAddress, minutes }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.error || "IP를 차단하지 못했습니다.");
  }

  setText(elements.ipBlockSaveState, "차단됨");
}

async function unblockIp(ipAddress) {
  setText(elements.ipBlockSaveState, "해제 중");

  const response = await fetch(`/api/ip-blocks/${encodeURIComponent(ipAddress)}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.error || "IP 차단을 해제하지 못했습니다.");
  }

  setText(elements.ipBlockSaveState, "해제됨");
}

async function refreshDashboard() {
  if (isRefreshing) {
    return;
  }

  isRefreshing = true;
  if (elements.refreshButton) {
    elements.refreshButton.disabled = true;
  }

  try {
    if (pageMode === "users") {
      await loadUsers();
    } else if (pageMode === "blocked-ips") {
      await loadIpBlocks();
    } else if (pageMode === "file-events") {
      await loadEvents();
    } else if (pageMode === "security-logs") {
      await loadSecurityLogs();
    } else {
      const [events, eventSummary, users, ipBlocks] = await Promise.all([
        loadEvents(),
        loadEvents({ limit: 500, render: false }),
        loadUsers(),
        loadIpBlocks(),
        loadSecurityLogs(),
        loadHealth(),
      ]);
      updateSummary(eventSummary, users, ipBlocks);
    }
  } catch (error) {
    setText(elements.apiState, "연결 실패");
    setText(elements.monitorState, "확인 실패");
    setText(elements.userSaveState, error.message);
    console.error(error);
  } finally {
    if (elements.refreshButton) {
      elements.refreshButton.disabled = false;
    }
    isRefreshing = false;
  }
}

elements.refreshButton?.addEventListener("click", refreshDashboard);
elements.limitSelect?.addEventListener("change", async () => {
  const [events, users, ipBlocks] = await Promise.all([loadEvents(), loadUsers(), loadIpBlocks()]);
  updateSummary(events, users, ipBlocks);
});

elements.securityLimitSelect?.addEventListener("change", loadSecurityLogs);

elements.manualBlockForm?.addEventListener("submit", async (event) => {
  event.preventDefault();

  try {
    await blockIp(elements.manualBlockIp.value.trim(), elements.manualBlockMinutes.value);
    elements.manualBlockIp.value = "";
    const [events, users, ipBlocks] = await Promise.all([loadEvents(), loadUsers(), loadIpBlocks(), loadSecurityLogs()]);
    updateSummary(events, users, ipBlocks);
  } catch (error) {
    setText(elements.ipBlockSaveState, error.message);
  }
});

elements.ipBlocksTable?.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action='unblock-ip']");
  if (!button) {
    return;
  }

  try {
    await unblockIp(button.dataset.ip);
    const [events, users, ipBlocks] = await Promise.all([loadEvents(), loadUsers(), loadIpBlocks(), loadSecurityLogs()]);
    updateSummary(events, users, ipBlocks);
  } catch (error) {
    setText(elements.ipBlockSaveState, error.message);
  }
});

elements.usersTable?.addEventListener("change", async (event) => {
  if (!event.target.matches(".role-select")) {
    return;
  }

  try {
    await updateUser(event.target.dataset.userId, { role: event.target.value });
  } catch (error) {
    setText(elements.userSaveState, error.message);
    await loadUsers();
  }
});

elements.usersTable?.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) {
    return;
  }

  const payload =
    button.dataset.action === "approve"
      ? { is_active: true, role: "user" }
      : { is_active: false };

  try {
    await updateUser(button.dataset.userId, payload);
  } catch (error) {
    setText(elements.userSaveState, error.message);
  }
});

refreshDashboard();
if (pageMode === "dashboard") {
  setInterval(refreshDashboard, 5000);
}

const eventLabels = {
  created: "생성",
  deleted: "삭제",
};

const roleLabels = {
  admin: "관리자",
  user: "사용자",
  viewer: "열람자",
};

const elements = {
  apiState: document.querySelector("#apiState"),
  createdEvents: document.querySelector("#createdEvents"),
  databasePath: document.querySelector("#databasePath"),
  deletedEvents: document.querySelector("#deletedEvents"),
  emptyState: document.querySelector("#emptyState"),
  eventsTable: document.querySelector("#eventsTable"),
  limitSelect: document.querySelector("#limitSelect"),
  monitorConfigured: document.querySelector("#monitorConfigured"),
  monitorDot: document.querySelector("#monitorDot"),
  monitorPathState: document.querySelector("#monitorPathState"),
  monitorState: document.querySelector("#monitorState"),
  pendingUsers: document.querySelector("#pendingUsers"),
  refreshButton: document.querySelector("#refreshButton"),
  totalEvents: document.querySelector("#totalEvents"),
  userSaveState: document.querySelector("#userSaveState"),
  usersEmptyState: document.querySelector("#usersEmptyState"),
  usersTable: document.querySelector("#usersTable"),
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

function updateSummary(events, users) {
  elements.totalEvents.textContent = events.length;
  elements.createdEvents.textContent = events.filter((event) => event.event_type === "created").length;
  elements.deletedEvents.textContent = events.filter((event) => event.event_type === "deleted").length;
  elements.pendingUsers.textContent = users.filter((user) => !user.is_active).length;
}

function renderEvents(events) {
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

  elements.emptyState.classList.toggle("visible", events.length === 0);
}

function renderUsers(users) {
  elements.usersTable.innerHTML = users
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

  elements.usersEmptyState.classList.toggle("visible", users.length === 0);
}

async function updateUser(userId, payload) {
  elements.userSaveState.textContent = "저장 중";

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

  elements.userSaveState.textContent = "저장됨";
  await loadUsers();
}

async function loadHealth() {
  const response = await fetch("/health");
  const health = await response.json();

  elements.apiState.textContent = health.status === "ok" ? "정상" : "확인 필요";
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

  renderEvents(events);
  return events;
}

async function loadUsers() {
  const response = await fetch("/api/users");
  const users = await response.json();

  renderUsers(users);
  return users;
}

async function refreshDashboard() {
  elements.refreshButton.disabled = true;

  try {
    const [events, users] = await Promise.all([loadEvents(), loadUsers(), loadHealth()]);
    updateSummary(events, users);
  } catch (error) {
    elements.apiState.textContent = "연결 실패";
    elements.monitorState.textContent = "확인 실패";
    elements.userSaveState.textContent = error.message;
    console.error(error);
  } finally {
    elements.refreshButton.disabled = false;
  }
}

elements.refreshButton.addEventListener("click", refreshDashboard);
elements.limitSelect.addEventListener("change", async () => {
  const [events, users] = await Promise.all([loadEvents(), loadUsers()]);
  updateSummary(events, users);
});

elements.usersTable.addEventListener("change", async (event) => {
  if (!event.target.matches(".role-select")) {
    return;
  }

  try {
    await updateUser(event.target.dataset.userId, { role: event.target.value });
  } catch (error) {
    elements.userSaveState.textContent = error.message;
    await loadUsers();
  }
});

elements.usersTable.addEventListener("click", async (event) => {
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
    elements.userSaveState.textContent = error.message;
  }
});

refreshDashboard();
setInterval(refreshDashboard, 10000);

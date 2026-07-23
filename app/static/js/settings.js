const elements = {
  allowMappedDriveInput: document.querySelector("#allowMappedDriveInput"),
  databasePath: document.querySelector("#databasePath"),
  nasPathInput: document.querySelector("#nasPathInput"),
  runtimeNasPath: document.querySelector("#runtimeNasPath"),
  savedAllowMappedDrive: document.querySelector("#savedAllowMappedDrive"),
  savedNasPath: document.querySelector("#savedNasPath"),
  settingsForm: document.querySelector("#settingsForm"),
  settingsSaveState: document.querySelector("#settingsSaveState"),
};

function displayValue(value) {
  return value || "미설정";
}

function displayBoolean(value) {
  return value ? "허용" : "차단";
}

async function loadSettings() {
  const response = await fetch("/api/settings");

  if (!response.ok) {
    throw new Error("설정을 불러오지 못했습니다.");
  }

  const settings = await response.json();
  elements.nasPathInput.value = settings.nas_monitor_path || "";
  elements.allowMappedDriveInput.checked = Boolean(settings.nas_allow_mapped_drive);
  elements.savedNasPath.textContent = displayValue(settings.nas_monitor_path);
  elements.savedAllowMappedDrive.textContent = displayBoolean(settings.nas_allow_mapped_drive);
  elements.runtimeNasPath.textContent = displayValue(settings.runtime_nas_monitor_path);
  elements.databasePath.textContent = settings.database_path || "확인 불가";
  elements.settingsSaveState.textContent = settings.restart_required ? ".env와 실행 중 설정 다름" : "";
}

async function saveSettings() {
  elements.settingsSaveState.textContent = "저장 중";

  const response = await fetch("/api/settings", {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      nas_monitor_path: elements.nasPathInput.value.trim(),
      nas_allow_mapped_drive: elements.allowMappedDriveInput.checked,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.error || "설정을 저장하지 못했습니다.");
  }

  const settings = await response.json();
  elements.settingsSaveState.textContent = settings.restart_required ? "저장됨 · 감시는 서버 재시작 필요" : "저장됨";
  await loadSettings();
}

elements.settingsForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  try {
    await saveSettings();
  } catch (error) {
    elements.settingsSaveState.textContent = error.message;
  }
});

loadSettings().catch((error) => {
  elements.settingsSaveState.textContent = error.message;
});

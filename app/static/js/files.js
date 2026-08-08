const renameDetails = Array.from(document.querySelectorAll(".rename-details"));

function closeRenameDetails(exceptDetail = null) {
  renameDetails.forEach((detail) => {
    if (detail !== exceptDetail) {
      detail.open = false;
    }
  });
}

renameDetails.forEach((detail) => {
  detail.addEventListener("toggle", () => {
    if (!detail.open) {
      return;
    }

    closeRenameDetails(detail);
    detail.querySelector("input")?.select();
  });
});

document.addEventListener("pointerdown", (event) => {
  if (event.target.closest(".rename-details")) {
    return;
  }

  closeRenameDetails();
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeRenameDetails();
  }
});

const uploadForm = document.querySelector(".upload-form");
const uploadInput = document.querySelector("#uploadFiles");
const uploadDropzone = document.querySelector(".upload-dropzone");
const uploadStatus = document.querySelector(".upload-status");
const uploadSummary = document.querySelector("#uploadSummary");
const uploadBytes = document.querySelector("#uploadBytes");
const uploadProgress = document.querySelector("#uploadProgress");
const uploadQueue = document.querySelector("#uploadQueue");

let queuedUploads = [];
let uploadSequence = 0;
let isUploading = false;

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "0 B";
  }

  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unitIndex = 0;

  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }

  if (unitIndex === 0) {
    return `${Math.round(value)} ${units[unitIndex]}`;
  }

  return `${value >= 10 ? value.toFixed(1) : value.toFixed(2)} ${units[unitIndex]}`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function statusLabel(item) {
  if (item.status === "uploading") {
    return `업로드 중 ${item.progress}%`;
  }

  if (item.status === "done") {
    return "완료";
  }

  if (item.status === "failed") {
    return `실패: ${item.message}`;
  }

  return "대기 중";
}

function renderUploadQueue() {
  if (!uploadStatus || !uploadQueue || !uploadSummary || !uploadBytes || !uploadProgress) {
    return;
  }

  uploadStatus.hidden = queuedUploads.length === 0;

  const totalCount = queuedUploads.length;
  const doneCount = queuedUploads.filter((item) => item.status === "done").length;
  const failedCount = queuedUploads.filter((item) => item.status === "failed").length;
  const remainingCount = queuedUploads.filter((item) => item.status === "queued" || item.status === "uploading").length;
  const totalBytes = queuedUploads.reduce((sum, item) => sum + item.file.size, 0);
  const processedBytes = queuedUploads.reduce((sum, item) => {
    if (item.status === "done" || item.status === "failed") {
      return sum + item.file.size;
    }

    return sum + item.loaded;
  }, 0);
  const percent = totalBytes > 0 ? Math.round((processedBytes / totalBytes) * 100) : 0;

  if (totalCount === 0) {
    uploadSummary.textContent = "업로드 대기 중";
  } else if (isUploading) {
    uploadSummary.textContent = `${doneCount}/${totalCount}개 완료, ${failedCount}개 실패, ${remainingCount}개 남음`;
  } else if (doneCount === 0 && failedCount === 0) {
    uploadSummary.textContent = `${remainingCount}개 대기 중`;
  } else if (failedCount > 0) {
    uploadSummary.textContent = `${doneCount}/${totalCount}개 완료, ${failedCount}개 실패`;
  } else {
    uploadSummary.textContent = `${doneCount}/${totalCount}개 완료`;
  }

  uploadBytes.textContent = `${formatBytes(processedBytes)} / ${formatBytes(totalBytes)}`;
  uploadProgress.value = percent;
  uploadQueue.innerHTML = queuedUploads
    .map(
      (item) => `
        <li class="upload-item ${item.status}">
          <span class="upload-file-name">${escapeHtml(item.file.name)}</span>
          <span class="upload-file-size">${formatBytes(item.file.size)}</span>
          <span class="upload-file-status">${escapeHtml(statusLabel(item))}</span>
        </li>
      `
    )
    .join("");
}

function addFilesToQueue(files) {
  Array.from(files || []).forEach((file) => {
    queuedUploads.push({
      id: uploadSequence,
      file,
      status: "queued",
      loaded: 0,
      progress: 0,
      message: "",
    });
    uploadSequence += 1;
  });

  renderUploadQueue();
}

function uploadFile(item) {
  return new Promise((resolve) => {
    const formData = new FormData();
    const currentPath = uploadForm.querySelector('input[name="current_path"]')?.value || "";
    const request = new XMLHttpRequest();

    item.status = "uploading";
    item.loaded = 0;
    item.progress = 0;
    renderUploadQueue();

    formData.append("current_path", currentPath);
    formData.append("file", item.file);

    request.upload.addEventListener("progress", (event) => {
      if (!event.lengthComputable) {
        return;
      }

      item.loaded = event.loaded;
      item.progress = Math.min(99, Math.round((event.loaded / event.total) * 100));
      renderUploadQueue();
    });

    request.addEventListener("load", () => {
      let response = {};

      try {
        response = JSON.parse(request.responseText || "{}");
      } catch (_error) {
        response = {};
      }

      if (request.status >= 200 && request.status < 300 && response.ok !== false) {
        item.status = "done";
        item.loaded = item.file.size;
        item.progress = 100;
        item.message = response.message || "업로드가 완료되었습니다.";
      } else {
        item.status = "failed";
        item.loaded = item.file.size;
        item.progress = 100;
        item.message = response.message || response.error || "업로드에 실패했습니다.";
      }

      renderUploadQueue();
      resolve();
    });

    request.addEventListener("error", () => {
      item.status = "failed";
      item.loaded = item.file.size;
      item.progress = 100;
      item.message = "네트워크 오류로 업로드에 실패했습니다.";
      renderUploadQueue();
      resolve();
    });

    request.addEventListener("abort", () => {
      item.status = "failed";
      item.loaded = item.file.size;
      item.progress = 100;
      item.message = "업로드가 취소되었습니다.";
      renderUploadQueue();
      resolve();
    });

    request.open("POST", uploadForm.dataset.uploadUrl || uploadForm.action);
    request.setRequestHeader("X-Requested-With", "XMLHttpRequest");
    request.send(formData);
  });
}

async function uploadQueuedFiles() {
  if (isUploading) {
    return;
  }

  const pendingItems = queuedUploads.filter((item) => item.status === "queued");
  if (pendingItems.length === 0) {
    renderUploadQueue();
    return;
  }

  isUploading = true;
  uploadForm.querySelector('button[type="submit"]').disabled = true;
  renderUploadQueue();

  for (const item of pendingItems) {
    await uploadFile(item);
  }

  isUploading = false;
  uploadForm.querySelector('button[type="submit"]').disabled = false;
  renderUploadQueue();

  if (
    queuedUploads.some((item) => item.status === "done") &&
    !queuedUploads.some((item) => item.status === "failed")
  ) {
    window.setTimeout(() => {
      window.location.reload();
    }, 1200);
  }
}

uploadInput?.addEventListener("change", () => {
  addFilesToQueue(uploadInput.files);
  uploadInput.value = "";
});

uploadForm?.addEventListener("submit", (event) => {
  if (!window.FormData || !window.XMLHttpRequest) {
    return;
  }

  event.preventDefault();
  addFilesToQueue(uploadInput?.files);
  uploadQueuedFiles();
});

["dragenter", "dragover"].forEach((eventName) => {
  uploadDropzone?.addEventListener(eventName, (event) => {
    event.preventDefault();
    uploadDropzone.classList.add("dragging");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  uploadDropzone?.addEventListener(eventName, (event) => {
    event.preventDefault();
    uploadDropzone.classList.remove("dragging");
  });
});

uploadDropzone?.addEventListener("drop", (event) => {
  addFilesToQueue(event.dataTransfer?.files);
});

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

const planbSessionKey = "planbNasActiveBrowserSession";

async function logoutExpiredBrowserSession() {
  try {
    await fetch("/session/logout", {
      method: "POST",
      keepalive: true,
    });
  } finally {
    window.location.replace("/login");
  }
}

if (sessionStorage.getItem(planbSessionKey) !== "1") {
  logoutExpiredBrowserSession();
}

document.querySelectorAll('a[href$="/logout"], a[href="/logout"]').forEach((link) => {
  link.addEventListener("click", () => {
    sessionStorage.removeItem(planbSessionKey);
  });
});

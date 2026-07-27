const planbSessionKey = "planbNasActiveBrowserSession";

document.querySelector("[data-login-form]")?.addEventListener("submit", () => {
  sessionStorage.setItem(planbSessionKey, "1");
});

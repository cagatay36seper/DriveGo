import { secureFetch } from "../shared/api.js";

function setAlert(message, type = "error") {
  const alertBox = document.querySelector("#alert");
  if (!alertBox) return;
  if (!message) {
    alertBox.className = "alert";
    alertBox.textContent = "";
    return;
  }
  alertBox.className = `alert show alert-${type === "error" ? "danger" : "success"}`;
  alertBox.textContent = message;
}

function setBusy(button, busy, label) {
  if (!button) return;
  button.disabled = busy;
  button.dataset.originalLabel = button.dataset.originalLabel || button.innerHTML;
  button.innerHTML = busy ? `<span class="spinner"></span>${label}` : button.dataset.originalLabel;
}

window.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("#loginForm");
  const password = document.querySelector("#password");
  const togglePassword = document.querySelector("#togglePassword");
  const button = document.querySelector("#loginBtn");

  togglePassword?.addEventListener("click", () => {
    const nextType = password.type === "password" ? "text" : "password";
    password.type = nextType;
    togglePassword.innerHTML = nextType === "password"
      ? '<i class="fas fa-eye"></i>'
      : '<i class="fas fa-eye-slash"></i>';
  });

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    setAlert("");
    setBusy(button, true, "Giriş yapılıyor...");

    try {
      await secureFetch("/api/auth/login", {
        method: "POST",
        body: {
          email: document.querySelector("#email").value.trim(),
          password: password.value,
        },
        includeAcIntBody: true,
        includeAcIntHeader: true,
      });
      window.location.href = "/dashboard";
    } catch (error) {
      setAlert(error.message, "error");
    } finally {
      setBusy(button, false);
    }
  });
});

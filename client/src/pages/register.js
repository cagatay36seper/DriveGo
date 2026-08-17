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
  const form = document.querySelector("#registerForm");
  const password = document.querySelector("#password");
  const confirmPassword = document.querySelector("#confirmPassword");
  const togglePassword = document.querySelector("#togglePassword");
  const toggleConfirmPassword = document.querySelector("#toggleConfirmPassword");
  const button = document.querySelector("#registerBtn");

  const toggleVisibility = (input, toggleButton) => {
    const nextType = input.type === "password" ? "text" : "password";
    input.type = nextType;
    toggleButton.innerHTML = nextType === "password"
      ? '<i class="fas fa-eye"></i>'
      : '<i class="fas fa-eye-slash"></i>';
  };

  togglePassword?.addEventListener("click", () => toggleVisibility(password, togglePassword));
  toggleConfirmPassword?.addEventListener("click", () => toggleVisibility(confirmPassword, toggleConfirmPassword));

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    setAlert("");

    if (password.value !== confirmPassword.value) {
      setAlert("Şifreler eşleşmiyor.", "error");
      return;
    }

    setBusy(button, true, "Kaydediliyor...");

    try {
      await secureFetch("/api/auth/register", {
        method: "POST",
        body: {
          username: document.querySelector("#username").value.trim(),
          email: document.querySelector("#email").value.trim(),
          password: password.value,
          fullName: document.querySelector("#fullName").value.trim(),
          phone: document.querySelector("#phone").value.trim(),
          driverLicense: document.querySelector("#driverLicense").value.trim(),
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

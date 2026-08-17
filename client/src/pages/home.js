window.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".view-options button").forEach((btn) => {
    btn.addEventListener("click", function () {
      document.querySelectorAll(".view-options button").forEach((button) => button.classList.remove("active"));
      this.classList.add("active");
    });
  });

  document.querySelector(".search-btn")?.addEventListener("click", function (event) {
    event.preventDefault();
    location.href = "/register";
  });

  document.querySelectorAll(".car-card .btn-primary").forEach((btn) => {
    btn.addEventListener("click", function (event) {
      event.preventDefault();
      location.href = "/register";
    });
  });
});

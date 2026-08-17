import { secureFetch } from "../shared/api.js";

const $ = (selector, root = document) => root.querySelector(selector);

let activeReserveCar = null;
let reviewSummaries = {};
let myReviewsByCar = {};

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function safeImageUrl(value) {
  if (!value) return "";
  try {
    const url = new URL(value, window.location.origin);
    return ["http:", "https:"].includes(url.protocol) ? url.href : "";
  } catch {
    return "";
  }
}

function setAlert(message, type = "error") {
  const alertBox = $("#dashboardAlert");
  if (!alertBox) return;
  if (!message) {
    alertBox.className = "alert";
    alertBox.textContent = "";
    return;
  }
  alertBox.className = `alert show alert-${type === "error" ? "danger" : "success"}`;
  alertBox.textContent = message;
}

function setBusy(button, busy, label = "İşleniyor...") {
  if (!button) return;
  button.disabled = busy;
  button.dataset.originalLabel = button.dataset.originalLabel || button.innerHTML;
  button.innerHTML = busy ? `<span class="spinner"></span>${label}` : button.dataset.originalLabel;
}

function formatMoney(value) {
  if (value === null || value === undefined || value === "") return "Fiyat yok";
  return `₺${Number(value).toLocaleString("tr-TR")}`;
}

function formatDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleDateString("tr-TR");
}

function todayPlus(days) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

function rentalDays(startValue, endValue) {
  if (!startValue || !endValue) return 0;
  const start = new Date(startValue);
  const end = new Date(endValue);
  const diff = Math.ceil((end - start) / (1000 * 60 * 60 * 24));
  return Math.max(diff, 1);
}

function reservationTotal(reservation) {
  if (reservation.toplam_tutar) return Number(reservation.toplam_tutar);
  const dailyPrice = Number(reservation.car?.gunluk_fiyat || 0);
  return rentalDays(reservation.baslangic_tarihi, reservation.bitis_tarihi) * dailyPrice;
}

function paymentLabel(method) {
  const labels = {
    kart: "Kart",
    havale: "Havale",
    teslimatta: "Teslimatta Ödeme",
  };
  return labels[method] || method || "-";
}

function getSelectedPaymentMethod() {
  return document.querySelector('input[name="paymentMethod"]:checked')?.value || "kart";
}

function getFilterDates() {
  const url = new URL(window.location.href);
  return {
    baslangic_tarihi: url.searchParams.get("baslangic_tarihi") || $("#dashboardStartDate")?.value || todayPlus(1),
    bitis_tarihi: url.searchParams.get("bitis_tarihi") || $("#dashboardEndDate")?.value || todayPlus(2),
  };
}

function updatePaymentFields() {
  const method = getSelectedPaymentMethod();
  const cardFields = $("#cardFields");
  const paymentNote = $("#paymentNote");
  if (!cardFields || !paymentNote) return;

  cardFields.style.display = method === "kart" ? "grid" : "none";
  paymentNote.textContent = method === "kart"
    ? "Demo ödeme akışında kart numarası saklanmaz, yalnızca son 4 hane rezervasyon özetinde gösterilir."
    : "Bu ödeme yönteminde rezervasyon alınır, ödeme durumu beklemede olarak kaydedilir.";
}

function updateReservePrice() {
  const start = $("#reserveStart")?.value;
  const end = $("#reserveEnd")?.value;
  const priceBox = $("#reservePriceBox");
  const dailyPrice = Number($("#reserveDailyPrice")?.value || 0);
  if (!priceBox || !activeReserveCar) return;

  const days = rentalDays(start, end);
  const total = days * dailyPrice;

  priceBox.innerHTML = `
    <div>
      <span>Günlük fiyat</span>
      <strong>${formatMoney(dailyPrice)}</strong>
    </div>
    <div>
      <span>Kiralama süresi</span>
      <strong>${days} gün</strong>
    </div>
    <div class="reserve-total-row">
      <span>Toplam tutar</span>
      <strong>${formatMoney(total)}</strong>
    </div>
  `;
}

function openModal(car) {
  const modal = $("#reserveModal");
  const reserveCarId = $("#reserveCarId");
  const reserveDailyPrice = $("#reserveDailyPrice");
  const summary = $("#reserveSummary");
  const startInput = $("#reserveStart");
  const endInput = $("#reserveEnd");
  const title = $("#reserveModalTitle");
  const dates = getFilterDates();

  activeReserveCar = car;
  reserveCarId.value = car.id;
  reserveDailyPrice.value = car.gunluk_fiyat || 0;
  title.textContent = `${car.marka} ${car.model}`;
  summary.innerHTML = `
    <div class="reserve-car-preview">
      <div class="reserve-car-image">
        ${safeImageUrl(car.image_url) ? `<img src="${escapeHtml(safeImageUrl(car.image_url))}" alt="${escapeHtml(car.marka)} ${escapeHtml(car.model)}">` : '<i class="fas fa-car"></i>'}
      </div>
      <div>
        <strong>${escapeHtml(car.marka)} ${escapeHtml(car.model)}</strong>
        <span>${escapeHtml(car.yil || "-")} • ${escapeHtml(car.vites || "-")} • ${escapeHtml(car.yakit || "-")}</span>
        <span><i class="fas fa-id-card"></i> ${escapeHtml(car.plaka)}</span>
      </div>
    </div>
  `;
  startInput.value = dates.baslangic_tarihi;
  endInput.value = dates.bitis_tarihi;
  $("#cardHolder").value = "";
  $("#cardNumber").value = "";
  document.querySelector('input[name="paymentMethod"][value="kart"]').checked = true;
  updatePaymentFields();
  updateReservePrice();
  modal.classList.add("show");
  modal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
  startInput.focus();
}

function closeModal() {
  const modal = $("#reserveModal");
  if (!modal) return;
  activeReserveCar = null;
  modal.classList.remove("show");
  modal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
}

function renderStats(stats = {}, user = null, reservations = []) {
  const statsGrid = $("#statsGrid");
  if (!statsGrid) return;

  const activeItems = reservations.filter((item) => item.durum === "aktif");
  const totalAmount = activeItems.reduce((sum, item) => sum + reservationTotal(item), 0);

  const cards = [
    { label: "Toplam Araç", value: stats.total_cars ?? 0, icon: "fa-car" },
    { label: "Müsait Araç", value: stats.available_cars ?? 0, icon: "fa-circle-check" },
    { label: "Aktif Rezervasyon", value: activeItems.length, icon: "fa-calendar-check" },
    { label: "Aktif Tutar", value: formatMoney(totalAmount), icon: "fa-wallet" },
  ];

  statsGrid.innerHTML = cards
    .map(
      (card) => `
        <article class="dashboard-stat-card">
          <div class="dashboard-stat-icon"><i class="fas ${card.icon}"></i></div>
          <div>
            <p>${card.label}</p>
            <h3>${card.value}</h3>
          </div>
        </article>
      `,
    )
    .join("");
}

function starsMarkup(rating) {
  const safeRating = Math.max(0, Math.min(5, Number(rating) || 0));
  const fullStars = Math.floor(safeRating);
  const hasHalfStar = safeRating - fullStars >= 0.25 && safeRating - fullStars < 0.75;
  return Array.from({ length: 5 }, (_, index) => {
    if (index < fullStars) return '<i class="fas fa-star"></i>';
    if (index === fullStars && hasHalfStar) return '<i class="fas fa-star-half-stroke"></i>';
    return '<i class="fas fa-star muted-star"></i>';
  }).join("");
}

function renderCars(items = [], summaries = {}) {
  const grid = $("#carsGrid");
  if (!grid) return;

  if (!items.length) {
    grid.innerHTML = `
      <div class="empty-state">
        <i class="fas fa-car-burst"></i>
        <h3>Bu tarih aralığında uygun araç yok</h3>
        <p>Farklı bir tarih aralığı deneyin.</p>
      </div>
    `;
    return;
  }

  grid.innerHTML = items
    .map(
      (car) => {
        const rating = summaries[String(car.id)];
        return `
        <article class="car-card">
          <div class="car-image">
            ${safeImageUrl(car.image_url) ? `<img src="${escapeHtml(safeImageUrl(car.image_url))}" alt="${escapeHtml(car.marka)} ${escapeHtml(car.model)}" loading="lazy">` : '<i class="fas fa-car"></i>'}
            <span class="car-badge popular">${car.musait ? "Müsait" : "Dolu"}</span>
          </div>
          <div class="car-details">
            <h3>${escapeHtml(car.marka)} ${escapeHtml(car.model)}</h3>
            <p class="car-type">${escapeHtml(car.yil || "-")} • ${escapeHtml(car.vites || "-")} • ${escapeHtml(car.yakit || "-")}</p>
            ${rating ? `<div class="car-rating"><span class="review-stars">${starsMarkup(rating.average)}</span><small>${escapeHtml(rating.average)} / 5 (${escapeHtml(rating.count)})</small></div>` : ""}
            <div class="car-specs">
              <span><i class="fas fa-id-card"></i> ${escapeHtml(car.plaka)}</span>
              <span><i class="fas fa-check-circle"></i> ${car.musait ? "Hazır" : "Rezerveli"}</span>
            </div>
            <div class="car-price">
              <span class="price">${formatMoney(car.gunluk_fiyat)} <small>/gün</small></span>
              <button type="button" class="btn btn-primary btn-sm reserve-btn" data-car-id="${car.id}">
                <i class="fas fa-calendar-plus"></i> Kirala
              </button>
            </div>
          </div>
        </article>
      `;
      },
    )
    .join("");

  grid.querySelectorAll(".reserve-btn").forEach((button) => {
    button.addEventListener("click", () => {
      const car = items.find((item) => String(item.id) === button.dataset.carId);
      if (car) openModal(car);
    });
  });
}

function renderReviews(items = []) {
  const grid = $("#reviewsGrid");
  if (!grid) return;

  if (!items.length) {
    grid.innerHTML = `
      <div class="empty-state">
        <i class="fas fa-star"></i>
        <h3>Henüz değerlendirme yok</h3>
        <p>Kiraladığın araç için ilk değerlendirmeyi sen paylaşabilirsin.</p>
      </div>
    `;
    return;
  }

  grid.innerHTML = items
    .map((review) => `
      <article class="review-card">
        <div class="review-card-header">
          <div>
            <h3>${escapeHtml(review.car_name)}</h3>
            <span class="review-card-author">${escapeHtml(review.author)}</span>
          </div>
          <span class="review-stars">${starsMarkup(review.puan)}</span>
        </div>
        <p>${escapeHtml(review.yorum)}</p>
        <time datetime="${escapeHtml(review.updated_at || review.created_at)}">${formatDate(review.updated_at || review.created_at)}</time>
      </article>
    `)
    .join("");
}

function openReviewModal(reservation, existingReview = null) {
  const modal = $("#reviewModal");
  const car = reservation.car;
  if (!modal) return;

  $("#reviewCarId").value = reservation.arac_id;
  $("#reviewModalTitle").textContent = existingReview ? "Değerlendirmeni güncelle" : "Puanını paylaş";
  $("#reviewCarContext").textContent = `${car?.marka || "Araç"} ${car?.model || reservation.arac_id}`;
  $("#reviewComment").value = existingReview?.yorum || "";
  const selectedRating = existingReview?.puan || 5;
  const selectedInput = document.querySelector(`input[name="reviewRating"][value="${selectedRating}"]`);
  if (selectedInput) selectedInput.checked = true;

  modal.classList.add("show");
  modal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
  $("#reviewComment").focus();
}

function closeReviewModal() {
  const modal = $("#reviewModal");
  if (!modal) return;
  modal.classList.remove("show");
  modal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
}

function renderReservations(items = [], reviewsByCar = {}) {
  const grid = $("#reservationsGrid");
  if (!grid) return;

  if (!items.length) {
    grid.innerHTML = `
      <div class="empty-state reservation-empty-state">
        <i class="fas fa-file-contract"></i>
        <h3>Henüz rezervasyon yok</h3>
        <p>İlk rezervasyonunu oluşturduğunda araç, tarih, ödeme ve toplam fiyat burada görünecek.</p>
      </div>
    `;
    return;
  }

  grid.innerHTML = items
    .map((reservation) => {
      const days = rentalDays(reservation.baslangic_tarihi, reservation.bitis_tarihi);
      const total = reservationTotal(reservation);
      const car = reservation.car;
      const paymentText = reservation.kart_son_dort
        ? `${paymentLabel(reservation.odeme_yontemi)} • **** ${reservation.kart_son_dort}`
        : paymentLabel(reservation.odeme_yontemi);
      const reviewable = reservation.durum === "aktif";
      const existingReview = reviewsByCar[String(reservation.arac_id)];

      return `
        <article class="reservation-card reservation-card-rich">
          <div class="reservation-cover">
            ${safeImageUrl(car?.image_url) ? `<img src="${escapeHtml(safeImageUrl(car.image_url))}" alt="${escapeHtml(car?.marka)} ${escapeHtml(car?.model)}" loading="lazy">` : '<i class="fas fa-car"></i>'}
            <span class="reservation-status ${reservation.durum === "aktif" ? "is-active" : "is-cancelled"}">${escapeHtml(reservation.durum)}</span>
          </div>
          <div class="reservation-content">
            <div>
              <h3>${escapeHtml(car?.marka || "Araç")} ${escapeHtml(car?.model || reservation.arac_id)}</h3>
              <p>${escapeHtml(car?.plaka || "-")} • ${escapeHtml(car?.yakit || "-")} • ${escapeHtml(car?.vites || "-")}</p>
            </div>
            <div class="reservation-meta">
              <span><i class="fas fa-calendar"></i> ${formatDate(reservation.baslangic_tarihi)} - ${formatDate(reservation.bitis_tarihi)}</span>
              <span><i class="fas fa-clock"></i> ${days} gün</span>
              <span><i class="fas fa-credit-card"></i> ${escapeHtml(paymentText)}</span>
              <span><i class="fas fa-circle-check"></i> ${escapeHtml(reservation.odeme_durumu || "beklemede")}</span>
            </div>
            <div class="reservation-price-line">
              <span>Toplam</span>
              <strong>${formatMoney(total)}</strong>
            </div>
            <div class="reservation-actions">
              ${reservation.durum === "aktif" ? `<button type="button" class="btn btn-outline btn-sm cancel-reservation" data-id="${reservation.id}"><i class="fas fa-ban"></i> İptal Et</button>` : ""}
              ${reviewable ? `<button type="button" class="btn btn-primary btn-sm review-reservation" data-car-id="${reservation.arac_id}"><i class="fas fa-star"></i> ${existingReview ? "Düzenle" : "Puanla"}</button>` : ""}
            </div>
          </div>
        </article>
      `;
    })
    .join("");

  grid.querySelectorAll(".cancel-reservation").forEach((button) => {
    button.addEventListener("click", async () => {
      setBusy(button, true, "İptal ediliyor...");
      try {
        await secureFetch(`/api/rezervasyonlar/${button.dataset.id}/iptal`, {
          method: "POST",
          includeAcIntHeader: true,
        });
        setAlert("Rezervasyon iptal edildi.", "success");
        await loadDashboard();
      } catch (error) {
        setAlert(error.message, "error");
      } finally {
        setBusy(button, false);
      }
    });
  });

  grid.querySelectorAll(".review-reservation").forEach((button) => {
    button.addEventListener("click", () => {
      const reservation = items.find((item) => String(item.arac_id) === button.dataset.carId);
      if (reservation) openReviewModal(reservation, reviewsByCar[button.dataset.carId]);
    });
  });
}

async function loadDashboard() {
  const dates = getFilterDates();
  $("#dashboardStartDate").value = dates.baslangic_tarihi;
  $("#dashboardEndDate").value = dates.bitis_tarihi;
  $("#carsMeta").textContent = `Filtre: ${dates.baslangic_tarihi} - ${dates.bitis_tarihi}`;

  try {
    const [dashboardData, carsData, reservationsData, reviewsData] = await Promise.all([
      secureFetch("/api/dashboard"),
      secureFetch(`/api/araclar/musait?baslangic_tarihi=${dates.baslangic_tarihi}&bitis_tarihi=${dates.bitis_tarihi}`),
      secureFetch("/api/rezervasyonlar/benim"),
      secureFetch("/api/yorumlar"),
    ]);

    const user = dashboardData.user;
    const reservations = reservationsData.items || [];
    $("#welcomeTitle").textContent = `Hoş geldin, ${user.full_name || user.username}`;
    $("#welcomeSubtitle").textContent = "Tarih aralığını seç, ödeme yöntemini belirle ve rezervasyonunu kolayca tamamla.";

    reviewSummaries = reviewsData.summaries || {};
    myReviewsByCar = Object.fromEntries((reviewsData.my_items || []).map((item) => [String(item.arac_id), item]));
    renderStats(dashboardData.stats, user, reservations);
    renderCars(carsData.items || [], reviewSummaries);
    renderReservations(reservations, myReviewsByCar);
    renderReviews(reviewsData.items || []);
    setAlert("");
  } catch (error) {
    window.location.href = "/login";
  }
}

window.addEventListener("DOMContentLoaded", () => {
  const form = $("#availabilityForm");
  const reserveForm = $("#reserveForm");
  const logoutButton = $("#logoutBtn");
  const cancelButton = $("#reserveCancel");
  const closeButton = $("#reserveModalClose");
  const modal = $("#reserveModal");
  const reserveStart = $("#reserveStart");
  const reserveEnd = $("#reserveEnd");
  const reserveSubmit = $("#reserveSubmit");
  const cardNumber = $("#cardNumber");
  const reviewForm = $("#reviewForm");
  const reviewSubmit = $("#reviewSubmit");
  const reviewModal = $("#reviewModal");
  const reviewCancel = $("#reviewCancel");
  const reviewClose = $("#reviewModalClose");

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const url = new URL(window.location.href);
    url.searchParams.set("baslangic_tarihi", $("#dashboardStartDate").value);
    url.searchParams.set("bitis_tarihi", $("#dashboardEndDate").value);
    window.history.replaceState({}, "", url.toString());
    await loadDashboard();
  });

  reserveStart?.addEventListener("change", updateReservePrice);
  reserveEnd?.addEventListener("change", updateReservePrice);
  document.querySelectorAll('input[name="paymentMethod"]').forEach((input) => {
    input.addEventListener("change", updatePaymentFields);
  });
  cardNumber?.addEventListener("input", () => {
    cardNumber.value = cardNumber.value
      .replace(/\D/g, "")
      .slice(0, 16)
      .replace(/(.{4})/g, "$1 ")
      .trim();
  });

  reserveForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const paymentMethod = getSelectedPaymentMethod();
    setBusy(reserveSubmit, true, "Rezervasyon alınıyor...");
    try {
      await secureFetch("/api/rezervasyonlar", {
        method: "POST",
        body: {
          arac_id: Number($("#reserveCarId").value),
          baslangic_tarihi: $("#reserveStart").value,
          bitis_tarihi: $("#reserveEnd").value,
          odeme_yontemi: paymentMethod,
          kart_sahibi: paymentMethod === "kart" ? $("#cardHolder").value.trim() : null,
          kart_numarasi: paymentMethod === "kart" ? $("#cardNumber").value.trim() : null,
        },
        includeAcIntHeader: true,
        includeAcIntBody: true,
      });
      closeModal();
      setAlert("Rezervasyon ve ödeme bilgisi kaydedildi.", "success");
      await loadDashboard();
    } catch (error) {
      setAlert(error.message, "error");
    } finally {
      setBusy(reserveSubmit, false);
    }
  });

  reviewForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const rating = Number(document.querySelector('input[name="reviewRating"]:checked')?.value || 0);
    setBusy(reviewSubmit, true, "Kaydediliyor...");
    try {
      await secureFetch("/api/yorumlar", {
        method: "POST",
        body: {
          arac_id: Number($("#reviewCarId").value),
          puan: rating,
          yorum: $("#reviewComment").value.trim(),
        },
        includeAcIntHeader: true,
        includeAcIntBody: true,
      });
      closeReviewModal();
      setAlert("Değerlendirmeniz kaydedildi.", "success");
      await loadDashboard();
    } catch (error) {
      setAlert(error.message, "error");
    } finally {
      setBusy(reviewSubmit, false);
    }
  });

  logoutButton?.addEventListener("click", async () => {
    try {
      await secureFetch("/api/auth/logout", {
        method: "POST",
        includeAcIntHeader: true,
      });
    } finally {
      window.location.href = "/login";
    }
  });

  cancelButton?.addEventListener("click", closeModal);
  closeButton?.addEventListener("click", closeModal);
  modal?.addEventListener("click", (event) => {
    if (event.target === modal) closeModal();
  });
  reviewCancel?.addEventListener("click", closeReviewModal);
  reviewClose?.addEventListener("click", closeReviewModal);
  reviewModal?.addEventListener("click", (event) => {
    if (event.target === reviewModal) closeReviewModal();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    if (reviewModal?.classList.contains("show")) closeReviewModal();
    else if (modal?.classList.contains("show")) closeModal();
  });

  updatePaymentFields();
  loadDashboard();
});

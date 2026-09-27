/**
 * CampusPulse AI – report-form.js
 * Handles the submit report page:
 *   - Leaflet map location picker
 *   - Drag-and-drop image upload with preview
 *   - Character counter for description
 */

(function () {
  "use strict";

  // ── Leaflet location picker ────────────────────────────────────────────────
  const mapEl = document.getElementById("location-map");
  if (mapEl && window.L) {
    const cfg = window.CAMPUS_CONFIG || { lat: 28.6139, lng: 77.209, zoom: 16 };
    const map = L.map("location-map").setView([cfg.lat, cfg.lng], cfg.zoom);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map);

    let marker = null;
    const latInput = document.getElementById("latitude");
    const lngInput = document.getElementById("longitude");
    const coordsDisplay = document.getElementById("coords-display");

    map.on("click", function (e) {
      const { lat, lng } = e.latlng;

      if (marker) {
        marker.setLatLng(e.latlng);
      } else {
        marker = L.marker(e.latlng, { draggable: true }).addTo(map);
        marker.on("dragend", function () {
          const pos = marker.getLatLng();
          updateCoords(pos.lat, pos.lng);
        });
      }

      updateCoords(lat, lng);
    });

    function updateCoords(lat, lng) {
      latInput.value = lat.toFixed(6);
      lngInput.value = lng.toFixed(6);
      coordsDisplay.textContent = `Selected: ${lat.toFixed(5)}, ${lng.toFixed(5)}`;
    }
  }

  // ── Description character counter ─────────────────────────────────────────
  const descTextarea = document.getElementById("description");
  const charCount = document.getElementById("desc-char-count");
  if (descTextarea && charCount) {
    descTextarea.addEventListener("input", function () {
      const len = this.value.length;
      const max = parseInt(this.getAttribute("maxlength") || 2000);
      charCount.textContent = `${len} / ${max} characters`;
      charCount.style.color = len > max * 0.9 ? "var(--clr-warning)" : "";
    });
  }

  // ── Image drag-and-drop + preview ──────────────────────────────────────────
  const dropZone = document.getElementById("file-drop-zone");
  const fileInput = document.getElementById("image");
  const dropContent = document.getElementById("file-drop-content");
  const filePreview = document.getElementById("file-preview");
  const previewImg = document.getElementById("preview-img");
  const removeBtn = document.getElementById("remove-file");

  if (dropZone && fileInput) {
    ["dragenter", "dragover"].forEach((evt) => {
      dropZone.addEventListener(evt, (e) => {
        e.preventDefault();
        dropZone.classList.add("drag-over");
      });
    });

    ["dragleave", "drop"].forEach((evt) => {
      dropZone.addEventListener(evt, (e) => {
        e.preventDefault();
        dropZone.classList.remove("drag-over");
      });
    });

    dropZone.addEventListener("drop", (e) => {
      const files = e.dataTransfer.files;
      if (files.length) {
        fileInput.files = files;
        showPreview(files[0]);
      }
    });

    fileInput.addEventListener("change", function () {
      if (this.files.length) showPreview(this.files[0]);
    });

    removeBtn &&
      removeBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        fileInput.value = "";
        filePreview.style.display = "none";
        dropContent.style.display = "";
      });

    function showPreview(file) {
      if (!file.type.startsWith("image/")) return;
      const reader = new FileReader();
      reader.onload = (e) => {
        previewImg.src = e.target.result;
        filePreview.style.display = "block";
        dropContent.style.display = "none";
      };
      reader.readAsDataURL(file);
    }
  }

  // ── Form submit state ──────────────────────────────────────────────────────
  const form = document.getElementById("report-form");
  const submitBtn = document.getElementById("submit-btn");
  if (form && submitBtn) {
    form.addEventListener("submit", function () {
      submitBtn.disabled = true;
      submitBtn.textContent = "Submitting…";
    });
  }
})();

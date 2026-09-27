/**
 * CampusPulse AI – admin.js
 * Handles admin-specific interactions:
 *   - Inline status update via PATCH /admin/reports/<id>/status
 *   - Priority override via PATCH /admin/reports/<id>/priority
 *   - Admin notes save via POST /admin/reports/<id>/note
 *   - Report delete via DELETE /admin/reports/<id>/delete
 *   - Inline status changes on the reports list table
 */

(function () {
  "use strict";

  // ── Helper: show a brief toast notification ────────────────────────────────
  function toast(message, type = "success") {
    const container = document.querySelector(".flash-container") ||
      (() => {
        const el = document.createElement("div");
        el.className = "flash-container";
        document.body.appendChild(el);
        return el;
      })();

    const el = document.createElement("div");
    el.className = `flash flash--${type}`;
    el.innerHTML = `<span class="flash-message">${message}</span>
      <button class="flash-close" onclick="this.parentElement.remove()">×</button>`;
    container.appendChild(el);
    setTimeout(() => { el.style.opacity = "0"; setTimeout(() => el.remove(), 400); }, 4000);
  }

  // ── Helper: PATCH/DELETE JSON request ─────────────────────────────────────
  async function apiRequest(url, method, body) {
    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: "Request failed" }));
      throw new Error(err.error || "Request failed");
    }
    return res.json();
  }

  // ── Update Status (detail page) ───────────────────────────────────────────
  const updateStatusBtn = document.getElementById("update-status-btn");
  if (updateStatusBtn) {
    updateStatusBtn.addEventListener("click", async function () {
      const reportId = this.dataset.report;
      const newStatus = document.getElementById("new-status").value;
      const note = document.getElementById("status-note").value.trim();

      this.disabled = true;
      this.textContent = "Updating…";

      try {
        await apiRequest(`/admin/reports/${reportId}/status`, "PATCH", { status: newStatus, note });
        toast(`Status updated to "${newStatus}"`);

        // Update badge on page without reload
        const badge = document.getElementById("status-badge");
        if (badge) {
          badge.textContent = newStatus;
          badge.className = `badge badge--status badge--status-${newStatus.toLowerCase().replace(/ /g, "-")}`;
        }
        document.getElementById("status-note").value = "";
      } catch (err) {
        toast(err.message, "danger");
      } finally {
        this.disabled = false;
        this.textContent = "Update Status";
      }
    });
  }

  // ── Override Priority (detail page) ───────────────────────────────────────
  const updatePriorityBtn = document.getElementById("update-priority-btn");
  if (updatePriorityBtn) {
    updatePriorityBtn.addEventListener("click", async function () {
      const reportId = this.dataset.report;
      const newPriority = document.getElementById("new-priority").value;

      this.disabled = true;
      this.textContent = "Saving…";

      try {
        await apiRequest(`/admin/reports/${reportId}/priority`, "PATCH", { priority: newPriority });
        toast(`Priority updated to "${newPriority}"`);

        const badge = document.getElementById("priority-badge");
        if (badge) {
          badge.textContent = newPriority;
          badge.className = `badge badge--priority badge--${newPriority.toLowerCase()}`;
        }
      } catch (err) {
        toast(err.message, "danger");
      } finally {
        this.disabled = false;
        this.textContent = "Override Priority";
      }
    });
  }

  // ── Save Admin Note (detail page) ─────────────────────────────────────────
  const saveNoteBtn = document.getElementById("save-note-btn");
  if (saveNoteBtn) {
    saveNoteBtn.addEventListener("click", async function () {
      const reportId = this.dataset.report;
      const note = document.getElementById("admin-note").value.trim();

      if (!note) { toast("Note cannot be empty.", "warning"); return; }

      this.disabled = true;
      this.textContent = "Saving…";

      try {
        await apiRequest(`/admin/reports/${reportId}/note`, "POST", { note });
        toast("Admin note saved.");
      } catch (err) {
        toast(err.message, "danger");
      } finally {
        this.disabled = false;
        this.textContent = "Save Note";
      }
    });
  }

  // ── Delete Report (detail page) ────────────────────────────────────────────
  const deleteBtn = document.getElementById("delete-report-btn");
  if (deleteBtn) {
    deleteBtn.addEventListener("click", async function () {
      const reportId = this.dataset.report;
      if (!confirm("Permanently delete this report? This cannot be undone.")) return;

      this.disabled = true;
      this.textContent = "Deleting…";

      try {
        await apiRequest(`/admin/reports/${reportId}/delete`, "DELETE");
        toast("Report deleted.");
        setTimeout(() => { window.location.href = "/admin/reports"; }, 1200);
      } catch (err) {
        toast(err.message, "danger");
        this.disabled = false;
        this.textContent = "Delete Report";
      }
    });
  }

  // ── Inline status selects on the reports list table ───────────────────────
  document.querySelectorAll(".status-select").forEach((select) => {
    select.addEventListener("change", async function () {
      const reportId = this.dataset.reportId;
      const newStatus = this.value;

      try {
        await apiRequest(`/admin/reports/${reportId}/status`, "PATCH", { status: newStatus });
        toast(`Report #${reportId} → "${newStatus}"`);
      } catch (err) {
        toast(err.message, "danger");
      }
    });
  });
})();

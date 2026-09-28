/**
 * CampusPulse AI – charts.js
 * Fetches analytics data from /analytics/* endpoints and
 * renders Chart.js charts on the admin dashboard with light theme palette.
 */

(function () {
  "use strict";

  // Shared Chart.js defaults for modern clean light theme
  Chart.defaults.color = "#64748b";
  Chart.defaults.borderColor = "#e2e8f0";
  Chart.defaults.font.family = "'Inter', system-ui, -apple-system, sans-serif";

  const PALETTE = {
    primary:  "#2563eb",
    purple:   "#7c3aed",
    accent:   "#0d9488",
    danger:   "#dc2626",
    warning:  "#d97706",
    info:     "#0284c7",
    success:  "#16a34a",
    muted:    "#64748b",
  };

  const CATEGORY_COLORS = [
    "#2563eb", "#0d9488", "#dc2626", "#ea580c",
    "#0284c7", "#16a34a", "#7c3aed", "#db2777",
    "#0891b2", "#d97706",
  ];

  const STATUS_COLORS = {
    "Reported":     PALETTE.muted,
    "Under Review": PALETTE.info,
    "In Progress":  PALETTE.warning,
    "Resolved":     PALETTE.success,
  };

  // ── Category Bar Chart ─────────────────────────────────────────────────────
  const catCanvas = document.getElementById("categoryChart");
  if (catCanvas) {
    fetch("/analytics/category-breakdown")
      .then((r) => r.json())
      .then((data) => {
        new Chart(catCanvas, {
          type: "bar",
          data: {
            labels: data.labels,
            datasets: [
              {
                label: "Reports",
                data: data.data,
                backgroundColor: CATEGORY_COLORS.slice(0, data.labels.length),
                borderRadius: 6,
                borderSkipped: false,
              },
            ],
          },
          options: {
            responsive: true,
            plugins: {
              legend: { display: false },
              tooltip: {
                backgroundColor: "#0f172a",
                titleColor: "#ffffff",
                bodyColor: "#f8fafc",
                padding: 10,
                cornerRadius: 8,
                callbacks: { label: (ctx) => ` ${ctx.raw} reports` }
              },
            },
            scales: {
              y: {
                beginAtZero: true,
                ticks: { stepSize: 1, color: "#64748b" },
                grid: { color: "#f1f5f9" }
              },
              x: {
                ticks: { maxRotation: 45, font: { size: 11 }, color: "#64748b" },
                grid: { display: false }
              },
            },
          },
        });
      })
      .catch(console.error);
  }

  // ── Status Doughnut Chart ──────────────────────────────────────────────────
  const statusCanvas = document.getElementById("statusChart");
  if (statusCanvas) {
    fetch("/analytics/summary")
      .then((r) => r.json())
      .then((data) => {
        const labels = Object.keys(data.by_status);
        const values = Object.values(data.by_status);
        const colors = labels.map((l) => STATUS_COLORS[l] || PALETTE.muted);

        new Chart(statusCanvas, {
          type: "doughnut",
          data: {
            labels,
            datasets: [
              {
                data: values,
                backgroundColor: colors,
                borderColor: "#ffffff",
                borderWidth: 3,
                hoverOffset: 6,
              },
            ],
          },
          options: {
            responsive: true,
            cutout: "68%",
            plugins: {
              legend: {
                position: "bottom",
                labels: { padding: 16, boxWidth: 12, font: { size: 12 }, color: "#334155" },
              },
              tooltip: {
                backgroundColor: "#0f172a",
                titleColor: "#ffffff",
                bodyColor: "#f8fafc",
                padding: 10,
                cornerRadius: 8,
              }
            },
          },
        });
      })
      .catch(console.error);
  }

  // ── 30-Day Trend Line Chart ────────────────────────────────────────────────
  const trendCanvas = document.getElementById("trendChart");
  if (trendCanvas) {
    fetch("/analytics/trends?days=30")
      .then((r) => r.json())
      .then((data) => {
        const labels = data.labels.map((d) => {
          const dt = new Date(d);
          return dt.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
        });

        new Chart(trendCanvas, {
          type: "line",
          data: {
            labels,
            datasets: [
              {
                label: "Reports Submitted",
                data: data.data,
                borderColor: PALETTE.primary,
                backgroundColor: "rgba(37, 99, 235, 0.08)",
                borderWidth: 2.5,
                fill: true,
                tension: 0.35,
                pointBackgroundColor: PALETTE.primary,
                pointBorderColor: "#ffffff",
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6,
              },
            ],
          },
          options: {
            responsive: true,
            plugins: {
              legend: { display: false },
              tooltip: {
                mode: "index",
                intersect: false,
                backgroundColor: "#0f172a",
                titleColor: "#ffffff",
                bodyColor: "#f8fafc",
                padding: 10,
                cornerRadius: 8,
              },
            },
            scales: {
              y: {
                beginAtZero: true,
                ticks: { stepSize: 1, color: "#64748b" },
                grid: { color: "#f1f5f9" }
              },
              x: {
                ticks: { maxTicksLimit: 10, color: "#64748b" },
                grid: { display: false }
              },
            },
            interaction: { mode: "nearest", axis: "x", intersect: false },
          },
        });
      })
      .catch(console.error);
  }
})();

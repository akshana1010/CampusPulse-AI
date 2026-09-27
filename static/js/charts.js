/**
 * CampusPulse AI – charts.js
 * Fetches analytics data from /analytics/* endpoints and
 * renders Chart.js charts on the admin dashboard.
 */

(function () {
  "use strict";

  // Shared Chart.js defaults for dark mode
  Chart.defaults.color = "#8b90a8";
  Chart.defaults.borderColor = "#2e3250";
  Chart.defaults.font.family = "'Inter', system-ui, sans-serif";

  const PALETTE = {
    primary:  "#6c63ff",
    accent:   "#00d4aa",
    danger:   "#ef4444",
    warning:  "#f59e0b",
    info:     "#3b82f6",
    success:  "#22c55e",
    muted:    "#6b7280",
  };

  const CATEGORY_COLORS = [
    "#6c63ff","#00d4aa","#ef4444","#f59e0b",
    "#3b82f6","#22c55e","#a855f7","#ec4899",
    "#14b8a6","#f97316",
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
                backgroundColor: CATEGORY_COLORS,
                borderRadius: 6,
                borderSkipped: false,
              },
            ],
          },
          options: {
            responsive: true,
            plugins: {
              legend: { display: false },
              tooltip: { callbacks: { label: (ctx) => ` ${ctx.raw} reports` } },
            },
            scales: {
              y: { beginAtZero: true, ticks: { stepSize: 1 } },
              x: { ticks: { maxRotation: 45, font: { size: 11 } } },
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
                borderColor: "#1a1d27",
                borderWidth: 3,
                hoverOffset: 8,
              },
            ],
          },
          options: {
            responsive: true,
            cutout: "68%",
            plugins: {
              legend: {
                position: "bottom",
                labels: { padding: 16, boxWidth: 14, font: { size: 12 } },
              },
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
        // Format labels as "DD MMM"
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
                backgroundColor: "rgba(108,99,255,0.1)",
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: PALETTE.primary,
                pointRadius: 3,
                pointHoverRadius: 6,
              },
            ],
          },
          options: {
            responsive: true,
            plugins: {
              legend: { display: false },
              tooltip: { mode: "index", intersect: false },
            },
            scales: {
              y: { beginAtZero: true, ticks: { stepSize: 1 } },
              x: { ticks: { maxTicksLimit: 10 } },
            },
            interaction: { mode: "nearest", axis: "x", intersect: false },
          },
        });
      })
      .catch(console.error);
  }
})();

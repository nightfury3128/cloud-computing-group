(function () {
  if (typeof Chart === "undefined") return;

  const palette = ["#4f46e5", "#06b6d4", "#10b981", "#f59e0b", "#ef4444",
                   "#8b5cf6", "#ec4899", "#14b8a6", "#3b82f6", "#f97316",
                   "#84cc16", "#eab308"];
  const money = v => "$" + Number(v).toLocaleString(undefined, {maximumFractionDigits: 0});

  if (typeof byYear !== "undefined" && document.getElementById("chartYear")) {
    new Chart(document.getElementById("chartYear"), {
      type: "bar",
      data: {
        labels: byYear.map(r => String(r.year)),
        datasets: [{ label: "Spend", data: byYear.map(r => Number(r.spend)), backgroundColor: palette[0] }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { ticks: { callback: money } } }
      }
    });
  }

  if (typeof byDept !== "undefined" && document.getElementById("chartDept")) {
    new Chart(document.getElementById("chartDept"), {
      type: "doughnut",
      data: {
        labels: byDept.map(r => r.department || "unknown"),
        datasets: [{ data: byDept.map(r => Number(r.spend)), backgroundColor: palette.slice(0, byDept.length) }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: "right" } }
      }
    });
  }

  if (typeof byMonth !== "undefined" && document.getElementById("chartMonth")) {
    const labels = byMonth.map(r => r.year + "-" + String(r.month).padStart(2, "0"));
    new Chart(document.getElementById("chartMonth"), {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: "Spend",
          data: byMonth.map(r => Number(r.spend)),
          borderColor: palette[0], backgroundColor: palette[0] + "22",
          tension: 0.25, fill: true, pointRadius: 2
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { ticks: { callback: money } } }
      }
    });
  }
})();

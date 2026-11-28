(function () {
  if (typeof Chart === "undefined") return;

  const palette = ["#4f46e5", "#06b6d4", "#10b981", "#f59e0b", "#ef4444",
                   "#8b5cf6", "#ec4899", "#14b8a6", "#3b82f6", "#f97316"];
  const money = v => "$" + Number(v).toLocaleString(undefined, {maximumFractionDigits: 0});

  if (typeof hhDept !== "undefined" && document.getElementById("chartHhDept")) {
    new Chart(document.getElementById("chartHhDept"), {
      type: "bar",
      data: {
        labels: hhDept.map(r => r.department || "unknown"),
        datasets: [{ label: "Spend", data: hhDept.map(r => Number(r.spend)), backgroundColor: palette[1] }]
      },
      options: {
        indexAxis: "y", responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { ticks: { callback: money } } }
      }
    });
  }

  if (typeof hhTrend !== "undefined" && document.getElementById("chartHhTrend")) {
    const labels = hhTrend.map(r => r.year + "-" + String(r.month).padStart(2, "0"));
    new Chart(document.getElementById("chartHhTrend"), {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: "Spend",
          data: hhTrend.map(r => Number(r.spend)),
          borderColor: palette[0], backgroundColor: palette[0] + "22",
          tension: 0.25, fill: true, pointRadius: 3
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

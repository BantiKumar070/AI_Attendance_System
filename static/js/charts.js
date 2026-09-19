/**
 * static/js/charts.js
 * ====================
 * Renders the two Chart.js dashboards on templates/admin/dashboard.html.
 * Expects `weeklyTrendData` and `classDistributionData` globals, defined
 * inline by the dashboard template from server-rendered JSON.
 */

document.addEventListener("DOMContentLoaded", () => {
    renderWeeklyTrendChart();
    renderClassDistributionChart();
});

function renderWeeklyTrendChart() {
    const canvas = document.getElementById("weeklyTrendChart");
    if (!canvas || typeof weeklyTrendData === "undefined") return;

    new Chart(canvas, {
        type: "line",
        data: {
            labels: weeklyTrendData.labels,
            datasets: [
                {
                    label: "Students Present",
                    data: weeklyTrendData.values,
                    borderColor: "#4361ee",
                    backgroundColor: "rgba(67, 97, 238, 0.1)",
                    fill: true,
                    tension: 0.35,
                    pointRadius: 4,
                },
            ],
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
        },
    });
}

function renderClassDistributionChart() {
    const canvas = document.getElementById("classDistributionChart");
    if (!canvas || typeof classDistributionData === "undefined") return;

    const palette = ["#4361ee", "#2ec4b6", "#ff9f1c", "#e63946", "#7209b7", "#4cc9f0"];

    new Chart(canvas, {
        type: "doughnut",
        data: {
            labels: classDistributionData.labels,
            datasets: [
                {
                    data: classDistributionData.values,
                    backgroundColor: classDistributionData.labels.map((_, i) => palette[i % palette.length]),
                    borderWidth: 2,
                },
            ],
        },
        options: {
            responsive: true,
            plugins: { legend: { position: "bottom" } },
        },
    });
}

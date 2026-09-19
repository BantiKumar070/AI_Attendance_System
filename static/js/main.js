/**
 * static/js/main.js
 * ==================
 * Global site-wide behaviors: mobile sidebar toggle, live clock in the
 * navbar, and auto-dismissing flash messages. Loaded on every page.
 */

document.addEventListener("DOMContentLoaded", () => {
    initSidebarToggle();
    initLiveClock();
    initFlashAutoDismiss();
});

/** Toggle the sidebar's visibility on small screens. */
function initSidebarToggle() {
    const toggleBtn = document.getElementById("sidebarToggle");
    const sidebar = document.getElementById("appSidebar");
    if (!toggleBtn || !sidebar) return;

    toggleBtn.addEventListener("click", () => {
        sidebar.classList.toggle("show");
    });

    document.addEventListener("click", (event) => {
        const isClickInside = sidebar.contains(event.target) || toggleBtn.contains(event.target);
        if (!isClickInside && sidebar.classList.contains("show") && window.innerWidth < 992) {
            sidebar.classList.remove("show");
        }
    });
}

/** Show a ticking HH:MM:SS clock in the navbar. */
function initLiveClock() {
    const clockEl = document.getElementById("liveClock");
    if (!clockEl) return;

    const tick = () => {
        clockEl.textContent = new Date().toLocaleTimeString();
    };
    tick();
    setInterval(tick, 1000);
}

/** Auto-dismiss Bootstrap alerts after a few seconds. */
function initFlashAutoDismiss() {
    const alerts = document.querySelectorAll(".flash-container .alert");
    alerts.forEach((alertEl) => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alertEl);
            bsAlert.close();
        }, 5000);
    });
}

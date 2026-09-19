/**
 * session_timeout.js
 * ===================
 * Tracks user inactivity and shows a warning modal SESSION_WARNING_SECONDS
 * before the server-side session (PERMANENT_SESSION_LIFETIME) expires.
 *
 * How it works:
 *   - SESSION_LIFETIME_SECONDS and SESSION_WARNING_SECONDS are injected
 *     into the page by base.html (read from config.py).
 *   - Any mouse/keyboard/touch activity resets the idle timer AND
 *     pings the server (/auth/session-ping), which — thanks to
 *     SESSION_REFRESH_EACH_REQUEST — resets the actual server-side
 *     session expiry too. So as long as the user is active, they never
 *     see the warning.
 *   - If the user goes idle, a countdown starts. At
 *     (LIFETIME - WARNING) seconds of inactivity, a Bootstrap modal
 *     appears showing a live countdown with an "Extend Session" button.
 *   - If they click "Extend Session", we ping the server and reset
 *     everything. If the countdown reaches zero, we redirect to logout.
 */

(function () {
    if (typeof SESSION_LIFETIME_SECONDS === "undefined") {
        return; // Guest page (login screen) — nothing to track.
    }

    const warningLeadSeconds = typeof SESSION_WARNING_SECONDS !== "undefined" ? SESSION_WARNING_SECONDS : 60;
    const idleBeforeWarningMs = Math.max((SESSION_LIFETIME_SECONDS - warningLeadSeconds) * 1000, 0);

    let idleTimer = null;
    let countdownTimer = null;
    let secondsRemaining = warningLeadSeconds;
    let modalInstance = null;

    function getModalElements() {
        return {
            modalEl: document.getElementById("sessionTimeoutModal"),
            countdownEl: document.getElementById("sessionCountdown"),
        };
    }

    function pingServer() {
        fetch(SESSION_PING_URL, { method: "POST", headers: { "X-Requested-With": "XMLHttpRequest" } }).catch(() => {
            /* Network errors here are non-fatal — the idle timer will still work locally. */
        });
    }

    function resetIdleTimer() {
        clearTimeout(idleTimer);
        idleTimer = setTimeout(showWarning, idleBeforeWarningMs);
    }

    function showWarning() {
        const { modalEl, countdownEl } = getModalElements();
        if (!modalEl) return;

        if (typeof window.bootstrap === "undefined" || !window.bootstrap.Modal) {
            window.location.href = LOGOUT_URL;
            return;
        }

        secondsRemaining = warningLeadSeconds;
        if (countdownEl) countdownEl.textContent = secondsRemaining;

        modalInstance = window.bootstrap.Modal.getOrCreateInstance(modalEl, { backdrop: "static", keyboard: false });
        modalInstance.show();

        countdownTimer = setInterval(() => {
            secondsRemaining -= 1;
            if (countdownEl) countdownEl.textContent = Math.max(secondsRemaining, 0);
            if (secondsRemaining <= 0) {
                clearInterval(countdownTimer);
                window.location.href = LOGOUT_URL;
            }
        }, 1000);
    }

    function extendSession() {
        clearInterval(countdownTimer);
        if (modalInstance) modalInstance.hide();
        pingServer();
        onUserActivity(); // restart the idle countdown from zero
    }

    function onUserActivity() {
        resetIdleTimer();
        pingServer();
    }

    // Any of these events count as "the user is here" and should reset the timer.
    // Throttle with a flag so we don't reset the timer hundreds of times per second on mousemove.
    let activityThrottle = false;
    ["mousemove", "mousedown", "keydown", "touchstart", "scroll"].forEach((eventName) => {
        window.addEventListener(
            eventName,
            () => {
                if (activityThrottle) return;
                activityThrottle = true;
                setTimeout(() => (activityThrottle = false), 5000); // ping/reset at most once every 5s
                onUserActivity();
            },
            { passive: true }
        );
    });

    document.addEventListener("DOMContentLoaded", () => {
        const extendBtn = document.getElementById("extendSessionBtn");
        if (extendBtn) extendBtn.addEventListener("click", extendSession);
        resetIdleTimer();
    });
})();

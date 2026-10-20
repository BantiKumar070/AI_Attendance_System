/**
 * static/js/live_recognition.js
 * ===============================
 * Drives the "Take Attendance" live page (templates/admin/live_recognition.html).
 *
 * Every ~1.2s, grabs a webcam frame, POSTs it to PROCESS_FRAME_URL, and:
 *   - Draws bounding boxes + name labels over each detected face.
 *   - Appends newly-marked students to the on-screen session log.
 *
 * Expects PROCESS_FRAME_URL to be defined inline by the template.
 */

(() => {
    const video = document.getElementById("webcamVideo");
    const captureCanvas = document.getElementById("captureCanvas");
    const overlayCanvas = document.getElementById("overlayCanvas");
    const startBtn = document.getElementById("startRecognitionBtn");
    const stopBtn = document.getElementById("stopRecognitionBtn");
    const subjectSelect = document.getElementById("subjectSelect");
    const recognitionLog = document.getElementById("recognitionLog");
    const activeSubjectBanner = document.getElementById("activeSubjectBanner");
    const activeSubjectName = document.getElementById("activeSubjectName");

    let mediaStream = null;
    let intervalId = null;
    let activeSubjectId = null;
    const markedThisSession = new Set();

    async function startWebcam() {
        mediaStream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: false });
        video.srcObject = mediaStream;
        await new Promise((resolve) => (video.onloadedmetadata = resolve));
        overlayCanvas.width = video.videoWidth;
        overlayCanvas.height = video.videoHeight;
        
    }

    function stopWebcam() {
        if (mediaStream) {
            mediaStream.getTracks().forEach((t) => t.stop());
            mediaStream = null;
        }
    }

    function captureFrameAsBase64() {
        captureCanvas.width = video.videoWidth;
        captureCanvas.height = video.videoHeight;
        captureCanvas.getContext("2d").drawImage(video, 0, 0, captureCanvas.width, captureCanvas.height);
        return captureCanvas.toDataURL("image/jpeg", 0.8);
    }

    function drawOverlay(faces) {
        const ctx = overlayCanvas.getContext("2d");
        ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

        faces.forEach((face) => {
            const [top, right, bottom, left] = face.box;
            const color = face.status === "unknown" ? "#e63946" : "#2ec4b6";

            // Because the <video> preview is mirrored via CSS (scaleX(-1)),
            // flip the box horizontally to match what the user visually sees.
            const mirroredLeft = overlayCanvas.width - right;
            const mirroredRight = overlayCanvas.width - left;

            ctx.strokeStyle = color;
            ctx.lineWidth = 2;
            ctx.strokeRect(mirroredLeft, top, mirroredRight - mirroredLeft, bottom - top);

            const label = face.name === "Unknown" ? "Unknown" : `${face.name} (${Math.round(face.confidence * 100)}%)`;
            ctx.fillStyle = color;
            ctx.font = "14px sans-serif";
            const textWidth = ctx.measureText(label).width;
            ctx.fillRect(mirroredLeft, bottom, textWidth + 10, 22);
            ctx.fillStyle = "#fff";
            ctx.fillText(label, mirroredLeft + 5, bottom + 16);
        });
    }

    // function addLogEntry(face) {
    //     const key = face.roll_number || face.name;
    //     if (face.status !== "marked" || markedThisSession.has(key)) return;
    //     markedThisSession.add(key);

    //     const subjectLabel = subjectSelect.options[subjectSelect.selectedIndex]?.text || "";
    //     const li = document.createElement("li");
    //     li.className = "list-group-item";
    //     li.innerHTML = `
    //         <span>
    //             <i class="bi bi-check-circle-fill text-success"></i> ${face.name} (${face.roll_number})
    //             <span class="d-block text-muted small">${subjectLabel}</span>
    //         </span>
    //         <span class="text-muted small">${new Date().toLocaleTimeString()}</span>
    //     `;
    //     recognitionLog.prepend(li);
    // }

    function addLogEntry(face) {
        const key = face.roll_number || face.name;

        // Show only newly marked attendance.
        // Ignore already_marked, cooldown, unknown and error statuses.
        if (face.status !== "marked" || markedThisSession.has(key)) {
            return;
        }

        markedThisSession.add(key);

        const subjectLabel =
            subjectSelect.options[subjectSelect.selectedIndex]?.text || "";

        const li = document.createElement("li");
        li.className = "list-group-item";

        const details = document.createElement("span");

        const icon = document.createElement("i");
        icon.className = "bi bi-check-circle-fill text-success me-1";

        details.appendChild(icon);
        details.appendChild(
            document.createTextNode(
                ` ${face.name} (${face.roll_number})`
            )
        );

        const subject = document.createElement("span");
        subject.className = "d-block text-muted small";
        subject.textContent = subjectLabel;

        details.appendChild(subject);

        const time = document.createElement("span");
        time.className = "text-muted small";
        time.textContent = new Date().toLocaleTimeString();

        li.appendChild(details);
        li.appendChild(time);

        recognitionLog.prepend(li);
    }

    async function processFrame() {
        const imageData = captureFrameAsBase64();
        try {
            const response = await fetch(PROCESS_FRAME_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ image: imageData, subject_id: activeSubjectId }),
            });
            const result = await response.json();
            if (!result.success) return;

            drawOverlay(result.faces);
            result.faces.forEach(addLogEntry);
        } catch (err) {
            console.error("Recognition frame failed:", err);
        }
    }

    startBtn.addEventListener("click", async () => {
        if (!subjectSelect.value) {
            subjectSelect.classList.add("is-invalid");
            subjectSelect.reportValidity();
            return;
        }
        subjectSelect.classList.remove("is-invalid");

        activeSubjectId = subjectSelect.value;
        activeSubjectName.textContent = subjectSelect.options[subjectSelect.selectedIndex].text;
        activeSubjectBanner.classList.remove("d-none");
        subjectSelect.disabled = true; // lock the lecture for the whole session — no switching mid-scan

        if (!mediaStream) await startWebcam();
        startBtn.classList.add("d-none");
        stopBtn.classList.remove("d-none");
        intervalId = setInterval(processFrame, 1200);
    });

    stopBtn.addEventListener("click", () => {
        clearInterval(intervalId);
        stopWebcam();
        startBtn.classList.remove("d-none");
        stopBtn.classList.add("d-none");
        subjectSelect.disabled = false;
        activeSubjectBanner.classList.add("d-none");
        activeSubjectId = null;
        overlayCanvas.getContext("2d").clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
    });

    window.addEventListener("beforeunload", stopWebcam);
})();

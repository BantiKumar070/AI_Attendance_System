
/**
 * static/js/webcam.js
 * ====================
 * Face Capture Wizard
 *
 * Flow:
 * 1. Open webcam
 * 2. Click Start Capture
 * 3. Capture one frame
 * 4. Send frame to Flask
 * 5. Flask detects exactly one face
 * 6. Save image
 * 7. Repeat until REQUIRED_SAMPLES
 * 8. Generate face encodings
 */

(() => {
    "use strict";

    // ---------------------------------------------------------
    // DOM ELEMENTS
    // ---------------------------------------------------------

    const video = document.getElementById("webcamVideo");
    const canvas = document.getElementById("captureCanvas");

    const startBtn =
        document.getElementById("startCaptureBtn");

    const stopBtn =
        document.getElementById("stopCaptureBtn");

    const generateBtn =
        document.getElementById("generateEncodingsBtn");

    const progressBar =
        document.getElementById("captureProgressBar");

    const progressText =
        document.getElementById("captureProgressText");

    const overlayMsg =
        document.getElementById("faceOverlayMsg");

    const statusMsg =
        document.getElementById("captureStatusMsg");


    // ---------------------------------------------------------
    // VALIDATE REQUIRED ELEMENTS
    // ---------------------------------------------------------

    if (
        !video ||
        !canvas ||
        !startBtn ||
        !stopBtn ||
        !generateBtn ||
        !progressBar ||
        !progressText ||
        !statusMsg
    ) {
        console.error(
            "Face Capture: Required HTML elements are missing."
        );

        return;
    }


    // ---------------------------------------------------------
    // STATE
    // ---------------------------------------------------------

    let mediaStream = null;

    let isCapturing = false;

    let captureInProgress = false;

    let capturedCount =
        parseInt(
            progressText.textContent
                .split("/")[0]
                .trim(),
            10
        ) || 0;


    // ---------------------------------------------------------
    // STATUS MESSAGE
    // ---------------------------------------------------------

    function showStatus(message, type = "info") {

        statusMsg.innerHTML = `
            <div class="alert alert-${type}">
                ${message}
            </div>
        `;
    }


    // ---------------------------------------------------------
    // OVERLAY MESSAGE
    // ---------------------------------------------------------

    function showOverlay(message) {

        if (!overlayMsg) return;

        overlayMsg.textContent = message;

        overlayMsg.classList.add("show");
    }


    function hideOverlay() {

        if (!overlayMsg) return;

        overlayMsg.textContent = "";

        overlayMsg.classList.remove("show");
    }


    // ---------------------------------------------------------
    // CAMERA ERROR MESSAGE
    // ---------------------------------------------------------

    function getCameraErrorMessage(error) {

        if (!error) {
            return "Unable to access camera.";
        }


        switch (error.name) {

            case "NotAllowedError":

                return `
                    Camera permission was denied.
                    Please allow camera access for this website
                    and reload the page.
                `;


            case "PermissionDeniedError":

                return `
                    Camera permission was denied.
                    Please allow camera access in browser settings.
                `;


            case "NotFoundError":

                return `
                    No camera was found on this device.
                `;


            case "NotReadableError":

                return `
                    Camera is already being used by another application.
                    Close other camera applications and try again.
                `;


            case "OverconstrainedError":

                return `
                    The requested camera configuration is not available.
                    Trying a simpler camera configuration.
                `;


            case "SecurityError":

                return `
                    Browser security blocked camera access.
                    Use localhost or HTTPS.
                `;


            default:

                return `
                    Unable to access camera.
                    Error: ${error.name || "Unknown error"}
                `;
        }
    }


    // ---------------------------------------------------------
    // START WEBCAM
    // ---------------------------------------------------------

    async function startWebcam() {

        // Camera already running
        if (
            mediaStream &&
            mediaStream.active
        ) {

            return true;
        }


        // Browser support check
        if (
            !navigator.mediaDevices ||
            !navigator.mediaDevices.getUserMedia
        ) {

            showStatus(
                "Camera API is not supported by this browser. Please use a modern Chrome/Edge browser.",
                "danger"
            );

            return false;
        }


        try {

            console.log(
                "Requesting camera permission..."
            );


            // First try normal configuration
            try {

                mediaStream =
                    await navigator.mediaDevices.getUserMedia({

                        video: {
                            width: {
                                ideal: 640
                            },

                            height: {
                                ideal: 480
                            },

                            facingMode: "user"
                        },

                        audio: false
                    });

            } catch (firstError) {

                console.warn(
                    "Preferred camera configuration failed:",
                    firstError
                );


                // Fallback:
                // ask for any available camera
                mediaStream =
                    await navigator.mediaDevices.getUserMedia({

                        video: true,

                        audio: false
                    });
            }


            // Attach stream to video
            video.srcObject =
                mediaStream;


            // Important for Chrome
            video.muted = true;

            video.playsInline = true;

            video.autoplay = true;


            // Wait until video metadata is ready
            await new Promise(
                (resolve) => {

                    if (
                        video.readyState >= 2
                    ) {

                        resolve();

                        return;
                    }


                    video.onloadedmetadata =
                        () => {

                            resolve();

                        };
                }
            );


            // Explicitly start playback
            try {

                await video.play();

            } catch (playError) {

                console.warn(
                    "Video play() warning:",
                    playError
                );
            }


            console.log(
                "Camera started successfully."
            );


            showStatus(
                "Camera connected successfully. Click Start Capture.",
                "success"
            );


            return true;

        } catch (error) {

            console.error(
                "Camera access error:",
                error
            );


            mediaStream = null;


            showStatus(
                getCameraErrorMessage(error),
                "danger"
            );


            return false;
        }
    }


    // ---------------------------------------------------------
    // STOP WEBCAM
    // ---------------------------------------------------------

    function stopWebcam() {

        if (mediaStream) {

            mediaStream
                .getTracks()
                .forEach(
                    (track) => {

                        track.stop();

                    }
                );


            mediaStream = null;
        }


        if (video) {

            video.srcObject = null;
        }
    }


    // ---------------------------------------------------------
    // CAPTURE FRAME
    // ---------------------------------------------------------

    function captureFrameAsBase64() {

        // Make sure video is actually ready
        if (
            !video.videoWidth ||
            !video.videoHeight
        ) {

            throw new Error(
                "Camera video is not ready yet."
            );
        }


        canvas.width =
            video.videoWidth;

        canvas.height =
            video.videoHeight;


        const ctx =
            canvas.getContext("2d");


        if (!ctx) {

            throw new Error(
                "Could not create canvas context."
            );
        }


        /*
         * Do NOT mirror the image here.
         *
         * CSS may mirror the preview,
         * but the actual image sent to Flask
         * remains normal.
         */

        ctx.drawImage(
            video,
            0,
            0,
            canvas.width,
            canvas.height
        );


        return canvas.toDataURL(
            "image/jpeg",
            0.85
        );
    }


    // ---------------------------------------------------------
    // SEND ONE FRAME TO FLASK
    // ---------------------------------------------------------

    async function sendFrame() {

        if (!isCapturing) {

            return;
        }


        // Prevent multiple requests at once
        if (captureInProgress) {

            return;
        }


        if (
            capturedCount >=
            REQUIRED_SAMPLES
        ) {

            finishCapture();

            return;
        }


        captureInProgress = true;


        try {

            const imageData =
                captureFrameAsBase64();


            console.log(
                `Sending frame... ${capturedCount}/${REQUIRED_SAMPLES}`
            );


            const response =
                await fetch(
                    CAPTURE_FRAME_URL,
                    {

                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json",

                            "Accept":
                                "application/json"
                        },

                        body: JSON.stringify({
                            image: imageData
                        })
                    }
                );


            /*
             * Check HTTP status first.
             */

            if (!response.ok) {

                const errorText =
                    await response.text();

                throw new Error(
                    `Server returned ${response.status}: ${errorText}`
                );
            }


            /*
             * Backend should return JSON.
             */

            const result =
                await response.json();


            console.log(
                "Capture response:",
                result
            );


            if (result.success) {

                capturedCount =
                    Number(result.count) ||
                    capturedCount + 1;


                updateProgress();

                hideOverlay();


                showStatus(
                    `Image captured successfully (${capturedCount}/${REQUIRED_SAMPLES})`,
                    "success"
                );


                if (
                    capturedCount >=
                    REQUIRED_SAMPLES
                ) {

                    finishCapture();
                }

            } else {

                /*
                 * This is NOT a camera error.
                 *
                 * Flask may say:
                 * - No face detected
                 * - Multiple faces detected
                 */

                showOverlay(
                    result.message ||
                    "Adjust your face position..."
                );


                console.log(
                    "Frame rejected:",
                    result.message
                );
            }

        } catch (error) {

            console.error(
                "Frame capture failed:",
                error
            );


            showStatus(
                `
                Capture request failed.
                <br>
                <small>${escapeHtml(
                    error.message
                )}</small>
                `,
                "danger"
            );

        } finally {

            captureInProgress = false;
        }
    }


    // ---------------------------------------------------------
    // SAFE HTML ESCAPE
    // ---------------------------------------------------------

    function escapeHtml(value) {

        return String(value)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }


    // ---------------------------------------------------------
    // UPDATE PROGRESS
    // ---------------------------------------------------------

    function updateProgress() {

        const required =
            Number(REQUIRED_SAMPLES) || 1;


        const percent =
            Math.min(
                100,
                Math.round(
                    (
                        capturedCount /
                        required
                    ) * 100
                )
            );


        progressBar.style.width =
            `${percent}%`;


        progressText.textContent =
            `${capturedCount} / ${REQUIRED_SAMPLES}`;
    }


    // ---------------------------------------------------------
    // START CAPTURE LOOP
    // ---------------------------------------------------------

    async function startCapture() {

        if (isCapturing) {

            return;
        }


        /*
         * Make absolutely sure camera is available.
         */

        if (
            !mediaStream ||
            !mediaStream.active
        ) {

            const cameraStarted =
                await startWebcam();


            if (!cameraStarted) {

                return;
            }
        }


        /*
         * Make sure video actually contains frames.
         */

        if (
            !video.videoWidth ||
            !video.videoHeight
        ) {

            showStatus(
                "Camera is connected but video is not ready yet. Please wait a moment and try again.",
                "warning"
            );

            return;
        }


        isCapturing = true;


        startBtn.classList.add(
            "d-none"
        );


        stopBtn.classList.remove(
            "d-none"
        );


        hideOverlay();


        showStatus(
            "Face capture started. Slowly move your head left and right.",
            "info"
        );


        /*
         * Capture immediately.
         */

        await sendFrame();


        /*
         * Then capture sequentially.
         *
         * We intentionally DON'T use setInterval()
         * because multiple POST requests can overlap.
         */

        async function captureLoop() {

            while (
                isCapturing &&
                capturedCount <
                    REQUIRED_SAMPLES
            ) {

                await new Promise(
                    (resolve) =>
                        setTimeout(
                            resolve,
                            500
                        )
                );


                if (!isCapturing) {

                    break;
                }


                await sendFrame();
            }
        }


        captureLoop();
    }


    // ---------------------------------------------------------
    // FINISH CAPTURE
    // ---------------------------------------------------------

    function finishCapture() {

        isCapturing = false;

        captureInProgress = false;


        startBtn.classList.add(
            "d-none"
        );


        stopBtn.classList.add(
            "d-none"
        );


        generateBtn.classList.remove(
            "d-none"
        );


        updateProgress();


        showStatus(
            `
            <strong>All images captured!</strong>
            <br>
            Click "Generate Face Encodings" to finish enrollment.
            `,
            "success"
        );


        hideOverlay();
    }


    // ---------------------------------------------------------
    // STOP CAPTURE
    // ---------------------------------------------------------

    function stopCapture() {

        isCapturing = false;

        captureInProgress = false;


        startBtn.classList.remove(
            "d-none"
        );


        stopBtn.classList.add(
            "d-none"
        );


        showStatus(
            "Capture stopped. Click Start Capture to continue.",
            "warning"
        );
    }


    // ---------------------------------------------------------
    // GENERATE FACE ENCODINGS
    // ---------------------------------------------------------

    async function generateEncodings() {

        generateBtn.disabled = true;


        generateBtn.innerHTML =
            `
            <span class="spinner-border spinner-border-sm"></span>
            Generating...
            `;


        showStatus(
            "Generating face encodings. Please wait...",
            "info"
        );


        try {

            const response =
                await fetch(
                    GENERATE_ENCODINGS_URL,
                    {

                        method: "POST",

                        headers: {
                            "Accept":
                                "application/json"
                        }
                    }
                );


            if (!response.ok) {

                const errorText =
                    await response.text();

                throw new Error(
                    `Server returned ${response.status}: ${errorText}`
                );
            }


            const result =
                await response.json();


            console.log(
                "Encoding response:",
                result
            );


            if (result.success) {

                showStatus(
                    result.message ||
                    "Face encodings generated successfully.",
                    "success"
                );


                stopWebcam();


                setTimeout(
                    () => {

                        window.location.href =
                            "/students/";

                    },
                    1500
                );

            } else {

                showStatus(
                    result.message ||
                    "Failed to generate face encodings.",
                    "danger"
                );


                generateBtn.disabled =
                    false;


                generateBtn.innerHTML =
                    `
                    <i class="bi bi-cpu-fill"></i>
                    Generate Face Encodings
                    `;
            }

        } catch (error) {

            console.error(
                "Encoding generation failed:",
                error
            );


            showStatus(
                `
                Failed to generate face encodings.
                <br>
                <small>${escapeHtml(
                    error.message
                )}</small>
                `,
                "danger"
            );


            generateBtn.disabled =
                false;


            generateBtn.innerHTML =
                `
                <i class="bi bi-cpu-fill"></i>
                Generate Face Encodings
                `;
        }
    }


    // ---------------------------------------------------------
    // BUTTON EVENTS
    // ---------------------------------------------------------

    startBtn.addEventListener(
        "click",
        startCapture
    );


    stopBtn.addEventListener(
        "click",
        stopCapture
    );


    generateBtn.addEventListener(
        "click",
        generateEncodings
    );


    // ---------------------------------------------------------
    // PAGE LOAD
    // ---------------------------------------------------------

    updateProgress();


    /*
     * Start camera automatically.
     *
     * This is why your live preview should appear
     * before clicking Start Capture.
     */

    startWebcam();


    // ---------------------------------------------------------
    // CLEANUP
    // ---------------------------------------------------------

    window.addEventListener(
        "beforeunload",
        () => {

            isCapturing = false;

            stopWebcam();

        }
    );

})();

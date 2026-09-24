
/**
 * static/js/charts.js
 * ====================
 * Dashboard charts using native Canvas.
 */

document.addEventListener("DOMContentLoaded", () => {
    renderWeeklyTrendChart();
    renderClassDistributionChart();
});


/* =========================================================
   CANVAS SETUP
   ========================================================= */

function setupCanvas(canvas) {

    const rect = canvas.getBoundingClientRect();

    const width = Math.max(rect.width, 320);
    const height = Math.max(rect.height, 260);

    const dpr = window.devicePixelRatio || 1;

    canvas.width = width * dpr;
    canvas.height = height * dpr;

    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;

    const ctx = canvas.getContext("2d");

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    ctx.clearRect(0, 0, width, height);

    return {
        ctx,
        width,
        height
    };
}


/* =========================================================
   EMPTY DATA MESSAGE
   ========================================================= */

function drawMessage(canvas, message) {

    const { ctx, width, height } =
        setupCanvas(canvas);

    ctx.fillStyle = "#6c757d";

    ctx.font =
        "14px Arial, sans-serif";

    ctx.textAlign = "center";

    ctx.textBaseline = "middle";

    ctx.fillText(
        message,
        width / 2,
        height / 2
    );
}


/* =========================================================
   WEEKLY ATTENDANCE TREND
   ========================================================= */

function renderWeeklyTrendChart() {

    const canvas =
        document.getElementById(
            "weeklyTrendChart"
        );

    if (!canvas) return;


    // IMPORTANT:
    // dashboard.html defines weeklyTrendData
    // using `const`, so use the variable directly.
    if (
        typeof weeklyTrendData === "undefined"
    ) {

        drawMessage(
            canvas,
            "Attendance data unavailable"
        );

        return;
    }


    const labels =
        Array.isArray(
            weeklyTrendData.labels
        )
            ? weeklyTrendData.labels
            : [];


    const values =
        Array.isArray(
            weeklyTrendData.values
        )
            ? weeklyTrendData.values.map(
                value => Number(value) || 0
            )
            : [];


    if (
        labels.length === 0 ||
        values.length === 0
    ) {

        drawMessage(
            canvas,
            "No attendance data available"
        );

        return;
    }


    const {
        ctx,
        width,
        height
    } = setupCanvas(canvas);


    const padding = {
        top: 25,
        right: 25,
        bottom: 45,
        left: 45
    };


    const chartWidth =
        width -
        padding.left -
        padding.right;


    const chartHeight =
        height -
        padding.top -
        padding.bottom;


    const maxValue =
        Math.max(...values, 1);


    const ySteps = 5;


    /* -------------------------
       GRID
       ------------------------- */

    ctx.strokeStyle =
        "#e9ecef";

    ctx.fillStyle =
        "#6c757d";

    ctx.font =
        "12px Arial, sans-serif";

    ctx.textAlign =
        "right";

    ctx.textBaseline =
        "middle";


    for (
        let i = 0;
        i <= ySteps;
        i++
    ) {

        const y =
            padding.top +
            chartHeight -
            (i / ySteps) *
            chartHeight;


        const value =
            Math.round(
                (i / ySteps) *
                maxValue
            );


        ctx.beginPath();

        ctx.moveTo(
            padding.left,
            y
        );

        ctx.lineTo(
            width -
            padding.right,
            y
        );

        ctx.stroke();


        ctx.fillText(
            String(value),
            padding.left - 8,
            y
        );
    }


    /* -------------------------
       POINTS
       ------------------------- */

    const xStep =
        labels.length === 1
            ? 0
            : chartWidth /
              (labels.length - 1);


    const points =
        values.map(
            (value, index) => {

                return {

                    x:
                        padding.left +
                        index * xStep,

                    y:
                        padding.top +
                        chartHeight -
                        (value / maxValue) *
                        chartHeight,

                    value
                };
            }
        );


    /* -------------------------
       AREA
       ------------------------- */

    ctx.beginPath();


    points.forEach(
        (point, index) => {

            if (index === 0) {

                ctx.moveTo(
                    point.x,
                    point.y
                );

            } else {

                ctx.lineTo(
                    point.x,
                    point.y
                );
            }
        }
    );


    if (points.length > 1) {

        ctx.lineTo(
            points[
                points.length - 1
            ].x,

            padding.top +
            chartHeight
        );


        ctx.lineTo(
            points[0].x,

            padding.top +
            chartHeight
        );


        ctx.closePath();


        ctx.fillStyle =
            "rgba(67, 97, 238, 0.10)";

        ctx.fill();
    }


    /* -------------------------
       LINE
       ------------------------- */

    ctx.beginPath();


    points.forEach(
        (point, index) => {

            if (index === 0) {

                ctx.moveTo(
                    point.x,
                    point.y
                );

            } else {

                ctx.lineTo(
                    point.x,
                    point.y
                );
            }
        }
    );


    ctx.strokeStyle =
        "#4361ee";

    ctx.lineWidth = 3;

    ctx.lineJoin =
        "round";

    ctx.lineCap =
        "round";

    ctx.stroke();


    /* -------------------------
       POINTS + LABELS
       ------------------------- */

    points.forEach(
        (point, index) => {

            ctx.beginPath();

            ctx.arc(
                point.x,
                point.y,
                4,
                0,
                Math.PI * 2
            );


            ctx.fillStyle =
                "#4361ee";

            ctx.fill();


            ctx.fillStyle =
                "#6c757d";

            ctx.font =
                "11px Arial, sans-serif";

            ctx.textAlign =
                "center";

            ctx.textBaseline =
                "top";


            const date =
                String(
                    labels[index]
                );


            // Show only MM-DD
            const shortDate =
                date.length >= 10
                    ? date.substring(5)
                    : date;


            ctx.fillText(
                shortDate,
                point.x,
                padding.top +
                chartHeight +
                12
            );
        }
    );
}


/* =========================================================
   STUDENTS PER CLASS
   ========================================================= */

function renderClassDistributionChart() {

    const canvas =
        document.getElementById(
            "classDistributionChart"
        );

    if (!canvas) return;


    // IMPORTANT:
    // Directly access const variable
    // from dashboard.html.
    if (
        typeof classDistributionData ===
        "undefined"
    ) {

        drawMessage(
            canvas,
            "Class data unavailable"
        );

        return;
    }


    const labels =
        Array.isArray(
            classDistributionData.labels
        )
            ? classDistributionData.labels
            : [];


    const values =
        Array.isArray(
            classDistributionData.values
        )
            ? classDistributionData.values.map(
                value => Number(value) || 0
            )
            : [];


    const total =
        values.reduce(
            (sum, value) =>
                sum + value,
            0
        );


    if (
        labels.length === 0 ||
        total === 0
    ) {

        drawMessage(
            canvas,
            "No class data available"
        );

        return;
    }


    const {
        ctx,
        width,
        height
    } = setupCanvas(canvas);


    const colors = [
        "#4361ee",
        "#2ec4b6",
        "#ff9f1c",
        "#e63946",
        "#7209b7",
        "#4cc9f0"
    ];


    const centerX =
        width / 2;


    const centerY =
        height * 0.40;


    const radius =
        Math.min(
            width,
            height
        ) * 0.28;


    const innerRadius =
        radius * 0.55;


    let startAngle =
        -Math.PI / 2;


    /* -------------------------
       DOUGHNUT
       ------------------------- */

    values.forEach(
        (value, index) => {

            if (value <= 0) return;


            const angle =
                (
                    value /
                    total
                ) *
                Math.PI *
                2;


            const endAngle =
                startAngle +
                angle;


            ctx.beginPath();


            ctx.moveTo(
                centerX,
                centerY
            );


            ctx.arc(
                centerX,
                centerY,
                radius,
                startAngle,
                endAngle
            );


            ctx.closePath();


            ctx.fillStyle =
                colors[
                    index %
                    colors.length
                ];


            ctx.fill();


            startAngle =
                endAngle;
        }
    );


    /* -------------------------
       INNER CIRCLE
       ------------------------- */

    ctx.beginPath();


    ctx.arc(
        centerX,
        centerY,
        innerRadius,
        0,
        Math.PI * 2
    );


    ctx.fillStyle =
        "#ffffff";


    ctx.fill();


    /* -------------------------
       TOTAL
       ------------------------- */

    ctx.fillStyle =
        "#212529";

    ctx.font =
        "bold 20px Arial, sans-serif";

    ctx.textAlign =
        "center";

    ctx.textBaseline =
        "middle";


    ctx.fillText(
        String(total),
        centerX,
        centerY
    );


    /* -------------------------
       LEGEND
       ------------------------- */

    ctx.font =
        "12px Arial, sans-serif";

    ctx.textAlign =
        "left";

    ctx.textBaseline =
        "middle";


    const legendStartY =
        centerY +
        radius +
        30;


    labels.forEach(
        (label, index) => {

            const value =
                values[index] || 0;


            if (value <= 0) return;


            const column =
                index % 2;


            const row =
                Math.floor(
                    index / 2
                );


            const x =
                column === 0
                    ? 15
                    : width / 2 + 5;


            const y =
                legendStartY +
                row * 22;


            ctx.fillStyle =
                colors[
                    index %
                    colors.length
                ];


            ctx.fillRect(
                x,
                y - 5,
                10,
                10
            );


            ctx.fillStyle =
                "#495057";


            ctx.fillText(
                `${label} (${value})`,
                x + 16,
                y
            );
        }
    );
}


/* =========================================================
   RESIZE
   ========================================================= */

let resizeTimer = null;


window.addEventListener(
    "resize",
    () => {

        clearTimeout(
            resizeTimer
        );


        resizeTimer =
            setTimeout(
                () => {

                    renderWeeklyTrendChart();

                    renderClassDistributionChart();

                },
                150
            );
    }
);
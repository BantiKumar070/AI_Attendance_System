"""
services/export_service.py
============================
Generates downloadable Excel (.xlsx) and PDF attendance reports from a
list of Attendance records, saved into the exports/ folder.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import List

import pandas as pd
from flask import current_app
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from models import Attendance
from utils.logger import get_logger

logger = get_logger(__name__)


class ExportService:
    """Builds Excel / PDF exports of attendance data."""

    def _rows_to_dataframe(self, records: List[Attendance]) -> pd.DataFrame:
        data = [
            {
                "Roll Number": r.student.roll_number if r.student else "",
                "Name": r.student.name if r.student else "",
                "Class": f"{r.class_room.name} {r.class_room.section}" if r.class_room else "",
                "Subject": r.subject.name if r.subject else "General",
                "Date": r.attendance_date.strftime("%Y-%m-%d"),
                "Time": r.time_in.strftime("%H:%M:%S"),
                "Status": r.status.title(),
                "Marked By": r.marked_by.replace("_", " ").title(),
            }
            for r in records
        ]
        return pd.DataFrame(data)

    def export_to_excel(self, records: List[Attendance], filename_prefix: str = "attendance") -> str:
        """
        Write attendance records to a formatted .xlsx file.

        Returns:
            The absolute filepath of the generated Excel file.
        """
        df = self._rows_to_dataframe(records)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.xlsx"
        filepath = os.path.join(current_app.config["EXPORTS_FOLDER"], filename)

        with pd.ExcelWriter(filepath, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Attendance")
            worksheet = writer.sheets["Attendance"]
            workbook = writer.book

            header_format = workbook.add_format(
                {"bold": True, "bg_color": "#4361ee", "font_color": "white", "border": 1}
            )
            for col_idx, column_name in enumerate(df.columns):
                worksheet.write(0, col_idx, column_name, header_format)
                max_width = max(df[column_name].astype(str).map(len).max() if not df.empty else 10, len(column_name))
                worksheet.set_column(col_idx, col_idx, max_width + 4)

        logger.info("Excel export generated: %s (%d rows)", filepath, len(df))
        return filepath

    def export_to_pdf(self, records: List[Attendance], filename_prefix: str = "attendance", title: str = "Attendance Report") -> str:
        """
        Write attendance records to a formatted PDF report.

        Returns:
            The absolute filepath of the generated PDF file.
        """
        df = self._rows_to_dataframe(records)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.pdf"
        filepath = os.path.join(current_app.config["EXPORTS_FOLDER"], filename)

        doc = SimpleDocTemplate(filepath, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = [
            Paragraph(title, styles["Title"]),
            Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]),
            Spacer(1, 16),
        ]

        table_data = [list(df.columns)] + df.astype(str).values.tolist() if not df.empty else [list(df.columns)]
        table = Table(table_data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4361ee")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6fb")]),
                ]
            )
        )
        elements.append(table)
        doc.build(elements)

        logger.info("PDF export generated: %s (%d rows)", filepath, len(df))
        return filepath

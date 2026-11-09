"""
Universal Report Generation Engine.
Supports:
- Formatted PDF generation via ReportLab (landscape & portrait, styled tables, metadata, clean typography)
- Multi-sheet Excel (XLSX) generation via openpyxl
- Standardized CSV exports
- Individual student report cards with recommendations and attendance
"""

import pandas as pd
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

import database
from utils.analysis import (
    get_student_performance,
    get_subject_analysis,
    get_department_performance,
    get_semester_performance,
)
from utils.recommendations import generate_student_recommendations


def generate_pdf_report(dataframe: pd.DataFrame, title: str, subtitle: str = None) -> bytes:
    """
    Builds a PDF document from a DataFrame with styling.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=32,
        leftMargin=32,
        topMargin=32,
        bottomMargin=32,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        name="RepTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        alignment=0,
    )

    sub_style = ParagraphStyle(
        name="RepSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#64748b"),
    )

    elements = [
        Paragraph("STUDENT PERFORMANCE INTELLIGENCE SYSTEM", sub_style),
        Spacer(1, 4),
        Paragraph(title, title_style),
        Spacer(1, 4),
    ]

    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    elements.append(Paragraph(f"Dossier generated on {timestamp_str} | Official Academic Record", sub_style))
    if subtitle:
        elements.append(Paragraph(subtitle, sub_style))

    elements.append(Spacer(1, 16))

    # Convert DataFrame into table elements
    cols = list(dataframe.columns)
    table_data = [cols]

    for _, row in dataframe.iterrows():
        formatted_row = []
        for v in row:
            if isinstance(v, float):
                formatted_row.append(f"{v:.2f}")
            else:
                formatted_row.append(str(v) if pd.notna(v) else "-")
        table_data.append(formatted_row)

    col_count = len(cols)
    col_width = (doc.width) / max(col_count, 1)

    table = Table(table_data, colWidths=[col_width] * col_count, repeatRows=1)
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#ffffff")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8.5),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("PADDING", (0, 1), (-1, -1), 5),
            ("FONTSIZE", (0, 1), (-1, -1), 7.5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ])
    )

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def generate_student_report_card_pdf(student_id: int, exam_id=None, allow_all=False) -> bytes:
    """
    Builds an Individual Academic Report Card with subject marks, attendance, and recommendations
    scoped to a specific examination milestone or comprehensive aggregate.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        name="CardTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
        alignment=1,
    )

    heading_style = ParagraphStyle(
        name="CardHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1e293b"),
    )

    body_style = ParagraphStyle(
        name="CardBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=14,
        textColor=colors.HexColor("#334155"),
    )

    rec = generate_student_recommendations(student_id, exam_id=exam_id, allow_all=allow_all)
    if not rec:
        return b""

    students = database.get_students()
    s_info = students[students["id"] == student_id].iloc[0]
    exam_scope_str = rec.get("exam_scope", "Selected Examination")

    elements = [
        Paragraph("OFFICIAL ACADEMIC REPORT CARD", title_style),
        Spacer(1, 4),
        Paragraph(f"STUDENT PERFORMANCE INTELLIGENCE SYSTEM | {exam_scope_str.upper()}", ParagraphStyle(name="Sub", parent=body_style, alignment=1)),
        Spacer(1, 16),
    ]

    # Student Details Table
    att_str = f"{rec['attendance']:.1f}%" if rec["attendance"] is not None else "Not Recorded"
    details = [
        ["Student Name", rec["name"], "Student ID", str(rec["id"])],
        ["Department", s_info["department"], "Semester", str(s_info["semester"])],
        ["Evaluation Scope", exam_scope_str, "Institutional Rank", str(rec["rank"])],
        ["Cohort Average", f"{rec['average']:.2f}", "Overall Grade", rec["grade"]],
        ["Attendance Rate", att_str, "Risk Level", rec["risk_level"]],
    ]

    d_table = Table(details, colWidths=[120, 140, 120, 140])
    d_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f1f5f9")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ])
    )
    elements.append(d_table)
    elements.append(Spacer(1, 18))

    # Subject Marks Breakdown
    elements.append(Paragraph("Coursework & Subject Marks", heading_style))
    elements.append(Spacer(1, 8))

    subj_table_data = [["Subject", "Marks", "Status", "Evaluation Category"]]
    for item in rec["subjects"]:
        stat = "Pass" if item["marks"] >= 40.0 else "Fail"
        subj_table_data.append([item["subject"], f"{item['marks']:.1f}", stat, item["category"]])

    s_table = Table(subj_table_data, colWidths=[140, 80, 80, 220])
    s_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#ffffff")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ALIGN", (1, 0), (2, -1), "CENTER"),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ])
    )
    elements.append(s_table)
    elements.append(Spacer(1, 18))

    # Personalized Recommendations
    elements.append(Paragraph("Personalized Improvement Recommendations", heading_style))
    elements.append(Spacer(1, 6))

    for item in rec["subjects"]:
        advice_text = f"<b>{item['subject']}:</b> {item['advice']}"
        elements.append(Paragraph(advice_text, body_style))
        elements.append(Spacer(1, 4))

    elements.append(Spacer(1, 8))
    elements.append(Paragraph(f"<b>Overall Action Plan:</b> {rec['risk_action']}", body_style))
    elements.append(Spacer(1, 20))

    # Verification footer
    footer_text = f"Report generated automatically on {datetime.now().strftime('%Y-%m-%d')} | Academic Registrar Verification"
    elements.append(Paragraph(footer_text, ParagraphStyle(name="Foot", parent=body_style, fontSize=7.5, textColor=colors.HexColor("#94a3b8"), alignment=1)))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def generate_excel_dossier() -> bytes:
    """
    Generates a multi-sheet Excel workbook with student details, subject analysis, and attendance.
    """
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        perf = get_student_performance()
        if not perf.empty:
            perf.to_excel(writer, sheet_name="Performance", index=False)

        subj = get_subject_analysis()
        if not subj.empty:
            subj.to_excel(writer, sheet_name="Subjects", index=False)

        att = database.get_attendance_summary()
        if not att.empty:
            att.to_excel(writer, sheet_name="Attendance", index=False)

        dept = get_department_performance()
        if not dept.empty:
            dept.to_excel(writer, sheet_name="Departments", index=False)

    buffer.seek(0)
    return buffer.getvalue()


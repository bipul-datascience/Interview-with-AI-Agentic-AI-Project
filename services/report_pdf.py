"""Create a concise downloadable PDF from an AI interview report."""

from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _bullets(items: list[str], styles) -> list:
    return [Paragraph(f"- {item}", styles["BodyText"]) for item in items]


def generate_interview_report(*, report: dict, role: str, difficulty: str, interview_style: str) -> bytes:
    """Return a polished in-memory PDF; no user report is written to disk."""
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.7 * cm, leftMargin=1.7 * cm, topMargin=1.7 * cm, bottomMargin=1.7 * cm)
    styles = getSampleStyleSheet()
    story = [Paragraph("Get interview ready with AI", styles["Title"]), Paragraph("AI Mock Interview Report", styles["Heading2"]), Spacer(1, 8)]
    story += [Paragraph(f"<b>Role:</b> {role}<br/><b>Level:</b> {difficulty}<br/><b>Style:</b> {interview_style}<br/><b>Overall score:</b> {report['overall_score']}/100", styles["BodyText"]), Spacer(1, 10)]
    story += [Paragraph("Summary", styles["Heading2"]), Paragraph(report["summary"], styles["BodyText"]), Spacer(1, 8)]
    rows = [["Rubric", "Score"]] + [[item["dimension"], f"{item['score']}/100"] for item in report["rubric_scores"]]
    table = Table(rows, colWidths=[12.5 * cm, 3 * cm])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1D4ED8")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")), ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FAFC")), ("ALIGN", (1, 0), (1, -1), "CENTER"), ("PADDING", (0, 0), (-1, -1), 7)]))
    story += [Paragraph("Rubric scores", styles["Heading2"]), table, Spacer(1, 10)]
    story += [Paragraph("Strengths", styles["Heading2"]), *_bullets(report["strengths"], styles), Spacer(1, 8)]
    story += [Paragraph("Improvement areas", styles["Heading2"]), *_bullets(report["improvement_areas"], styles), Spacer(1, 8)]
    story += [Paragraph("Practice plan", styles["Heading2"]), *_bullets(report["practice_plan"], styles)]
    document.build(story)
    return buffer.getvalue()

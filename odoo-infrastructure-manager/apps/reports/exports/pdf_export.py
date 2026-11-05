from html import escape
from io import BytesIO

from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def build_pdf_response(report, rows, filename, filters):
    stream = BytesIO()
    page_size = landscape(A4)
    document = SimpleDocTemplate(
        stream,
        pagesize=page_size,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=report.title,
    )
    styles = getSampleStyleSheet()
    body_style = ParagraphStyle(
        "ReportCell",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=7,
        leading=8,
        alignment=TA_LEFT,
        wordWrap="CJK",
    )
    heading_style = ParagraphStyle(
        "ReportHeader",
        parent=body_style,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    elements = [
        Paragraph(escape(report.title), styles["Heading1"]),
        Paragraph(
            f"Generated {escape(timezone.localtime().isoformat())} · "
            f"{len(rows)} row(s)",
            body_style,
        ),
    ]
    filter_labels = []
    if filters.get("from"):
        filter_labels.append(f"From: {filters['from']}")
    if filters.get("to"):
        filter_labels.append(f"To: {filters['to']}")
    if filters.get("host"):
        filter_labels.append(f"Host ID: {filters['host']}")
    if filter_labels:
        elements.append(Paragraph(escape(" · ".join(filter_labels)), body_style))
    elements.append(Spacer(1, 5 * mm))

    table_data = [[
        Paragraph(escape(label), heading_style) for _, label in report.columns
    ]]
    for row in rows:
        table_data.append([
            Paragraph(
                escape(str(row.get(key) if row.get(key) is not None else "")),
                body_style,
            )
            for key, _ in report.columns
        ])
    available_width = page_size[0] - 24 * mm
    column_width = available_width / len(report.columns)
    table = Table(
        table_data,
        colWidths=[column_width] * len(report.columns),
        repeatRows=1,
        hAlign="LEFT",
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#243b53")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#b8c4ce")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f5f8")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(table)

    def draw_page_number(canvas, _document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#52606d"))
        canvas.drawRightString(
            page_size[0] - 12 * mm,
            7 * mm,
            f"Page {canvas.getPageNumber()}",
        )
        canvas.restoreState()

    document.build(
        elements,
        onFirstPage=draw_page_number,
        onLaterPages=draw_page_number,
    )
    response = HttpResponse(stream.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response

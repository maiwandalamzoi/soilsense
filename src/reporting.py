"""
Report generation — PDF and CSV export for field officers and programme staff.

We use ReportLab for PDF because it's pure Python (no system deps on
Streamlit Cloud) and gives us enough typographic control for a credible
one-pager. The layout is deliberately austere — tables, not charts —
because this is the kind of document that gets printed in the field.
"""

from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from src.erosion_model import ErosionEstimate
from src.ml_model import DegradationPrediction
from src.recommendations import Recommendation
from src.soil_health import SoilHealthResult


# --------------------------------------------------------------------------- #
# PDF
# --------------------------------------------------------------------------- #
def build_pdf_report(
    *,
    location_label: str,
    lon: float,
    lat: float,
    health: SoilHealthResult,
    erosion: ErosionEstimate,
    degradation: DegradationPrediction,
    recommendations: list[Recommendation],
) -> bytes:
    """Render a single-page PDF summary and return the bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title", parent=styles["Heading1"],
        fontName="Times-Bold", fontSize=18, textColor=colors.HexColor("#4A2E1A"),
        spaceAfter=4,
    )
    sub_style = ParagraphStyle(
        "sub", parent=styles["Normal"],
        fontName="Times-Italic", fontSize=10, textColor=colors.HexColor("#6B4A2E"),
        spaceAfter=14,
    )
    h2 = ParagraphStyle(
        "h2", parent=styles["Heading2"],
        fontName="Times-Bold", fontSize=13, textColor=colors.HexColor("#2D3A1F"),
        spaceBefore=10, spaceAfter=6,
    )
    body = ParagraphStyle(
        "body", parent=styles["Normal"],
        fontName="Times-Roman", fontSize=10, leading=13,
    )

    story = []

    # --- Header --------------------------------------------------------- #
    story.append(Paragraph("SoilSense — Soil Management Assessment", title_style))
    story.append(Paragraph(
        f"{location_label} &nbsp;·&nbsp; {lat:.4f}°, {lon:.4f}° &nbsp;·&nbsp; "
        f"Generated {datetime.utcnow().strftime('%Y-%m-%d')}",
        sub_style,
    ))

    # --- Headline scorecard --------------------------------------------- #
    story.append(Paragraph("Soil Health Scorecard", h2))
    headline = [[
        f"Overall: {health.overall:.0f}/100 (Grade {health.grade})",
        f"Erosion risk: {erosion.risk_class} ({erosion.soil_loss_t_ha_yr} t/ha/yr)",
        f"Degradation probability: {degradation.probability*100:.0f}% ({degradation.risk_label})",
    ]]
    headline_tbl = Table(headline, colWidths=[5.6 * cm, 5.6 * cm, 5.6 * cm])
    headline_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F2ECDB")),
        ("FONTNAME", (0, 0), (-1, -1), "Times-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#A0522D")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#A0522D")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(headline_tbl)
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(health.summary, body))

    # --- Indicator breakdown -------------------------------------------- #
    story.append(Paragraph("Indicator Breakdown", h2))
    rows = [["Indicator", "Value", "Score", "Note"]]
    for s in health.subscores:
        val = "—" if s.value is None else f"{s.value:.2f} {s.unit}".strip()
        rows.append([s.name, val, f"{s.score:.0f}/100", s.note])
    tbl = Table(rows, colWidths=[5 * cm, 3.5 * cm, 2.3 * cm, 6.2 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2D3A1F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAF7F2")]),
    ]))
    story.append(tbl)

    # --- Erosion -------------------------------------------------------- #
    story.append(Paragraph("Erosion Assessment (RUSLE)", h2))
    story.append(Paragraph(erosion.narrative, body))
    f = erosion.factors
    fac_rows = [
        ["R", f"{f['R']:.1f}"],
        ["K", f"{f['K']:.3f}"],
        ["LS", f"{f['LS']:.2f}"],
        ["C", f"{f['C']:.3f}"],
        ["P", f"{f['P']:.2f}"],
    ]
    fac_tbl = Table(fac_rows, colWidths=[2 * cm, 3 * cm])
    fac_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ]))
    story.append(fac_tbl)

    # --- Recommendations ------------------------------------------------ #
    story.append(Paragraph("Recommended Practices", h2))
    for i, r in enumerate(recommendations[:5], 1):
        story.append(Paragraph(
            f"<b>{i}. {r.title}</b> &nbsp; "
            f"<font color='#6B4A2E'>[{r.category} · {r.time_to_impact}]</font>",
            body,
        ))
        story.append(Paragraph(r.rationale, body))
        story.append(Paragraph(
            f"<i>Reference: {r.fao_reference}</i>",
            ParagraphStyle("ref", parent=body, fontSize=8, textColor=colors.grey),
        ))
        story.append(Spacer(1, 0.2 * cm))

    # --- Footer --------------------------------------------------------- #
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        "<i>Screening-level assessment. Validate with field observations before "
        "programming decisions. Data: SoilGrids 2.0 (ISRIC), MODIS, CHIRPS, SRTM, "
        "ESA WorldCover. Method: RUSLE (Renard 1997); EPIC K-factor (Williams 1995).</i>",
        ParagraphStyle("footer", parent=body, fontSize=8, textColor=colors.grey),
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# --------------------------------------------------------------------------- #
# CSV
# --------------------------------------------------------------------------- #
def build_csv_export(
    location_label: str,
    lon: float,
    lat: float,
    health: SoilHealthResult,
    erosion: ErosionEstimate,
    degradation: DegradationPrediction,
) -> str:
    """Tidy CSV export for downstream analysis."""
    rows = [
        {"metric": "location",               "value": location_label},
        {"metric": "lon",                    "value": lon},
        {"metric": "lat",                    "value": lat},
        {"metric": "soil_health_score",      "value": health.overall},
        {"metric": "soil_health_grade",      "value": health.grade},
        {"metric": "erosion_t_ha_yr",        "value": erosion.soil_loss_t_ha_yr},
        {"metric": "erosion_class",          "value": erosion.risk_class},
        {"metric": "degradation_probability","value": degradation.probability},
        {"metric": "degradation_risk",       "value": degradation.risk_label},
    ]
    for s in health.subscores:
        rows.append({"metric": f"score_{s.name.lower().replace(' ', '_')}",
                     "value": s.score})
        rows.append({"metric": f"value_{s.name.lower().replace(' ', '_')}",
                     "value": s.value})
    for fk, fv in erosion.factors.items():
        rows.append({"metric": f"rusle_factor_{fk}", "value": fv})

    return pd.DataFrame(rows).to_csv(index=False)

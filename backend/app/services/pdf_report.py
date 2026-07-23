"""Renders a scan's AI risk report as a downloadable PDF."""

from pathlib import Path

from fpdf import FPDF

from app.models.finding import Finding
from app.models.report import Report
from app.models.scan import Scan

FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

SEVERITY_LABELS = {
    "critical": "Kritik",
    "high": "Yuksek",
    "medium": "Orta",
    "low": "Dusuk",
    "info": "Bilgi",
}


class ReportPDF(FPDF):
    def header(self) -> None:
        self.set_font("DejaVu", "B", 14)
        self.set_text_color(88, 28, 135)
        self.cell(0, 10, "SentraScan Guvenlik Raporu", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(200, 200, 200)
        self.line(10, 20, 200, 20)
        self.ln(4)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Sayfa {self.page_no()}", align="C")


def _multi_cell(pdf: ReportPDF, h: float, text: str) -> None:
    pdf.multi_cell(0, h, text, new_x="LMARGIN", new_y="NEXT")


def _section_title(pdf: ReportPDF, text: str) -> None:
    pdf.set_font("DejaVu", "B", 12)
    pdf.set_text_color(30, 30, 30)
    pdf.ln(2)
    pdf.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")


def _paragraph(pdf: ReportPDF, text: str) -> None:
    pdf.set_font("DejaVu", "", 10)
    pdf.set_text_color(60, 60, 60)
    _multi_cell(pdf, 6, text or "-")
    pdf.ln(1)


def _risk_color(score: float) -> tuple[int, int, int]:
    if score >= 60:
        return (185, 28, 28)
    if score >= 30:
        return (202, 138, 4)
    return (21, 128, 61)


def build_report_pdf(target_domain: str, scan: Scan, report: Report, findings: list[Finding]) -> bytes:
    pdf = ReportPDF()
    pdf.add_font("DejaVu", "", str(FONT_DIR / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", str(FONT_DIR / "DejaVuSans-Bold.ttf"))
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    pdf.set_font("DejaVu", "B", 11)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 7, f"Hedef: {target_domain}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 10)
    scan_date = scan.finished_at or scan.created_at
    pdf.cell(0, 6, f"Tarama tarihi: {scan_date:%d.%m.%Y %H:%M}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Calistirilan moduller: {', '.join(scan.modules)}", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(2)
    pdf.set_font("DejaVu", "B", 20)
    pdf.set_text_color(*_risk_color(report.risk_score))
    pdf.cell(0, 12, f"Risk Skoru: {report.risk_score:.0f}/100", new_x="LMARGIN", new_y="NEXT")

    _section_title(pdf, "Yonetici Ozeti")
    _paragraph(pdf, report.executive_summary)

    _section_title(pdf, "Teknik Ozet")
    _paragraph(pdf, report.technical_summary)

    _section_title(pdf, "Onceliklendirilmis Bulgular")
    if not report.prioritized_findings:
        _paragraph(pdf, "Onceliklendirilmis bulgu yok.")
    for pf in report.prioritized_findings:
        severity_label = SEVERITY_LABELS.get(pf.get("severity", "info"), pf.get("severity", ""))
        pdf.set_font("DejaVu", "B", 10)
        pdf.set_text_color(30, 30, 30)
        _multi_cell(pdf, 6, f"[{severity_label}] {pf.get('title', '')}")
        pdf.set_font("DejaVu", "", 9)
        pdf.set_text_color(80, 80, 80)
        _multi_cell(pdf, 5, f"Etki: {pf.get('business_impact', '-')}")
        pdf.set_text_color(21, 128, 61)
        _multi_cell(pdf, 5, f"Duzeltme: {pf.get('remediation', '-')}")
        pdf.ln(2)

    if findings:
        pdf.add_page()
        _section_title(pdf, f"Ham Bulgular ({len(findings)})")
        for f in findings:
            severity_label = SEVERITY_LABELS.get(f.severity, f.severity)
            pdf.set_font("DejaVu", "B", 9)
            pdf.set_text_color(30, 30, 30)
            _multi_cell(pdf, 5, f"[{severity_label}] {f.title}")
            if f.description:
                pdf.set_font("DejaVu", "", 8)
                pdf.set_text_color(100, 100, 100)
                _multi_cell(pdf, 4, f.description)
            pdf.ln(1)

    return bytes(pdf.output())

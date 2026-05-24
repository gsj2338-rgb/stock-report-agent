"""
pdf_generator.py — Builds a properly formatted A4 PDF report from collected stock data.
Uses Pretendard Korean font (installed at ~/Library/Fonts/Pretendard-*.ttf).
Inspired by kami.tw93.fun document design principles: clean typography, numbered sections,
ink blue headers, structured tables with fixed column widths.
"""
import logging
import os
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle,
    Spacer, HRFlowable, PageBreak, KeepTogether,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

logger = logging.getLogger(__name__)

_FONT_DIR = os.path.expanduser("~/Library/Fonts")
_fonts_ok = False


def _register_fonts() -> None:
    global _fonts_ok
    if _fonts_ok:
        return
    candidates = [
        (os.path.join(_FONT_DIR, "Pretendard-Regular.ttf"), "KR"),
        (os.path.join(_FONT_DIR, "Pretendard-Bold.ttf"),    "KR-B"),
        (os.path.join(_FONT_DIR, "Pretendard-Light.ttf"),   "KR-L"),
    ]
    try:
        for path, name in candidates:
            pdfmetrics.registerFont(TTFont(name, path))
        _fonts_ok = True
    except Exception as e:
        logger.warning(f"Pretendard font not found, falling back to Helvetica: {e}")


# ---------------------------------------------------------------------------
# Color palette (kami.tw93.fun inspired)
# ---------------------------------------------------------------------------
INK_BLUE   = colors.HexColor("#1B365D")
ACCENT     = colors.HexColor("#2563EB")
TH_BG      = colors.HexColor("#1B365D")
ALT_ROW    = colors.HexColor("#F8F9FA")
BORDER_CLR = colors.HexColor("#DEE2E6")
GREEN_CLR  = colors.HexColor("#16A34A")
RED_CLR    = colors.HexColor("#DC2626")
ORANGE_CLR = colors.HexColor("#D97706")
GRAY_CLR   = colors.HexColor("#6B7280")
WHITE      = colors.white
BLACK      = colors.HexColor("#111827")

# Usable page width: A4(595pt) - 30mm margins ≈ 510pt
PAGE_W = A4[0] - 30 * mm


# ---------------------------------------------------------------------------
# Style factory
# ---------------------------------------------------------------------------
def _make_styles(fn: str, fn_b: str) -> dict:
    return {
        "title":  ParagraphStyle("title",  fontName=fn_b, fontSize=22, textColor=INK_BLUE, leading=28, spaceAfter=2),
        "sub":    ParagraphStyle("sub",    fontName=fn,   fontSize=11, textColor=GRAY_CLR,  leading=16, spaceAfter=8),
        "sh":     ParagraphStyle("sh",     fontName=fn_b, fontSize=14, textColor=INK_BLUE,  leading=20, spaceAfter=4, spaceBefore=6),
        "sh_num": ParagraphStyle("sh_num", fontName=fn_b, fontSize=11, textColor=ACCENT,    leading=16, spaceAfter=2),
        "body":   ParagraphStyle("body",   fontName=fn,   fontSize=10, textColor=BLACK,     leading=15, spaceAfter=5),
        "cap":    ParagraphStyle("cap",    fontName=fn,   fontSize=8,  textColor=GRAY_CLR,  leading=11, spaceAfter=2),
        "th":     ParagraphStyle("th",     fontName=fn_b, fontSize=9,  textColor=WHITE,     alignment=TA_CENTER, leading=12),
        "td":     ParagraphStyle("td",     fontName=fn,   fontSize=9,  textColor=BLACK,     leading=12),
        "td_c":   ParagraphStyle("td_c",   fontName=fn,   fontSize=9,  textColor=BLACK,     alignment=TA_CENTER, leading=12),
        "td_r":   ParagraphStyle("td_r",   fontName=fn,   fontSize=9,  textColor=BLACK,     alignment=TA_RIGHT,  leading=12),
        "td_g":   ParagraphStyle("td_g",   fontName=fn_b, fontSize=9,  textColor=GREEN_CLR, alignment=TA_CENTER, leading=12),
        "td_r2":  ParagraphStyle("td_r2",  fontName=fn_b, fontSize=9,  textColor=RED_CLR,   alignment=TA_CENTER, leading=12),
        "td_o":   ParagraphStyle("td_o",   fontName=fn_b, fontSize=9,  textColor=ORANGE_CLR,alignment=TA_CENTER, leading=12),
    }


_TABLE_STYLE = TableStyle([
    ("BACKGROUND",    (0, 0), (-1, 0),  TH_BG),
    ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
    ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, ALT_ROW]),
    ("GRID",          (0, 0), (-1, -1), 0.5, BORDER_CLR),
    ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING",    (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
])


def _section_header(num: str, title: str, S: dict) -> list:
    """Numbered section divider + title."""
    return [
        Spacer(1, 5 * mm),
        HRFlowable(width="100%", thickness=1, color=INK_BLUE),
        Spacer(1, 2 * mm),
        Paragraph(f"<font color='#2563EB'><b>{num}</b></font>  {title}", S["sh"]),
        Spacer(1, 2 * mm),
    ]


# ---------------------------------------------------------------------------
# Section: Cover
# ---------------------------------------------------------------------------
def _cover(data: dict, S: dict) -> list:
    date = data.get("date", "")
    prices = data.get("prices", [])
    n_reports = len(data.get("analyst_reports", [])) + len(data.get("broker_reports", []))
    n_disclosures = len(data.get("disclosures", []))
    n_semi = len(data.get("semi_news", []))

    story = [
        Spacer(1, 8 * mm),
        Paragraph("한국 주식 일간 분석 리포트", S["title"]),
        Paragraph(date, S["sub"]),
        HRFlowable(width="100%", thickness=2, color=INK_BLUE),
        Spacer(1, 3 * mm),
        Paragraph(
            f"종목 시세 {len(prices)}건 · 애널리스트 리포트 {n_reports}건 · "
            f"DART 공시 {n_disclosures}건 · 반도체 뉴스 {n_semi}건",
            S["cap"],
        ),
        Spacer(1, 4 * mm),
    ]
    return story


# ---------------------------------------------------------------------------
# Section 01: 시장 개요
# ---------------------------------------------------------------------------
def _market_overview(data: dict, S: dict, analysis: dict | None) -> list:
    prices = data.get("prices", [])
    story = _section_header("01", "시장 개요", S)

    if analysis and isinstance(analysis.get("market_overview"), str):
        story.append(Paragraph(analysis["market_overview"], S["body"]))
        story.append(Spacer(1, 3 * mm))

    if not prices:
        story.append(Paragraph("시세 데이터를 수집하지 못했습니다. (KIS API 오류 또는 장 마감 시간)", S["body"]))
        return story

    headers = ["종목명", "코드", "현재가", "등락률", "52주 고가", "52주 저가", "거래량"]
    col_w = [100, 50, 68, 60, 68, 68, 72]   # 486pt ≤ 510pt

    rows = [[Paragraph(h, S["th"]) for h in headers]]
    for p in prices:
        chg = p.get("change_pct", 0)
        try:
            chg_f = float(chg)
            chg_str = f"{chg_f:+.2f}%"
            chg_s = S["td_g"] if chg_f > 0 else (S["td_r2"] if chg_f < 0 else S["td_c"])
        except (ValueError, TypeError):
            chg_str = str(chg)
            chg_s = S["td_c"]

        close = p.get("close", 0)
        vol   = p.get("volume", 0)
        rows.append([
            Paragraph(p.get("name", ""), S["td"]),
            Paragraph(p.get("code", ""), S["td_c"]),
            Paragraph(f"{close:,}" if isinstance(close, int) else str(close), S["td_r"]),
            Paragraph(chg_str, chg_s),
            Paragraph(f"{p.get('high_52w', 0):,}", S["td_r"]),
            Paragraph(f"{p.get('low_52w', 0):,}", S["td_r"]),
            Paragraph(f"{vol:,}" if isinstance(vol, int) else str(vol), S["td_r"]),
        ])

    t = Table(rows, colWidths=col_w, repeatRows=1)
    t.setStyle(_TABLE_STYLE)
    story.append(t)
    story.append(Paragraph("출처: 한국투자증권 Open API (KIS)", S["cap"]))
    return story


# ---------------------------------------------------------------------------
# Section 02: 섹터별 종목 분석
# ---------------------------------------------------------------------------
def _sector_analysis(data: dict, S: dict, analysis: dict | None) -> list:
    all_reports = data.get("analyst_reports", []) + data.get("broker_reports", [])
    story = _section_header("02", "섹터별 종목 분석 — 매수/매도 의견", S)

    if not all_reports:
        story.append(Paragraph("애널리스트 리포트 데이터를 수집하지 못했습니다.", S["body"]))
        story.append(Paragraph(
            "수집 오류 원인: 네이버 금융 HTML 구조 변경 또는 해당 날짜 데이터 없음. "
            "증권사 페이지 scraping 실패 (삼성증권 404, 미래에셋/KB/키움/NH 응답 없음).",
            S["cap"],
        ))
        return story

    # Group reports by stock name
    grouped: dict[str, list] = {}
    for r in all_reports:
        name = r.get("stock_name", "기타")
        grouped.setdefault(name, []).append(r)

    headers = ["증권사", "투자의견", "목표주가", "날짜", "리포트 제목"]
    col_w   = [80, 68, 62, 62, 178]   # 450pt

    def _opinion_style(opinion: str) -> str:
        op = str(opinion)
        if any(w in op for w in ["매수", "BUY", "Buy", "강력", "Strong"]):
            return "td_g"
        if any(w in op for w in ["매도", "SELL", "Sell"]):
            return "td_r2"
        if any(w in op for w in ["중립", "보유", "Neutral", "Hold", "N/A"]):
            return "td_o"
        return "td_c"

    for stock_name, reports in sorted(grouped.items()):
        rows = [[Paragraph(h, S["th"]) for h in headers]]
        for r in reports[:10]:
            opinion = str(r.get("opinion", "N/A"))
            tp = r.get("target_price", 0)
            tp_str = f"{int(tp):,}" if isinstance(tp, (int, float)) and tp else (str(tp) if tp else "-")
            date_str = str(r.get("date", "-"))[:10]
            title_str = str(r.get("title", "-"))[:55]
            rows.append([
                Paragraph(str(r.get("broker", r.get("source", "-")))[:14], S["td"]),
                Paragraph(opinion, S[_opinion_style(opinion)]),
                Paragraph(tp_str, S["td_r"]),
                Paragraph(date_str, S["td_c"]),
                Paragraph(title_str, S["td"]),
            ])

        t = Table(rows, colWidths=col_w, repeatRows=1)
        t.setStyle(_TABLE_STYLE)

        block = [
            Spacer(1, 4 * mm),
            Paragraph(f"■ {stock_name}", S["sh_num"]),
            Spacer(1, 1 * mm),
            t,
        ]
        story.append(KeepTogether(block))

    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "출처: 네이버 금융, 삼성증권, 미래에셋, KB증권, 키움증권, NH투자증권",
        S["cap"],
    ))
    return story


# ---------------------------------------------------------------------------
# Section 03: DART 공시
# ---------------------------------------------------------------------------
def _dart_section(data: dict, S: dict, analysis: dict | None) -> list:
    disclosures = data.get("disclosures", [])
    story = _section_header("03", "주요 DART 공시", S)

    if analysis and isinstance(analysis.get("dart_summary"), str):
        story.append(Paragraph(analysis["dart_summary"], S["body"]))
        story.append(Spacer(1, 3 * mm))

    if not disclosures:
        story.append(Paragraph("공시 데이터를 수집하지 못했습니다.", S["body"]))
        story.append(Paragraph(
            "수집 오류 원인: DART API pblntf_ty='A' (정기공시)로 조회 시 해당일 데이터 없음 (status 013). "
            "개선 방안: pblntf_ty 파라미터 제거 또는 'B'(주요사항) 추가.",
            S["cap"],
        ))
        return story

    headers = ["기업명", "종목코드", "공시유형", "접수일"]
    col_w   = [135, 62, 185, 68]   # 450pt
    rows = [[Paragraph(h, S["th"]) for h in headers]]

    for d in disclosures:
        rcept = d.get("rcept_dt", "")
        if len(rcept) == 8:
            rcept = f"{rcept[:4]}-{rcept[4:6]}-{rcept[6:]}"
        rows.append([
            Paragraph(str(d.get("corp_name", "")), S["td"]),
            Paragraph(str(d.get("stock_code", "")), S["td_c"]),
            Paragraph(str(d.get("report_nm", ""))[:45], S["td"]),
            Paragraph(rcept, S["td_c"]),
        ])

    t = Table(rows, colWidths=col_w, repeatRows=1)
    t.setStyle(_TABLE_STYLE)
    story.append(t)
    story.append(Paragraph("출처: DART 전자공시시스템 (금융감독원)", S["cap"]))
    return story


# ---------------------------------------------------------------------------
# Section 04: 글로벌 반도체 동향
# ---------------------------------------------------------------------------
def _semi_section(data: dict, S: dict, analysis: dict | None) -> list:
    semi = data.get("semi_news", [])
    story = _section_header("04", "글로벌 반도체 동향", S)

    if analysis and isinstance(analysis.get("semi_summary"), str):
        story.append(Paragraph(analysis["semi_summary"], S["body"]))
        story.append(Spacer(1, 3 * mm))

    if not semi:
        story.append(Paragraph("반도체 뉴스 데이터를 수집하지 못했습니다.", S["body"]))
        story.append(Paragraph(
            "수집 오류 원인: TrendForce HTML 구조 변경 가능성, SEMI.org 403/404 응답. "
            "개선 방안: RSS 피드 또는 공식 API 사용.",
            S["cap"],
        ))
        return story

    for item in semi:
        title   = str(item.get("title", ""))
        source  = str(item.get("source", ""))
        summary = str(item.get("summary", ""))[:250]
        block = [
            Paragraph(f"<b>■ {title}</b>", S["body"]),
            Paragraph(f"출처: {source}", S["cap"]),
        ]
        if summary:
            block.append(Paragraph(summary, S["body"]))
        block.append(Spacer(1, 2 * mm))
        story.append(KeepTogether(block))

    return story


# ---------------------------------------------------------------------------
# Section 05: 출처 및 면책조항
# ---------------------------------------------------------------------------
def _sources_section(data: dict, S: dict) -> list:
    story = _section_header("05", "출처 및 면책조항", S)

    sources = {"한국투자증권 Open API (KIS)", "DART 전자공시시스템 (금융감독원)"}
    for key in ("analyst_reports", "broker_reports", "disclosures", "semi_news"):
        for item in data.get(key, []):
            src = item.get("source", "").strip()
            if src:
                sources.add(src)

    story.append(Paragraph("■ 데이터 출처", S["sh_num"]))
    for src in sorted(sources):
        story.append(Paragraph(f"• {src}", S["body"]))

    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "【면책조항】 본 리포트는 공개된 데이터를 AI가 자동 분석·생성한 참고용 자료이며, "
        "투자 권유를 목적으로 하지 않습니다. 주식 투자는 원금 손실 위험이 있으며, "
        "투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다. "
        "본 자료의 정확성·완전성을 보장하지 않으며, 이를 근거로 한 투자 결과에 대해 책임지지 않습니다.",
        S["cap"],
    ))
    return story


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate(collected_data: dict, analysis: dict | None = None) -> bytes:
    """
    Generate a complete A4 PDF report with all 5 sections.

    Args:
        collected_data: dict with keys date, prices, analyst_reports,
                        broker_reports, disclosures, semi_news
        analysis: optional dict from Composer.compose_sections() with keys:
                  market_overview, dart_summary, semi_summary

    Returns:
        PDF as bytes
    """
    _register_fonts()
    fn   = "KR"   if _fonts_ok else "Helvetica"
    fn_b = "KR-B" if _fonts_ok else "Helvetica-Bold"
    S = _make_styles(fn, fn_b)

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"한국 주식 일간 분석 리포트 — {collected_data.get('date', '')}",
        author="Stock Report Agent (Claude)",
    )

    story: list = []
    story += _cover(collected_data, S)
    story += _market_overview(collected_data, S, analysis)
    story.append(PageBreak())
    story += _sector_analysis(collected_data, S, analysis)
    story.append(PageBreak())
    story += _dart_section(collected_data, S, analysis)
    story += _semi_section(collected_data, S, analysis)
    story.append(PageBreak())
    story += _sources_section(collected_data, S)

    doc.build(story)
    return buf.getvalue()

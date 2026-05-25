import argparse
import logging
import os
from datetime import date, datetime, timedelta, timezone

from dotenv import load_dotenv

from collectors.dart_collector import DartCollector
from collectors.kis_collector import KisCollector
from collectors.naver_collector import NaverCollector
from collectors.broker_collector import BrokerCollector
from collectors.semi_collector import SemiCollector
from composer import Composer
from emailer import Emailer
from pdf_generator import generate as generate_pdf

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def _build_email_body(collected_data: dict, narrative: str) -> str:
    """
    Compose a structured email body that shows collection status
    (disclosures, analyst reports) plus Claude's narrative summary.
    """
    date = collected_data.get("date", "")
    disclosures = collected_data.get("disclosures", [])
    analyst_reports = collected_data.get("analyst_reports", [])
    broker_reports = collected_data.get("broker_reports", [])
    prices = collected_data.get("prices", [])
    semi = collected_data.get("semi_news", [])
    all_reports = analyst_reports + broker_reports

    lines = [f"[{date} 한국 주식 일간 분석 리포트]", ""]
    lines += ["─" * 36, "수집 현황", "─" * 36]

    # Prices
    lines.append(f"종목 시세: {len(prices)}개 종목 조회")

    # Disclosures
    if disclosures:
        lines.append(f"DART 공시: {len(disclosures)}건")
        for d in disclosures[:5]:
            lines.append(f"  • {d.get('corp_name', '')} — {d.get('report_nm', '')}")
        if len(disclosures) > 5:
            lines.append(f"  ... 외 {len(disclosures) - 5}건")
    else:
        lines.append("DART 공시: 해당일 공시 없음")

    # Analyst + Broker reports
    if all_reports:
        lines.append(f"애널리스트 리포트: {len(all_reports)}건")
        for r in all_reports[:6]:
            stock = r.get("stock_name", "")
            broker = r.get("broker", r.get("source", ""))
            opinion = r.get("opinion", "")
            tp = r.get("target_price", "")
            tp_str = f" / 목표 {int(tp):,}원" if isinstance(tp, (int, float)) and tp else (f" / 목표 {tp}원" if tp else "")
            lines.append(f"  • {stock} — {broker} [{opinion}{tp_str}]")
        if len(all_reports) > 6:
            lines.append(f"  ... 외 {len(all_reports) - 6}건")
    else:
        lines.append("애널리스트 리포트: 해당일 리포트 없음")

    # Semi news
    if semi:
        lines.append(f"반도체 뉴스: {len(semi)}건")

    lines += ["", "─" * 36, "시장 요약", "─" * 36]
    lines.append(narrative)
    lines += ["", "상세 분석은 첨부된 PDF 리포트를 확인해주세요."]

    return "\n".join(lines)


KST = timezone(timedelta(hours=9))


def resolve_date(date_str: str | None) -> str:
    """Return YYYYMMDD (KST). If None, use today KST. If weekend, use last Friday."""
    if date_str:
        return date_str.replace("-", "")
    today = datetime.now(KST).date()
    if today.weekday() == 5:   # Saturday
        today -= timedelta(days=1)
    elif today.weekday() == 6:  # Sunday
        today -= timedelta(days=2)
    return today.strftime("%Y%m%d")


def _check_env() -> None:
    required = [
        "DART_API_KEY", "KIS_APP_KEY", "KIS_APP_SECRET", "KIS_ACCOUNT_NO",
        "ANTHROPIC_API_KEY", "GMAIL_SENDER", "GMAIL_APP_PASSWORD", "REPORT_RECIPIENTS",
    ]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")


def run(date: str | None = None) -> None:
    _check_env()
    report_date = resolve_date(date)
    display_date = f"{report_date[:4]}-{report_date[4:6]}-{report_date[6:]}"
    logger.info(f"Generating report for {display_date}")

    dart = DartCollector(api_key=os.environ["DART_API_KEY"])
    kis = KisCollector(
        app_key=os.environ["KIS_APP_KEY"],
        app_secret=os.environ["KIS_APP_SECRET"],
        account_no=os.environ["KIS_ACCOUNT_NO"],
        account_product_code=os.environ.get("KIS_ACCOUNT_PRODUCT_CODE", "01"),
    )
    naver = NaverCollector()
    broker = BrokerCollector()
    semi = SemiCollector()

    logger.info("Collecting data from all sources...")
    disclosures = dart.fetch_disclosures(date=report_date)
    prices = kis.fetch_watchlist_prices()
    analyst_reports = naver.fetch_analyst_reports(date=report_date)
    broker_reports = broker.fetch_all(date=report_date)
    semi_news = semi.fetch(date=report_date)

    logger.info(
        f"Collected: {len(disclosures)} disclosures, {len(prices)} prices, "
        f"{len(analyst_reports)} analyst reports, {len(broker_reports)} broker reports, "
        f"{len(semi_news)} semi news items"
    )

    collected_data = {
        "date": display_date,
        "disclosures": disclosures,
        "prices": prices,
        "analyst_reports": analyst_reports,
        "broker_reports": broker_reports,
        "semi_news": semi_news,
    }

    composer = Composer(api_key=os.environ["ANTHROPIC_API_KEY"])
    logger.info("Generating AI analysis sections and text summary...")
    analysis = composer.compose_sections(collected_data)
    narrative = composer.compose_summary(collected_data)
    text_summary = _build_email_body(collected_data, narrative)

    logger.info("Building PDF report...")
    pdf_bytes = None
    pdf_filename = f"stock-report-{display_date}.pdf"
    try:
        pdf_bytes = generate_pdf(collected_data, analysis)
        logger.info(f"PDF generated ({len(pdf_bytes):,} bytes)")
    except Exception as e:
        logger.error(f"PDF generation failed, sending without attachment: {e}")

    emailer = Emailer(
        sender=os.environ["GMAIL_SENDER"],
        app_password=os.environ["GMAIL_APP_PASSWORD"],
    )
    recipients = [r.strip() for r in os.environ["REPORT_RECIPIENTS"].split(",")]
    subject = emailer.build_subject(display_date)
    emailer.send(
        recipients=recipients,
        subject=subject,
        text_body=text_summary,
        pdf_bytes=pdf_bytes,
        pdf_filename=pdf_filename,
    )
    logger.info("Report sent successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Korean Stock Analysis Email Agent")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Date to generate report for (YYYY-MM-DD or YYYYMMDD). Defaults to today.",
    )
    args = parser.parse_args()
    run(date=args.date)

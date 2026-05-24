import argparse
import logging
import os
from datetime import date, timedelta

from dotenv import load_dotenv

from collectors.dart_collector import DartCollector
from collectors.kis_collector import KisCollector
from collectors.naver_collector import NaverCollector
from collectors.broker_collector import BrokerCollector
from collectors.semi_collector import SemiCollector
from composer import Composer
from emailer import Emailer

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def resolve_date(date_str: str | None) -> str:
    """Return YYYYMMDD. If None, use today. If today is weekend, use last Friday."""
    if date_str:
        return date_str.replace("-", "")
    today = date.today()
    if today.weekday() == 5:   # Saturday
        today -= timedelta(days=1)
    elif today.weekday() == 6:  # Sunday
        today -= timedelta(days=2)
    return today.strftime("%Y%m%d")


def run(date: str | None = None) -> None:
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

    composer = Composer(api_key=os.environ["ANTHROPIC_API_KEY"])
    html_report = composer.compose({
        "date": display_date,
        "disclosures": disclosures,
        "prices": prices,
        "analyst_reports": analyst_reports,
        "broker_reports": broker_reports,
        "semi_news": semi_news,
    })

    emailer = Emailer(
        sender=os.environ["GMAIL_SENDER"],
        app_password=os.environ["GMAIL_APP_PASSWORD"],
    )
    recipients = [r.strip() for r in os.environ["REPORT_RECIPIENTS"].split(",")]
    subject = emailer.build_subject(display_date)
    emailer.send(recipients=recipients, subject=subject, html_body=html_report)
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

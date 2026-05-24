import requests
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

BIO_KEYWORDS = ["바이오", "제약", "의약", "헬스케어", "병원", "의료", "셀트리온", "삼성바이오"]


def _is_bio(name: str) -> bool:
    return any(kw in name for kw in BIO_KEYWORDS)


class BrokerCollector:
    def __init__(self):
        self.brokers = ["삼성증권", "미래에셋", "KB증권", "키움증권", "NH투자증권"]

    def _fetch_broker(self, broker_name: str, date: str) -> list[dict]:
        parsers = {
            "삼성증권": self._fetch_samsung,
            "미래에셋": self._fetch_mirae,
            "KB증권": self._fetch_kb,
            "키움증권": self._fetch_kiwoom,
            "NH투자증권": self._fetch_nh,
        }
        return parsers[broker_name](date)

    def _scrape_table(self, url: str, date_fmt: str, broker: str) -> list[dict]:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "lxml")
            results = []
            for row in soup.select("tr, .research-item, .report-item"):
                text = row.get_text(separator="|", strip=True)
                if date_fmt not in text:
                    continue
                results.append({
                    "broker": broker,
                    "stock_name": "확인 필요",
                    "title": text[:80],
                    "opinion": "N/A",
                    "date": date_fmt,
                    "url": url,
                    "source": broker,
                })
            return results
        except Exception as e:
            logger.warning(f"Generic scrape failed for {broker}: {e}")
            return []

    def _fetch_samsung(self, date: str) -> list[dict]:
        return self._scrape_table(
            "https://www.samsungpop.com/mobile/research.do?cmd=researchList&research_type=CO",
            f"{date[:4]}.{date[4:6]}.{date[6:]}", "삼성증권")

    def _fetch_mirae(self, date: str) -> list[dict]:
        return self._scrape_table(
            "https://securities.miraeasset.com/bbs/board/message/list.do?categoryId=1531",
            f"{date[:4]}.{date[4:6]}.{date[6:]}", "미래에셋")

    def _fetch_kb(self, date: str) -> list[dict]:
        return self._scrape_table(
            "https://www.kbsec.com/go.able?linkcd=10301",
            f"{date[:4]}.{date[4:6]}.{date[6:]}", "KB증권")

    def _fetch_kiwoom(self, date: str) -> list[dict]:
        return self._scrape_table(
            "https://www.kiwoom.com/h/invest/research/VResrcSIBNdStockHList",
            f"{date[:4]}.{date[4:6]}.{date[6:]}", "키움증권")

    def _fetch_nh(self, date: str) -> list[dict]:
        return self._scrape_table(
            "https://www.nhqv.com/research/stockAnalysisList",
            f"{date[:4]}.{date[4:6]}.{date[6:]}", "NH투자증권")

    def fetch_all(self, date: str) -> list[dict]:
        """Fetch from all brokers. Failed brokers logged and skipped. Bio filtered out."""
        results = []
        for broker in self.brokers:
            try:
                items = self._fetch_broker(broker, date)
                for item in items:
                    if not _is_bio(item.get("stock_name", "")):
                        results.append(item)
            except Exception as e:
                logger.error(f"Broker collector failed for {broker}: {e}")
        return results

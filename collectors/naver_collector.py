import requests
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

NAVER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://finance.naver.com/",
}

BIO_KEYWORDS = ["바이오", "제약", "의약", "헬스케어", "병원", "의료", "셀트리온", "삼성바이오"]


class NaverCollector:
    def __init__(self):
        self.base_url = "https://finance.naver.com/research/company_list.naver"

    def _is_bio(self, name: str) -> bool:
        return any(kw in name for kw in BIO_KEYWORDS)

    def _parse_price(self, text: str) -> int:
        try:
            return int(text.replace(",", "").replace("원", "").strip())
        except (ValueError, AttributeError):
            return 0

    def fetch_analyst_reports(self, date: str, pages: int = 3) -> list[dict]:
        """
        Scrape Naver Finance analyst reports filtered by date (YYYYMMDD).
        Returns list of dicts: stock_name, broker, title, opinion, target_price, date, url, source.
        Returns [] on error.
        """
        results = []
        date_fmt = f"{date[:4]}.{date[4:6]}.{date[6:]}"

        for page in range(1, pages + 1):
            try:
                resp = requests.get(self.base_url, params={"page": page}, headers=NAVER_HEADERS, timeout=10)
                resp.raise_for_status()
                resp.encoding = "euc-kr"
                soup = BeautifulSoup(resp.text, "lxml")

                table = soup.find("table", class_="type_1")
                if not table:
                    break

                rows = table.find_all("tr")
                page_had_date = False

                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) < 6:
                        continue
                    row_date = cols[5].get_text(strip=True)
                    if row_date != date_fmt:
                        continue
                    page_had_date = True
                    company_tag = cols[0].find("a")
                    title_tag = cols[1].find("a")
                    stock_name = company_tag.get_text(strip=True) if company_tag else ""
                    title = title_tag.get_text(strip=True) if title_tag else ""
                    broker = cols[2].get_text(strip=True)
                    target_price = self._parse_price(cols[3].get_text(strip=True))
                    opinion = cols[4].get_text(strip=True)
                    report_url = "https://finance.naver.com" + (title_tag["href"] if title_tag else "")
                    if self._is_bio(stock_name):
                        continue
                    results.append({
                        "stock_name": stock_name,
                        "broker": broker,
                        "title": title,
                        "opinion": opinion,
                        "target_price": target_price,
                        "date": row_date,
                        "url": report_url,
                        "source": f"네이버 금융 ({broker})",
                    })

                if not page_had_date and page > 1:
                    break

            except Exception as e:
                logger.error(f"Naver collector error on page {page}: {e}")
                break

        return results

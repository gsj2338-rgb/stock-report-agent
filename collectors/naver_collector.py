from __future__ import annotations
import re
import requests
import logging
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

NAVER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://finance.naver.com/",
}

BIO_KEYWORDS = ["바이오", "제약", "의약", "헬스케어", "병원", "의료", "셀트리온", "삼성바이오"]

_BASE = "https://finance.naver.com"


class NaverCollector:
    def __init__(self):
        self.list_url = f"{_BASE}/research/company_list.naver"

    def _is_bio(self, name: str) -> bool:
        return any(kw in name for kw in BIO_KEYWORDS)

    def _date_to_naver_fmt(self, date: str) -> str:
        """YYYYMMDD → YY.MM.DD (Naver 2-digit year format)."""
        return f"{date[2:4]}.{date[4:6]}.{date[6:]}"

    def _prev_business_day(self, date: str) -> str:
        from datetime import datetime, timedelta
        d = datetime.strptime(date, "%Y%m%d") - timedelta(days=1)
        while d.weekday() >= 5:
            d -= timedelta(days=1)
        return d.strftime("%Y%m%d")

    def _fetch_detail(self, report: dict) -> dict:
        """
        Fetch individual report page to extract opinion, target_price, summary.
        Returns the report dict enriched with those fields.
        Gracefully falls back if the page fails.
        """
        nid = report.get("_nid", "")
        if not nid:
            return report
        try:
            r = requests.get(
                f"{_BASE}/research/company_read.naver?nid={nid}",
                headers=NAVER_HEADERS, timeout=8,
            )
            r.encoding = "euc-kr"
            s = BeautifulSoup(r.text, "lxml")

            # Opinion
            op_el = s.find("em", class_="coment")
            opinion = op_el.get_text(strip=True) if op_el else "N/A"
            if opinion in ("", "없음"):
                opinion = "N/A"

            # Target price — try <strong> first, then parse from summary text
            target = 0
            for strong in s.find_all("strong"):
                m = re.search(r"목표.*?([\d,]+)원", strong.get_text())
                if m:
                    target = int(m.group(1).replace(",", ""))
                    break

            # Summary — first substantial paragraph
            summary = ""
            for p in s.find_all("p"):
                text = p.get_text(strip=True)
                if len(text) > 60:
                    summary = text[:300]
                    break

            # Fallback: parse target from summary if not found
            if not target and summary:
                m = re.search(r"목표.*?([\d,]+)원", summary)
                if m:
                    target = int(m.group(1).replace(",", ""))

            return {
                **report,
                "opinion": opinion,
                "target_price": target,
                "summary": summary,
            }
        except Exception as e:
            logger.debug(f"Detail fetch failed for nid={nid}: {e}")
            return report

    def _scrape_pages(self, target_naver_fmt: str, max_pages: int = 8) -> list[dict]:
        """
        Scrape list pages and collect stubs for the target date.
        Columns (2026): 종목명 | 제목 | 증권사 | 첨부 | 작성일 | 조회수
        """
        stubs: list[dict] = []
        for page in range(1, max_pages + 1):
            try:
                resp = requests.get(
                    self.list_url, params={"page": page},
                    headers=NAVER_HEADERS, timeout=10,
                )
                resp.raise_for_status()
                resp.encoding = "euc-kr"
                soup = BeautifulSoup(resp.text, "lxml")

                table = soup.find("table", class_="type_1")
                if not table:
                    break

                rows = table.find_all("tr")
                page_dates: set[str] = set()

                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) < 5:
                        continue

                    row_date = cols[4].get_text(strip=True)
                    page_dates.add(row_date)

                    if row_date != target_naver_fmt:
                        continue

                    company_tag = cols[0].find("a")
                    title_tag   = cols[1].find("a")
                    stock_name  = company_tag.get_text(strip=True) if company_tag else ""
                    title       = title_tag.get_text(strip=True)   if title_tag   else ""
                    broker      = cols[2].get_text(strip=True)
                    href        = title_tag.get("href", "") if title_tag else ""
                    report_url  = _BASE + href if href else self.list_url
                    nid         = href.split("nid=")[1].split("&")[0] if "nid=" in href else ""

                    if self._is_bio(stock_name):
                        continue

                    stubs.append({
                        "stock_name":   stock_name,
                        "broker":       broker,
                        "title":        title,
                        "opinion":      "N/A",
                        "target_price": 0,
                        "summary":      "",
                        "date":         row_date,
                        "url":          report_url,
                        "source":       f"네이버 금융 ({broker})",
                        "_nid":         nid,
                    })

                older_only = all(d < target_naver_fmt for d in page_dates if d)
                if older_only and page_dates:
                    break

            except Exception as e:
                logger.error(f"Naver collector error on page {page}: {e}")
                break

        return stubs

    def _enrich_details(self, stubs: list[dict], max_workers: int = 8) -> list[dict]:
        """
        Parallel-fetch detail pages to get opinion, target_price, summary.
        Strips private _nid field before returning.
        """
        enriched: list[dict] = []
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(self._fetch_detail, s): i for i, s in enumerate(stubs)}
            results: dict[int, dict] = {}
            for fut in as_completed(futures):
                idx = futures[fut]
                results[idx] = fut.result()
        for i in range(len(stubs)):
            r = results.get(i, stubs[i])
            r.pop("_nid", None)
            enriched.append(r)
        return enriched

    def fetch_analyst_reports(self, date: str, pages: int = 8) -> list[dict]:
        """
        Fetch Naver Finance analyst reports for a given date (YYYYMMDD).
        Enriches each report with opinion, target_price, and a brief summary
        via parallel detail page fetches.
        Falls back to previous business day if no reports found for target date.
        """
        target_fmt = self._date_to_naver_fmt(date)
        stubs = self._scrape_pages(target_fmt, max_pages=pages)

        if not stubs:
            prev_date = self._prev_business_day(date)
            prev_fmt  = self._date_to_naver_fmt(prev_date)
            logger.info(f"Naver: no reports for {target_fmt}, trying {prev_fmt}")
            stubs = self._scrape_pages(prev_fmt, max_pages=pages)

        if not stubs:
            return []

        results = self._enrich_details(stubs)
        logger.info(f"Naver collector: {len(results)} reports collected")
        return results

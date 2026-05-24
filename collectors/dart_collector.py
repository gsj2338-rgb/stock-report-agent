import requests
import logging

logger = logging.getLogger(__name__)

BIO_STOCK_CODES = {
    "068270",  # 셀트리온
    "207940",  # 삼성바이오로직스
    "128940",  # 한미약품
    "002080",  # 녹십자
    "185750",  # 종근당
    "000100",  # 유한양행
}

BIO_KEYWORDS = ["바이오", "제약", "의약", "헬스케어", "병원", "의료"]

DART_BASE_URL = "https://opendart.fss.or.kr/api"


class DartCollector:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def _is_bio(self, corp_name: str, stock_code: str) -> bool:
        if stock_code in BIO_STOCK_CODES:
            return True
        return any(kw in corp_name for kw in BIO_KEYWORDS)

    def fetch_disclosures(self, date: str) -> list[dict]:
        """
        Fetch major disclosures for a given date (YYYYMMDD).
        Returns list of dicts: corp_name, stock_code, report_nm, rcept_dt, url, source.
        Returns [] on any error.
        """
        try:
            params = {
                "crtfc_key": self.api_key,
                "bgn_de": date,
                "end_de": date,
                "last_reprt_at": "N",
                "pblntf_ty": "A",
                "page_no": "1",
                "page_count": "40",
            }
            resp = requests.get(f"{DART_BASE_URL}/list.json", params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "000":
                logger.warning(f"DART API returned status {data.get('status')}: {data.get('message')}")
                return []

            results = []
            for item in data.get("list", []):
                corp_name = item.get("corp_name", "")
                stock_code = item.get("stock_code", "")
                if self._is_bio(corp_name, stock_code):
                    continue
                results.append({
                    "corp_name": corp_name,
                    "stock_code": stock_code,
                    "report_nm": item.get("report_nm", ""),
                    "rcept_dt": item.get("rcept_dt", ""),
                    "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcept_no={item.get('rcept_no', '')}",
                    "source": "DART 전자공시시스템",
                })
            return results

        except Exception as e:
            logger.error(f"DART collector error: {e}")
            return []

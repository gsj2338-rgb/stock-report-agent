import requests
import logging
import time

logger = logging.getLogger(__name__)

KIS_BASE_URL = "https://openapi.koreainvestment.com:9443"

WATCHLIST = {
    "반도체": ["005930", "000660"],
    "IT/플랫폼": ["035720", "035420"],
    "자동차": ["005380", "000270"],
    "금융": ["105560", "055550", "086790"],
    "에너지/조선": ["010950", "267250"],
    "소비재/화장품": ["051900", "090430"],
    "통신": ["017670", "030200"],
    "철강/소재": ["005490", "004020"],
}

ALL_WATCHLIST = [code for codes in WATCHLIST.values() for code in codes]


class KisCollector:
    def __init__(self, app_key: str, app_secret: str, account_no: str, account_product_code: str):
        self.app_key = app_key
        self.app_secret = app_secret
        self.account_no = account_no
        self.account_product_code = account_product_code
        self._token = None

    def _get_access_token(self) -> str:
        if self._token:
            return self._token
        resp = requests.post(
            f"{KIS_BASE_URL}/oauth2/tokenP",
            json={"grant_type": "client_credentials", "appkey": self.app_key, "appsecret": self.app_secret},
            timeout=10,
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token

    def get_stock_price(self, code: str) -> dict | None:
        """Returns dict: code, name, close, change_pct, volume, high_52w, low_52w. None on error."""
        try:
            token = self._get_access_token()
            headers = {
                "authorization": f"Bearer {token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": "FHKST01010100",
            }
            params = {"fid_cond_mrkt_div_code": "J", "fid_input_iscd": code}
            resp = requests.get(
                f"{KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price",
                headers=headers, params=params, timeout=10,
            )
            resp.raise_for_status()
            out = resp.json().get("output", {})
            return {
                "code": code,
                "name": out.get("hts_kor_isnm", ""),
                "close": int(out.get("stck_prpr", 0)),
                "change_pct": float(out.get("prdy_ctrt", 0)),
                "volume": int(out.get("acml_vol", 0)),
                "high_52w": int(out.get("stck_hgpr", 0)),
                "low_52w": int(out.get("stck_lwpr", 0)),
            }
        except Exception as e:
            logger.error(f"KIS price fetch failed for {code}: {e}")
            return None

    def fetch_watchlist_prices(self, codes: list[str] | None = None) -> list[dict]:
        """Fetch prices for watchlist stocks. Skips failed ones. 0.2s delay between requests."""
        codes = codes or ALL_WATCHLIST
        results = []
        for code in codes:
            price = self.get_stock_price(code)
            if price:
                results.append(price)
            time.sleep(0.2)
        return results

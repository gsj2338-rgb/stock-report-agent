import pytest
from unittest.mock import patch, MagicMock
from collectors.kis_collector import KisCollector

MOCK_PRICE_RESPONSE = {
    "rt_cd": "0",
    "output": {
        "stck_prpr": "75000",
        "prdy_vrss": "-900",
        "prdy_ctrt": "-1.19",
        "acml_vol": "15234567",
        "stck_hgpr": "88000",
        "stck_lwpr": "60000",
        "hts_kor_isnm": "삼성전자"
    }
}

def test_get_stock_price_returns_dict():
    collector = KisCollector(app_key="k", app_secret="s", account_no="12345678", account_product_code="01")
    with patch.object(collector, "_get_access_token", return_value="test_token"):
        with patch("requests.get") as mock_get:
            mock_get.return_value.json.return_value = MOCK_PRICE_RESPONSE
            mock_get.return_value.raise_for_status = MagicMock()
            result = collector.get_stock_price("005930")
    assert result["code"] == "005930"
    assert result["name"] == "삼성전자"
    assert result["close"] == 75000
    assert result["change_pct"] == -1.19

def test_get_stock_price_returns_none_on_error():
    collector = KisCollector(app_key="k", app_secret="s", account_no="12345678", account_product_code="01")
    with patch.object(collector, "_get_access_token", return_value="test_token"):
        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("API error")
            result = collector.get_stock_price("005930")
    assert result is None

def test_fetch_watchlist_prices_skips_failed():
    collector = KisCollector(app_key="k", app_secret="s", account_no="12345678", account_product_code="01")
    def side_effect(code):
        if code == "000660":
            return None
        return {"code": code, "name": "삼성전자", "close": 75000, "change_pct": -1.19,
                "volume": 15000000, "high_52w": 88000, "low_52w": 60000}
    with patch.object(collector, "get_stock_price", side_effect=side_effect):
        results = collector.fetch_watchlist_prices(["005930", "000660"])
    assert len(results) == 1
    assert results[0]["code"] == "005930"

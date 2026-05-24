import pytest
from unittest.mock import patch, MagicMock
from collectors.naver_collector import NaverCollector

MOCK_REPORT_HTML = """
<html><body>
<table class="type_1">
<tr>
  <td class="company"><a href="/research/company_read.naver?nid=12345">삼성전자</a></td>
  <td><a href="/research/company_read.naver?nid=12345">AI 반도체 수요로 실적 개선</a></td>
  <td>삼성증권</td>
  <td class="price">90,000</td>
  <td>매수</td>
  <td>2026.05.23</td>
</tr>
<tr>
  <td class="company"><a href="/research/company_read.naver?nid=12346">SK하이닉스</a></td>
  <td><a href="/research/company_read.naver?nid=12346">HBM 공급 과잉 우려</a></td>
  <td>키움증권</td>
  <td class="price">180,000</td>
  <td>중립</td>
  <td>2026.05.23</td>
</tr>
</table>
</body></html>
"""

def test_parse_reports_returns_list():
    collector = NaverCollector()
    with patch("requests.get") as mock_get:
        mock_get.return_value.text = MOCK_REPORT_HTML
        mock_get.return_value.raise_for_status = MagicMock()
        mock_get.return_value.encoding = "euc-kr"
        result = collector.fetch_analyst_reports(date="20260523")
    assert isinstance(result, list)

def test_parse_reports_extracts_fields():
    collector = NaverCollector()
    with patch("requests.get") as mock_get:
        mock_get.return_value.text = MOCK_REPORT_HTML
        mock_get.return_value.raise_for_status = MagicMock()
        mock_get.return_value.encoding = "euc-kr"
        result = collector.fetch_analyst_reports(date="20260523")
    assert any(r["stock_name"] == "삼성전자" for r in result)
    first = next(r for r in result if r["stock_name"] == "삼성전자")
    assert first["broker"] == "삼성증권"
    assert first["opinion"] == "매수"
    assert first["target_price"] == 90000

def test_fetch_reports_returns_empty_on_error():
    collector = NaverCollector()
    with patch("requests.get") as mock_get:
        mock_get.side_effect = Exception("Network error")
        result = collector.fetch_analyst_reports(date="20260523")
    assert result == []

import pytest
from unittest.mock import patch, MagicMock
from collectors.naver_collector import NaverCollector

# Matches actual Naver Finance HTML structure (as of 2026):
# cols: 종목명 | 제목 | 증권사 | 첨부 | 작성일(YY.MM.DD) | 조회수
MOCK_REPORT_HTML = """
<html><body>
<table class="type_1">
<tr>
  <td style="padding-left:10"><a class="stock_item" href="/item/main.naver?code=005930" title="삼성전자">삼성전자</a></td>
  <td><a href="/research/company_read.naver?nid=12345">AI 반도체 수요로 실적 개선</a></td>
  <td>삼성증권</td>
  <td class="file"></td>
  <td class="date" style="padding-left:5px">26.05.23</td>
  <td class="date">5200</td>
</tr>
<tr>
  <td style="padding-left:10"><a class="stock_item" href="/item/main.naver?code=000660" title="SK하이닉스">SK하이닉스</a></td>
  <td><a href="/research/company_read.naver?nid=12346">HBM 공급 과잉 우려</a></td>
  <td>키움증권</td>
  <td class="file"></td>
  <td class="date" style="padding-left:5px">26.05.23</td>
  <td class="date">3100</td>
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
    # opinion and target_price not available in Naver list view
    assert first["opinion"] == "N/A"
    assert first["target_price"] == 0
    assert first["title"] == "AI 반도체 수요로 실적 개선"


def test_fetch_reports_returns_empty_on_error():
    collector = NaverCollector()
    with patch("requests.get") as mock_get:
        mock_get.side_effect = Exception("Network error")
        result = collector.fetch_analyst_reports(date="20260523")
    assert result == []

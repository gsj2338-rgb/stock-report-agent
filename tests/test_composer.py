import pytest
from unittest.mock import patch, MagicMock
from composer import Composer

SAMPLE_DATA = {
    "date": "2026-05-23",
    "disclosures": [
        {"corp_name": "삼성전자", "report_nm": "주요사항보고서", "rcept_dt": "20260523",
         "url": "https://dart.fss.or.kr/...", "source": "DART"}
    ],
    "prices": [
        {"code": "005930", "name": "삼성전자", "close": 75000, "change_pct": -1.19,
         "volume": 15000000, "high_52w": 88000, "low_52w": 60000}
    ],
    "analyst_reports": [
        {"stock_name": "삼성전자", "broker": "삼성증권", "title": "AI 수요 회복",
         "opinion": "매수", "target_price": 90000, "date": "2026.05.23",
         "url": "https://finance.naver.com/...", "source": "네이버 금융 (삼성증권)"}
    ],
    "broker_reports": [],
    "semi_news": [
        {"title": "TSMC CoWoS Capacity Up 40%", "source": "TrendForce",
         "url": "https://trendforce.com/...", "summary": "Strong AI chip demand..."}
    ],
}

def test_compose_returns_html_string():
    composer = Composer(api_key="test_key")
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="<html><body>리포트</body></html>")]
    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        result = composer.compose(SAMPLE_DATA)
    assert isinstance(result, str)
    assert len(result) > 0

def test_compose_calls_claude_with_both_sides_instruction():
    composer = Composer(api_key="test_key")
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="<html>리포트</html>")]
    captured_prompt = []
    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_client = MagicMock()
        def capture_call(**kwargs):
            captured_prompt.append(str(kwargs))
            return mock_response
        mock_client.messages.create.side_effect = capture_call
        mock_anthropic.return_value = mock_client
        composer.compose(SAMPLE_DATA)
    assert any("매수" in p and "매도" in p for p in captured_prompt)

def test_compose_returns_fallback_on_api_error():
    composer = Composer(api_key="test_key")
    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API error")
        mock_anthropic.return_value = mock_client
        result = composer.compose(SAMPLE_DATA)
    assert isinstance(result, str)
    assert "오류" in result or "error" in result.lower()

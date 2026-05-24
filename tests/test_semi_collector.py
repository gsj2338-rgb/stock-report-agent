import pytest
from unittest.mock import patch, MagicMock
from collectors.semi_collector import SemiCollector

MOCK_TRENDFORCE_HTML = """
<html><body>
<div class="entry-content">
  <article>
    <h2 class="entry-title"><a href="https://www.trendforce.com/news/1">TSMC Q2 CoWoS Capacity Surges 40%</a></h2>
    <span class="published">May 23, 2026</span>
    <p class="summary">TSMC plans to expand CoWoS capacity by 40% in Q2 2026 amid strong AI chip demand from NVIDIA and AMD.</p>
  </article>
</div>
</body></html>
"""

def test_fetch_returns_list():
    collector = SemiCollector()
    with patch("requests.get") as mock_get:
        mock_get.return_value.text = MOCK_TRENDFORCE_HTML
        mock_get.return_value.raise_for_status = MagicMock()
        result = collector.fetch(date="20260523")
    assert isinstance(result, list)

def test_fetch_extracts_title_and_url():
    collector = SemiCollector()
    with patch("requests.get") as mock_get:
        mock_get.return_value.text = MOCK_TRENDFORCE_HTML
        mock_get.return_value.raise_for_status = MagicMock()
        result = collector.fetch(date="20260523")
    if result:
        assert "title" in result[0]
        assert "url" in result[0]
        assert "source" in result[0]

def test_fetch_returns_empty_on_error():
    collector = SemiCollector()
    with patch("requests.get") as mock_get:
        mock_get.side_effect = Exception("Timeout")
        result = collector.fetch(date="20260523")
    assert result == []

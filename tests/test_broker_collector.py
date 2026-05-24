import pytest
from unittest.mock import patch, MagicMock
from collectors.broker_collector import BrokerCollector

def test_fetch_all_returns_list():
    collector = BrokerCollector()
    with patch.object(collector, "_fetch_broker", return_value=[]):
        result = collector.fetch_all(date="20260523")
    assert isinstance(result, list)

def test_failed_broker_does_not_crash_others():
    collector = BrokerCollector()
    call_count = [0]
    def side_effect(broker_name, date):
        call_count[0] += 1
        if broker_name == "미래에셋":
            raise Exception("Connection refused")
        return [{"broker": broker_name, "stock_name": "테스트", "title": "테스트 리포트",
                 "opinion": "매수", "date": date, "url": "https://example.com", "source": broker_name}]
    with patch.object(collector, "_fetch_broker", side_effect=side_effect):
        result = collector.fetch_all(date="20260523")
    assert call_count[0] == len(collector.brokers)

def test_fetch_all_excludes_bio():
    collector = BrokerCollector()
    bio_report = [{"broker": "삼성증권", "stock_name": "셀트리온", "title": "바이오 성장",
                   "opinion": "매수", "date": "2026.05.23", "url": "https://example.com",
                   "source": "삼성증권"}]
    with patch.object(collector, "_fetch_broker", return_value=bio_report):
        result = collector.fetch_all(date="20260523")
    assert all(r["stock_name"] != "셀트리온" for r in result)

import pytest
from unittest.mock import patch, MagicMock
from collectors.dart_collector import DartCollector

MOCK_LIST_RESPONSE = {
    "status": "000",
    "message": "정상",
    "total_count": 2,
    "list": [
        {
            "corp_name": "삼성전자",
            "corp_code": "00126380",
            "stock_code": "005930",
            "report_nm": "주요사항보고서",
            "rcept_no": "20260523000001",
            "flr_nm": "삼성전자",
            "rcept_dt": "20260523",
            "rm": ""
        },
        {
            "corp_name": "SK하이닉스",
            "corp_code": "00164779",
            "stock_code": "000660",
            "report_nm": "분기보고서",
            "rcept_no": "20260523000002",
            "flr_nm": "SK하이닉스",
            "rcept_dt": "20260523",
            "rm": ""
        }
    ]
}

def test_fetch_disclosures_returns_list():
    collector = DartCollector(api_key="test_key")
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = MOCK_LIST_RESPONSE
        mock_get.return_value.raise_for_status = MagicMock()
        result = collector.fetch_disclosures(date="20260523")
    assert isinstance(result, list)
    assert len(result) == 2

def test_fetch_disclosures_formats_output():
    collector = DartCollector(api_key="test_key")
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = MOCK_LIST_RESPONSE
        mock_get.return_value.raise_for_status = MagicMock()
        result = collector.fetch_disclosures(date="20260523")
    item = result[0]
    assert item["corp_name"] == "삼성전자"
    assert item["report_nm"] == "주요사항보고서"
    assert item["rcept_dt"] == "20260523"
    assert "url" in item

def test_fetch_disclosures_excludes_bio():
    collector = DartCollector(api_key="test_key")
    bio_response = {
        "status": "000",
        "message": "정상",
        "total_count": 1,
        "list": [
            {
                "corp_name": "셀트리온",
                "corp_code": "00000000",
                "stock_code": "068270",
                "report_nm": "분기보고서",
                "rcept_no": "20260523000003",
                "flr_nm": "셀트리온",
                "rcept_dt": "20260523",
                "rm": ""
            }
        ]
    }
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = bio_response
        mock_get.return_value.raise_for_status = MagicMock()
        result = collector.fetch_disclosures(date="20260523")
    assert all(item["corp_name"] != "셀트리온" for item in result)

def test_fetch_disclosures_returns_empty_on_api_error():
    collector = DartCollector(api_key="test_key")
    with patch("requests.get") as mock_get:
        mock_get.side_effect = Exception("Connection error")
        result = collector.fetch_disclosures(date="20260523")
    assert result == []

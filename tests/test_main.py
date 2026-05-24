import pytest
from unittest.mock import patch, MagicMock

TEST_ENV = {
    "DART_API_KEY": "test_dart_key",
    "KIS_APP_KEY": "test_kis_key",
    "KIS_APP_SECRET": "test_kis_secret",
    "KIS_ACCOUNT_NO": "12345678",
    "KIS_ACCOUNT_PRODUCT_CODE": "01",
    "ANTHROPIC_API_KEY": "test_anthropic_key",
    "GMAIL_SENDER": "sender@gmail.com",
    "GMAIL_APP_PASSWORD": "testapppass",
    "REPORT_RECIPIENTS": "a@gmail.com,b@gmail.com",
}

def test_main_runs_without_error():
    with patch.dict("os.environ", TEST_ENV), \
         patch("main.DartCollector") as MockDart, \
         patch("main.KisCollector") as MockKis, \
         patch("main.NaverCollector") as MockNaver, \
         patch("main.BrokerCollector") as MockBroker, \
         patch("main.SemiCollector") as MockSemi, \
         patch("main.Composer") as MockComposer, \
         patch("main.Emailer") as MockEmailer:

        MockDart.return_value.fetch_disclosures.return_value = []
        MockKis.return_value.fetch_watchlist_prices.return_value = []
        MockNaver.return_value.fetch_analyst_reports.return_value = []
        MockBroker.return_value.fetch_all.return_value = []
        MockSemi.return_value.fetch.return_value = []
        MockComposer.return_value.compose.return_value = "<html>report</html>"
        mock_emailer = MagicMock()
        MockEmailer.return_value = mock_emailer

        import main
        main.run(date="20260523")

    mock_emailer.send.assert_called_once()

def test_main_date_defaults_to_today():
    from main import resolve_date
    result = resolve_date(None)
    assert len(result) == 8
    assert result.isdigit()

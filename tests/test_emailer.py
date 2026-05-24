import pytest
from unittest.mock import patch, MagicMock
from emailer import Emailer

def test_send_calls_smtp():
    emailer = Emailer(sender="from@gmail.com", app_password="testpass")
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        emailer.send(
            recipients=["a@gmail.com", "b@gmail.com"],
            subject="Test Subject",
            text_body="테스트 요약",
        )
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("from@gmail.com", "testpass")
    mock_server.sendmail.assert_called_once()

def test_send_raises_on_auth_failure():
    emailer = Emailer(sender="from@gmail.com", app_password="wrong")
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        mock_server.login.side_effect = Exception("Authentication failed")
        with pytest.raises(Exception, match="Authentication failed"):
            emailer.send(
                recipients=["a@gmail.com"],
                subject="Test",
                text_body="요약",
            )

def test_build_subject_includes_date():
    emailer = Emailer(sender="from@gmail.com", app_password="pass")
    subject = emailer.build_subject("2026-05-23")
    assert "2026" in subject
    assert "05" in subject or "5" in subject
    assert "23" in subject

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


class Emailer:
    def __init__(self, sender: str, app_password: str):
        self.sender = sender
        self.app_password = app_password

    def build_subject(self, date: str) -> str:
        """date: YYYY-MM-DD"""
        parts = date.split("-")
        if len(parts) == 3:
            return f"[주식 리포트] {parts[0]}년 {int(parts[1])}월 {int(parts[2])}일 — 한국 주식 애널리스트 분석"
        return f"[주식 리포트] {date}"

    def send(self, recipients: list[str], subject: str, html_body: str) -> None:
        """Send HTML email via Gmail SMTP. Raises on SMTP or auth failure."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = ", ".join(recipients)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(self.sender, self.app_password)
            server.sendmail(self.sender, recipients, msg.as_string())

        logger.info(f"Email sent to {recipients}")

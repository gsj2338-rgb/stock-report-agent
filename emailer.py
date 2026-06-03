from __future__ import annotations
import smtplib
import logging
from email import encoders
from email.header import Header
from email.mime.base import MIMEBase
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

    def send(self, recipients: list[str], subject: str, text_body: str,
             pdf_bytes: bytes | None = None, pdf_filename: str = "report.pdf") -> None:
        """
        Send plain-text email with optional PDF attachment via Gmail SMTP.
        Raises on SMTP or auth failure.
        """
        msg = MIMEMultipart("mixed")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = self.sender
        msg["To"] = ", ".join(recipients)
        msg.attach(MIMEText(text_body, "plain", "utf-8"))

        if pdf_bytes:
            pdf_part = MIMEBase("application", "pdf")
            pdf_part.set_payload(pdf_bytes)
            encoders.encode_base64(pdf_part)
            pdf_part.add_header("Content-Disposition", f'attachment; filename="{pdf_filename}"')
            msg.attach(pdf_part)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(self.sender, self.app_password)
            server.send_message(msg)

        logger.info(f"Email sent to {recipients}")

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage as SMTPEmailMessage


class DigestSender:
    def send(self, *, to_email: str, subject: str, body: str) -> None:
        host = os.environ.get("SMTP_HOST", "")
        port = int(os.environ.get("SMTP_PORT", "587"))
        username = os.environ.get("SMTP_USERNAME", "")
        password = os.environ.get("SMTP_PASSWORD", "")
        from_email = os.environ.get("SMTP_FROM") or username
        if not all([host, username, password, from_email, to_email]):
            raise ValueError("SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM, and recipient are required.")

        message = SMTPEmailMessage()
        message["From"] = from_email
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)

        with smtplib.SMTP(host, port) as smtp:
            smtp.starttls()
            smtp.login(username, password)
            smtp.send_message(message)

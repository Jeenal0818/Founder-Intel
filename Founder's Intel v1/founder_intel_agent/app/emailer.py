# app/emailer.py
import smtplib
from email.mime.text import MIMEText
from typing import List
from .config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS


def send_intel_email(subject: str, body: str, recipients: List[str]):
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = ", ".join(recipients)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, recipients, msg.as_string())

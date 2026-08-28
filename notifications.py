"""Failure notifications: generic/Slack/Discord/ntfy webhooks, or email via SMTP."""
import json
import smtplib
from email.mime.text import MIMEText
from urllib import error, request


def _send_webhook(url: str, webhook_type: str, message: str, logger) -> None:
    try:
        if webhook_type == "slack":
            body = json.dumps({"text": message}).encode("utf-8")
            headers = {"Content-Type": "application/json"}
        elif webhook_type == "discord":
            body = json.dumps({"content": message}).encode("utf-8")
            headers = {"Content-Type": "application/json"}
        elif webhook_type == "ntfy":
            body = message.encode("utf-8")
            headers = {"Content-Type": "text/plain; charset=utf-8"}
        else:  # generic
            body = json.dumps({"text": message}).encode("utf-8")
            headers = {"Content-Type": "application/json"}

        req = request.Request(url, data=body, headers=headers, method="POST")
        with request.urlopen(req, timeout=10) as resp:
            resp.read()
    except error.URLError as e:
        logger.warning(f"Failed to send webhook notification: {e}")


def _send_email(email_cfg: dict, subject: str, message: str, logger) -> None:
    try:
        msg = MIMEText(message)
        msg["Subject"] = subject
        msg["From"] = email_cfg["from"]
        msg["To"] = ", ".join(email_cfg["to"])

        with smtplib.SMTP(email_cfg["smtp_host"], email_cfg.get("smtp_port", 587), timeout=10) as server:
            if email_cfg.get("use_tls", True):
                server.starttls()
            if email_cfg.get("username"):
                server.login(email_cfg["username"], email_cfg["password"])
            server.sendmail(email_cfg["from"], email_cfg["to"], msg.as_string())
    except Exception as e:
        logger.warning(f"Failed to send email notification: {e}")


def send_notification(subject: str, message: str, notify_cfg: dict, logger) -> None:
    """Send via whichever channels are configured. Never raises — failures are only logged."""
    if not notify_cfg:
        return
    if notify_cfg.get("webhook_url"):
        _send_webhook(notify_cfg["webhook_url"], notify_cfg.get("webhook_type", "generic"), message, logger)
    if notify_cfg.get("email"):
        _send_email(notify_cfg["email"], subject, message, logger)

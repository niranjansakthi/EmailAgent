import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from groq import Groq
from app.tools.base import BaseTool
from app.tools.tool_prompts import EMAIL_GENERATION_PROMPT
from typing import Any, Dict


class email_writer:
    """Generates a personalised cold email draft using Groq."""

    def write_email(self, profile_data: str, our_data: str) -> str:
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        model = os.environ.get("GROQ_MODEL", "qwen/qwen3.8-27b")
        prompt = EMAIL_GENERATION_PROMPT.format(
            profile_data=profile_data, our_data=our_data
        )
        chat_completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return chat_completion.choices[0].message.content


class emailsender:
    """Sends an email via SMTP."""

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        sender_email: str = None,
        sender_password: str = None,
    ) -> str:
        sender_email = (sender_email or os.environ.get("SENDER_EMAIL", "")).strip()
        sender_pass = (sender_password or os.environ.get("SENDER_PASSWORD", "")).strip()
        smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com").strip()
        try:
            smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        except (ValueError, TypeError):
            smtp_port = 587

        # Strip spaces from Google App Passwords (e.g. 'abcd efgh ijkl mnop' -> 'abcdefghijklmnop')
        if sender_pass and "gmail" in smtp_server.lower() and len(sender_pass.replace(" ", "")) == 16:
            sender_pass = sender_pass.replace(" ", "")

        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        try:
            # Port 465 uses direct SSL; 587 and others use STARTTLS
            if smtp_port == 465:
                with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=15) as server:
                    server.login(sender_email, sender_pass)
                    server.sendmail(sender_email, to_email, message.as_string())
            else:
                with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as server:
                    server.starttls()
                    server.login(sender_email, sender_pass)
                    server.sendmail(sender_email, to_email, message.as_string())

            return json.dumps({"status": "success", "message": f"Email sent to {to_email}"})
        except smtplib.SMTPAuthenticationError:
            return json.dumps({
                "status": "error",
                "error": (
                    "SMTP Authentication failed (535). For Gmail, you must use a 16-character "
                    "Google App Password (https://myaccount.google.com/apppasswords) with 2-Step "
                    "Verification enabled, NOT your standard Gmail login password."
                ),
            })
        except (smtplib.SMTPConnectError, TimeoutError, OSError) as e:
            return json.dumps({
                "status": "error",
                "error": f"Failed to connect to SMTP server '{smtp_server}:{smtp_port}': {str(e)}",
            })
        except smtplib.SMTPRecipientsRefused:
            return json.dumps({
                "status": "error",
                "error": f"Recipient address rejected by SMTP server: {to_email}",
            })
        except smtplib.SMTPSenderRefused:
            return json.dumps({
                "status": "error",
                "error": f"Sender address rejected by SMTP server: {sender_email}",
            })
        except Exception as e:
            return json.dumps({"status": "error", "error": str(e)})


class WriteEmailTool(BaseTool):
    name = "write_email"
    description = (
        "Writes a personalised cold email draft. "
        "Arguments: {'profile_data': '...', 'our_data': '...'}"
    )

    _writer = email_writer()

    def execute(self, arguments: Dict[str, Any]):
        profile_data = arguments.get("profile_data", "")
        our_data = arguments.get("our_data", "")
        if not profile_data or not our_data:
            return {"error": "write_email requires both 'profile_data' and 'our_data'"}
        return self._writer.write_email(profile_data=profile_data, our_data=our_data)


class SendEmailTool(BaseTool):
    name = "send_email"
    description = (
        "Sends an email via SMTP. "
        "Arguments: {'to_email': '...', 'subject': '...', 'body': '...'}"
    )

    _sender = emailsender()

    def execute(self, arguments: Dict[str, Any]):
        to_email = arguments.get("to_email", "")
        subject = arguments.get("subject", "")
        body = arguments.get("body", "")
        if not to_email or not subject or not body:
            return {"error": "send_email requires 'to_email', 'subject', and 'body'"}
        return self._sender.send_email(to_email=to_email, subject=subject, body=body)

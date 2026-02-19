"""Gmail API email sender for recruiter outreach.

Sends personalized emails with tailored resume attachments.
Uses OAuth2 for sending as the user's personal Gmail account.
"""

import os
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

import jinja2
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from utils.logger import logger

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


class EmailSender:
    def __init__(self, config: dict):
        self.from_name = config["email_outreach"]["from_name"]
        self.daily_limit = config["email_outreach"]["daily_send_limit"]
        self.sender_email = os.getenv("GMAIL_SENDER_EMAIL", "")
        self._sent_today = 0

        self.service = self._build_gmail_service()
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader("templates"),
            autoescape=True,
        )

    def _build_gmail_service(self):
        """Build Gmail API service with OAuth2 credentials."""
        token_path = os.getenv("GMAIL_TOKEN_PATH", "credentials/gmail_token.json")
        creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials/gmail_oauth.json")

        creds = None
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, GMAIL_SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, GMAIL_SCOPES)
                creds = flow.run_local_server(port=0)

            with open(token_path, "w") as f:
                f.write(creds.to_json())

        return build("gmail", "v1", credentials=creds)

    def send_outreach(self, recruiter: dict, job: dict, resume_path: str) -> bool:
        """Send personalized outreach email with tailored resume attached.

        Args:
            recruiter: {"email": str, "name": str}
            job: Job dict with Company, Role, etc.
            resume_path: Path to tailored PDF resume.

        Returns:
            True if sent successfully.
        """
        if self._sent_today >= self.daily_limit:
            logger.warning("Daily email send limit reached")
            return False

        company = job.get("Company", job.get("company", ""))
        role = job.get("Role", job.get("title", ""))

        subject = f"Interest in {role} at {company} — {self.from_name}"
        body_html = self._render_email(recruiter, company, role)

        message = self._create_message(
            to=recruiter["email"],
            subject=subject,
            body_html=body_html,
            attachment_path=resume_path,
        )

        try:
            self.service.users().messages().send(
                userId="me", body=message
            ).execute()
            self._sent_today += 1
            logger.info(f"Email sent to {recruiter['email']} for {role} at {company}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {recruiter['email']}: {e}")
            return False

    def _render_email(self, recruiter: dict, company: str, role: str) -> str:
        """Render the outreach email template."""
        try:
            template = self.jinja_env.get_template("outreach_email.html")
            return template.render(
                recruiter_name=recruiter.get("name", "Hiring Manager"),
                company=company,
                role=role,
                sender_name=self.from_name,
            )
        except jinja2.TemplateNotFound:
            # Inline fallback if template file missing
            name = recruiter.get("name", "Hiring Manager")
            return f"""<p>Hi {name},</p>
<p>I hope this message finds you well. I came across the <strong>{role}</strong>
position at <strong>{company}</strong> and am very excited about the opportunity.</p>
<p>I've attached my resume for your review. I'd love the chance to discuss how
my background aligns with what the team is looking for.</p>
<p>Would you be open to a brief conversation?</p>
<p>Thank you for your time,<br>{self.from_name}</p>"""

    def _create_message(self, to: str, subject: str, body_html: str,
                        attachment_path: str = None) -> dict:
        """Build MIME message with optional PDF attachment."""
        msg = MIMEMultipart()
        msg["to"] = to
        msg["from"] = f"{self.from_name} <{self.sender_email}>"
        msg["subject"] = subject
        msg.attach(MIMEText(body_html, "html"))

        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as f:
                att = MIMEBase("application", "octet-stream")
                att.set_payload(f.read())
                encoders.encode_base64(att)
                att.add_header(
                    "Content-Disposition",
                    f"attachment; filename={os.path.basename(attachment_path)}",
                )
                msg.attach(att)

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        return {"raw": raw}

    def reset_daily_counter(self):
        """Reset the daily send counter (call at start of new day)."""
        self._sent_today = 0

    @property
    def sends_remaining(self) -> int:
        return max(0, self.daily_limit - self._sent_today)

"""Notifications for pipeline events (console + optional Slack)."""

import os
from utils.logger import logger


class Notifier:
    def __init__(self, config: dict):
        self.slack_enabled = config["notifications"].get("slack_enabled", False)
        self.slack_client = None

        if self.slack_enabled:
            try:
                from slack_sdk import WebClient
                self.slack_client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
                self.slack_channel = config["notifications"]["slack_channel"]
            except ImportError:
                logger.warning("slack-sdk not installed, Slack notifications disabled")
                self.slack_enabled = False

    def notify_new_jobs(self, jobs: list[dict]):
        msg = f"Found {len(jobs)} new job(s):\n"
        for j in jobs[:10]:
            company = j.get("company", j.get("Company", ""))
            title = j.get("title", j.get("Role", ""))
            msg += f"  - {title} at {company}\n"
        if len(jobs) > 10:
            msg += f"  ... and {len(jobs) - 10} more\n"
        self._send(msg)

    def notify_emails_sent(self, count: int):
        self._send(f"Sent {count} outreach email(s) this run.")

    def notify_applications(self, auto_count: int, manual_count: int):
        self._send(f"Auto-applied: {auto_count} | Manual needed: {manual_count}")

    def notify_error(self, error: str):
        self._send(f"ERROR: {error}")

    def notify_summary(self, stats: dict):
        msg = "Pipeline run summary:\n"
        for key, value in stats.items():
            msg += f"  {key}: {value}\n"
        self._send(msg)

    def _send(self, message: str):
        logger.info(f"[Notification] {message}")
        if self.slack_enabled and self.slack_client:
            try:
                self.slack_client.chat_postMessage(
                    channel=self.slack_channel, text=message
                )
            except Exception as e:
                logger.error(f"Slack notification failed: {e}")

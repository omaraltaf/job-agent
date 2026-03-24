"""
Notifier — sends summary notifications (email, desktop, Slack)
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

log = logging.getLogger(__name__)


class Notifier:
    def __init__(self, config):
        self.config = config

    def send_summary(self, stats: dict):
        method = self.config.NOTIFICATION_METHOD

        message = self._build_message(stats)

        if method == "email":
            self._send_email(message, stats)
        elif method == "slack":
            self._send_slack(message)
        elif method == "desktop":
            self._send_desktop(stats)

        log.info(f"Summary notification sent via {method}")

    def _build_message(self, stats: dict) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        applied = stats.get("applied_list", [])

        lines = [
            f"🤖 Job Agent Report — {now}",
            f"",
            f"📊 Summary:",
            f"  • Jobs found:   {stats['jobs_found']}",
            f"  • Jobs matched: {stats['jobs_matched']}",
            f"  • Applied to:   {stats['jobs_applied']}",
            f"  • Skipped:      {stats['jobs_skipped']}",
            f"  • Errors:       {stats['errors']}",
            f"",
        ]

        if applied:
            lines.append("✅ Applied to:")
            for job in applied:
                lines.append(f"  • {job['title']} @ {job['company']} ({job['source']}) — Score: {job['score']}/10")
        else:
            lines.append("ℹ️ No new applications this run.")

        lines += [
            "",
            "📁 Applications saved to: applications/",
            "📋 Full log: agent.log",
        ]

        return "\n".join(lines)

    def _send_email(self, message: str, stats: dict):
        try:
            msg = MIMEMultipart()
            msg["From"] = self.config.NOTIFY_EMAIL
            msg["To"] = self.config.NOTIFY_EMAIL
            msg["Subject"] = f"🤖 Job Agent: {stats['jobs_applied']} applications sent — {datetime.now().strftime('%Y-%m-%d %H:%M')}"

            msg.attach(MIMEText(message, "plain"))

            try:
                # Try port 465 (SSL) first
                with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
                    server.login(self.config.NOTIFY_EMAIL, self.config.GMAIL_APP_PASSWORD)
                    server.send_message(msg)
            except (TimeoutError, OSError):
                # Fallback: port 587 with STARTTLS (works on more networks)
                with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
                    server.starttls()
                    server.login(self.config.NOTIFY_EMAIL, self.config.GMAIL_APP_PASSWORD)
                    server.send_message(msg)

            log.info("Email notification sent")
        except Exception as e:
            log.warning(f"Email notification failed: {e}")

    def _send_slack(self, message: str):
        try:
            import httpx
            httpx.post(
                self.config.SLACK_WEBHOOK_URL,
                json={"text": f"```{message}```"},
                timeout=5
            )
        except Exception as e:
            log.warning(f"Slack notification failed: {e}")

    def _send_desktop(self, stats: dict):
        """Desktop notification (macOS / Linux)"""
        try:
            import subprocess
            title = f"Job Agent: {stats['jobs_applied']} applications sent"
            body = f"{stats['jobs_found']} found | {stats['jobs_matched']} matched | {stats['errors']} errors"

            # macOS
            subprocess.run([
                "osascript", "-e",
                f'display notification "{body}" with title "{title}"'
            ], check=False)
        except Exception:
            try:
                # Linux (notify-send)
                import subprocess
                subprocess.run(["notify-send", title, body], check=False)
            except Exception as e:
                log.warning(f"Desktop notification failed: {e}")

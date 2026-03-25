"""
Alert service for sending notifications to Microsoft Teams and Slack.

Configure via environment variables:
  SLACK_WEBHOOK_URL   – Slack incoming webhook URL
  TEAMS_WEBHOOK_URL   – Microsoft Teams incoming webhook URL
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL", "")

_TIMEOUT = 10.0  # seconds


class AlertService:
    """Send structured alerts to Slack and/or Microsoft Teams."""

    # ------------------------------------------------------------------
    # Slack
    # ------------------------------------------------------------------

    def send_slack_alert(
        self,
        title: str,
        message: str,
        severity: str = "info",
        fields: Optional[List[Dict[str, str]]] = None,
    ) -> bool:
        """Post a rich message to the configured Slack webhook.

        Returns True if the request succeeded, False otherwise.
        """
        if not SLACK_WEBHOOK_URL:
            logger.warning("SLACK_WEBHOOK_URL not configured – alert skipped.")
            return False

        colour_map = {"high": "#E01E5A", "medium": "#ECB22E", "low": "#2EB67D", "info": "#36C5F0"}
        colour = colour_map.get(severity.lower(), "#36C5F0")

        attachment: Dict[str, Any] = {
            "color": colour,
            "title": title,
            "text": message,
        }
        if fields:
            attachment["fields"] = [
                {"title": f["title"], "value": f["value"], "short": True} for f in fields
            ]

        payload = {"attachments": [attachment]}

        try:
            resp = httpx.post(SLACK_WEBHOOK_URL, json=payload, timeout=_TIMEOUT)
            resp.raise_for_status()
            logger.info("Slack alert sent: %s", title)
            return True
        except Exception as exc:
            logger.error("Failed to send Slack alert: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Microsoft Teams
    # ------------------------------------------------------------------

    def send_teams_alert(
        self,
        title: str,
        message: str,
        severity: str = "info",
        facts: Optional[List[Dict[str, str]]] = None,
    ) -> bool:
        """Post an Adaptive Card / MessageCard to the configured Teams webhook.

        Returns True if the request succeeded, False otherwise.
        """
        if not TEAMS_WEBHOOK_URL:
            logger.warning("TEAMS_WEBHOOK_URL not configured – alert skipped.")
            return False

        colour_map = {"high": "attention", "medium": "warning", "low": "good", "info": "accent"}
        theme = colour_map.get(severity.lower(), "accent")

        # Office 365 MessageCard format (supported by all Teams tenants)
        payload: Dict[str, Any] = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "themeColor": {"attention": "FF0000", "warning": "FFA500", "good": "00FF00", "accent": "0078D4"}.get(
                theme, "0078D4"
            ),
            "summary": title,
            "sections": [
                {
                    "activityTitle": f"**{title}**",
                    "activityText": message,
                    "facts": facts or [],
                }
            ],
        }

        try:
            resp = httpx.post(TEAMS_WEBHOOK_URL, json=payload, timeout=_TIMEOUT)
            resp.raise_for_status()
            logger.info("Teams alert sent: %s", title)
            return True
        except Exception as exc:
            logger.error("Failed to send Teams alert: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Convenience: broadcast to all configured channels
    # ------------------------------------------------------------------

    def broadcast(
        self,
        title: str,
        message: str,
        severity: str = "info",
        extra: Optional[Dict[str, str]] = None,
    ) -> Dict[str, bool]:
        """Send the alert to every configured channel.

        Returns a dict of channel → success.
        """
        fields = [{"title": k, "value": v} for k, v in (extra or {}).items()]
        facts = [{"name": k, "value": v} for k, v in (extra or {}).items()]

        return {
            "slack": self.send_slack_alert(title, message, severity, fields),
            "teams": self.send_teams_alert(title, message, severity, facts),
        }


# Singleton
alert_service = AlertService()

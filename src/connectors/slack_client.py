"""This module contains the functions to interact with the Slack API."""
import os
import requests
from src.utils import secrets_manager

class SlackClient:
    """A client for interacting with the Slack API."""

    def __init__(self):
        # Try to get from secrets manager first, then fall back to environment variables
        self.slack_webhook_url = secrets_manager.get_secret_value("SLACK_WEBHOOK_URL") or os.environ.get("SLACK_WEBHOOK_URL")
        if not self.slack_webhook_url:
            raise ValueError("SLACK_WEBHOOK_URL not configured.")

    def send_notification(self, payload):
        """Sends a notification to a Slack channel via a webhook URL."""
        try:
            response = requests.post(self.slack_webhook_url, json=payload, timeout=10)
            response.raise_for_status()  # Raise an exception for bad status codes
            print("Successfully sent notification to Slack.")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error sending notification to Slack: {e}")
            return None
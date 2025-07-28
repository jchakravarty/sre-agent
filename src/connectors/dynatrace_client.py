"""This module contains the functions to interact with the Dynatrace API."""
import os
import time
from functools import wraps
import requests

from src.utils import secrets_manager

class DynatraceClient:
    """A client for interacting with the Dynatrace API."""

    def __init__(self):
        # Try to get from secrets manager first, then fall back to environment variables
        self.dynatrace_api_url = secrets_manager.get_secret_value("DYNATRACE_API_URL") or os.environ.get("DYNATRACE_API_URL")
        self.dynatrace_api_token = secrets_manager.get_secret_value("DYNATRACE_API_TOKEN") or os.environ.get("DYNATRACE_API_TOKEN")
        if not all([self.dynatrace_api_url, self.dynatrace_api_token]):
            raise ValueError("Dynatrace API URL or Token not configured.")

    def send_event(self, event_payload):
        """Sends a custom event to the Dynatrace events API."""
        headers = {
            "Authorization": f"Api-Token {self.dynatrace_api_token}",
            "Content-Type": "application/json"
        }
        events_endpoint = f"{self.dynatrace_api_url}/api/v2/events/ingest"

        try:
            response = requests.post(events_endpoint, headers=headers, json=event_payload, timeout=10)
            response.raise_for_status()
            print(f"Successfully sent event to Dynatrace: {event_payload.get('title')}")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error sending event to Dynatrace: {e}")
            return None

def trace_function(func):
    """A decorator to send trace-level events for a function's execution to Dynatrace."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        dt_client = DynatraceClient()
        func_name = func.__name__
        repo_name = kwargs.get('repo_name', args[0] if args else 'N/A')

        start_time = time.time()
        start_event = {
            "eventType": "CUSTOM_INFO",
            "title": f"Function Started: {func_name}",
            "entitySelector": "type(CUSTOM_DEVICE),tag(sre-agent)",
            "properties": {"application": repo_name, "function": func_name, "status": "STARTED"}
        }
        dt_client.send_event(start_event)

        try:
            result = func(*args, **kwargs)
            duration = round((time.time() - start_time) * 1000, 2)

            finish_event = {
                "eventType": "CUSTOM_INFO",
                "title": f"Function Finished: {func_name}",
                "entitySelector": "type(CUSTOM_DEVICE),tag(sre-agent)",
                "properties": {
                    "application": repo_name,
                    "function": func_name,
                    "status": "SUCCESS",
                    "duration_ms": duration,
                    "result": str(result)[:250]
                }
            }
            dt_client.send_event(finish_event)
            return result
        except Exception as e:
            duration = round((time.time() - start_time) * 1000, 2)
            print(f"Function {func_name} failed with error: {e}")

            fail_event = {
                "eventType": "CUSTOM_ERROR",
                "title": f"Function Failed: {func_name}",
                "entitySelector": "type(CUSTOM_DEVICE),tag(sre-agent)",
                "properties": {
                    "application": repo_name,
                    "function": func_name,
                    "status": "FAILURE",
                    "duration_ms": duration,
                    "error_message": str(e)
                }
            }
            dt_client.send_event(fail_event)
            raise
    return wrapper
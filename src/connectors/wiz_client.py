"""This module contains the functions to interact with the Wiz API."""
import os
import requests
from src.utils import secrets_manager

class WizClient:
    """A client for interacting with the Wiz API."""

    def __init__(self):
        self.wiz_api_token = secrets_manager.get_secret_value("WIZ_API_TOKEN")
        self.wiz_api_url = secrets_manager.get_secret_value("WIZ_API_URL")
        if not all([self.wiz_api_token, self.wiz_api_url]):
            raise ValueError("Wiz API URL or Token not configured.")

    def get_cve_status(self, artifact_id):
        """
        Checks for critical vulnerabilities for a given artifact using the Wiz API.
        This is a simplified example. The actual Wiz API might require more complex queries.
        """
        # This is a hypothetical endpoint. The actual endpoint and query will need to be
        # determined from the Wiz API documentation. We assume a query for an image artifact.
        url = f"{self.wiz_api_url}/api/v1/images"

        params = {
            # Assuming the artifact_id from Harness is the Docker image digest or name
            "filter[name]": artifact_id,
            "filter[vulnerabilities][severity]": "Critical",
            "count": 1
        }

        headers = {
            "Authorization": f"Bearer {self.wiz_api_token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()

            # If the count of images with critical vulnerabilities is greater than 0, fail the check.
            if data.get("count", 0) > 0:
                # A more detailed implementation would fetch the actual CVEs and list them.
                return {
                    "status": "FAILURE",
                    "message": f"Wiz found critical vulnerabilities for artifact '{artifact_id}'."
                }
            return {
                "status": "SUCCESS",
                "message": "Wiz scan passed. No new critical CVEs found."
            }

        except requests.exceptions.RequestException as e:
            print(f"Error fetching Wiz status: {e}")
            raise
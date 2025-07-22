"""This module contains the functions to interact with the SonarQube API."""
import requests
from src.utils import secrets_manager

class SonarQubeClient:
    """A client for interacting with the SonarQube API."""

    def __init__(self):
        self.sonar_api_url = secrets_manager.get_secret_value("SONAR_API_URL")
        self.sonar_api_token = secrets_manager.get_secret_value("SONAR_API_TOKEN")
        if not all([self.sonar_api_url, self.sonar_api_token]):
            raise ValueError("SonarQube URL or Token not configured.")

    def get_quality_gate_status(self, project_key):
        """
        Fetches the Quality Gate status for a project from SonarQube.
        """
        # SonarQube API endpoint for quality gate status
        # We assume the main branch is what's being checked. This can be parameterized.
        url = f"{self.sonar_api_url}/api/qualitygates/project_status"

        params = {"projectKey": project_key}
        auth = (self.sonar_api_token, "")

        try:
            response = requests.get(url, params=params, auth=auth, timeout=10)
            response.raise_for_status()

            data = response.json()
            project_status = data.get("projectStatus", {})
            status = project_status.get("status")

            if status == "OK":
                return {"status": "SUCCESS", "message": "SonarQube Quality Gate passed."}

            if status == "ERROR":
                failed_conditions = []
                conditions = project_status.get("conditions", [])
                for cond in conditions:
                    if cond.get("status") == "ERROR":
                        metric = cond.get('metricKey')
                        actual = cond.get('actualValue')
                        threshold = cond.get('errorThreshold')
                        failed_conditions.append(
                            f"'{metric}' is '{actual}' (threshold is {threshold})"
                        )

                message = f"SonarQube Quality Gate failed. Issues: {'; '.join(failed_conditions)}"
                return {"status": "FAILURE", "message": message}

            return {"status": "FAILURE", "message": f"SonarQube Quality Gate status is '{status}'."}

        except requests.exceptions.RequestException as e:
            print(f"Error fetching SonarQube status: {e}")
            raise
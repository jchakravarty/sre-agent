"""This module contains the functions to interact with the Git API."""
import os
import base64
import requests
from src.utils import secrets_manager

class GitClient:
    """A client for interacting with the Git API."""

    def __init__(self):
        self.git_api_token = secrets_manager.get_secret_value("GIT_API_TOKEN")
        self.git_api_url = "https://api.github.com"  # This can be parameterized for other Git providers
        if not self.git_api_token:
            raise ValueError("GIT_API_TOKEN environment variable not set.")

    def get_file_content(self, repo_name, file_path, commit_sha):
        """
        Fetches the content of a file from a Git repository at a specific commit.
        Assumes GitHub API, but can be adapted.
        repo_name should be in the format 'owner/repo'.
        """
        # The repo_name from Harness might be 'org.project', which needs to be 'org/project'
        # for GitHub API
        if '.' in repo_name:
            repo_name = repo_name.replace('.', '/', 1)

        url = f"{self.git_api_url}/repos/{repo_name}/contents/{file_path}?ref={commit_sha}"

        headers = {
            "Authorization": f"token {self.git_api_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)

            data = response.json()
            if data.get('encoding') == 'base64':
                return base64.b64decode(data['content']).decode('utf-8')
            return data['content']

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"File '{file_path}' not found in repo '{repo_name}' at commit '{commit_sha}'.")
                return None
            print(f"HTTP error fetching file: {e}")
            raise
        except requests.exceptions.RequestException as e:
            print(f"Error fetching file from Git: {e}")
            raise
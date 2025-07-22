"""This module contains a client for the Ollama API."""
import os
import json
import urllib.request
from .base import LLMClient


class OllamaClient(LLMClient):
    """A client for the Ollama API."""
    def __init__(self, api_endpoint=None, model=None):
        self.api_endpoint = api_endpoint or os.environ.get(
            "OLLAMA_API_ENDPOINT", "http://localhost:11434/api/chat"
        )
        self.model = model or os.environ.get("OLLAMA_MODEL", "codellama:13b")

    def call(self, messages, tools=None):
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False
        }
        if tools:
            payload["tools"] = tools

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            self.api_endpoint, data=data, headers=headers, method='POST'
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            response_data = json.loads(response.read().decode('utf-8'))
            return response_data.get('message', {})

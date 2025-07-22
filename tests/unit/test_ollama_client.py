import unittest
from unittest.mock import patch, MagicMock
import json
import urllib.request
import urllib.error
from src.llm_client.ollama_client import OllamaClient


class TestOllamaClient(unittest.TestCase):

    def test_init_with_defaults(self):
        """Test OllamaClient initialization with default values"""
        with patch.dict('os.environ', {}, clear=True):
            client = OllamaClient()
            self.assertEqual(client.api_endpoint, "http://localhost:11434/api/chat")
            self.assertEqual(client.model, "codellama:13b")

    def test_init_with_environment_variables(self):
        """Test OllamaClient initialization with environment variables"""
        with patch.dict('os.environ', {
            'OLLAMA_API_ENDPOINT': 'http://custom-endpoint:8080/api/chat',
            'OLLAMA_MODEL': 'custom-model:7b'
        }):
            client = OllamaClient()
            self.assertEqual(client.api_endpoint, "http://custom-endpoint:8080/api/chat")
            self.assertEqual(client.model, "custom-model:7b")

    def test_init_with_explicit_parameters(self):
        """Test OllamaClient initialization with explicit parameters"""
        client = OllamaClient(
            api_endpoint="http://explicit-endpoint:9000/api/chat",
            model="explicit-model:latest"
        )
        self.assertEqual(client.api_endpoint, "http://explicit-endpoint:9000/api/chat")
        self.assertEqual(client.model, "explicit-model:latest")

    @patch('src.llm_client.ollama_client.urllib.request.urlopen')
    def test_call_success_without_tools(self, mock_urlopen):
        """Test successful API call without tools"""
        # Mock response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "message": {"role": "assistant", "content": "Test response"}
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        client = OllamaClient()
        messages = [{"role": "user", "content": "Hello"}]
        
        result = client.call(messages)
        
        self.assertEqual(result, {"role": "assistant", "content": "Test response"})
        mock_urlopen.assert_called_once()

    @patch('src.llm_client.ollama_client.urllib.request.urlopen')
    def test_call_success_with_tools(self, mock_urlopen):
        """Test successful API call with tools"""
        # Mock response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "message": {"role": "assistant", "content": "Tool response"}
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        client = OllamaClient()
        messages = [{"role": "user", "content": "Use tools"}]
        tools = [{"name": "test_tool", "description": "A test tool"}]
        
        result = client.call(messages, tools=tools)
        
        self.assertEqual(result, {"role": "assistant", "content": "Tool response"})

    @patch('src.llm_client.ollama_client.urllib.request.urlopen')
    def test_call_request_parameters(self, mock_urlopen):
        """Test that call method constructs request with correct parameters"""
        # Mock response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "message": {"role": "assistant", "content": "Test"}
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        client = OllamaClient(
            api_endpoint="http://test-endpoint:8080/api/chat",
            model="test-model:latest"
        )
        messages = [{"role": "user", "content": "Test message"}]
        tools = [{"name": "tool1"}]
        
        client.call(messages, tools=tools)
        
        # Verify the request was constructed correctly
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        
        # Check URL
        self.assertEqual(request.full_url, "http://test-endpoint:8080/api/chat")
        
        # Check method
        self.assertEqual(request.get_method(), "POST")
        
        # Check headers
        self.assertEqual(request.headers["Content-type"], "application/json")
        
        # Check payload
        payload = json.loads(request.data.decode('utf-8'))
        expected_payload = {
            "model": "test-model:latest",
            "messages": messages,
            "stream": False,
            "tools": tools
        }
        self.assertEqual(payload, expected_payload)

    @patch('src.llm_client.ollama_client.urllib.request.urlopen')
    def test_call_no_message_in_response(self, mock_urlopen):
        """Test API call when response has no message field"""
        # Mock response without message field
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "other_field": "value"
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        client = OllamaClient()
        messages = [{"role": "user", "content": "Hello"}]
        
        result = client.call(messages)
        
        self.assertEqual(result, {})

    @patch('src.llm_client.ollama_client.urllib.request.urlopen')
    def test_call_url_error(self, mock_urlopen):
        """Test API call with URL error"""
        # Mock URL error
        mock_urlopen.side_effect = urllib.error.URLError("Connection failed")
        
        client = OllamaClient()
        messages = [{"role": "user", "content": "Hello"}]
        
        with self.assertRaises(urllib.error.URLError):
            client.call(messages)

    @patch('src.llm_client.ollama_client.urllib.request.urlopen')
    def test_call_http_error(self, mock_urlopen):
        """Test API call with HTTP error"""
        # Mock HTTP error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="http://test", code=500, msg="Server Error", 
            hdrs=None, fp=None
        )
        
        client = OllamaClient()
        messages = [{"role": "user", "content": "Hello"}]
        
        with self.assertRaises(urllib.error.HTTPError):
            client.call(messages)

    @patch('src.llm_client.ollama_client.urllib.request.urlopen')
    def test_call_json_decode_error(self, mock_urlopen):
        """Test API call with JSON decode error"""
        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.read.return_value = b"invalid json"
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        client = OllamaClient()
        messages = [{"role": "user", "content": "Hello"}]
        
        with self.assertRaises(json.JSONDecodeError):
            client.call(messages)


if __name__ == '__main__':
    unittest.main()

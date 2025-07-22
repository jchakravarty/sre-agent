import unittest
from unittest.mock import patch, MagicMock
import json
import urllib.request
import urllib.error
from src.llm_client.bring_your_own_llm_client import BringYourOwnLLMClient


class TestBringYourOwnLLMClient(unittest.TestCase):

    def test_init(self):
        """Test initialization of BringYourOwnLLMClient"""
        client = BringYourOwnLLMClient(api_key="test-key", api_endpoint="http://api.test.com")
        self.assertEqual(client.api_key, "test-key")
        self.assertEqual(client.api_endpoint, "http://api.test.com")

    @patch('src.llm_client.bring_your_own_llm_client.urllib.request.urlopen')
    def test_call_success(self, mock_urlopen):
        """Test successful API call with bring your own LLM client"""
        # Mock response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"response": "Test response"}).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        client = BringYourOwnLLMClient(api_key="test-key", api_endpoint="http://api.test.com")
        messages = [{"role": "user", "content": "Hello"}]
        tools = [{"name": "test-tool"}]
        
        result = client.call(messages, tools=tools)
        
        self.assertEqual(result, {"response": "Test response"})
        mock_urlopen.assert_called_once()

    @patch('src.llm_client.bring_your_own_llm_client.urllib.request.urlopen')
    def test_call_request_parameters(self, mock_urlopen):
        """Test that call method constructs request with correct parameters"""
        # Mock response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "response": "Test"
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        client = BringYourOwnLLMClient(
            api_key="custom-key", api_endpoint="http://custom-api.test.com"
        )
        messages = [{"role": "user", "content": "Test message"}]
        tools = [{"name": "tool1"}]
        
        client.call(messages, tools=tools)
        
        # Verify the request was constructed correctly
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        
        # Check URL
        self.assertEqual(request.full_url, "http://custom-api.test.com")
        
        # Check method
        self.assertEqual(request.get_method(), "POST")
        
        # Check headers
        self.assertEqual(request.headers["Content-type"], "application/json")
        self.assertEqual(request.headers["Authorization"], "Bearer custom-key")
        
        # Check payload
        payload = json.loads(request.data.decode('utf-8'))
        expected_payload = {
            "messages": messages,
            "tools": tools
        }
        self.assertEqual(payload, expected_payload)

    @patch('src.llm_client.bring_your_own_llm_client.urllib.request.urlopen')
    def test_call_no_tools(self, mock_urlopen):
        """Test API call without tools parameter"""
        # Mock response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "response": "Test"
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        client = BringYourOwnLLMClient(api_key="test-key", api_endpoint="http://api.test.com")
        messages = [{"role": "user", "content": "Just a message"}]
        
        result = client.call(messages)
        
        self.assertEqual(result, {"response": "Test"})

    @patch('src.llm_client.bring_your_own_llm_client.urllib.request.urlopen')
    def test_call_url_error(self, mock_urlopen):
        """Test API call with URL error"""
        # Mock URL error
        mock_urlopen.side_effect = urllib.error.URLError("Connection failed")
        
        client = BringYourOwnLLMClient(api_key="test-key", api_endpoint="http://api.test.com")
        messages = [{"role": "user", "content": "Hello"}]
        
        with self.assertRaises(urllib.error.URLError):
            client.call(messages)

    @patch('src.llm_client.bring_your_own_llm_client.urllib.request.urlopen')
    def test_call_http_error(self, mock_urlopen):
        """Test API call with HTTP error"""
        # Mock HTTP error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="http://test", code=500, msg="Server Error", 
            hdrs=None, fp=None
        )
        
        client = BringYourOwnLLMClient(api_key="test-key", api_endpoint="http://api.test.com")
        messages = [{"role": "user", "content": "Hello"}]
        
        with self.assertRaises(urllib.error.HTTPError):
            client.call(messages)

    @patch('src.llm_client.bring_your_own_llm_client.urllib.request.urlopen')
    def test_call_json_decode_error(self, mock_urlopen):
        """Test API call with JSON decode error"""
        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.read.return_value = b"invalid json"
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        client = BringYourOwnLLMClient(api_key="test-key", api_endpoint="http://api.test.com")
        messages = [{"role": "user", "content": "Hello"}]
        
        with self.assertRaises(json.JSONDecodeError):
            client.call(messages)


if __name__ == '__main__':
    unittest.main()

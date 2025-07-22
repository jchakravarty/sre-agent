import unittest
import os
import requests
from unittest.mock import patch, MagicMock
import pytest
from src.connectors.dynatrace_client import DynatraceClient
from src.connectors.sonarqube_client import SonarQubeClient
from src.connectors.wiz_client import WizClient
from src.connectors.slack_client import SlackClient
from src.connectors.git_client import GitClient


class TestConnectorIntegration:

    def test_dynatrace_client_integration(self):
        """Test Dynatrace client integration."""
        mock_event_response = {
            'eventIngestResults': [
                {
                    'status': 'OK',
                    'correlationId': 'test-correlation-id'
                }
            ]
        }
        
        with patch.dict(os.environ, {
            'DYNATRACE_API_URL': 'https://test.dynatrace.com',
            'DYNATRACE_API_TOKEN': 'test_token'
        }):
            with patch('src.utils.secrets_manager.get_secret_value', side_effect=lambda x: os.environ.get(x)):
                with patch('requests.post') as mock_post:
                    mock_post.return_value.status_code = 200
                    mock_post.return_value.json.return_value = mock_event_response
                    
                    client = DynatraceClient()
                    
                    test_event = {
                        'eventType': 'CUSTOM_INFO',
                        'title': 'Test Event',
                        'entitySelector': 'type(CUSTOM_DEVICE)'
                    }
                    
                    result = client.send_event(test_event)
                    
                    assert result['eventIngestResults'][0]['status'] == 'OK'
                    assert 'correlationId' in result['eventIngestResults'][0]
                    
                    # Verify the request was made correctly
                    mock_post.assert_called_once()
                    call_args = mock_post.call_args
                    assert 'events/ingest' in call_args[0][0]
                    assert call_args[1]['headers']['Authorization'] == 'Api-Token test_token'
                    assert call_args[1]['json'] == test_event

    def test_sonarqube_client_integration(self):
        """Test SonarQube client integration."""
        mock_quality_gate_response = {
            'projectStatus': {
                'status': 'OK',
                'conditions': [
                    {
                        'status': 'OK',
                        'metricKey': 'coverage',
                        'actualValue': '85.5'
                    }
                ]
            }
        }
        
        with patch.dict(os.environ, {
            'SONAR_API_URL': 'https://sonarqube.example.com',
            'SONAR_API_TOKEN': 'test_sonar_token'
        }):
            with patch('src.utils.secrets_manager.get_secret_value', side_effect=lambda x: os.environ.get(x)):
                with patch('requests.get') as mock_get:
                    mock_get.return_value.status_code = 200
                    mock_get.return_value.json.return_value = mock_quality_gate_response
                    
                    client = SonarQubeClient()
                    result = client.get_quality_gate_status('test-project')
                    
                    assert result['status'] == 'SUCCESS'
                    assert 'SonarQube Quality Gate passed' in result['message']
                    
                    # Verify the request was made correctly
                    mock_get.assert_called_once()
                    call_args = mock_get.call_args
                    assert 'qualitygates/project_status' in call_args[0][0]
                    assert call_args[1]['auth'] == ('test_sonar_token', '')

    def test_wiz_client_integration(self):
        """Test Wiz client integration."""
        mock_cve_response = {
            'count': 3
        }
        
        with patch.dict(os.environ, {
            'WIZ_API_URL': 'https://api.wiz.io',
            'WIZ_API_TOKEN': 'test_wiz_token'
        }):
            with patch('src.utils.secrets_manager.get_secret_value', side_effect=lambda x: os.environ.get(x)):
                with patch('requests.get') as mock_get:
                    mock_get.return_value.status_code = 200
                    mock_get.return_value.json.return_value = mock_cve_response
                    
                    client = WizClient()
                    result = client.get_cve_status('test-artifact:v1.0.0')
                    
                    assert result['status'] == 'FAILURE'
                    assert 'critical vulnerabilities' in result['message']
                    
                    # Verify the request was made correctly
                    mock_get.assert_called_once()
                    call_args = mock_get.call_args
                    assert 'api/v1/images' in call_args[0][0]
                    assert call_args[1]['headers']['Authorization'] == 'Bearer test_wiz_token'

    def test_slack_client_integration(self):
        """Test Slack client integration."""
        mock_slack_response = {
            'ok': True,
            'message': {
                'ts': '1234567890.123456'
            }
        }
        
        with patch.dict(os.environ, {
            'SLACK_WEBHOOK_URL': 'https://hooks.slack.com/services/test/webhook/url'
        }):
            with patch('src.utils.secrets_manager.get_secret_value', side_effect=lambda x: os.environ.get(x)):
                with patch('requests.post') as mock_post:
                    mock_post.return_value.status_code = 200
                    mock_post.return_value.json.return_value = mock_slack_response
                    
                    client = SlackClient()
                    
                    test_notification = {
                        'blocks': [
                            {
                                'type': 'section',
                                'text': {
                                    'type': 'mrkdwn',
                                    'text': 'Test notification'
                                }
                            }
                        ]
                    }
                    
                    result = client.send_notification(test_notification)
                    
                    assert result['ok'] is True
                    assert 'ts' in result['message']
                    
                    # Verify webhook was called
                    mock_post.assert_called_once()
                    call_args = mock_post.call_args
                    assert 'hooks.slack.com' in call_args[0][0]

    def test_git_client_integration(self):
        """Test Git client integration."""
        mock_file_response = {
            'content': 'SGVsbG8gV29ybGQ=',  # base64 encoded "Hello World"
            'encoding': 'base64'
        }
        
        with patch.dict(os.environ, {
            'GIT_API_TOKEN': 'test_github_token'
        }):
            with patch('src.utils.secrets_manager.get_secret_value', side_effect=lambda x: os.environ.get(x)):
                with patch('requests.get') as mock_get:
                    mock_get.return_value.status_code = 200
                    mock_get.return_value.json.return_value = mock_file_response
                    
                    client = GitClient()
                    result = client.get_file_content('test-org/test-repo', 'README.md', 'abc123')
                    
                    assert result == 'Hello World'
                    
                    # Verify API was called correctly
                    mock_get.assert_called_once()
                    call_args = mock_get.call_args
                    assert 'api.github.com' in call_args[0][0]
                    assert call_args[1]['headers']['Authorization'] == 'token test_github_token'

    def test_connector_error_handling(self):
        """Test error handling in connectors."""
        with patch.dict(os.environ, {
            'DYNATRACE_API_URL': 'https://test.dynatrace.com',
            'DYNATRACE_API_TOKEN': 'test_token'
        }):
            with patch('src.utils.secrets_manager.get_secret_value', side_effect=lambda x: os.environ.get(x)):
                with patch('requests.post') as mock_post:
                    # Simulate API error
                    mock_post.return_value.status_code = 500
                    mock_post.return_value.raise_for_status.side_effect = requests.exceptions.HTTPError('500 Server Error')
                    
                    client = DynatraceClient()
                    
                    test_event = {
                        'eventType': 'CUSTOM_INFO',
                        'title': 'Test Event'
                    }
                    
                    # Should handle error gracefully
                    result = client.send_event(test_event)
                    
                    # Should return None due to error
                    assert result is None

    def test_connector_configuration_validation(self):
        """Test connector configuration validation."""
        # Test missing configuration
        with patch.dict(os.environ, {}, clear=True):
            with patch('src.utils.secrets_manager.get_secret_value', side_effect=lambda x: os.environ.get(x)):
                with pytest.raises(ValueError, match="Dynatrace API URL or Token not configured"):
                    DynatraceClient()
        
        # Test missing SonarQube config
        with patch.dict(os.environ, {}, clear=True):
            with patch('src.utils.secrets_manager.get_secret_value', side_effect=lambda x: os.environ.get(x)):
                with pytest.raises(ValueError, match="SonarQube URL or Token not configured"):
                    SonarQubeClient()
        
        # Test missing Wiz config
        with patch.dict(os.environ, {}, clear=True):
            with patch('src.utils.secrets_manager.get_secret_value', side_effect=lambda x: os.environ.get(x)):
                with pytest.raises(ValueError, match="Wiz API URL or Token not configured"):
                    WizClient()

    def test_connector_timeout_handling(self):
        """Test connector timeout handling."""
        with patch.dict(os.environ, {
            'DYNATRACE_API_URL': 'https://test.dynatrace.com',
            'DYNATRACE_API_TOKEN': 'test_token'
        }):
            with patch('src.utils.secrets_manager.get_secret_value', side_effect=lambda x: os.environ.get(x)):
                with patch('requests.post') as mock_post:
                    # Simulate timeout
                    mock_post.side_effect = requests.exceptions.Timeout("Request timed out")
                    
                    client = DynatraceClient()
                    
                    test_event = {
                        'eventType': 'CUSTOM_INFO',
                        'title': 'Test Event'
                    }
                    
                    # Should handle timeout gracefully
                    result = client.send_event(test_event)
                    
                    # Should return None due to timeout
                    assert result is None

    def test_multiple_connector_integration(self):
        """Test integration between multiple connectors."""
        # Mock responses for all connectors
        mock_responses = {
            'dynatrace': {'eventIngestResults': [{'status': 'OK'}]},
            'sonarqube': {'projectStatus': {'status': 'OK'}},
            'wiz': {'count': 0},
            'slack': {'ok': True}
        }
        
        with patch.dict(os.environ, {
            'DYNATRACE_API_URL': 'https://test.dynatrace.com',
            'DYNATRACE_API_TOKEN': 'test_token',
            'SONAR_API_URL': 'https://sonarqube.example.com',
            'SONAR_API_TOKEN': 'test_sonar_token',
            'WIZ_API_URL': 'https://api.wiz.io',
            'WIZ_API_TOKEN': 'test_wiz_token',
            'SLACK_WEBHOOK_URL': 'https://hooks.slack.com/test',
            'GIT_API_TOKEN': 'test_github_token'
        }):
            with patch('src.utils.secrets_manager.get_secret_value', side_effect=lambda x: os.environ.get(x)):
                with patch('requests.post') as mock_post:
                    with patch('requests.get') as mock_get:

                        # Configure mock responses
                        def mock_post_response(url, **kwargs):
                            mock_resp = MagicMock()
                            mock_resp.status_code = 200
                            if 'dynatrace' in url:
                                mock_resp.json.return_value = mock_responses['dynatrace']
                            elif 'slack' in url:
                                mock_resp.json.return_value = mock_responses['slack']
                            return mock_resp

                        def mock_get_response(url, **kwargs):
                            mock_resp = MagicMock()
                            mock_resp.status_code = 200
                            if 'sonarqube' in url:
                                mock_resp.json.return_value = mock_responses['sonarqube']
                            elif 'wiz' in url:
                                mock_resp.json.return_value = mock_responses['wiz']
                            return mock_resp

                        mock_post.side_effect = mock_post_response
                        mock_get.side_effect = mock_get_response

                        # Test all connectors working together
                        dynatrace_client = DynatraceClient()
                        sonarqube_client = SonarQubeClient()
                        wiz_client = WizClient()
                        slack_client = SlackClient()

                        # Test each connector
                        dt_result = dynatrace_client.send_event({'eventType': 'CUSTOM_INFO', 'title': 'Test'})
                        sq_result = sonarqube_client.get_quality_gate_status('test-project')
                        wiz_result = wiz_client.get_cve_status('test-artifact')
                        slack_result = slack_client.send_notification({'text': 'Test notification'})

                        # Verify results
                        assert dt_result['eventIngestResults'][0]['status'] == 'OK'
                        assert sq_result['status'] == 'SUCCESS'
                        assert wiz_result['status'] == 'SUCCESS'
                        assert slack_result['ok'] is True

                        # Verify all APIs were called
                        assert mock_post.call_count >= 2  # Dynatrace + Slack
                        assert mock_get.call_count >= 2   # SonarQube + Wiz

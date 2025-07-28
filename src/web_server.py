"""
Web server wrapper for SRE Orchestration Agent.

This module provides a Flask web server that wraps the Lambda functions
to enable performance testing and local development.
"""

import json
import os
from flask import Flask, request, jsonify
from .main import lambda_handler

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'sre-agent',
        'version': '1.0.0'
    })

@app.route('/', methods=['GET'])
def root():
    """Root endpoint."""
    return jsonify({
        'service': 'SRE Orchestration Agent',
        'version': '1.0.0',
        'endpoints': {
            '/suggestion': 'POST - Get scaling suggestions',
            '/gate': 'POST - Quality gate checks',
            '/health': 'GET - Health check'
        }
    })

@app.route('/suggestion', methods=['POST'])
def suggestion_endpoint():
    """Suggestion endpoint wrapper."""
    try:
        # Convert Flask request to Lambda event format
        event = {
            'path': '/suggest',
            'httpMethod': 'POST',
            'body': request.get_data(as_text=True),
            'headers': dict(request.headers),
            'queryStringParameters': dict(request.args) if request.args else None
        }
        
        # Call the Lambda handler
        response = lambda_handler(event, {})
        
        # Convert Lambda response to Flask response
        return jsonify(json.loads(response['body'])), response['statusCode']
    
    except Exception as e:
        return jsonify({
            'status': 'ERROR',
            'message': f'Internal server error: {str(e)}'
        }), 500

@app.route('/gate', methods=['POST'])
def gate_endpoint():
    """Quality gate endpoint wrapper."""
    try:
        # Convert Flask request to Lambda event format
        event = {
            'path': '/gate',
            'httpMethod': 'POST',
            'body': request.get_data(as_text=True),
            'headers': dict(request.headers),
            'queryStringParameters': dict(request.args) if request.args else None
        }
        
        # Call the Lambda handler
        response = lambda_handler(event, {})
        
        # Convert Lambda response to Flask response
        return jsonify(json.loads(response['body'])), response['statusCode']
    
    except Exception as e:
        return jsonify({
            'status': 'ERROR',
            'message': f'Internal server error: {str(e)}'
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"Starting SRE Agent web server on port {port}")
    print(f"Debug mode: {debug}")
    
    app.run(host='0.0.0.0', port=port, debug=debug) 
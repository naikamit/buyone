# app.py
from flask import Flask, request, jsonify, render_template
import os
import logging
import json
from datetime import datetime
import pytz
import traceback
import sys

from tasty_api import TastyTradeAPI
from trading import TradingLogic

# Configure logging - use more verbose DEBUG level
logging.basicConfig(
    level=logging.DEBUG,  # More detailed logging level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(stream=sys.stdout),  # Explicitly log to stdout for Render logs
        logging.FileHandler('app.log')
    ]
)

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize the Tasty Trade API with credentials from environment variables
username = os.environ.get('TASTYTRADE_USERNAME')
password = os.environ.get('TASTYTRADE_PASSWORD')
environment = os.environ.get('ENVIRONMENT', 'sandbox')
account_number = os.environ.get('ACCOUNT_NUMBER')

# Validate required environment variables
if not username:
    logger.error("TASTYTRADE_USERNAME environment variable is not set")
if not password:
    logger.error("TASTYTRADE_PASSWORD environment variable is not set")
if not account_number:
    logger.error("ACCOUNT_NUMBER environment variable is not set")

try:
    tasty_api = TastyTradeAPI(
        username=username,
        password=password,
        environment=environment
    )
    
    # Set the account number
    tasty_api.account_number = account_number
    
    logger.info(f"TastyTradeAPI initialized with username: {username}, environment: {environment}")
except ValueError as e:
    logger.error(f"Error initializing TastyTradeAPI: {str(e)}")
    # Create a placeholder API instance for the app to function
    tasty_api = None

# Initialize the trading logic
trading_logic = TradingLogic(tasty_api) if tasty_api is not None else None

# Store API calls for dashboard display
api_calls = []

@app.before_first_request
def initialize_app():
    """Initialize the app by logging in to Tasty Trade API"""
    logger.info("Initializing the application on first request")
    
    # Log environment details (without exposing credentials)
    logger.info(f"Username: {username or 'Not set'}")
    logger.info(f"Password: {'Set' if password else 'Not set'}")
    logger.info(f"Environment: {environment}")
    logger.info(f"Account Number: {account_number or 'Not set'}")
    
    # Test the authentication if API client is available
    if tasty_api is not None:
        login_success = tasty_api.login()
        if login_success:
            logger.info("Successfully authenticated with Tasty Trade API on startup")
        else:
            logger.error("Failed to authenticate with Tasty Trade API on startup")
    else:
        logger.error("Cannot authenticate - TastyTradeAPI client not initialized")

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Handle webhook requests from TradingView
    """
    # Log the incoming webhook request
    request_data = request.json
    ist_timestamp = datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S')
    
    # Create API call record for tracking
    api_call = {
        'timestamp': ist_timestamp,
        'direction': 'incoming',
        'endpoint': '/webhook',
        'method': 'POST',
        'data': request_data,
        'status': 'received'
    }
    
    api_calls.append(api_call)
    
    logger.info(f'Received webhook: {request_data}')
    
    # Check if API client was properly initialized
    if tasty_api is None:
        error_message = "TastyTradeAPI client is not initialized due to missing credentials"
        api_call['status'] = 'error'
        api_call['message'] = error_message
        logger.error(error_message)
        return jsonify({'status': 'error', 'message': error_message})
    
    try:
        # Validate signal
        signal = request_data.get('signal')
        if not signal:
            api_call['status'] = 'error'
            api_call['message'] = 'No signal provided'
            return jsonify({'status': 'error', 'message': 'No signal provided'})
        
        # Make sure we're authenticated
        if not tasty_api.session_token:
            logger.info('Not authenticated, logging in...')
            login_result = tasty_api.login()
            if not login_result:
                api_call['status'] = 'error'
                api_call['message'] = 'Failed to authenticate with Tasty Trade API'
                return jsonify({'status': 'error', 'message': 'Authentication failed'})
            
        # Process the signal
        result = trading_logic.process_signal(signal)
        
        # Log the result
        api_call['status'] = result['status']
        api_call['message'] = result['message']
        
        return jsonify(result)
    except Exception as e:
        # Log any exceptions that occur
        error_message = f"Error processing webhook: {str(e)}"
        logger.error(error_message)
        logger.error(traceback.format_exc())
        
        api_call['status'] = 'error'
        api_call['message'] = error_message
        
        return jsonify({'status': 'error', 'message': error_message})

@app.route('/')
def dashboard():
    """
    Display the dashboard showing all API calls
    """
    # Combine API calls from the Flask app and the Tasty Trade API
    all_api_calls = api_calls
    
    # Add API calls from tasty_api if it was properly initialized
    if tasty_api is not None:
        all_api_calls += tasty_api.api_calls
    
    # Sort by timestamp in descending order (most recent first)
    all_api_calls.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Add environment information to display on dashboard
    env_info = {
        'api_initialized': tasty_api is not None,
        'username': username if username else 'Not set',
        'environment': environment,
        'account_number': account_number if account_number else 'Not set'
    }
    
    return render_template('dashboard.html', api_calls=all_api_calls, env_info=env_info)

if __name__ == '__main__':
    # Login manually in development only
    if tasty_api is not None:
        tasty_api.login()
    
    # Start the server
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

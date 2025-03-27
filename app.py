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
tasty_api = TastyTradeAPI(
    username=os.environ.get('TASTYTRADE_USERNAME'),
    password=os.environ.get('TASTYTRADE_PASSWORD'),
    environment=os.environ.get('ENVIRONMENT', 'sandbox')
)

# Set the account number from environment variable
tasty_api.account_number = os.environ.get('ACCOUNT_NUMBER')

# Initialize the trading logic
trading_logic = TradingLogic(tasty_api)

# Store API calls for dashboard display
api_calls = []

@app.before_first_request
def initialize_app():
    """Initialize the app by logging in to Tasty Trade API"""
    logger.info("Initializing the application on first request")
    
    # Log environment details (without exposing credentials)
    logger.info(f"Username: {os.environ.get('TASTYTRADE_USERNAME', 'Not set')}")
    logger.info(f"Password: {'Set' if os.environ.get('TASTYTRADE_PASSWORD') else 'Not set'}")
    logger.info(f"Environment: {os.environ.get('ENVIRONMENT', 'Not set')}")
    logger.info(f"Account Number: {os.environ.get('ACCOUNT_NUMBER', 'Not set')}")
    
    # Test the authentication
    login_success = tasty_api.login()
    if login_success:
        logger.info("Successfully authenticated with Tasty Trade API on startup")
    else:
        logger.error("Failed to authenticate with Tasty Trade API on startup")

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
    all_api_calls = api_calls + tasty_api.api_calls
    
    # Sort by timestamp in descending order (most recent first)
    all_api_calls.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return render_template('dashboard.html', api_calls=all_api_calls)

if __name__ == '__main__':
    # Login manually in development only
    tasty_api.login()
    
    # Start the server
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

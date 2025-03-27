# tasty_api.py
import requests
import logging
import time
from datetime import datetime
import pytz
import json
import os

logger = logging.getLogger(__name__)

class TastyTradeAPI:
    def __init__(self, username, password, environment='sandbox'):
        """
        Initialize the Tasty Trade API client
        
        Args:
            username: Tasty Trade username or email
            password: Tasty Trade password
            environment: 'sandbox' or 'production'
        """
        self.username = username
        self.password = password
        self.environment = environment
        self.session_token = None
        self.account_number = None
        
        # Set the base URL based on the environment
        self.base_url = 'https://api.tastyworks.com' if environment == 'production' else 'https://api.cert.tastyworks.com'
        
        # Store API calls for dashboard display
        self.api_calls = []
        
    def _log_api_call(self, method, endpoint, request_data=None, response_data=None, status_code=None, error=None):
        """
        Log API call details for tracking and dashboard display
        """
        # Convert to IST timezone for display
        ist_timestamp = datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S')
        
        api_call = {
            'timestamp': ist_timestamp,
            'method': method,
            'endpoint': endpoint,
            'request_data': request_data,
            'response_data': response_data,
            'status_code': status_code,
            'error': error,
            'direction': 'outgoing',
            'status': 'error' if error else 'success'
        }
        
        self.api_calls.append(api_call)
        logger.info(f"API Call: {method} {endpoint} - Status: {status_code}")
        return api_call
        
    def login(self):
        """
        Authenticate with the Tasty Trade API and obtain a session token
        
        Returns:
            bool: True if authentication was successful, False otherwise
        """
        endpoint = '/sessions'
        method = 'POST'
        data = {
            'login': self.username,
            'password': self.password,
            'remember-me': True  # Add remember-me flag to potentially help with authentication
        }
        
        user_agent = 'TastyTradeWebhook/1.0'
        
        try:
            # Log the exact authentication request and URL
            logger.info(f"Attempting to authenticate with {self.base_url}{endpoint}")
            logger.info(f"Username: {self.username}, Environment: {self.environment}")
            
            response = requests.post(
                f'{self.base_url}{endpoint}',
                json=data,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'User-Agent': user_agent
                }
            )
            
            # Log detailed response information
            status_code = response.status_code
            response_text = response.text
            logger.info(f"Auth response status code: {status_code}")
            logger.info(f"Auth response text: {response_text}")
            
            # Try to parse JSON response if possible
            try:
                response_data = response.json()
                logger.info(f"Auth response JSON: {json.dumps(response_data, indent=2)}")
                
                if 'data' in response_data and 'session-token' in response_data['data']:
                    self.session_token = response_data['data']['session-token']
                    logger.info('Successfully authenticated with Tasty Trade API')
                    self._log_api_call(method, endpoint, data, response_data, status_code)
                    return True
                else:
                    error_msg = "Session token not found in response"
                    if 'error' in response_data:
                        error_msg = f"API error: {response_data['error']}"
                    logger.error(error_msg)
                    self._log_api_call(method, endpoint, data, response_data, status_code, error_msg)
                    return False
                    
            except json.JSONDecodeError:
                error_msg = f"Failed to parse response as JSON: {response_text}"
                logger.error(error_msg)
                self._log_api_call(method, endpoint, data, {"raw_text": response_text}, status_code, error_msg)
                return False
                
            # This is needed in case the response status is non-200 but it didn't raise an exception
            response.raise_for_status()
            
        except requests.exceptions.RequestException as e:
            # Handle specific request exceptions
            error_msg = f"Request exception: {str(e)}"
            logger.error(error_msg)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_response = e.response.json()
                    logger.error(f"Error response: {json.dumps(error_response, indent=2)}")
                except:
                    logger.error(f"Error response text: {e.response.text}")
            self._log_api_call(method, endpoint, data, None, getattr(e, 'response', None), error_msg)
            return False
        except Exception as e:
            # Handle all other exceptions
            error_msg = f"Unexpected error authenticating with Tasty Trade API: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self._log_api_call(method, endpoint, data, None, None, error_msg)
            return False
    
    def get_account_balance(self):
        """
        Get the account balance
        
        Returns:
            dict: Account balance data or None if the request failed
        """
        if not self.session_token:
            logger.error('Not authenticated')
            return None
            
        endpoint = f'/accounts/{self.account_number}/balances'
        method = 'GET'
        
        try:
            response = requests.get(
                f'{self.base_url}{endpoint}',
                headers={
                    'Authorization': self.session_token,
                    'Content-Type': 'application/json'
                }
            )
            response.raise_for_status()
            response_data = response.json()
            
            logger.info('Successfully retrieved account balance')
            self._log_api_call(method, endpoint, None, response_data, response.status_code)
            
            return response_data['data']
        except Exception as e:
            logger.error(f'Error getting account balance: {str(e)}')
            self._log_api_call(method, endpoint, None, None, None, str(e))
            return None
    
    def get_positions(self):
        """
        Get current positions in the account
        
        Returns:
            list: List of position objects or None if the request failed
        """
        if not self.session_token:
            logger.error('Not authenticated')
            return None
            
        endpoint = f'/accounts/{self.account_number}/positions'
        method = 'GET'
        
        try:
            response = requests.get(
                f'{self.base_url}{endpoint}',
                headers={
                    'Authorization': self.session_token,
                    'Content-Type': 'application/json'
                }
            )
            response.raise_for_status()
            response_data = response.json()
            
            logger.info('Successfully retrieved positions')
            self._log_api_call(method, endpoint, None, response_data, response.status_code)
            
            # Return the list of positions
            return response_data['data']['items']
        except Exception as e:
            logger.error(f'Error getting positions: {str(e)}')
            self._log_api_call(method, endpoint, None, None, None, str(e))
            return None
    
    def get_stock_price(self, symbol):
        """
        Get the price of a stock by buying 1 share and checking the difference in cash balance
        
        Args:
            symbol: Stock symbol
            
        Returns:
            float: Stock price or None if the request failed
        """
        if not self.session_token:
            logger.error('Not authenticated')
            return None
            
        # Get the initial cash balance
        initial_balance = self.get_account_balance()
        if not initial_balance:
            return None
            
        initial_cash = float(initial_balance['cash-available-to-withdraw'])
        
        # Buy 1 share of the stock
        order_result = self.place_order(symbol, 1, 'Buy to Open')
        if not order_result:
            return None
            
        # Wait for the order to fill
        time.sleep(1)
        
        # Get the new cash balance
        new_balance = self.get_account_balance()
        if not new_balance:
            return None
            
        new_cash = float(new_balance['cash-available-to-withdraw'])
        
        # Calculate the price (difference in cash balance)
        price = initial_cash - new_cash
        
        logger.info(f'Calculated price of {symbol}: {price}')
        
        return price
    
    def place_order(self, symbol, quantity, action):
        """
        Place a market order
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares
            action: Buy to Open, Sell to Open, Buy to Close, or Sell to Close
            
        Returns:
            dict: Order data or None if the request failed
        """
        if not self.session_token:
            logger.error('Not authenticated')
            return None
            
        endpoint = f'/accounts/{self.account_number}/orders'
        method = 'POST'
        
        data = {
            'time-in-force': 'Day',
            'order-type': 'Market',
            'legs': [
                {
                    'instrument-type': 'Equity',
                    'symbol': symbol,
                    'quantity': quantity,
                    'action': action
                }
            ]
        }
        
        try:
            response = requests.post(
                f'{self.base_url}{endpoint}',
                json=data,
                headers={
                    'Authorization': self.session_token,
                    'Content-Type': 'application/json'
                }
            )
            response.raise_for_status()
            response_data = response.json()
            
            logger.info(f'Successfully placed order for {quantity} shares of {symbol} with action {action}')
            self._log_api_call(method, endpoint, data, response_data, response.status_code)
            
            return response_data['data']['order']
        except Exception as e:
            logger.error(f'Error placing order: {str(e)}')
            self._log_api_call(method, endpoint, data, None, None, str(e))
            return None
    
    def close_position(self, symbol, quantity, direction):
        """
        Close a position
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares to close
            direction: Direction of the position (Long or Short)
            
        Returns:
            dict: Order data or None if the request failed
        """
        if not self.session_token:
            logger.error('Not authenticated')
            return None
            
        # Determine the appropriate action based on the position direction
        action = 'Sell to Close' if direction == 'Long' else 'Buy to Close'
        
        return self.place_order(symbol, quantity, action)

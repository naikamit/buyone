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
            'password': self.password
        }
        
        try:
            response = requests.post(
                f'{self.base_url}{endpoint}',
                json=data,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            response_data = response.json()
            
            # Extract session token
            self.session_token = response_data['data']['session-token']
            
            logger.info('Successfully authenticated with Tasty Trade API')
            self._log_api_call(method, endpoint, data, response_data, response.status_code)
            
            return True
        except Exception as e:
            logger.error(f'Error authenticating with Tasty Trade API: {str(e)}')
            self._log_api_call(method, endpoint, data, None, None, str(e))
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

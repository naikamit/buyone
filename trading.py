# trading.py
import logging
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TradingLogic:
    def __init__(self, tasty_api):
        """
        Initialize the trading logic
        
        Args:
            tasty_api: TastyTradeAPI instance
        """
        self.tasty_api = tasty_api
        self.last_successful_buy = None
        
    def process_signal(self, signal):
        """
        Process a trading signal from TradingView
        
        Args:
            signal: 'long' or 'short'
            
        Returns:
            dict: Result of the signal processing
        """
        # Validate signal
        if signal not in ['long', 'short']:
            logger.error(f'Invalid signal: {signal}')
            return {
                'status': 'error',
                'message': 'Invalid signal'
            }
            
        # Check if we're in the cooldown period (12 hours after a successful buy)
        if self.last_successful_buy:
            cooldown_period = timedelta(hours=12)
            time_since_last_buy = datetime.now() - self.last_successful_buy
            
            if time_since_last_buy < cooldown_period:
                logger.info('In cooldown period, closing MSTU and MSTZ positions')
                return self.close_positions(['MSTU', 'MSTZ'])
                
        # Process the signal based on type
        if signal == 'long':
            return self.process_long_signal()
        else:  # signal == 'short'
            return self.process_short_signal()
    
    def process_long_signal(self):
        """
        Process a long signal
        
        Returns:
            dict: Result of processing the long signal
        """
        # Get account balance
        balance = self.tasty_api.get_account_balance()
        if not balance:
            return {
                'status': 'error',
                'message': 'Failed to get account balance'
            }
            
        cash_available = float(balance['cash-available-to-withdraw'])
        
        # Get positions
        positions = self.tasty_api.get_positions()
        if positions is None:  # Could be empty list, which is fine
            return {
                'status': 'error',
                'message': 'Failed to get positions'
            }
            
        # Get price of MSTU
        price = self.tasty_api.get_stock_price('MSTU')
        if not price:
            return {
                'status': 'error',
                'message': 'Failed to get price of MSTU'
            }
            
        # Calculate quantity to buy based on whether positions exist or not
        if positions:
            # If other positions exist, use all available cash
            quantity = int(cash_available / price)
        else:
            # If no positions exist, use 50% of available cash
            quantity = int(cash_available * 0.5 / price)
            
        if quantity <= 0:
            return {
                'status': 'error',
                'message': 'Not enough cash to buy MSTU'
            }
            
        # Buy MSTU
        order_result = self.tasty_api.place_order('MSTU', quantity, 'Buy to Open')
        
        # If order failed, retry with 95% less quantity
        if not order_result:
            reduced_quantity = int(quantity * 0.05)
            if reduced_quantity <= 0:
                return {
                    'status': 'error',
                    'message': 'Failed to buy MSTU'
                }
                
            logger.info(f'Retrying with reduced quantity: {reduced_quantity}')
            order_result = self.tasty_api.place_order('MSTU', reduced_quantity, 'Buy to Open')
            
            if not order_result:
                return {
                    'status': 'error',
                    'message': 'Failed to buy MSTU even with reduced quantity'
                }
            else:
                quantity = reduced_quantity
                
        # If there were existing positions, close them
        if positions:
            time.sleep(1)  # Pause for 1 second
            closed_positions = []
            
            for position in positions:
                symbol = position['symbol']
                pos_quantity = int(float(position['quantity']))
                direction = position['quantity-direction']
                
                if symbol != 'MSTU':  # Don't close the MSTU position we just bought
                    result = self.tasty_api.close_position(symbol, pos_quantity, direction)
                    if result:
                        closed_positions.append(symbol)
            
            logger.info(f'Closed positions: {", ".join(closed_positions)}')
                    
        # Update last successful buy timestamp
        self.last_successful_buy = datetime.now()
        
        return {
            'status': 'success',
            'message': f'Bought {quantity} shares of MSTU',
            'quantity': quantity,
            'symbol': 'MSTU'
        }
    
    def process_short_signal(self):
        """
        Process a short signal
        
        Returns:
            dict: Result of processing the short signal
        """
        # Get account balance
        balance = self.tasty_api.get_account_balance()
        if not balance:
            return {
                'status': 'error',
                'message': 'Failed to get account balance'
            }
            
        cash_available = float(balance['cash-available-to-withdraw'])
        
        # Get positions
        positions = self.tasty_api.get_positions()
        if positions is None:  # Could be empty list, which is fine
            return {
                'status': 'error',
                'message': 'Failed to get positions'
            }
            
        # Get price of MSTZ
        price = self.tasty_api.get_stock_price('MSTZ')
        if not price:
            return {
                'status': 'error',
                'message': 'Failed to get price of MSTZ'
            }
            
        # Calculate quantity to buy based on whether positions exist or not
        if positions:
            # If other positions exist, use all available cash
            quantity = int(cash_available / price)
        else:
            # If no positions exist, use 50% of available cash
            quantity = int(cash_available * 0.5 / price)
            
        if quantity <= 0:
            return {
                'status': 'error',
                'message': 'Not enough cash to buy MSTZ'
            }
            
        # Buy MSTZ
        order_result = self.tasty_api.place_order('MSTZ', quantity, 'Buy to Open')
        
        # If order failed, retry with 95% less quantity
        if not order_result:
            reduced_quantity = int(quantity * 0.05)
            if reduced_quantity <= 0:
                return {
                    'status': 'error',
                    'message': 'Failed to buy MSTZ'
                }
                
            logger.info(f'Retrying with reduced quantity: {reduced_quantity}')
            order_result = self.tasty_api.place_order('MSTZ', reduced_quantity, 'Buy to Open')
            
            if not order_result:
                return {
                    'status': 'error',
                    'message': 'Failed to buy MSTZ even with reduced quantity'
                }
            else:
                quantity = reduced_quantity
                
        # If there were existing positions, close them
        if positions:
            time.sleep(1)  # Pause for 1 second
            closed_positions = []
            
            for position in positions:
                symbol = position['symbol']
                pos_quantity = int(float(position['quantity']))
                direction = position['quantity-direction']
                
                if symbol != 'MSTZ':  # Don't close the MSTZ position we just bought
                    result = self.tasty_api.close_position(symbol, pos_quantity, direction)
                    if result:
                        closed_positions.append(symbol)
            
            logger.info(f'Closed positions: {", ".join(closed_positions)}')
                    
        # Update last successful buy timestamp
        self.last_successful_buy = datetime.now()
        
        return {
            'status': 'success',
            'message': f'Bought {quantity} shares of MSTZ',
            'quantity': quantity,
            'symbol': 'MSTZ'
        }
    
    def close_positions(self, symbols=None):
        """
        Close positions for specified symbols
        
        Args:
            symbols: List of symbols to close positions for (None = close all)
            
        Returns:
            dict: Result of closing positions
        """
        positions = self.tasty_api.get_positions()
        if positions is None:
            return {
                'status': 'error',
                'message': 'Failed to get positions'
            }
            
        if not positions:
            return {
                'status': 'success',
                'message': 'No positions to close'
            }
            
        closed_positions = []
        
        for position in positions:
            symbol = position['symbol']
            if not symbols or symbol in symbols:
                quantity = int(float(position['quantity']))
                direction = position['quantity-direction']
                
                result = self.tasty_api.close_position(symbol, quantity, direction)
                if result:
                    closed_positions.append(symbol)
                
        if closed_positions:
            return {
                'status': 'success',
                'message': f'Closed positions: {", ".join(closed_positions)}',
                'closed_positions': closed_positions
            }
        else:
            return {
                'status': 'success',
                'message': 'No matching positions found to close'
            }

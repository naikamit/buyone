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
    
    def binary_search_max_quantity(self, symbol, max_cash):
        """
        Find maximum purchasable quantity using binary search
        
        Args:
            symbol: Stock symbol to buy
            max_cash: Maximum cash available to spend
            
        Returns:
            int: Maximum quantity that can be successfully purchased
        """
        logger.info(f'Starting binary search for maximum quantity of {symbol} with max cash: {max_cash}')
        
        # Get the price of the stock
        price = self.tasty_api.get_stock_price(symbol)
        if not price or price <= 0:
            logger.error(f'Failed to get valid price for {symbol}')
            return 0
        
        # Calculate theoretical maximum based on price and cash
        theoretical_max = int(max_cash / price)
        logger.info(f'Theoretical maximum quantity for {symbol}: {theoretical_max} at price {price}')
        
        if theoretical_max <= 0:
            logger.info(f'Not enough cash to buy any {symbol}')
            return 0
        
        # Binary search bounds
        low = 1
        high = theoretical_max
        max_successful = 0
        
        logger.info(f'Starting binary search with low={low}, high={high}')
        
        while low <= high:
            mid = (low + high) // 2
            logger.info(f'Trying to buy {mid} shares of {symbol}')
            
            order_result = self.tasty_api.place_order(symbol, mid, 'Buy to Open')
            
            if order_result:
                # If successful, try higher quantity
                logger.info(f'Successfully bought {mid} shares of {symbol}, trying higher')
                max_successful = mid
                low = mid + 1
            else:
                # If failed, try lower quantity
                logger.info(f'Failed to buy {mid} shares of {symbol}, trying lower')
                high = mid - 1
        
        logger.info(f'Binary search complete. Maximum quantity for {symbol}: {max_successful}')
        return max_successful
    
    def process_long_signal(self):
        """
        Process a long signal
        
        Returns:
            dict: Result of processing the long signal
        """
        logger.info('Processing long signal')
        
        # Get account balance
        balance = self.tasty_api.get_account_balance()
        if not balance:
            logger.error('Failed to get account balance')
            return {
                'status': 'error',
                'message': 'Failed to get account balance'
            }
            
        cash_available = float(balance['cash-available-to-withdraw'])
        logger.info(f'Cash available: {cash_available}')
        
        # Get positions
        positions = self.tasty_api.get_positions()
        if positions is None:  # Could be empty list, which is fine
            logger.error('Failed to get positions')
            return {
                'status': 'error',
                'message': 'Failed to get positions'
            }
            
        # Determine cash to use based on whether positions exist
        max_cash = cash_available if positions else cash_available * 0.5
        logger.info(f'Using {max_cash} for purchase ({"100%" if positions else "50%"} of available cash)')
        
        # Use binary search to find maximum quantity
        quantity = self.binary_search_max_quantity('MSTU', max_cash)
        
        if quantity <= 0:
            logger.error('Failed to buy any MSTU shares')
            return {
                'status': 'error',
                'message': 'Failed to buy MSTU'
            }
            
        logger.info(f'Successfully bought {quantity} shares of MSTU')
        
        # If positions exist, close all MSTZ positions
        if positions:
            logger.info('Pausing for 1 second before closing positions')
            time.sleep(1)  # Pause for 1 second
            
            mstz_positions = [pos for pos in positions if pos['symbol'] == 'MSTZ']
            
            if mstz_positions:
                logger.info(f'Found {len(mstz_positions)} MSTZ positions to close')
                for position in mstz_positions:
                    quantity_to_close = int(float(position['quantity']))
                    direction = position['quantity-direction']
                    
                    logger.info(f'Closing {quantity_to_close} shares of MSTZ ({direction})')
                    self.tasty_api.close_position('MSTZ', quantity_to_close, direction)
            else:
                logger.info('No MSTZ positions to close')
        
        # Update last successful buy timestamp
        self.last_successful_buy = datetime.now()
        logger.info(f'Updated last successful buy timestamp to {self.last_successful_buy}')
        
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
        logger.info('Processing short signal')
        
        # Get account balance
        balance = self.tasty_api.get_account_balance()
        if not balance:
            logger.error('Failed to get account balance')
            return {
                'status': 'error',
                'message': 'Failed to get account balance'
            }
            
        cash_available = float(balance['cash-available-to-withdraw'])
        logger.info(f'Cash available: {cash_available}')
        
        # Get positions
        positions = self.tasty_api.get_positions()
        if positions is None:  # Could be empty list, which is fine
            logger.error('Failed to get positions')
            return {
                'status': 'error',
                'message': 'Failed to get positions'
            }
            
        # Determine cash to use based on whether positions exist
        max_cash = cash_available if positions else cash_available * 0.5
        logger.info(f'Using {max_cash} for purchase ({"100%" if positions else "50%"} of available cash)')
        
        # Use binary search to find maximum quantity
        quantity = self.binary_search_max_quantity('MSTZ', max_cash)
        
        if quantity <= 0:
            logger.error('Failed to buy any MSTZ shares')
            return {
                'status': 'error',
                'message': 'Failed to buy MSTZ'
            }
            
        logger.info(f'Successfully bought {quantity} shares of MSTZ')
        
        # If positions exist, close all MSTU positions
        if positions:
            logger.info('Pausing for 1 second before closing positions')
            time.sleep(1)  # Pause for 1 second
            
            mstu_positions = [pos for pos in positions if pos['symbol'] == 'MSTU']
            
            if mstu_positions:
                logger.info(f'Found {len(mstu_positions)} MSTU positions to close')
                for position in mstu_positions:
                    quantity_to_close = int(float(position['quantity']))
                    direction = position['quantity-direction']
                    
                    logger.info(f'Closing {quantity_to_close} shares of MSTU ({direction})')
                    self.tasty_api.close_position('MSTU', quantity_to_close, direction)
            else:
                logger.info('No MSTU positions to close')
        
        # Update last successful buy timestamp
        self.last_successful_buy = datetime.now()
        logger.info(f'Updated last successful buy timestamp to {self.last_successful_buy}')
        
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
        logger.info(f'Closing positions for symbols: {symbols if symbols else "all"}')
        
        positions = self.tasty_api.get_positions()
        if positions is None:
            logger.error('Failed to get positions')
            return {
                'status': 'error',
                'message': 'Failed to get positions'
            }
            
        if not positions:
            logger.info('No positions to close')
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
                
                logger.info(f'Closing {quantity} shares of {symbol} ({direction})')
                result = self.tasty_api.close_position(symbol, quantity, direction)
                if result:
                    closed_positions.append(symbol)
                    logger.info(f'Successfully closed position in {symbol}')
                else:
                    logger.error(f'Failed to close position in {symbol}')
                
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

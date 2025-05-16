from datetime import datetime
import os
import logging

class Logger:
    _instance = None
    _last_date = None
    
    @staticmethod
    def get_logger():
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Create new logger if it doesn't exist or if the date has changed
        if Logger._instance is None or Logger._last_date != current_date:
            # Create logs directory
            log_directory = 'logs'
            os.makedirs(log_directory, exist_ok=True)
            
            # Create log filename with current date
            log_filename = os.path.join(log_directory, f"app_{current_date}.log")
            
            # Configure logger
            logger = logging.getLogger('app')
            logger.setLevel(logging.INFO)
            
            # Remove all existing handlers
            logger.handlers.clear()
            
            # Add new file handler
            file_handler = logging.FileHandler(log_filename, encoding='utf-8')
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logger.addHandler(file_handler)
            
            # Add console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logger.addHandler(console_handler)
            
            Logger._instance = logger
            Logger._last_date = current_date
            
        return Logger._instance

# Get logger instance
logger = Logger.get_logger()
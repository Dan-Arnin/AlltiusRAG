import logging
from datetime import datetime
import os

# Set up logging
def setup_logger():
    # Create logs directory if it doesn't exist
    log_dir = './logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # File path for the log file
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    LOG_FILE = f'{log_dir}/dmcc_rag_dev_{current_time}.log'

    logger = logging.getLogger('MyLogger')
    logger.setLevel(logging.INFO)

    # Create file handler that logs to 'my_log_file.log'
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.INFO)

    # Create formatter and add it to the handler
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(file_handler)
    return logger

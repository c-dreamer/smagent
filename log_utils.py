import logging
import logging.handlers
import os
from datetime import datetime

def setup_logging():
    """
    Set up logging for the social media agent.
    Logs to stdout (INFO+) and to a daily rotating file (DEBUG+).
    """
    # Create logs directory if it doesn't exist
    log_dir = "logs/social-media"
    os.makedirs(log_dir, exist_ok=True)

    # Define log format
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture all levels, handlers will filter

    # Avoid adding handlers multiple times
    if root_logger.handlers:
        return

    # stdout handler (INFO and above)
    stdout_handler = logging.StreamHandler()
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(formatter)
    root_logger.addHandler(stdout_handler)

    # file handler (DEBUG and above) with rotation
    log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log")
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

def get_logger(name: str) -> logging.Logger:
    """
    Factory function to get a logger with the given name.
    Ensures logging is set up.
    """
    setup_logging()
    return logging.getLogger(name)
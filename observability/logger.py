import logging
import json
import datetime
import os

# Ensure logs directory exists
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "component": record.name,
            "message": record.getMessage(),
        }
        # Add extra fields if present
        if hasattr(record, "event"):
            log_entry["event"] = record.event
        if hasattr(record, "data"):
            log_entry["data"] = record.data
            
        return json.dumps(log_entry)

def get_logger(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Avoid adding multiple handlers if get_logger is called multiple times
    if not logger.handlers:
        # File Handler
        file_handler = logging.FileHandler(os.path.join(LOG_DIR, "app.jsonl"))
        file_handler.setFormatter(JsonFormatter())
        logger.addHandler(file_handler)
        
        # Console Handler (optional, for dev visibility)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(console_handler)
        
    return logger

import functools
import json
import time
from datetime import datetime
from observability.logger import get_logger

logger = get_logger("Tracer")

def trace_agent(func):
    """Decorator to trace agent execution inputs and outputs."""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        agent_name = self.__class__.__name__
        method_name = func.__name__
        start_time = time.time()
        
        # Log Entry
        entry_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "agent_start",
            "agent": agent_name,
            "method": method_name,
            "args": [str(a) for a in args],
            "kwargs": {k: str(v) for k, v in kwargs.items()}
        }
        _log_trace(entry_log)
        
        try:
            result = func(self, *args, **kwargs)
            
            # Log Success
            duration = time.time() - start_time
            exit_log = {
                "timestamp": datetime.utcnow().isoformat(),
                "event": "agent_end",
                "agent": agent_name,
                "method": method_name,
                "duration_seconds": duration,
                "result": str(result)[:500] + "..." if len(str(result)) > 500 else str(result)
            }
            _log_trace(exit_log)
            return result
            
        except Exception as e:
            # Log Error
            duration = time.time() - start_time
            error_log = {
                "timestamp": datetime.utcnow().isoformat(),
                "event": "agent_error",
                "agent": agent_name,
                "method": method_name,
                "duration_seconds": duration,
                "error": str(e)
            }
            _log_trace(error_log)
            raise e
            
    return wrapper

def _log_trace(data):
    """Append trace data to a JSONL file."""
    try:
        with open("traces.jsonl", "a") as f:
            f.write(json.dumps(data) + "\n")
    except Exception as e:
        logger.error(f"Failed to write trace: {e}")
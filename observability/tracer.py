import uuid
import time
import contextvars
from typing import Optional
from observability.logger import get_logger

# Context variable to store the current trace ID
_trace_id_ctx = contextvars.ContextVar("trace_id", default=None)

def get_current_trace_id() -> Optional[str]:
    return _trace_id_ctx.get()

class Tracer:
    """
    Context manager for tracing operations.
    Manages trace_id and logs start/end of operations with latency.
    """
    def __init__(self, operation_name: str, trace_id: Optional[str] = None):
        self.operation_name = operation_name
        self.logger = get_logger("Tracer")
        self.trace_id = trace_id
        self.token = None
        self.start_time = None

    def __enter__(self):
        # Generate new trace ID if not provided and none exists in context
        current_id = get_current_trace_id()
        if self.trace_id:
            new_id = self.trace_id
        elif current_id:
            new_id = current_id
        else:
            new_id = str(uuid.uuid4())
        
        # Set the trace ID in context
        self.token = _trace_id_ctx.set(new_id)
        self.start_time = time.time()
        
        self.logger.info(f"Starting {self.operation_name}", extra={
            "event": "trace_start",
            "trace_id": new_id,
            "data": {"operation": self.operation_name}
        })
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        trace_id = get_current_trace_id()
        
        status = "error" if exc_type else "success"
        
        self.logger.info(f"Finished {self.operation_name}", extra={
            "event": "trace_end",
            "trace_id": trace_id,
            "data": {
                "operation": self.operation_name,
                "duration_ms": round(duration_ms, 2),
                "status": status
            }
        })
        
        # Reset context
        if self.token:
            _trace_id_ctx.reset(self.token)

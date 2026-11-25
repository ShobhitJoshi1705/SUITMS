import time
import random
import logging
from enum import Enum
from typing import Callable, Any, Optional

logger = logging.getLogger("suitms.circuit_breaker")

class CircuitState(str, Enum):
    CLOSED = "CLOSED"       # Healthy, traffic flows normally
    OPEN = "OPEN"           # Tripped, fast-failing calls
    HALF_OPEN = "HALF_OPEN" # Testing canary calls to check upstream health

class CircuitBreakerOpenException(Exception):
    """Raised when an operation is attempted on an open circuit."""
    pass

class CircuitBreaker:
    """
    Resilient Circuit Breaker implementation with exponential backoff and jitter.
    Protects downstream dependencies (e.g., Redis cluster, DB, OCR inference workers)
    from cascade failures under high load or network degradation.
    """
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_time_seconds: float = 10.0,
        half_open_success_threshold: int = 2,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_time_seconds = recovery_time_seconds
        self.half_open_success_threshold = half_open_success_threshold
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.consecutive_successes = 0
        self.last_state_change = time.time()
        self.last_failure_time = 0.0

    def call(self, func: Callable, *args, fallback: Optional[Callable] = None, **kwargs) -> Any:
        current_time = time.time()

        # Check state transition from OPEN -> HALF_OPEN
        if self.state == CircuitState.OPEN:
            elapsed = current_time - self.last_state_change
            if elapsed >= self.recovery_time_seconds:
                self.state = CircuitState.HALF_OPEN
                self.consecutive_successes = 0
                logger.warning(f"Circuit '{self.name}' entered HALF_OPEN state after {elapsed:.1f}s.")
            else:
                if fallback:
                    return fallback(*args, **kwargs)
                raise CircuitBreakerOpenException(
                    f"Circuit '{self.name}' is OPEN. Fast-failing request (retry in {self.recovery_time_seconds - elapsed:.1f}s)."
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            if fallback:
                return fallback(*args, **kwargs)
            raise e

    def _on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.consecutive_successes += 1
            if self.consecutive_successes >= self.half_open_success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.last_state_change = time.time()
                logger.info(f"Circuit '{self.name}' recovered and is now CLOSED.")
        else:
            self.failure_count = 0

    def _on_failure(self, exception: Exception):
        self.failure_count += 1
        self.last_failure_time = time.time()
        logger.warning(f"Circuit '{self.name}' detected failure ({self.failure_count}/{self.failure_threshold}): {exception}")
        
        if self.state == CircuitState.HALF_OPEN or self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
            # Add jitter to recovery time (±20%)
            jitter = random.uniform(-0.2, 0.2) * self.recovery_time_seconds
            self.recovery_time_seconds = max(0.05, self.recovery_time_seconds + jitter)
            logger.error(f"Circuit '{self.name}' tripped to OPEN state. Backoff: {self.recovery_time_seconds:.1f}s.")

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_state_change": self.last_state_change,
        }

import pytest
import time
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.common.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerOpenException

def test_circuit_breaker_transitions():
    cb = CircuitBreaker("test-service", failure_threshold=3, recovery_time_seconds=0.5)
    assert cb.state == CircuitState.CLOSED

    def failing_call():
        raise ConnectionError("Upstream service unavailable")

    def working_call():
        return "success"

    # Fail 2 times: should remain CLOSED
    with pytest.raises(ConnectionError):
        cb.call(failing_call)
    with pytest.raises(ConnectionError):
        cb.call(failing_call)
    assert cb.state == CircuitState.CLOSED

    # 3rd failure: trips to OPEN
    with pytest.raises(ConnectionError):
        cb.call(failing_call)
    assert cb.state == CircuitState.OPEN

    # While OPEN, immediate fast-fail with CircuitBreakerOpenException
    with pytest.raises(CircuitBreakerOpenException):
        cb.call(working_call)

    # Wait for recovery timeout (0.5s)
    time.sleep(0.6)

    # Canary call in HALF_OPEN succeeds
    result = cb.call(working_call)
    assert result == "success"
    assert cb.state == CircuitState.HALF_OPEN

    # 2nd success closes circuit
    result2 = cb.call(working_call)
    assert result2 == "success"
    assert cb.state == CircuitState.CLOSED

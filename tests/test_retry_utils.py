import pytest
import sys
import os
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from retry_utils import retry_with_backoff


# --- Happy path ---

def test_succeeds_on_first_attempt():
    """Function that never fails should return normally."""
    @retry_with_backoff(max_attempts=3)
    def always_works():
        return "ok"

    assert always_works() == "ok"


def test_returns_value_from_wrapped_function():
    @retry_with_backoff(max_attempts=3)
    def get_value():
        return 42

    assert get_value() == 42


# --- Retry behaviour ---

def test_retries_on_failure_then_succeeds():
    """Fails twice, succeeds on the third attempt."""
    call_count = {"n": 0}

    @retry_with_backoff(max_attempts=3, base_delay=0)
    def flaky():
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise ValueError("not yet")
        return "success"

    with patch("retry_utils.time.sleep"):  # Don't actually sleep in tests
        result = flaky()

    assert result == "success"
    assert call_count["n"] == 3


def test_raises_after_all_attempts_exhausted():
    """Should re-raise the exception once max_attempts is reached."""
    @retry_with_backoff(max_attempts=3, base_delay=0)
    def always_fails():
        raise ConnectionError("down")

    with patch("retry_utils.time.sleep"):
        with pytest.raises(ConnectionError, match="down"):
            always_fails()


def test_correct_number_of_attempts_made():
    """Should call the function exactly max_attempts times before giving up."""
    mock_fn = MagicMock(side_effect=RuntimeError("fail"))

    @retry_with_backoff(max_attempts=4, base_delay=0)
    def wrapped():
        return mock_fn()

    with patch("retry_utils.time.sleep"):
        with pytest.raises(RuntimeError):
            wrapped()

    assert mock_fn.call_count == 4


# --- Exception filtering ---

def test_only_retries_specified_exceptions():
    """Should NOT retry exceptions not in the exceptions tuple."""
    call_count = {"n": 0}

    @retry_with_backoff(max_attempts=3, base_delay=0, exceptions=(ValueError,))
    def raises_type_error():
        call_count["n"] += 1
        raise TypeError("wrong type")

    with patch("retry_utils.time.sleep"):
        with pytest.raises(TypeError):
            raises_type_error()

    # TypeError is not in the retry list, so it should fail immediately
    assert call_count["n"] == 1


def test_retries_matching_exception_subclass():
    """Should retry subclasses of the specified exception type."""
    call_count = {"n": 0}

    @retry_with_backoff(max_attempts=3, base_delay=0, exceptions=(OSError,))
    def raises_subclass():
        call_count["n"] += 1
        raise FileNotFoundError("missing")  # FileNotFoundError is a subclass of OSError

    with patch("retry_utils.time.sleep"):
        with pytest.raises(FileNotFoundError):
            raises_subclass()

    assert call_count["n"] == 3


# --- Backoff timing ---

def test_sleep_called_between_retries():
    """sleep() should be called once between each retry (not after final failure)."""
    @retry_with_backoff(max_attempts=3, base_delay=1.0, exponential_base=2)
    def always_fails():
        raise RuntimeError("fail")

    with patch("retry_utils.time.sleep") as mock_sleep:
        with pytest.raises(RuntimeError):
            always_fails()

    # 3 attempts = 2 sleeps (after attempt 1 and 2, not after the final failure)
    assert mock_sleep.call_count == 2


def test_exponential_backoff_delays():
    """Delay should double each retry: 1s, 2s with defaults."""
    @retry_with_backoff(max_attempts=3, base_delay=1.0, exponential_base=2)
    def always_fails():
        raise RuntimeError("fail")

    with patch("retry_utils.time.sleep") as mock_sleep:
        with pytest.raises(RuntimeError):
            always_fails()

    delays = [call.args[0] for call in mock_sleep.call_args_list]
    assert delays == [1.0, 2.0]


# --- Decorator metadata ---

def test_preserves_function_name():
    """@functools.wraps should keep the original function name."""
    @retry_with_backoff()
    def my_named_function():
        pass

    assert my_named_function.__name__ == "my_named_function"

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Dict, Tuple

from autogen_core import EVENT_LOGGER_NAME
from autogen_core.logging import LLMCallEvent


class LLMUsageTracker(logging.Handler):
    def __init__(self) -> None:
        """Logging handler that tracks the number of tokens used in the prompt and completion."""
        super().__init__()
        self._prompt_tokens = 0
        self._completion_tokens = 0
        self._model_calls = 0
        self._model_names = set()

    @property
    def tokens(self) -> int:
        return self._prompt_tokens + self._completion_tokens

    @property
    def prompt_tokens(self) -> int:
        return self._prompt_tokens

    @property
    def completion_tokens(self) -> int:
        return self._completion_tokens

    @property
    def model_calls(self) -> int:
        return self._model_calls

    @property
    def model_names(self) -> set:
        return self._model_names

    def reset(self) -> None:
        self._prompt_tokens = 0
        self._completion_tokens = 0
        self._model_calls = 0
        self._model_names = set()

    def emit(self, record: logging.LogRecord) -> None:
        """Emit the log record. To be used by the logging module."""
        try:
            # Use the StructuredMessage if the message is an instance of it
            if isinstance(record.msg, LLMCallEvent):
                event = record.msg
                self._prompt_tokens += event.prompt_tokens
                self._completion_tokens += event.completion_tokens
                self._model_calls += 1
                if hasattr(event, "model") and event.model:
                    self._model_names.add(event.model)
        except Exception:
            self.handleError(record)

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get the usage statistics as a dictionary."""
        return {
            "prompt_tokens": self._prompt_tokens,
            "completion_tokens": self._completion_tokens,
            "total_tokens": self.tokens,
            "model_calls": self._model_calls,
            "models_used": list(self._model_names),
        }


# Global tracker instance that can be accessed from anywhere
_global_tracker = LLMUsageTracker()


def get_global_tracker() -> LLMUsageTracker:
    """Get the global LLM usage tracker instance."""
    return _global_tracker


def reset_global_tracker() -> None:
    """Reset the global LLM usage tracker."""
    _global_tracker.reset()


def setup_tracking() -> None:
    """Set up the global LLM usage tracker."""
    logger = logging.getLogger(EVENT_LOGGER_NAME)
    logger.setLevel(logging.INFO)

    # Remove any existing handlers of our type to avoid duplicates
    for handler in logger.handlers:
        if isinstance(handler, LLMUsageTracker):
            logger.removeHandler(handler)

    # Add our global tracker
    logger.addHandler(_global_tracker)


def track_llm(func: Callable) -> Callable:
    """Decorator to track LLM usage in a function."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Reset the global tracker
        reset_global_tracker()

        # Set up tracking
        setup_tracking()

        # Run the function
        if asyncio.iscoroutinefunction(func):
            result = asyncio.run(func(*args, **kwargs))
        else:
            result = func(*args, **kwargs)

        # Get the usage stats
        usage_stats = _global_tracker.get_usage_stats()

        # Print the stats
        print("LLM Usage Statistics:")
        print(f"  Prompt Tokens: {usage_stats['prompt_tokens']}")
        print(f"  Completion Tokens: {usage_stats['completion_tokens']}")
        print(f"  Total Tokens: {usage_stats['total_tokens']}")
        print(f"  Model Calls: {usage_stats['model_calls']}")
        print(
            f"  Models Used: {', '.join(usage_stats['models_used']) if usage_stats['models_used'] else 'None'}"
        )

        return result, usage_stats

    return wrapper


async def track_async_task(coro) -> Tuple[Any, Dict[str, Any]]:
    """Track LLM usage in an async task."""
    # Reset the global tracker
    reset_global_tracker()

    # Set up tracking
    setup_tracking()

    # Run the coroutine
    result = await coro

    # Get the usage stats
    usage_stats = _global_tracker.get_usage_stats()

    return result, usage_stats

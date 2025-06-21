import logging
from typing import Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def no_except(f: Callable[[], T]) -> Optional[T]:
    try:
        return f()
    except Exception as e:
        logger.error(f"Error in {f.__name__}: {e}")
        return None

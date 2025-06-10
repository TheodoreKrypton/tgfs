import asyncio
from typing import TypeVar, Callable
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


def no_except(f: Callable[[], T]) -> T:
    try:
        return f()
    except Exception as e:
        logger.error(f"Error in {f.__name__}: {e}")
        return None

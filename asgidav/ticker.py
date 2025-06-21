import logging
import time

logger = logging.getLogger("asgidav.ticker")


class Ticker:
    def __init__(self, name: str):
        self._last_tick = time.time()
        self.name = name

    def tick(self, name: str):
        current_time = time.time()
        elapsed_time = current_time - self._last_tick
        logger.info(f"{self.name}:{name} tick: {elapsed_time:.2f} seconds")
        self._last_tick = current_time

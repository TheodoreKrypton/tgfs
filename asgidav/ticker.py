import time


class Ticker:
    def __init__(self, name: str):
        self._last_tick = time.time()
        self.name = name

    def tick(self, name: str):
        current_time = time.time()
        elapsed_time = current_time - self._last_tick
        print(f"{self.name}:{name} tick: {elapsed_time:.2f} seconds")
        self._last_tick = current_time

import time


class RateLimiter:
    def __init__(self, delay: float = 1.0):
        self._delay = max(0.0, delay)
        self._last_request: float = 0.0

    @property
    def delay(self) -> float:
        return self._delay

    @delay.setter
    def delay(self, value: float) -> None:
        self._delay = max(0.0, value)

    def wait(self) -> None:
        elapsed = time.time() - self._last_request
        if elapsed < self._delay:
            time.sleep(self._delay - elapsed)
        self._last_request = time.time()

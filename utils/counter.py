from utils.singleton import Singleton


class Counter(metaclass=Singleton):
    def __init__(self) -> None:
        self._counters = {}

    def get(self, key: str) -> int:
        result = self._counters.get(key, None)
        if not result:
            result = 0

        self._counters[key] = result + 1
        return result

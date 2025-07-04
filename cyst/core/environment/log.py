import logging
from typing import Callable

cyst_defaults = [
    "virtual_time",
    "run_id"
]


class CYSTFormatter(logging.Formatter):
    def format(self, record):
        for k, v in self._cyst_defaults.items():
            if isinstance(v, Callable):
                record.__setattr__(k, v())
            else:
                record.__setattr__(k, v)
        return super().format(record)

    def __init__(self, fmt=None, datefmt=None, style="%", validate=True, *, defaults=None):
        self._cyst_defaults = {}

        for k in cyst_defaults:
            if k in defaults:
                self._cyst_defaults[k] = defaults.get(k)

        super().__init__(fmt, datefmt, style, validate, defaults=defaults)


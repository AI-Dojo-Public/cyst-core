import datetime
from typing import Self


class Duration:
    """
    Duration class provides a subjectively more esthetically pleasing thin syntactical wrapper over Python's timedelta.
    Duration is not meant to be instantiated directly from users' code, but through the free functions, which get
    chained with member ones.

    Example:
        > print(secs(2).msecs(37))
        > 0:00:02.037000

    The code that requires the float representation of the whole duration (such as for the sleep function) can use the
    :func:`to_float` method.

    Example:
        time.sleep(secs(2).msecs(37).to_float())

    The available duration specifications mimics those of timedelta:
        :weeks
        :days
        :hours
        :mins [minutes]
        :secs [seconds]
        :msecs [milliseconds]
        :usecs [microsecods]

    For fractions of microseconds (such as hectonanoseconds) just use the appropriate fractional value of any available
    duration.
    """

    def __init__(self):
        self._weeks = 0.0
        self._days = 0.0
        self._hours = 0.0
        self._mins = 0.0
        self._secs = 0.0
        self._msecs = 0.0
        self._usecs = 0.0

    def weeks(self, value: float) -> Self:
        self._weeks = value
        return self

    def days(self, value: float) -> Self:
        self._days = value
        return self

    def hours(self, value: float) -> Self:
        self._hours = value
        return self

    def mins(self, value: float) -> Self:
        self._mins = value
        return self

    def secs(self, value: float) -> Self:
        self._secs = value
        return self

    def msecs(self, value: float) -> Self:
        self._msecs = value
        return self

    def usecs(self, value: float) -> Self:
        self._usecs = value
        return self

    def to_float(self) -> float:
        return self.__repr__().total_seconds()

    def __str__(self):
        return str(self.__repr__())

    def __repr__(self):
        return datetime.timedelta(weeks=self._weeks, days=self._days, hours=self._hours, minutes=self._mins,
                                  seconds=self._secs, milliseconds=self._msecs, microseconds=self._usecs)


def weeks(value: float) -> Duration:
    duration = Duration()
    duration.weeks(value)
    return duration


def days(value: float) -> Duration:
    duration = Duration()
    duration.days(value)
    return duration


def hours(value: float) -> Duration:
    duration = Duration()
    duration.hours(value)
    return duration


def mins(value: float) -> Duration:
    duration = Duration()
    duration.mins(value)
    return duration


def secs(value: float) -> Duration:
    duration = Duration()
    duration.secs(value)
    return duration


def msecs(value: float) -> Duration:
    duration = Duration()
    duration.msecs(value)
    return duration


def usecs(value: float) -> Duration:
    duration = Duration()
    duration.usecs(value)
    return duration

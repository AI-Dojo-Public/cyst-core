from abc import ABC, abstractmethod


class Data(ABC):
    """
    This class represents an arbitrary data.

    Warning:
        This is currently very underdeveloped and will be overhauled in the near future.
    """

    @property
    @abstractmethod
    def id(self) -> str:
        """
        An identifier of the data that is unique within one service, but preferably across simulation.

        :rtype: str
        """

    @property
    @abstractmethod
    def owner(self) -> str:
        """
        The identity of a user, to whom the data belongs.

        :rtype: str
        """

    @property
    @abstractmethod
    def description(self) -> str:
        """
        A textual description of the data. Currently it also serves as a way to store contents of the data, even though
        true contents of the data will never be a part of the simulation.

        :rtype: str
        """

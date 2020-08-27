from abc import ABC, abstractmethod


class Data(ABC):

    @property
    @abstractmethod
    def id(self):
        pass

    @property
    @abstractmethod
    def owner(self):
        pass

    @property
    @abstractmethod
    def description(self):
        pass

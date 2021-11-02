from enum import Enum
from typing import Union, NewType, Any, Type
from abc import abstractmethod, ABC

from cyst.api.environment.message import Message
from cyst.api.environment.stats import Statistics

read_write_data = [Statistics]
write_only_data = [Message]
append_only_data = [Message]


class DataStoreBackend:

    @abstractmethod
    def set(self, run_id: str, item: Any, item_type: Type) -> None:
        pass

    @abstractmethod
    def get(self, run_id: str, item: Any, item_type: Type) -> Any:
        pass

    @abstractmethod
    def update(self, run_id: str, item: Any, item_type: Type) -> None:
        pass

    @abstractmethod
    def remove(self, run_id: str, item: Any, item_type: Type) -> None:
        pass

    @abstractmethod
    def clear(self, run_id: str) -> None:
        pass

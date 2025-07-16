from typing import Dict, Union, List

from cyst.api.environment.data_model import ActionModel
from cyst.api.environment.message import Message, Signal
from cyst.api.environment.stats import Statistics
from cyst.api.environment.stores import DataStore, DataStoreDescription


class DataStoreMemory(DataStore):
    def __init__(self, run_id: str, params: Dict[str, str]):
        self._run_id = run_id
        self._memory: Dict[str, Union[None, List, Statistics]] = {
            "actions": [],
            "messages": [],
            "statistics": None,
            "signals": []
        }

    def add_action(self, action: ActionModel) -> None:
        self._memory["actions"].append(action)

    def add_message(self, message: Message) -> None:
        self._memory["messages"].append(message)

    def add_statistics(self, statistics: Statistics) -> None:
        self._memory["statistics"] = statistics

    def add_signal(self, signal: Signal) -> None:
        self._memory["signals"].append(signal)

def create_data_store_memory(run_id: str, params: Dict[str, str]) -> DataStore:
    return DataStoreMemory(run_id, params)


data_store_memory_description = DataStoreDescription(
    backend="memory",
    description="A memory-based data store backend. Due to a limited options to retrieve the system data from a data "
                "store, it is useful mostly when a only user data handling is required.",
    creation_fn=create_data_store_memory
)

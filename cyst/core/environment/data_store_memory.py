from typing import Dict

from cyst.api.environment.data_model import ActionModel
from cyst.api.environment.message import Message
from cyst.api.environment.stores import DataStore, DataStoreDescription


class DataStoreMemory(DataStore):
    def __init__(self, run_id: str, params: Dict[str, str]):
        self._run_id = run_id
        self._memory = {
            "actions": [],
            "messages": []
        }

    def add_action(self, action: ActionModel) -> None:
        self._memory["actions"].append(action)

    def add_message(self, message: Message) -> None:
        self._memory["messages"].append(message)


def create_data_store_memory(run_id: str, params: Dict[str, str]) -> DataStore:
    return DataStoreMemory(run_id, params)


data_store_memory_description = DataStoreDescription(
    backend="memory",
    description="A memory-based data store backend. Due to a limited options to retrieve the system data from a data "
                "store, it is useful mostly when a only user data handling is required.",
    creation_fn=create_data_store_memory
)

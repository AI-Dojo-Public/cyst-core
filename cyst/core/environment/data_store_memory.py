from typing import Dict

from cyst.api.environment.data_model import ActionModel
from cyst.api.environment.stores import DataStore, DataStoreDescription


class DataStoreMemory(DataStore):
    def __init__(self, params: Dict[str, str]):
        self._memory = {"actions": []}

    def add_action(self, action: ActionModel) -> None:
        self._memory["actions"].append(action)


def create_data_store_memory(params: Dict[str, str]) -> DataStore:
    return DataStoreMemory(params)


data_store_memory_description = DataStoreDescription(
    backend="memory",
    description="A memory-based data store backend. Due to a limited options to retrieve the system data from a data "
                "store, it is useful mostly when a only user data handling is required.",
    creation_fn=create_data_store_memory
)

from typing import List, Dict


from cyst.api.configuration.configuration import ConfigItem
from cyst.api.configuration.logic.access import *
from cyst.api.configuration.logic.data import *
from cyst.api.configuration.logic.exploit import *
from cyst.api.configuration.host.service import *
from cyst.api.configuration.network.network import *
from cyst.api.configuration.network.node import *
from cyst.api.configuration.network.router import *
from cyst.api.configuration.network.firewall import *
from cyst.api.configuration.network.elements import *


class Deserializer:
    def __init__(self, file, load_func):
        self._file = file
        self._items = []
        self._load_func = load_func

    def deserialize(self) -> List[ConfigItem]:
        self._traverse(self._load_func(self._file))
        return self._items

    def _traverse(self, collection: Dict):
        for item in collection.values():
            self._items.append(self._process(item))

    def _process(self, sub_collection):

        if isinstance(sub_collection, list) or isinstance(sub_collection, tuple):
            return [self._process(item) for item in sub_collection]

        if not isinstance(sub_collection, dict):
            return sub_collection

        cls_type = sub_collection.pop("cls_type", None)

        if cls_type is None:
            raise RuntimeError("cannot defer type, config serialized with inappropriate tool")

        for attribute_name, attribute_value in sub_collection.items():
            sub_collection[attribute_name] = self._process(attribute_value)

        return globals()[cls_type](**sub_collection)


def deserialize_toml(file):
    from rtoml import load
    toml_deserializer = Deserializer(file, load)
    return toml_deserializer.deserialize()

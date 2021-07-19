from typing import List

import rtoml

from cyst.api.configuration.configuration import ConfigItem


class Deserializer:
    def __init__(self, file, load_func):
        self._file = file
        self._items = []
        self._load_func = load_func

    def deserialize(self) -> List[ConfigItem]:
        self._traverse(self._load_func(self._file))
        return self._items

    def _traverse(self, collection):
        pass

    # for each top-level item, process

    def _process(self, sub_collection):
        pass

    # go like dfs, if attribute is dict/ container of dicts, use cls_type to extract what type the configItem is,
    # remove cls_type and construct with the **kwargs form, so keyed args from dict, once there is nowhere to dive


def deserialize_toml(file):
    from rtoml import load
    toml_deserializer = Deserializer(file, load)
    return toml_deserializer.deserialize()

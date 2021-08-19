# The definition here is only to make the type of configuration items obvious.
# Because we are operating on dataclasses, the initialization order precludes us from having some default initialized
# value, which is a real shame (though understandable)
import dataclasses
from typing import Any



class ConfigItem:
    id: str


class ConfigItemCloner:

    @classmethod
    def clone(cls, item: Any):
        if isinstance(item, list):
            return [cls.clone(value) for value in item]
        if not isinstance(item, ConfigItem):
            return item
        if not dataclasses.is_dataclass(item):
            raise RuntimeError("ConfigItem is not a dataclass")

        return dataclasses.replace(item,
                                   **dict(
                                       map(lambda field: cls._clone_field(item, field),
                                           filter(lambda field: cls._needs_further_processing(item, field),
                                                  dataclasses.fields(item)
                                                  )
                                           )
                                   )
                                   )

    @classmethod
    def _needs_further_processing(cls, item: ConfigItem, field: dataclasses.Field):
        return isinstance(getattr(item, field.name), ConfigItem) or \
               isinstance(getattr(item, field.name), list) # be careful with other collections, right now we dont use any,
                                                            # but future changes might be problematic as IPAddress,
                                                            # IPNetwork, str are all collections.abc.Collections,

    @classmethod
    def _clone_field(cls, item: ConfigItem, field: dataclasses.Field):
        value = getattr(item, field.name)
        if isinstance(value, list):
            return field.name, [cls.clone(obj) for obj in value]
        return field.name, cls.clone(value)

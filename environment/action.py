from enum import Enum
from typing import Optional, List

from environment.exploit import Exploit
from environment.tag import TagList
from utils.singleton import Singleton


class ActionParameterType(Enum):
    NONE = 0,
    ID = 1


class ActionParameter:
    def __init__(self, action_type: ActionParameterType, value: str):
        self._type = action_type
        self._value = value

    @property
    def action_type(self) -> ActionParameterType:
        return self._type

    @property
    def value(self) -> str:
        return self._value


class Action:
    def __init__(self, *tags, id: str = None, content: str = None, exploit: Exploit = None):
        self._id = id
        self._content = content
        self._exploit = exploit
        self._parameters = []
        self._tags = []
        for tag in tags[:9]:
            x = TagList().add_tag(tag, self)
            self._tags.append(x)

    @property
    def tags(self):
        return self._tags

    @property
    def id(self):
        return self._id

    @property
    def content(self):
        return self._content

    @property
    def exploit(self):
        return self._exploit

    @property
    def parameters(self) -> List[ActionParameter]:
        return self._parameters

    def add_parameters(self, *parameters) -> None:
        for parameter in parameters:
            self._parameters.append(parameter)

    def get_values(self, prefix = ""):
        return [x.value for x in self._tags if x.is_prefixed_by(prefix)]

    def set_id(self, id):
        self._id = id

    def set_content(self, content):
        self._content = content

    def set_exploit(self, exploit: Exploit) -> None:
        self._exploit = exploit


class ActionList(metaclass=Singleton):
    def __init__(self):
        self._actions = []

    def add_action(self, action: Action):
        self._actions.append(action)
        # Actions have id 1-indexed this way
        action.set_id(len(self._actions))

    def get_actions(self, prefix: str = ""):
        root = TagList().get_tags(prefix)
        return root.nested_refs
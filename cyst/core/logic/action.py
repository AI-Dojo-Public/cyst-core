from typing import List, Optional, Tuple

from cyst.api.logic.action import Action, ActionDescription, ActionParameter, ActionToken
from cyst.api.logic.exploit import Exploit


class ActionImpl(Action):

    def __init__(self, action: ActionDescription):
        self._id = action.id
        fragments = action.id.split(":")
        self._namespace = fragments[0]
        self._fragments = fragments[1:]
        self._description = action.description
        self._tokens = action.tokens
        self._exploit = None
        self._parameters = []

    @property
    def id(self) -> str:
        return self._id

    @property
    def namespace(self) -> str:
        return self._namespace

    @property
    def fragments(self) -> List[str]:
        return self._fragments

    @property
    def exploit(self) -> Exploit:
        return self._exploit

    def set_exploit(self, exploit: Optional[Exploit]) -> None:
        self._exploit = exploit

    @property
    def parameters(self) -> List[ActionParameter]:
        return self._parameters

    def add_parameters(self, *params: ActionParameter) -> None:
        for p in params:
            self._parameters.append(p)

    @property
    def tokens(self) -> List[Tuple[ActionToken, ActionToken]]:
        return self._tokens

    @staticmethod
    def cast_from(o: Action) -> 'ActionImpl':
        if isinstance(o, ActionImpl):
            return o
        else:
            raise ValueError("Malformed underlying object passed with the Action interface")

    def copy(self):
        return ActionImpl(ActionDescription(self.id, self._description, self._tokens))

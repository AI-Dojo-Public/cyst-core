from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from flags import Flags
from typing import NamedTuple, List, Tuple, Optional, Any, Dict, Union

from cyst.api.logic.access import AuthenticationToken
from cyst.api.logic.exploit import Exploit


class ActionParameterDomainType(Enum):
    """
    Specifies a type of the action parameter domain.

    Possible values:
        :ANY: The parameters can take any values. If possible avoid this domain, as it does not enable sampling of
            values, thus being less useful for automated processing and learning.
        :RANGE: The parameters belong to a certain numeric range, e.g., port numbers.
        :OPTIONS: The parameters are a collection of values to choose from.
    """
    ANY = 0,
    RANGE = 1,
    OPTIONS = 2


class ActionParameterDomain(Sequence):
    """
    Specifies a domain of action parameters.
    """
    @property
    @abstractmethod
    def type(self) -> ActionParameterDomainType:
        """
        Returns a type of the action parameter domain.

        :rtype: ActionParameterDomainType
        """

    @property
    @abstractmethod
    def range_min(self) -> int:
        """
        Returns a minimal value of the range, if the domain is of RANGE type. Otherwise the value is undefined.

        :rtype: int
        """

    @property
    @abstractmethod
    def range_max(self) -> int:
        """
        Returns a maximal value of the range, if the domain is of RANGE type. Otherwise the value is undefined.

        :rtype: int
        """

    @property
    @abstractmethod
    def range_step(self) -> int:
        """
        Returns a gap between two values in a range. E.g., a range [1,3,5,7] has a step = 2.

        :rtype: int
        """

    @property
    @abstractmethod
    def options(self) -> List[Any]:
        """
        Returns a list of possible values in the domain, if the type of the domain is OPTIONS. Otherwise and empty list.

        :rtype: List[Any]
        """

    @abstractmethod
    def validate(self, value: Any) -> bool:
        """
        Checks, whether a value belongs into a domain.

        :param value: A value to check.
        :type value: Any
        """

    @property
    @abstractmethod
    def default(self) -> Any:
        """
        :return: A value from the domain that is considered a default one.
        """

    @abstractmethod
    def __getitem__(self, item: int) -> Any:
        """
        This method is here for the domain to be treated as a range, so it can be, e.g., randomly sampled. It is not
        intended to be used directly. This does not work with domains of type ANY.

        :param item: An index of the item to get.
        :type item: int

        :return: The item with given index.
        """

    @abstractmethod
    def __len__(self) -> int:
        """
        This method is here for the domain to be treated as a range, so it can be, e.g., randomly sampled. It is not
        intended to be used directly. This does not work with domains of type ANY.

        :return: The number of items in the domain.
        """


class ActionParameterType(Enum):
    """
    Specifies a type of action parameters.

    Possible values:
        :NONE: Type not specified, or outside the current domain of parameter types. This should be used only after
            due consideration, as it is better to expand this domain than to use NONE. It may interfere with the
            learning process.
        :IDENTITY: The parameter is an identity of a user in the system.
        :IDENTIFIER: The parameter is some kind of identifier.
        :DURATION: The parameter represents a time duration in simulated time units.
        :TOKEN: The parameter is an instance of a token object, such as cyst.api.logic.access.AuthenticationToken.
        :DATA: Added as a temporary solution for actions and communication that carries actual data not encoded into
            the message structure. Given the complicated definition of parameters and factual uselessness of fitting
            data into a domain that can be sampled, this will likely be replaced by a more top-level solution.
    """
    NONE = 0,
    IDENTITY = 1,
    IDENTIFIER = 2,
    DURATION = 3,
    TOKEN = 4,
    DATA = 5

@dataclass
class ActionParameter:
    """
    Action parameter represents a mechanism to further specify details of actions. An action can have an arbitrary
    number of parameters.

    :param type: The type of the parameter.
    :type type: ActionParameterType

    :param name: A name of the parameter, which is unique within an action.
    :type name: str

    :param domain: A domain of the parameter.
    :type domain: ActionParameterDomain

    :param value: A default value of the parameter.
    :type value: Optional[Any]
    """
    type: ActionParameterType
    name: str
    domain: ActionParameterDomain
    value: Optional[Any] = None


class ActionToken(Flags):
    """
    Action tokens are used to describe at the high level, which tokens are required for the action to properly execute
    in the context of an attack graph. Tokens are primarily used for automatic generation of simulation scenarios.
    They are also currently being restructured.

    An example usage:

        .. code-block::

            f1 = ActionToken.NONE
            f2 = ActionToken.DATA | ActionToken.SESSION

    Possible values:
        :NONE: No additional token is required. An example is a scanning action.
        :AUTH: Correct authorization or authentication tokens are required.
        :DATA: Specific data must be obtained or produced.
        :EXPLOIT: A working exploit must be present for this action to work.
        :SESSION: A session must be established to the node the action is being executed on.
    """
    NONE = (),
    AUTH = (),
    DATA = (),
    EXPLOIT = (),
    SESSION = ()


@dataclass
class ActionDescription:
    """
    A description of an action in the form that is used for registering into the system.

    :param id: A unique name of the action. This name must be unique across all behavioral models, so it is advisible
        to use own namespace for each model.
    :type id: str

    :param description: A textual description of the action.
    :type description: str

    :param parameters: A list of action parameters.
    :type parameters: List[ActionParameter]

    :param tokens: A list of action token tuples. Each tuple represents inputs and outputs like this (input tokens,
        output tokens). Because a token is a flag, multiple tokens can be supplied by means of the OR operator, e.g.:

        .. code-block::

            (ActionToken.AUTH | ActionToken.EXPLOIT, ActionToken.SESSION).
    """
    id: str
    description: str
    parameters: List[ActionParameter]
    tokens: List[Tuple[ActionToken, ActionToken]]


class Action(ABC):
    """
    An action represent an activity that an actor within simulation can do. Usage of actions is mostly the domain of
    active services. An action does not carry any semantics by itself. The semantics is provided by interpreters /
    behavioral models. One action can therefore have different impact depending on the model chosen.
    """
    @property
    @abstractmethod
    def id(self) -> str:
        """
        A unique identifier of the action within simulation. The identifier is expected to be a serialization of
        a position in hierarchy, separated by a colon. E.g., "aif:privilege_escalation:root_privilege_escalation".

        :rtype: str
        """

    @property
    @abstractmethod
    def description(self) -> str:
        """
        A textual description of the action.

        :rtype: str
        """

    @property
    @abstractmethod
    def fragments(self) -> List[str]:
        """
        The list of fragments of the id (i.e., what is left after removing the colons). E.g, ["aif",
        "privilege_escalation", "root_privilege escalation"].

        :rtype: List[str]
        """

    @property
    @abstractmethod
    def namespace(self) -> str:
        """
        Currently a shorthand for fragments()[0], but that can change in the future, as the namespace can span multiple
        fragments.

        :rtype: str
        """

    @property
    @abstractmethod
    def exploit(self) -> Optional[Exploit]:
        """
        Returns an exploit currently associated with the action.

        :rtype: Optional[Exploit]
        """

    @abstractmethod
    def set_exploit(self, exploit: Optional[Exploit]) -> None:
        """
        Sets an exploit associated with the action. TODO: Why the hell is this not a setter of the exploit property?

        :param exploit: The exploit to use. If None is passed as a value, removes the exploit from the action.
        :type exploit: Optional[Exploit]
        """

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, ActionParameter]:
        """
        Returns a collection of action parameters.

        :rtype: Dict[str, ActionParameter]
        """

    @abstractmethod
    def add_parameters(self, *params: ActionParameter) -> None:
        """
        Adds one or more parameters to the action. If a parameter of the same name is present, it gets overwritten.

        :param params: One or more action parameters.
        :type params: ActionParameter
        """

    @property
    @abstractmethod
    def tokens(self) -> List[Tuple[ActionToken, ActionToken]]:
        """
        Returns a list of action tokens, which define inputs and outputs of the action.

        :rtype: List[Tuple[ActionToken, ActionToken]]
        """

    @abstractmethod
    def copy(self) -> 'Action':
        """
        Returns a copy of the action. This is useful for keeping copies of action with different parameters or exploits.

        :rtype: Action
        """

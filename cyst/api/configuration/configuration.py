# Because we are operating on dataclasses, the initialization order precludes us from having some default initialized
# value, which is a real shame (though understandable)
from copy import copy
from dataclasses import dataclass, field
from enum import Enum, auto
from uuid import uuid4
from typing import Self, Any, List, Union

from serde import serialize

"""
Provides an API to configure all aspects of the simulation engine.

Available to: creator, models
Hidden from:  agents
"""


class ConfigItem:
    """
    A superclass of a configuration items.

    Most of the configuration items have an instantiated counterpart produced by the platform. To tie these two object
    classes together, the configuration item has three identification properties: ref, name, and id.

    :param ref: A unique identification of a given configuration item. This parameter is primarily used for referencing
        this configuration from other configurations, usually when a configuration of a particular item is shared among
        multiple other configuration items. Unless there is a good reason to set it explicitly, it is best to let it be
        autogenerated. By default, UUIDs are used.
    :type ref: str

    :param name: An identifier of the object produced from the configuration item. It should be unique among siblings
        within the same parent. As with the ref parameters, it is best to let it be autogenerated, as the system will
        try to come up with a memorable name. In case of name clash among siblings, a suffix is added to the name to
        distinguish different objects. Note that the name is often not accessible through CYST API, except for service
        names that are currently used for message routing and exploit evaluation.
    :type name: str

    :param id: An identifier of the object that is unique within the whole simulation. Unless you have a very good
        reason, you should let it be autogenerated. The id is automatically constructed with the dot notation to
        express the parent-child hierarchy. Note that the id is generally not accessible through CYST API, as it is
        considered an implementation detail that is used for management of simulation components.
    :type id: str
    """
    ref: str
    name: str
    id: str

    # TODO Nested configurations and their copies
    def __call__(self, ref: str | None = None, name: str = "", id: str = "") -> Self:
        """
        Create a copy of a configuration item with a new ref id, name, or id. With this, a configuration item can be
        used as a template to repeat repetitions.

        Example:
            .. code-block:: python

            local_password_auth = AuthenticationProviderConfig(
                provider_type=AuthenticationProviderType.LOCAL,
                token_type=AuthenticationTokenType.PASSWORD,
                token_security=AuthenticationTokenSecurity.SEALED,
                timeout=30
            )

            ssh_provider = local_password_auth(name="openssh_local_pwd_auth")

        :param ref: A new ref id of the configuration item. If none is provided, it is autogenerated. The system does
            not check for duplicate refs, so if you use an already present ref, it will likely end in strange errors
            down the line.
        :type ref: str | None

        :param name: A new name for the resulting object. If none is provided, it is autogenerated.
        :type name: str

        :param id: A new id for the resulting object. It is generally better to not provide an id as it can have
            unintended consequences. It will be autogenerated if none is provided.
        :type id: str

        :return: A copy of a config item.

        """
        new_one = copy(self)
        if ref:
            new_one.ref = ref
        else:
            new_one.ref = str(uuid4())

        if name:
            new_one.name = name

        if id:
            new_one.id = id

        return new_one

@serialize
@dataclass
class ConfigParameter(Any, str):
    """
    ConfigParameter serves as a placeholder, that will be replaced by a concrete value when configuration pass happens.

    Usage example:
        .. code-block:: python

            ...
            PassiveServiceConfig(
                name="bash",
                owner="root",
                version=ConfigParameter("my-custom-version"),
                access_level=ConfigParameter("my-custom-access_level"),
                local=True,
            )
            ...

    :param id: An identifier of the parameter. Must be unique within the configuration.
    :type id: str
    """
    id: str


class ConfigParameterValueType(Enum):
    """
    Configuration parameter can be replaced with a concrete value in the configuration pass in three different ways.
    However, in any case, the developer behind the parametrization is responsible for providing values of the correct
    type. This is not validated, until a configuration pass happens and in case of wrong value type, it will just die
    painfully.

        :VALUE: A specific value is provided.
        :REF: An existing configuration item with a given ref will be used. If multiple config parameters resolve to the
            same ref, then a one instance of the same configuration item will be present in multiple places. This can
            be desired in some cases, but more often it is not. So, beware!
        :REF_COPY: A copy of an existing configuration item will be used, with autogenerated identifiers. Thus, more
            instances of the same type can be created. This is usually the right choice.

    """
    VALUE = auto()
    REF = auto()
    REF_COPY = auto()


@dataclass
class ConfigParameterSingle:
    """
    This represents a single configurable parameter.

    :param name: The name is an identification of a configurable parameter. It must be unique among other configuration
        parameters.
    :type name: str

    :param value_type: The type of configuration parameter, i.e. what type of value will be there after substitution.
    :type value_type: ConfigParameterValueType

    :param description: Additional information about the purpose of the configuration parameter. Most useful for
        user-facing interfaces.
    :type description: str

    :param default: A default value of the parameter. This value will be used if there is no user-provided
        parametrization.
    :type default: Any

    :param parameter_id: An id of a parameter placeholder, which should be replaced by the value of this parameter.
    :type parameter_id: str
    """
    name: str
    value_type: ConfigParameterValueType
    description: str
    default: Any
    parameter_id: str


class ConfigParameterGroupType(Enum):
    """
    When a group of parameters is used, this specifies, how its elements can be selected.

        :ONE: Only one element of the group can be selected.
        :ANY: 0..N elements of the group can be selected.

    """
    ONE = auto()
    ANY = auto()
    # The following are suggested, but ignored until the need arises.
    # AT_LEAST = auto()
    # AT_MOST = auto()
    # ALL = auto()


@dataclass
class ConfigParameterGroupEntry:
    """
    A single choice from the parametrization group. Unlike the single configuration parameter, the group entry directly
    specifies the value. If you require the user to specify something within the group entry, do it two-step like this:

    Example:
        .. code-block:: python

            attacker_service = ActiveServiceConfig(
                type=ConfigParameter("attacker_type"),
                name="attacker",
                owner="attacker",
                access_level=AccessLevel.LIMITED,
                ref="attacker_service_ref"
            )

            ...

            parametrization = ConfigParametrization([
                ConfigParameterGroup(
                    name="Attacker position",
                    group_type=ConfigParameterGroupType.ONE,
                    value_type=ConfigParameterValueType.REF,
                    description="The node, where the attacker starts at.",
                    default="attacker_location_1",
                    options=[
                        ConfigParameterGroupEntry(
                            parameter_id="attacker_location_1",
                            value="attacker_service_ref",
                            description="Node 1"
                        ),
                        ConfigParameterGroupEntry(
                            parameter_id="attacker_location_2",
                            value="attacker_service_ref",
                            description="Node 2"
                        )
                    ]
                )
            ])

    This way, you will enable the user to specify both the position of the attacker from the group and its type.

    :param description: Additional information about the purpose of the configuration parameter. Most useful for
        user-facing interfaces.
    :type description: str

    :param value: The concrete value that will be used if chosen.
    :type value: Any

    :param parameter_id: An id of a parameter placeholder, which should be replaced by the value of this parameter.
    :type parameter_id: str
    """
    description: str
    value: Any
    parameter_id: str


@dataclass
class ConfigParameterGroup:
    """
    Config parameter group represents a choice of zero or more options that a user can make.

    :param name: The name is an identification of the group. It must be unique among other configuration parameters.
    :type name: str

    :param group_type: Specifies a selection method for group entries.
    :type group_type: ConfigParameterGroupType

    :param value_type: Specifies the type of configuration parameter, i.e. what type of value will be there after
        substitution.
    :type value_type: ConfigParameterValueType

    :param description: Provides additional information about the purpose of the group of parameters. Most useful for
        user-facing interfaces.
    :type description: str

    :param default: A `parameter_id` of the entry that is used if the user does not specify anything.
    :type default: str

    :param options: A list of configuration entries to select from.
    :type options: List[ConfigParameterGroupEntry]
    """
    parameter_id: str
    name: str
    group_type: ConfigParameterGroupType
    value_type: ConfigParameterValueType
    description: str
    default: list[str]
    options: List[ConfigParameterGroupEntry]

@dataclass
class ConfigParametrization(ConfigItem):
    """
    A top-level object covering all the parametrization in a given configuration.

    :param parameters: A list of configuration parameters and groups.
    :type parameters: List[Union[ConfigParameterSingle, ConfigParameterGroup]]
    """
    parameters: List[Union[ConfigParameterSingle, ConfigParameterGroup]]
    ref: str = field(default_factory=lambda: str(uuid4()))

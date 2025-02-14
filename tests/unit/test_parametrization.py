from dataclasses import is_dataclass, fields
from typing import Any

from cyst.api.configuration import *
from cyst.api.environment.environment import Environment

# ----------------------------------------------------------------------------------------------------------------------
# A test infrastructure configuration
# ----------------------------------------------------------------------------------------------------------------------
target = NodeConfig(
    active_services=[],
    passive_services=[
        PassiveServiceConfig(
            name="bash",
            owner="root",
            version=ConfigParameter("my-custom-version"),
            access_level=ConfigParameter("my-custom-access-level"),
            local=True,
        ),
        PassiveServiceConfig(
            name="lighttpd",
            owner="www",
            version="1.4.62",
            access_level=AccessLevel.LIMITED,
            local=False,
        )
    ],
    shell="bash",
    traffic_processors=[],
    interfaces=[],
    name="target"
)

attacker_service = ActiveServiceConfig(
            type="scripted_actor",
            name="attacker",
            owner="attacker",
            access_level=AccessLevel.LIMITED,
            ref="attacker_service_ref"
        )

attacker_node_1 = NodeConfig(
    active_services=[ConfigParameter("attacker_location_1")],
    passive_services=[],
    interfaces=[],
    shell="",
    traffic_processors=[],
    name="attacker_node_1"
)

attacker_node_2 = NodeConfig(
    active_services=[ConfigParameter("attacker_location_2")],
    passive_services=[],
    interfaces=[],
    shell="",
    traffic_processors=[],
    name="attacker_node_2"
)

router = RouterConfig(
    interfaces=[
        InterfaceConfig(
            ip=IPAddress("192.168.0.1"),
            net=IPNetwork("192.168.0.1/24"),
            index=0
        ),
        InterfaceConfig(
            ip=IPAddress("192.168.0.1"),
            net=IPNetwork("192.168.0.1/24"),
            index=1
        ),
        InterfaceConfig(
            ip=IPAddress("192.168.0.1"),
            net=IPNetwork("192.168.0.1/24"),
            index=2
        )
    ],
    traffic_processors=[
        FirewallConfig(
            default_policy=FirewallPolicy.ALLOW,
            chains=[
                FirewallChainConfig(
                    type=FirewallChainType.FORWARD,
                    policy=FirewallPolicy.ALLOW,
                    rules=[]
                )
            ]
        )
    ],
    id="router"
)

exploit1 = ExploitConfig(
    services=[
        VulnerableServiceConfig(
            service="lighttpd",
            min_version="1.3.11",
            max_version="1.4.62"
        )
    ],
    locality=ExploitLocality.REMOTE,
    category=ExploitCategory.CODE_EXECUTION,
    id="http_exploit"
)

connection1 = ConnectionConfig(
    src_ref=target.ref,
    src_port=-1,
    dst_ref=router.ref,
    dst_port=0
)

connection2 = ConnectionConfig(
    src_ref=attacker_node_1.ref,
    src_port=-1,
    dst_ref=router.ref,
    dst_port=1
)

connection3 = ConnectionConfig(
    src_ref=attacker_node_2.ref,
    src_port=-1,
    dst_ref=router.ref,
    dst_port=2
)


parametrization = ConfigParametrization(
    [
        ConfigParameterSingle(
            name="Vulnerable service version",
            type=ConfigParameterValueType.VALUE,
            description="Sets the version of a vulnerable service. If you put version smaller than 1.3.11 and larger than 1.4.62, the exploit will not work.",
            default="1.4.62",
            parameter_id="my-custom-version"
        ),
        ConfigParameterSingle(
            name="Vulnerable access level",
            type=ConfigParameterValueType.VALUE,
            description="Sets the access level for the service",
            default="user",
            parameter_id="my-custom-access-level"
        ),
        ConfigParameterGroup(
            parameter_id="attacker-position",
            name="Attacker position",
            group_type=ConfigParameterGroupType.ONE,
            value_type=ConfigParameterValueType.REF,
            description="The node, where the attacker starts at.",
            default=["attacker_location_1"],
            options=[
                ConfigParameterGroupEntry(
                    parameter_id="attacker_location_1",
                    value=attacker_service,
                    description="Node 1"
                ),
                ConfigParameterGroupEntry(
                    parameter_id="attacker_location_2",
                    value=attacker_service,
                    description="Node 2"
                )
            ]
        )
    ]
)


all_config = [target, attacker_service, attacker_node_1, attacker_node_2, router, exploit1, connection1, connection2, connection3, parametrization]

# Example of output that is passed from frontend or from user to /api/v1/environment/configure/ endpoint
parameters = {"SingleParameters": {"my-custom-access-level": "user"}, "GroupParameters": {"attacker-position": ["attacker_location_1"]}}

e = Environment.create()
e.configure(all_config, parameters)
e.control.init()
e.control.commit()


# --------------------------------------------------------------------------------------------------------------
# Parametrization testing

def parse_parameters(parametrization_config: ConfigParametrization, parameters: dict[str, Any]):
    """
    Parse user input parameters into a single dimensional dictionary for easier parametrization.
    """
    parsed_parameters = {}

    single_parameters = parameters['SingleParameters']
    group_parameters = parameters['GroupParameters']

    # Fill single parameters
    parsed_parameters.update(single_parameters)

    # Fill group parameters
    for parameter in parametrization_config.parameters:
        if isinstance(parameter, ConfigParameterGroup):
            for group_entry in parameter.options:
                if group_entry.parameter_id in group_parameters[parameter.parameter_id]:
                    parsed_parameters[group_entry.parameter_id] = group_entry.value

    return parsed_parameters


def check_and_default_parameters(parametrization_config: ConfigParametrization, parameters: dict[str, Any]):
    """
    Check the correctness of group parameters and fill in the defaults if the parameters are missing
    """

    def validate_group_entries(group_param, frontend_value):
        if group_param.group_type == ConfigParameterGroupType.ONE:
            if len(frontend_value) != 1:
                raise ValueError(f"Group '{group_param.parameter_id}' must have exactly one value")
        elif group_param.group_type == ConfigParameterGroupType.ANY:
            if len(frontend_value) < 1:
                raise ValueError(f"Group '{group_param.parameter_id}' must have at least one value")

    for parameter in parametrization_config.parameters:
        if isinstance(parameter, ConfigParameterSingle):
            if parameter.parameter_id not in parameters['SingleParameters']:
                parameters['SingleParameters'][parameter.parameter_id] = parameter.default
        elif isinstance(parameter, ConfigParameterGroup):
            if parameter.parameter_id not in parameters['GroupParameters']:
                parameters['GroupParameters'][parameter.parameter_id] = parameter.default
            validate_group_entries(parameter, parameters['GroupParameters'][parameter.parameter_id])


def combine_config_items_with_parameters(parametrization_config: ConfigParametrization,
                                         config_items: list[ConfigItem], parameters: dict[str, Any]):
    """
    Check the correctness of group parameters and fill in the defaults if the parameters are missing.
    Then iterate through config items and apply parameters in place of ConfigParameters.
    """
    # Check the correctness of group parameters and fill in the defaults if the parameters are missing
    check_and_default_parameters(parametrization_config, parameters)

    # Parse the parameters into a single-dimensional dict for easier config items parametrization
    parsed_parameters = parse_parameters(parametrization_config, parameters)

    def set_config_parameters(obj):
        if isinstance(obj, ConfigParameter):
            # If it's a ConfigParameter, replace it with the value from parameters if available
            if (parameter_value := parsed_parameters.get(obj.id)) is not None:
                return parameter_value
            else:
                print(f"Warning: No value found for ConfigParameter with id: {obj.id}")
                return obj
        elif isinstance(obj, dict):
            # Recursively handle dictionary items
            modified_dict = {key: set_config_parameters(value) for key, value in obj.items()}
            # Remove ConfigParameter instances from the dictionary
            return {k: v for k, v in modified_dict.items() if not isinstance(v, ConfigParameter)}
        elif isinstance(obj, list):
            # Recursively handle list elements
            modified_list = [set_config_parameters(item) for item in obj]
            # Remove ConfigParameter instances from the list
            return [item for item in modified_list if not isinstance(item, ConfigParameter)]
        elif is_dataclass(obj):  # This should be ConfigItem, but it's not a dataclass
            # Handle dataclass objects by iterating through their fields
            for field in fields(obj):
                setattr(obj, field.name, set_config_parameters(getattr(obj, field.name)))
        return obj

    # Apply the set_config_parameters function to each item in the configuration
    config_items = [set_config_parameters(item) for item in config_items]

    return config_items

#
# combine_config_items_with_parameters(parametrization, all_config, parameters)
# print(all_config)


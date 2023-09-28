from netaddr import IPNetwork, IPAddress

from cyst.api.environment.environment import Environment
from cyst.api.configuration import NodeConfig, PassiveServiceConfig, AccessLevel, ExploitConfig, VulnerableServiceConfig,\
                                   RouterConfig, InterfaceConfig, ConnectionConfig, ActiveServiceConfig
from cyst.api.host.service import Service
from cyst.api.network.node import Node
from cyst.api.logic.exploit import ExploitLocality, ExploitCategory

from cyst_services.scripted_actor.main import ScriptedActorControl

target = NodeConfig(
    active_services=[],
    passive_services=[
        PassiveServiceConfig(
            type="bash",
            owner="root",
            version="8.1.0",
            access_level=AccessLevel.LIMITED,
            local=True,
            id="bash_service"
        ),
        PassiveServiceConfig(
            type="lighttpd",
            owner="www",
            version="1.4.62",
            access_level=AccessLevel.LIMITED,
            local=False,
            id="web_server"
        )
    ],
    shell="bash_service",
    interfaces=[],
    traffic_processors=[],
    id="target"
)

attacker = NodeConfig(
    active_services=[
        ActiveServiceConfig(
            type="scripted_actor",
            name="attacker",
            owner="attacker",
            access_level=AccessLevel.LIMITED,
            id="attacker_service"
        )
    ],
    passive_services=[],
    interfaces=[],
    traffic_processors=[],
    shell="",
    id="attacker"
)

exploit1 = ExploitConfig(
    services=[
        VulnerableServiceConfig(
            name="lighttpd",
            min_version="1.4.62",
            max_version="1.4.62"
        )
    ],
    locality=ExploitLocality.REMOTE,
    category=ExploitCategory.CODE_EXECUTION,
    id="http_exploit"
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
      )
    ],
    traffic_processors=[],
    id="router"
)

connection1 = ConnectionConfig(
        src_id="target",
        src_port=-1,
        dst_id="router",
        dst_port=0
)

connection2 = ConnectionConfig(
        src_id="attacker",
        src_port=-1,
        dst_id="router",
        dst_port=1
)

e = Environment.create().configure(target, exploit1, router, connection1, attacker, connection2)

attacker_service = e.configuration.general.get_object_by_id("attacker_service", Service).active_service
attacker_control = e.configuration.service.get_service_interface(attacker_service, ScriptedActorControl)

e.control.init()

# ----------------------------------------------------------------------------------------------------------------------
# Addition to 05_create_adversary.py
# ----------------------------------------------------------------------------------------------------------------------
e.control.add_pause_on_response("attacker.attacker")

# Store the actions
actions = {}
for action in e.resources.action_store.get_prefixed("cyst"):
    actions[action.id] = action


# Display available actions
for action in actions.values():
    print(f"{action.id} ({action.description})")

# Scan the network for usable targets
action = actions["cyst:test:echo_success"]
for ip in IPNetwork("192.168.0.1/28").iter_hosts():
    attacker_control.execute_action(str(ip), "", action)
    e.control.run()
    print(f"{ip}: {attacker_control.get_last_response().status}")

# Look for exploitable services at the target
action = actions["cyst:host:get_remote_services"]
attacker_control.execute_action("192.168.0.2", "", action)
e.control.run()

services = attacker_control.get_last_response().content
print("Available services at 192.168.0.2: ", services)

useful_exploits = []

for service in services:
    service_name = service[0]
    service_version = service[1]
    potential_exploits = e.resources.exploit_store.get_exploit(service=service_name)
    for exp in potential_exploits:
        min_version = exp.services[service[0]].min_version
        max_version = exp.services[service[0]].max_version

        if min_version <= service_version <= max_version:
            useful_exploits.append((service[0], exp))

for exploit in useful_exploits:
    service_name = exploit[0]
    actual_exploit = exploit[1]
    print(f"Exploitable service: {service_name}, exploit category: {actual_exploit.category}, exploit locality: {actual_exploit.locality}")

# Use the exploit to get access to the target machine
action = actions["cyst:compound:session_after_exploit"]
action.set_exploit(useful_exploits[0][1])
attacker_control.execute_action("192.168.0.2", useful_exploits[0][0], action)
e.control.run()

# With the access, get information about the target
session = attacker_control.get_last_response().session
action = e.resources.action_store.get("meta:inspect:node")
attacker_control.execute_action("192.168.0.2", "", action, session=session)
e.control.run()

node: Node = attacker_control.get_last_response().content
print(f"Services at the target: {node.services.keys()}, interfaces at the target: {node.ips}")
# ----------------------------------------------------------------------------------------------------------------------

e.control.commit()

stats = e.resources.statistics
print(f"Run id: {stats.run_id}\nStart time real: {stats.start_time_real}\n"
      f"End time real: {stats.end_time_real}\nDuration virtual: {stats.end_time_virtual}")

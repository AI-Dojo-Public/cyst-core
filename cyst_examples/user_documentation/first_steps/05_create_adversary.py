from netaddr import IPNetwork, IPAddress

from cyst.api.environment.environment import Environment
from cyst.api.configuration import NodeConfig, PassiveServiceConfig, AccessLevel, ExploitConfig, VulnerableServiceConfig,\
                                   RouterConfig, InterfaceConfig, ConnectionConfig, ActiveServiceConfig
from cyst.api.host.service import Service
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
    shell="bash",
    interfaces=[],
    traffic_processors=[],
    id="target"
)

# ----------------------------------------------------------------------------------------------------------------------
# Addition to 04_create_network.py
# ----------------------------------------------------------------------------------------------------------------------
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
    id="attacker_node"
)
# ----------------------------------------------------------------------------------------------------------------------

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

# ----------------------------------------------------------------------------------------------------------------------
# Addition to 04_create_network.py
# ----------------------------------------------------------------------------------------------------------------------
connection2 = ConnectionConfig(
        src_id="attacker_node",
        src_port=-1,
        dst_id="router",
        dst_port=1
)

e = Environment.create().configure(target, exploit1, router, connection1, attacker, connection2)

attacker_service = e.configuration.general.get_object_by_id("attacker_node.attacker", Service).active_service
attacker_control = e.configuration.service.get_service_interface(attacker_service, ScriptedActorControl)
# ----------------------------------------------------------------------------------------------------------------------

e.control.init()
e.control.run()
e.control.commit()

stats = e.infrastructure.statistics
print(f"Run id: {stats.run_id}\nStart time real: {stats.start_time_real}\n"
      f"End time real: {stats.end_time_real}\nDuration virtual: {stats.end_time_virtual}")

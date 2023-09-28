from netaddr import IPNetwork, IPAddress

from cyst.api.environment.environment import Environment
from cyst.api.configuration import NodeConfig, PassiveServiceConfig, AccessLevel, ExploitConfig, VulnerableServiceConfig,\
                                   RouterConfig, InterfaceConfig, ConnectionConfig
from cyst.api.logic.exploit import ExploitLocality, ExploitCategory

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

# ----------------------------------------------------------------------------------------------------------------------
# Addition to 03_create_vulnerable_service.py
# ----------------------------------------------------------------------------------------------------------------------
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

e = Environment.create().configure(target, exploit1, router, connection1)
# ----------------------------------------------------------------------------------------------------------------------
e.control.init()
e.control.run()
e.control.commit()

stats = e.resources.statistics
print(f"Run id: {stats.run_id}\nStart time real: {stats.start_time_real}\n"
      f"End time real: {stats.end_time_real}\nDuration virtual: {stats.end_time_virtual}")

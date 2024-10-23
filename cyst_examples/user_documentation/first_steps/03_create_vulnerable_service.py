from cyst.api.environment.environment import Environment
from cyst.api.configuration import NodeConfig, PassiveServiceConfig, AccessLevel, ExploitConfig, VulnerableServiceConfig
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
        # --------------------------------------------------------------------------------------------------------------
        # Addition to 02_create_machine.py
        # --------------------------------------------------------------------------------------------------------------
        PassiveServiceConfig(
            type="lighttpd",
            owner="www",
            version="1.4.62",
            access_level=AccessLevel.LIMITED,
            local=False,
            id="web_server"
        )
        # --------------------------------------------------------------------------------------------------------------
    ],
    shell="bash",
    interfaces=[],
    traffic_processors=[],
    id="target"
)

# ----------------------------------------------------------------------------------------------------------------------
# Addition to 02_create_machine.py
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

e = Environment.create().configure(target, exploit1)
# ----------------------------------------------------------------------------------------------------------------------
e.control.init()
e.control.run()
e.control.commit()

stats = e.infrastructure.statistics
print(f"Run id: {stats.run_id}\nStart time real: {stats.start_time_real}\n"
      f"End time real: {stats.end_time_real}\nDuration virtual: {stats.end_time_virtual}")

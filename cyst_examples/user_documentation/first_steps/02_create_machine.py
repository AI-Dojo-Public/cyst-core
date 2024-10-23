from cyst.api.environment.environment import Environment
from cyst.api.configuration import NodeConfig, PassiveServiceConfig, AccessLevel

# ----------------------------------------------------------------------------------------------------------------------
# Addition to 01_do_nothing.py
# ----------------------------------------------------------------------------------------------------------------------
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
        )
    ],
    shell="bash",
    interfaces=[],
    traffic_processors=[],
    id="target"
)

e = Environment.create().configure(target)
# ----------------------------------------------------------------------------------------------------------------------
e.control.init()
e.control.run()
e.control.commit()

stats = e.infrastructure.statistics
print(f"Run id: {stats.run_id}\nStart time real: {stats.start_time_real}\n"
      f"End time real: {stats.end_time_real}\nDuration virtual: {stats.end_time_virtual}")

import uuid

from dataclasses import dataclass

from cyst.api.environment.stats import Statistics


@dataclass
class StatisticsImpl(Statistics):
    run_id: str = ""
    configuration_id: str = ""
    start_time_real: float = 0.0
    end_time_real: float = 0.0
    end_time_virtual: int = 0

    # This is a hack, because default_factory was being applied to the base class, which has read-only properties.
    # This way, everything works as expected
    def __post_init__(self):
        self.run_id = str(uuid.uuid4())

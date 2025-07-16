from dataclasses import dataclass

from cyst.api.environment.stats import Statistics


@dataclass
class StatisticsImpl(Statistics):
    run_id: str = ""
    configuration_id: str = ""
    start_time_real: float = 0.0
    end_time_real: float = 0.0
    end_time_virtual: int = 0

    @staticmethod
    def cast_from(o: Statistics) -> 'StatisticsImpl':
        if isinstance(o, StatisticsImpl):
            return o
        else:
            raise ValueError("Malformed underlying object passed with the Statistics interface")

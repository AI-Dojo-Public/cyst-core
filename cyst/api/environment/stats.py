from abc import ABC, abstractmethod


class Statistics(ABC):
    """
    Statistics class tracks various statistical information about simulation runs.
    """

    @property
    @abstractmethod
    def run_id(self) -> str:
        """
        Get the ID of the current run

        :rtype: str
        """
        pass

    @property
    @abstractmethod
    def configuration_id(self) -> str:
        """
        Get the ID of the configuration that is stored in the data store and that was used for the current run.

        :rtype: str
        """
        pass

    @property
    @abstractmethod
    def start_time_real(self) -> float:
        """
        Get the wall clock time when the current run started. The time is in the python time() format.

        :rtype: float
        """
        pass

    @property
    @abstractmethod
    def end_time_real(self) -> float:
        """
        Get the wall clock time when the current run was commited. The time is in the python time() format.

        :rtype: float
        """
        pass

    @property
    @abstractmethod
    def end_time_virtual(self) -> int:
        """
        Get the virtual time of the current run, i.e., the number of ticks. As the run always starts at 0, this function
        represents also the run duration.

        :rtype: int
        """
        pass

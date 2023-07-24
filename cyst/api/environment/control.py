import uuid

from abc import ABC, abstractmethod
from enum import Enum
from typing import Tuple


class EnvironmentState(Enum):
    """
    State of the environment

    State transition diagram:

    ::

                              reset()                 terminate()
                             ┌────────── TERMINATED ◄───────────┐
                             │               ▲                  │
                             │    terminate()│                  │
                             ▼               │    ──pause()──►  │
        CREATED ──init()─► INIT ──run()─► RUNNING             PAUSED
                             ▲               │    ◄──run()───
                             │               │
                             │               ▼
                             └────────── FINISHED
                              reset()

    Possible values:
        :CREATED: The environment was jus created.
        :INIT: The environment was initialized and is ready to run.
        :RUNNING: The environment is currently running a simulation.
        :PAUSED: The environment is paused. If unpaused, the messages on stack will be sent and simulation resumes.
        :FINISHED: The environment finished a simulation run. This means either no more messages on stack, or running
            past the specified time.
        :TERMINATED: The environment was forcefully stopped. It cannot be resumed, but its internal state can be
            investigated.

    """
    CREATED = -1,
    INIT = 0,
    RUNNING = 1,
    PAUSED = 2,
    FINISHED = 3,
    TERMINATED = 4


class EnvironmentControl(ABC):
    """
    EnvironmentControl provides mechanisms to control the execution of actions within the simulation environment.

    Availability:
        :Available: creator
        :Hidden:  agents, models
    """

    @property
    @abstractmethod
    def state(self) -> EnvironmentState:
        """ Provides the current state of the environment.

        :return: State of the environment
        :rtype: EnvironmentState
        """

    @abstractmethod
    def init(self, run_id: str = str(uuid.uuid4())) -> Tuple[bool, EnvironmentState]:
        """ Initializes the environment for the first time. The environment must be in the CREATED state.
        The following invocations do nothing and silently return true.

        :param run_id: The unique id of the current run. If a non-unique id is selected, it may produced unwanted
            results when saving the data to a data store.
        :type run_id: str

        :return: A tuple indicating, whether the operation was successful and which state the environment ended in.
        """

    @abstractmethod
    def commit(self) -> None:
        """ Stores the information of the currently executed run into the data store. This can only be executed from
        the FINISHED or TERMINATED state.

        :return: None
        """

    @abstractmethod
    def reset(self, run_id: str = str(uuid.uuid4())) -> Tuple[bool, EnvironmentState]:
        """ Resets the environment for another run. Only a previously FINISHED or TERMINATED run can be reset.

        :param run_id: The unique id of the current run. If a non-unique id is selected, it may produced unwanted
            results when saving the data to a data store.
        :type run_id: str

        :return: A tuple indicating, whether the operation was successful and which state the environment ended in.
        """

    @abstractmethod
    def run(self) -> Tuple[bool, EnvironmentState]:
        """ Starts or resumes the message processing in the current run. If the environment is in the INIT state, it
        activates the active services. If it is in INIT or PAUSED state, it begins message processing and transitions
        into the RUNNING state.

        :return: A tuple indicating, whether the operation was successful and which state the environment ended in.
        """

    @abstractmethod
    def pause(self) -> Tuple[bool, EnvironmentState]:
        """ Invokes an explicit transition into the PAUSED state and temporarily halts the message processing. Can only
        be applied in the running state.

        :return: A tuple indicating, whether the operation was successful and which state the environment ended in.
        """

    @abstractmethod
    def terminate(self) -> Tuple[bool, EnvironmentState]:
        """ Halts the message processing and transitions the environment into the TERMINATED state. From this state
        the environment cannot be re-run.

        :return: A tuple indicating, whether the operation was successful and which state the environment ended in.
        """

    @abstractmethod
    def add_pause_on_request(self, id: str) -> None:
        """ Adds an explicit interrupt to message processing, whenever a service sends a request. Transitions the
        environment into the PAUSED state. Used mainly in tests to break from the run().

        :param id: A fully qualified id of a service, i.e., also containing the node id.

        :return: None
        """

    @abstractmethod
    def remove_pause_on_request(self, id: str) -> None:
        """ Removes an explicit interrupt to message processing, whenever a service sends a request.

        :param id: A fully qualified id of a service, i.e., also containing the node id.

        :return: None
        """

    @abstractmethod
    def add_pause_on_response(self, id: str) -> None:
        """ Adds an explicit interrupt to message processing, whenever a service receives a response. Transitions the
        environment into the PAUSED state. Used mainly in tests to break from the run().

        :param id: A fully qualified id of a service, i.e., also containing the node id.

        :return: None
        """

    @abstractmethod
    def remove_pause_on_response(self, id: str) -> None:
        """ Removes an explicit interrupt to message processing, whenever a service sends a request.

        :param id: A fully qualified id of a service, i.e., also containing the node id.

        :return: None
        """

    @abstractmethod
    def snapshot_save(self) -> str:
        """ Returns a complete state of the environment, from which it can be restored.

        :return: String representation of the environment
        """

    @abstractmethod
    def snapshot_load(self, state: str) -> None:
        """ Attempts to restore the environment into the state described by the state string.

        :param state: State representation obtained by snapshot_save function. Currently, the snapshots are not
                      guaranteed to work across versions.
        :type state: str

        :return: None
        """

    @abstractmethod
    def transaction_start(self) -> Tuple[int, int, str]:
        """ Initiates a new transaction, which sets a point in time to which the environment can be reverted. The
        transaction has to begin as a first thing in a given time slot, i.e., if there was already a message processed
        in the time slot, the transaction will be set to start in the next time slot.

        Multiple calls to transaction_start() at the same time slot start only one transaction.

        Transactions can be interleaved. In case of a rollback, the state always returns to the beginning of
        transaction that was rolled back.

        Transactions do not necessarily modify the state of active services, it is up to their authors, if they want
        to preserve, e.g., learned behavior across transactions.

        :return: A tuple containing transaction_id of started transaction, the time when the transaction starts, and
                 additional information, if there is any.
        """

    @abstractmethod
    def transaction_commit(self, transaction_id: int) -> Tuple[bool, str]:
        """
        Finalizes a transaction. Such transaction is removed from the system and cannot be rolled back.

        Any transaction can be committed by anyone. There is no validation of the caller.

        :param transaction_id: The id of a transaction to commit.
        :type transaction_id: int

        :return: A tuple indicating whether the transaction was successfully committed and providing additional
                 information if present.
        """

    @abstractmethod
    def transaction_rollback(self, transaction_id: int) -> Tuple[bool, str]:
        """
        Returns the system into the state at the beginning of a transaction. After the transaction is rolled back, it is
        removed from the system.

        Any transaction can be rolled back by anyone. There is no validation of a caller.

        :param transaction_id: The ID of the transaction to roll back.
        :type transaction_id: int

        :return: A tuple indicating whether a rollback was successful and providing additional information in present.
        """

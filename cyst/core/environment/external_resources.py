import asyncio
import concurrent.futures
import functools
from abc import ABC, abstractmethod
from enum import Enum, auto
from time import mktime
from typing import Union, Optional, Callable, Type, Any, Tuple
from urllib.parse import urlparse, ParseResult
from dataclasses import dataclass

from cyst.api.environment.clock import Clock
from cyst.api.environment.external import ExternalResources, Resource, ResourcePersistence
from cyst.api.environment.message import Status, StatusOrigin, StatusValue
from cyst.api.host.service import Service

from cyst.core.environment.message import ResourceMessageImpl


class ResourcesState(Enum):
    CREATED = auto()
    INIT = auto()
    OPENED = auto()
    CLOSED = auto()


class ResourceImpl(Resource, ABC):

    def path(self) -> str:
        pass

    def persistence(self) -> ResourcePersistence:
        pass

    def persist(self) -> bool:
        pass

    def state(self) -> ResourcesState:
        pass

    def init(self, params: dict[str, str]) -> bool:
        pass

    def open(self) -> bool:
        pass

    def close(self) -> bool:
        pass

    def send(self, params: dict[str, str], timeout: int) -> int:
        pass

    def receive(self, params: dict[str, str], timeout: int) -> str:
        pass


class FileResource(ResourceImpl):

    def __init__(self, path: ParseResult):
        self._path = path.netloc
        self._url = str(path)
        self._persistent = ResourcePersistence.TRANSIENT
        self._mode = "r"
        self._handle = None
        self._state = ResourcesState.CREATED

    def path(self) -> str:
        return self._url

    def persistence(self) -> ResourcePersistence:
        return self._persistent

    def persist(self) -> bool:
        self._persistent = ResourcePersistence.PERSISTENT
        return True

    def state(self) -> ResourcesState:
        return self._state

    def init(self, params: dict[str, str]) -> bool:
        if "mode" in params:
            self._mode = params["mode"]

        self._state = ResourcesState.INIT

        return True

    def open(self) -> bool:
        try:
            self._handle = open(self._path, self._mode)
        except Exception as e:
            raise("Failed to open a file. Reason: " + str(e))

        self._state = ResourcesState.OPENED
        return True

    def close(self) -> bool:
        self._handle.close()
        self._state = ResourcesState.CLOSED
        return True

    def send(self, params: dict[str, str], timeout: int) -> int:
        if ("w" in self._mode) or ("a" in self._mode):
            if "data" in params:
                data = params["data"]
                self._handle.write(data)
            else:
                raise RuntimeError("No data specified for writing")
        else:
            raise RuntimeError("File not opened for writing")
        return len(data)

    def receive(self, params: dict[str, str], timeout: int) -> str:
        if "r" in self._mode:
            data = self._handle.read()
            return data
        else:
            raise RuntimeError("File not opened for reading")


@dataclass
class ResourceTask:
    path: str
    fn: Callable
    params: dict[str, str]
    virtual_timeout: int
    real_timeout: int
    service: Service = None
    coroutine: Any = None


class ResourceTaskGroup:
    def __init__(self, event_loop, thread_pool, clock: Clock):
        self._event_loop = event_loop
        self._thread_pool = thread_pool
        self._tasks: list[ResourceTask] = []
        self._virtual_timeout = None
        self._real_timeout = 0
        self._clock = clock
        self._run_start = None

    def virtual_timeout(self) -> int:
        return self._virtual_timeout

    def real_timeout(self) -> int:
        return self._real_timeout

    def add_task(self, task: ResourceTask):
        if not self._tasks:
            self._virtual_timeout = task.virtual_timeout
        else:
            if self._virtual_timeout != task.virtual_timeout:
                raise RuntimeError("Task group must have identical virtual time tasks")

        # Store a starting time for a first task that is added
        if not self._run_start:
            self._run_start = mktime(self._clock.real_time())

        # If there is no timeout yet, just take it from the task
        if self._real_timeout == 0:
            self._real_timeout = task.real_timeout + self._run_start
        # If there is one (i.e., a task is already running), add to the timeout only if the task allocation would
        # overflow remaining timeouts of other tasks
        else:
            corrected_timeout = self._real_timeout - self._run_start
            if task.real_timeout > corrected_timeout:
                self._real_timeout = task.real_timeout + self._run_start

        # Finally, run the task and save it for later
        task.coroutine = self._event_loop.run_in_executor(self._thread_pool, functools.partial(task.fn, task.params, task.real_timeout))
        self._tasks.append(task)

    def collect_tasks(self) -> list[ResourceTask]:
        self._event_loop.run_until_complete(
            asyncio.wait(
                [t.coroutine for t in self._tasks],
                timeout=self._real_timeout
            )
        )
        return self._tasks


class ExternalResourcesImpl(ExternalResources):
    def __init__(self, clock: Clock, resource_task_callback: Callable[[int], None]):
        self._resources: dict[str, Type] = {
            "file": FileResource
        }

        self._event_loop = asyncio.new_event_loop()
        self._thread_pool = concurrent.futures.ThreadPoolExecutor()

        self._resource_task_callback = resource_task_callback

        self._clock = clock
        self._task_pool: dict[int, ResourceTaskGroup] = {}

    @staticmethod
    def cast_from(o: ExternalResources) -> 'ExternalResourcesImpl':
        if isinstance(o, ExternalResourcesImpl):
            return o
        else:
            raise ValueError("Malformed underlying object passed with the ExternalResources interface")

    def custom_resource(self, init: Callable[[dict[str, str]], bool], open: Callable[[], int], close: Callable[[], int], send: Callable[[dict[str, str]], int], receive: Callable[[], str]):
        pass

    def persistent_resource(self, path: str, params: dict[str, str]) -> Resource:
        pass

    def release_resource(self, resource: Resource) -> None:
        pass

    def send(self, resource: Union[str, Resource], params: Optional[dict[str, str]], virtual_duration: int = 0, timeout: int = 0) -> None:
        r = resource
        if isinstance(resource, str):
            r = self._create_resource(resource, params)

        if r.persistence() == ResourcePersistence.TRANSIENT:
            r.open()

        self._schedule_task(ResourceTask(r.path(), r.send, params, virtual_duration, timeout))

        if r.persistence() == ResourcePersistence.TRANSIENT:
            r.close()

    def fetch(self, resource: Union[str, Resource], params: Optional[dict[str, str]], virtual_duration: int = 0, timeout: int = 0, service: Optional[Service] = None) -> Optional[str]:
        if virtual_duration != 0 and not service:
            raise RuntimeError("Cannot fetch a resource with non-zero duration without a service specification")

        r = resource
        if isinstance(resource, str):
            r = self._create_resource(resource, params)

        if r.persistence() == ResourcePersistence.TRANSIENT:
            r.open()

        result = self._schedule_task(ResourceTask(r.path(), r.receive, params, virtual_duration, timeout, service))

        if r.persistence() == ResourcePersistence.TRANSIENT:
            r.close()

        return result

    def _create_resource(self, path: str, params: dict[str, str]) -> Optional[ResourceImpl]:
        r = urlparse(path)
        if not r.scheme:
            raise RuntimeError("Attempted to access a resource without specifying a scheme. Please, use file://, http://, etc.")

        if r.scheme not in self._resources:
            raise RuntimeError(f"No implementation for resource of type: {r.scheme}.")

        res = self._resources[r.scheme](r)
        res.init(params)
        return res

    def _schedule_task(self, task: ResourceTask) -> Optional[str]:
        # Special-casing for 0 virtual time - run blocking
        if task.virtual_timeout == 0:
            return task.fn(task.params, task.real_timeout)

        # Anything else runs inside a task group in separate threads and gets sorted out at the beginning of a message
        # processing loop
        virtual_time = self._clock.simulation_time() + task.virtual_timeout
        if virtual_time not in self._task_pool:
            tg = ResourceTaskGroup(self._event_loop, self._thread_pool, self._clock)
            self._task_pool[virtual_time] = tg
        else:
            tg = self._task_pool[virtual_time]

        tg.add_task(task)
        self._resource_task_callback(virtual_time)

        return None

    def collect_tasks(self, virtual_time: int) -> None:
        if virtual_time in self._task_pool:
            tasks = self._task_pool[virtual_time].collect_tasks()
            for t in tasks:
                # TODO: More detailed info about resource retrieval
                if t.coroutine.done():
                    status = Status(StatusOrigin.RESOURCE, StatusValue.SUCCESS)
                    data = t.coroutine.result()
                else:
                    status = Status(StatusOrigin.RESOURCE, StatusValue.FAILURE)
                    data = None

                # Create a message and call it on the service
                t.service.active_service.process_message(ResourceMessageImpl(t.path, status, t.service.name, data))

        return None

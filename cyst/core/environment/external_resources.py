import asyncio
import heapq
import os
import pathlib
import urllib
import urllib.request

from enum import Enum, auto
from heapq import heappush, heappop
from typing import Union, Optional, Type, Dict, Tuple, List, Any
from urllib.parse import urlparse, ParseResult

from netaddr import IPAddress

from cyst.api.environment.clock import Clock
from cyst.api.environment.message import Resource as ResourceMsg, T, MessageType, Status, StatusValue, StatusOrigin
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.external import ExternalResources, Resource, ResourcePersistence, ResourceImpl
from cyst.api.host.service import Service, ActiveService
from cyst.api.logic.access import Authorization, AuthenticationToken, AuthenticationTarget
from cyst.api.logic.metadata import Metadata
from cyst.api.network.session import Session
from cyst.api.utils.counter import Counter


class ResourcesState(Enum):
    CREATED = auto()
    INIT = auto()
    OPENED = auto()
    CLOSED = auto()

class ResourceOp(Enum):
    SEND = auto()
    FETCH = auto()


# ----------------------------------------------------------------------------------------------------------------------
# Resource message is just a thin wrapper over resource contents to enable correct calling of process_message() of
# active services.
class ResourceMessage(ResourceMsg):
    def __init__(self, path: str, status: Status, data: str):
        self._path = path
        self._status = status
        self._data = data
        self._id = Counter().get("message")

    @property
    def type(self) -> MessageType:
        return MessageType.RESOURCE

    @property
    def id(self) -> int:
        return self._id

    @property
    def path(self) -> str:
        return self._path

    @property
    def status(self) -> Status:
        return self._status

    @property
    def data(self) -> Optional[str]:
        return self._data

    # ------------------------------------------------------------------------------------------------------------------
    # Unfortunately, these have to be implemented
    @property
    def src_ip(self) -> Optional[IPAddress]:
        raise NotImplementedError("Resources do not implement ordinary Message attributes.")

    @property
    def dst_ip(self) -> Optional[IPAddress]:
        raise NotImplementedError("Resources do not implement ordinary Message attributes.")

    @property
    def src_service(self) -> Optional[str]:
        raise NotImplementedError("Resources do not implement ordinary Message attributes.")

    @property
    def dst_service(self) -> str:
        raise NotImplementedError("Resources do not implement ordinary Message attributes.")

    @property
    def session(self) -> Optional[Session]:
        raise NotImplementedError("Resources do not implement ordinary Message attributes.")

    @property
    def auth(self) -> Optional[Union[Authorization, AuthenticationToken, AuthenticationTarget]]:
        raise NotImplementedError("Resources do not implement ordinary Message attributes.")

    @property
    def ttl(self) -> int:
        raise NotImplementedError("Resources do not implement ordinary Message attributes.")

    @property
    def metadata(self) -> Metadata:
        raise NotImplementedError("Resources do not implement ordinary Message attributes.")

    def set_metadata(self, metadata: Metadata) -> None:
        raise NotImplementedError("Resources do not implement ordinary Message attributes.")

    @property
    def platform_specific(self) -> Dict[str, Any]:
        raise NotImplementedError("Resources do not implement ordinary Message attributes.")

    def cast_to(self, type: Type[T]) -> T:
        raise NotImplementedError("Resources do not implement ordinary Message attributes.")

# ----------------------------------------------------------------------------------------------------------------------
# TODO: FileResource is internally synchronous. Which is not such a problem for intended use cases, but it should
#       probably be rewritten using aiofiles library.
class FileResource(ResourceImpl):

    def __init__(self):
        self._path: Optional[pathlib.Path] = None
        self._url = ""
        self._persistent = ResourcePersistence.TRANSIENT
        self._mode = "r"
        self._handle = None
        self._state = ResourcesState.CREATED

    @property
    def path(self) -> str:
        return self._url

    @property
    def persistence(self) -> ResourcePersistence:
        return self._persistent

    def init(self, path: ParseResult, params: Optional[dict[str, str]] = None, persistence: ResourcePersistence = ResourcePersistence.TRANSIENT) -> bool:
        self._url = str(path)
        self._path = urllib.request.url2pathname(path.path)
        self._persistent = persistence

        if params and "mode" in params:
            self._mode = params["mode"]

        self._state = ResourcesState.INIT

        return True

    def open(self) -> None:
        try:
            self._handle = open(self._path, self._mode)
        except Exception as e:
            raise RuntimeError("Failed to open a file. Reason: " + str(e))

        self._state = ResourcesState.OPENED

    def close(self) -> None:
        self._handle.close()
        self._state = ResourcesState.CLOSED

    async def send(self, data: str, params: Optional[dict[str, str]] = None) -> int:
        if ("w" in self._mode) or ("a" in self._mode):
            self._handle.write(data)
        else:
            raise RuntimeError("File not opened for writing")
        return len(data)

    async def receive(self, params: Optional[dict[str, str]] = None) -> str:
        if "r" in self._mode:
            data = self._handle.read()
            return data
        else:
            raise RuntimeError("File not opened for reading")


# ----------------------------------------------------------------------------------------------------------------------
class ExternalResourcesImpl(ExternalResources):
    def __init__(self, loop: asyncio.AbstractEventLoop, clock: Clock):
        self._loop = loop
        self._clock = clock

        self._tasks: Dict[str, Tuple[Union[asyncio.Future, ActiveService], asyncio.Task, Resource, float]] = {}
        self._finished: List[Tuple[float, int, Union[asyncio.Future, ActiveService], asyncio.Task, Resource]] = []
        self._pending: List[float] = []
        self._collecting = 0

        self._resources: dict[str, Union[Type, ResourceImpl]] = {}
        self.register_resource("file", FileResource)

    @staticmethod
    def cast_from(o: ExternalResources) -> 'ExternalResourcesImpl':
        if isinstance(o, ExternalResourcesImpl):
            return o
        else:
            raise ValueError("Malformed underlying object passed with the ExternalResources interface")

    def register_resource(self, scheme: str, resource: Union[Type, ResourceImpl]) -> bool:
        if scheme in self._resources:
            raise RuntimeError(f"Attempting to register already registered resource for scheme {scheme}")
        else:
            if (isinstance(resource, type) and not issubclass(resource, ResourceImpl)) and not isinstance(resource, ResourceImpl):
                raise RuntimeError(f"Resource of wrong type (not implementing ResourceImpl) passed for registration: {resource}")
            self._resources[scheme] = resource
            return True

    def create_resource(self, path: str, params: Optional[dict[str, str]] = None, persistence: ResourcePersistence = ResourcePersistence.TRANSIENT) -> Resource:
        parsed_path = urlparse(path)

        if not parsed_path.scheme:
            raise RuntimeError(f"Resource path does not contain a scheme: {parsed_path}")

        if parsed_path.scheme not in self._resources:
            raise RuntimeError(f"Could not create a resource of unknown scheme {parsed_path.scheme}")

        resource_template = self._resources[parsed_path.scheme]
        if isinstance(resource_template, type):
            r: ResourceImpl = resource_template()
        else:
            r = resource_template
        r.init(parsed_path, params, persistence)  # Init should throw exception which gets caught by the Task

        if persistence == ResourcePersistence.PERSISTENT:
            r.open()

        return r

    def release_resource(self, resource: Resource) -> None:
        if resource.persistence == ResourcePersistence.PERSISTENT:
            if isinstance(resource, ResourceImpl):
                resource.close()

    async def send_async(self, resource: Union[str, Resource], data: str, params: Optional[dict[str, str]] = None, timeout: float = 0.0) -> None:
        r = resource
        if isinstance(resource, str):
            r = self.create_resource(resource, params)

        if not isinstance(r, ResourceImpl):
            raise RuntimeError("Malformed object passed with Resource interface.")

        if r.persistence == ResourcePersistence.TRANSIENT:
            r.open()

        await self._schedule_task(r, ResourceOp.SEND, data, params, timeout)

    # Not really nice code duplication. But I still need to decide on whether jump into the rabbit hole and go full-on
    # on asyncio processing in the engine.
    def send(self, resource: Union[str, Resource], data: str, params: Optional[dict[str, str]] = None, timeout: float = 0.0, callback_service: Optional[ActiveService] = None) -> None:
        r = resource
        if isinstance(resource, str):
            r = self.create_resource(resource, params)

        if not isinstance(r, ResourceImpl):
            raise RuntimeError("Malformed object passed with Resource interface.")

        if r.persistence == ResourcePersistence.TRANSIENT:
            r.open()

        task = self._loop.create_task(r.send(data, params))
        self._tasks[task.get_name()] = (callback_service, task, r, self._clock.current_time() + timeout)
        task.add_done_callback(self._process_finished_tasks)
        heappush(self._pending, self._clock.current_time() + timeout)

    async def fetch_async(self, resource: Union[str, Resource], params: Optional[dict[str, str]] = None, timeout: float = 0.0) -> Optional[str]:
        r = resource
        if isinstance(resource, str):
            r = self.create_resource(resource, params)

        if not isinstance(r, ResourceImpl):
            raise RuntimeError("Malformed object passed with Resource interface.")

        if r.persistence == ResourcePersistence.TRANSIENT:
            r.open()

        result = await self._schedule_task(r, ResourceOp.FETCH, "", params, timeout)

        if r.persistence == ResourcePersistence.TRANSIENT:
            r.close()

        return result

    def fetch(self, resource: Union[str, Resource], params: Optional[dict[str, str]] = None, timeout: float = 0.0, callback_service: Optional[ActiveService] = None) -> None:
        r = resource
        if isinstance(resource, str):
            r = self.create_resource(resource, params)

        if not isinstance(r, ResourceImpl):
            raise RuntimeError("Malformed object passed with Resource interface.")

        if r.persistence == ResourcePersistence.TRANSIENT:
            r.open()

        task = self._loop.create_task(r.receive(params))
        self._tasks[task.get_name()] = (callback_service, task, r, self._clock.current_time() + timeout)
        task.add_done_callback(self._process_finished_tasks)
        heappush(self._pending, self._clock.current_time() + timeout)

    async def _schedule_task(self, resource: ResourceImpl, resource_op: ResourceOp, data: str, params: Optional[dict[str, str]], timeout: float = 0.0) -> Optional[str]:
        future = self._loop.create_future()

        if resource_op == ResourceOp.SEND:
            task = self._loop.create_task(resource.send(data, params))
        else:
            task = self._loop.create_task(resource.receive(params))

        real_timeout = self._clock.current_time() + timeout
        self._tasks[task.get_name()] = (future, task, resource, real_timeout)
        task.add_done_callback(self._process_finished_tasks)
        heappush(self._pending, real_timeout)

        # Tasks that fail timeout are cancelled and end here anyway
        await future
        # TODO: Exception not handled here!
        return future.result()

    def _process_finished_tasks(self, task: asyncio.Task):
        # Move task to finished
        future_or_service, _, resource, timeout = self._tasks[task.get_name()]
        heappush(self._finished, (timeout, Counter().get("resource"), future_or_service, task, resource))
        del self._tasks[task.get_name()]

        if resource.persistence == ResourcePersistence.TRANSIENT:
            if isinstance(resource, ResourceImpl):
                resource.close()

    def pending(self) -> Tuple[bool, float]:
        if not self._pending:
            return False, 0.0
        else:
            return True, self._pending[0] - self._clock.current_time()

    def collecting(self) -> bool:
        return self._collecting != 0

    def finish_collecting(self, task: asyncio.Task) -> None:
        self._collecting -= 1

    # Set futures on all finished tasks
    def collect_immediately(self) -> int:
        if not self._finished:
            return 0

        for timeout, _, future_or_service, task, resource in self._finished:
            self._pending.remove(timeout)
            if isinstance(future_or_service, asyncio.Future):
                future_or_service.set_result(task.result())
            else:
                # This is handling the case when a service callback is not specified, because we don't care (SEND case)
                if future_or_service:
                    if not task.exception():
                        status = Status(StatusOrigin.SYSTEM, StatusValue.SUCCESS)
                        t: asyncio.Task = self._loop.create_task(future_or_service.process_message(ResourceMessage(resource.path, status, task.result())))
                    else:
                        status = Status(StatusOrigin.SYSTEM, StatusValue.ERROR)
                        t: asyncio.Task = self._loop.create_task(future_or_service.process_message(ResourceMessage(resource.path, status, str(task.exception()))))
                    t.add_done_callback(self.finish_collecting)
                    self._collecting += 1

        # Reconstruct pending queue after reckless deletions
        heapq.heapify(self._pending)

        task_count = len(self._finished)
        self._finished.clear()
        return task_count

    # Set futures on tasks that past timeout
    def collect_at(self, current_time: float, ) -> int:
        if not self._finished:
            return 0

        task_count = 0

        timeout, _, _, _, _ = self._finished[0]
        while current_time <= timeout:
            self._pending.remove(timeout)
            _, _, future_or_service, task, resource = heappop(self._finished)
            task_count += 1
            if isinstance(future_or_service, asyncio.Future):
                future_or_service.set_result(task.result())
            else:
                if future_or_service:
                    if not task.exception():
                        status = Status(StatusOrigin.SYSTEM, StatusValue.SUCCESS)
                        t: asyncio.Task = self._loop.create_task(future_or_service.process_message(ResourceMessage(resource.path, status, task.result())))
                    else:
                        status = Status(StatusOrigin.SYSTEM, StatusValue.ERROR)
                        t: asyncio.Task = self._loop.create_task(future_or_service.process_message(ResourceMessage(resource.path, status, str(task.exception()))))
                    t.add_done_callback(self.finish_collecting)
                    self._collecting += 1

            if not self._finished:
                break

            timeout, _, _, _, _ = self._finished[0]

        # Reconstruct pending queue after reckless deletions
        heapq.heapify(self._pending)

        return task_count

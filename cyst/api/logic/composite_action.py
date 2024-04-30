from abc import abstractmethod

from cyst.api.environment.message import Request


class CompositeActionManager:

    @abstractmethod
    async def call_action(self, request: Request, delay: float = 0.0) -> None:
        pass

    @abstractmethod
    async def delay(self, delay: float = 0.0) -> None:
        pass

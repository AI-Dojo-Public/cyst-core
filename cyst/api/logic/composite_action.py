from abc import abstractmethod

from cyst.api.environment.message import Request


class CompositeActionManager:
    @abstractmethod
    def execute_request(self, request: Request, delay: int) -> None:
        pass

    @abstractmethod
    async def call_action(self, request: Request, delay: int) -> None:
        pass

    @abstractmethod
    def delay(self, delay: int) -> None:
        pass

from dataclasses import dataclass
from typing import List

from cyst.api.environment.message import Status, Request, Response


@dataclass
class ActionParameterModel:
    name: str
    value: str


@dataclass
class ActionModel:
    # Request part
    run_id: str
    message_id: int
    action_id: str
    caller_id: str
    src_ip: str
    dst_ip: str
    dst_service: str
    session_in: str
    auth_in: str
    parameters: List[ActionParameterModel]
    # Response part
    session_out: str = ""
    auth_out: str = ""
    status_origin: str = ""
    status_value: str = ""
    status_detail: str = ""
    response: str = ""

    @classmethod
    def from_request(cls, run_id: str, request: Request):
        parameters = []
        for param in request.action.parameters.values():
            parameters.append(ActionParameterModel(
                name=param.name,
                value=str(param.value)
            ))

        return cls(
            run_id=run_id,
            message_id=request.id,
            action_id=request.action.id,
            caller_id=request.platform_specific["caller_id"],
            src_ip=str(request.src_ip) if request.src_ip else "",
            dst_ip=str(request.dst_ip),
            dst_service=request.dst_service,
            session_in=str(request.session.id) if request.session else "",
            auth_in="", # TODO
            parameters=parameters
        )

    def set_response(self, response: Response):
        # This can easily happen, as the request gets assigned source IP in the platform code, after the ActionModel
        # was initialized.
        if not self.src_ip:
            self.src_ip = str(response.dst_ip)
        self.session_out = str(response.session.id) if response.session else ""
        self.auth_out = "" # TODO
        self.status_origin = str(response.status.origin)
        self.status_value = str(response.status.value)
        self.status_detail = str(response.status.detail) if response.status.detail else ""
        self.response = str(response.content)

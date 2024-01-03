from random import randint

from cyst.api.environment.message import Message
from cyst.api.environment.metadata_provider import MetadataProvider, MetadataProviderDescription
from cyst.api.logic.action import Action
from cyst.api.logic.metadata import Metadata, Flow, FlowDirection, TCPFlags, Protocol


class CAMMetadataProvider(MetadataProvider):

    def get_metadata(self, action: Action, message: Message) -> Metadata:
        result = Metadata()
        if action.id == "cam:component:tcp_flow":
            if action.parameters["direction"].value == "forward":
                direction = FlowDirection.REQUEST
                flags = TCPFlags.S | TCPFlags.F
            else:
                direction = FlowDirection.RESPONSE
                flags = TCPFlags.S | TCPFlags.A

            duration = randint(1, 5)  # Because, why not
            f = Flow(
                id=str(message.id),  # TODO: WTF?
                direction=direction,
                packet_count=action.parameters["byte_size"].value,
                duration=duration,
                flags=flags,
                protocol=Protocol.TCP
            )
            result.flows = [f]

        return result


def create_cam_mp() -> MetadataProvider:
    mp = CAMMetadataProvider()
    return mp


metadata_provider_description = MetadataProviderDescription(
    namespace="cam",
    description="Metadata provider for cam action namespace",
    creation_fn=create_cam_mp
)
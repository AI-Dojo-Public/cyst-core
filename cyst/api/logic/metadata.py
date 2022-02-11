from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, NamedTuple, Optional
from flags import Flags
from netaddr import IPAddress


@dataclass
class Event:
    """
    Event represents an identification of a phenomenon within a message. Typically it can be some alert from an IDS,
    which the mechanisms downstream can act upon.

    :param id: An identifier of the event.
    :type id: str
    """
    id: str


class TCPFlags(Flags):
    """
    TCP protocol flags. Can be used separately or combined together by means of the OR operator. Example:

    .. code-block:: python

        f1 = TCPFlags.R
        f2 = TCPFlags.S | TCPFlags.A

    Possible values:
        :S: SYN
        :A: ACK
        :R: RESET
        :P: PUSH
        :U: UPDATE
        :F: FIN

    """
    S = ()
    A = ()
    R = ()
    P = ()
    U = ()
    F = ()


class Protocol(Enum):
    """
    A communication protocol used in the messages.

    Possible values:
        :UDP: UDP Protocol.
        :TCP: TCP Protocol.
        :ICMP: ICMP Protocol.
    """
    UDP = auto()
    TCP = auto()
    ICMP = auto()


class FlowDirection(Enum):
    """
    Direction of the flow.

    Possible values:
        :REQUEST: The flow was create from a message of the request type.
        :RESPONSE: The flow was created from a message of the response type.
    """
    REQUEST = auto()
    RESPONSE = auto()


@dataclass
class Flow:
    """
    Flow (in network terminology) represents an aggregation of packets. However, because the simulation engine is not
    modelling the communication at the packet level, but rather a flow-level, the flow describes one message. It adds
    statistical and L2/L3 layer information on top of abstract message description.

    :param id: Identifier of the flow. It is the same as the ID of the message it was created from. TODO: There is a
        discrepancy, as the message id is int. What the hell is the purpose of Flow id?
    :type id: str

    :param direction: A direction of the flow.
    :type direction: FlowDirection

    :param packet_count: A number of packets aggregated into the flow.
    :type packet_count: int

    :param duration: A number of simulated time units it took for the flow to realize.
    :type duration: int

    :param flags: A set of TCP flags.
    :type flags: TCPFlags

    :param protocol: A protocol type.
    :type protocol: Protocol
    """
    id: str
    direction: FlowDirection
    packet_count: int
    duration: int
    flags: TCPFlags
    protocol: Protocol


@dataclass
class Metadata:
    """
    Metadata represents information that could be observed if one took a look at the packets that were exchanged
    between message source and destination. Metadata are supplied to messages by metadata providers. For more info
    see :class:`cyst.api.environment.metadata_provider.MetadataProvider`. Because of the reliance on providers,
    not all metadata need to be specified.

    :param src_ip: A source IP of the message. Does not necessarily have to be the same as message source IP, as the
        provider can put there anything it thinks is the source (e.g., seeing through the proxy or NAT).
    :type src_ip: Optional[IPAddress]

    :param dst_ip: A destination IP of the message. Does not necessarily have to be the same as message destination IP,
        as the provider can put there anything it thinks is the ultimate destination.
    :type dst_ip: Optional[IPAddress]

    :param dst_service: A destination service of the message. Does not necessarily have to be the same as message
        destination service, as the provider can put there anything it thinks is the ultimate destination (e.g.,
        final result of port knocking, understanding port forwarding).
    :type dst_service: Optional[str]

    :param event: A recognized event.
    :type event: Optional[str]

    :param flows: A list of flows associated with the message.
    :type flows: Optional[List[Flow]]
    """
    src_ip: Optional[IPAddress] = None
    dst_ip: Optional[IPAddress] = None
    dst_service: Optional[str] = None
    event: Optional[str] = None
    flows: Optional[List[Flow]] = None

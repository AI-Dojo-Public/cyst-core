from abc import ABC, abstractmethod
from deprecated.sphinx import versionchanged
from netaddr import IPAddress
from typing import Any, Optional, Union

from cyst.api.environment.message import Message, Request, Response, Status
from cyst.api.logic.action import Action
from cyst.api.logic.access import Authorization, AuthenticationTarget, AuthenticationToken
from cyst.api.network.session import Session


class EnvironmentMessaging(ABC):
    """
    This interface enables creating and sending of messages within simulation.
    """

    @abstractmethod
    def send_message(self, message: Message, delay: float = 0.0) -> None:
        """
        Sends a message into the simulation for processing. The system will attempt to route the message to its
        destination. If there is a problem with delivery, an indication of it will be received in form of another
        message. This call always succeeds.

        :param message: The message to be sent.
        :type message: Message

        :param delay: Simulation time delay between calling of this function and the actual dispatching of the message
            into the simulated infrastructure.
        :type delay: float

        :return: None
        """

    @abstractmethod
    @versionchanged(version="0.6.0", reason="Added original request parameter to enable request copying")
    def create_request(self, dst_ip: Union[str, IPAddress], dst_service: str = "", action: Optional[Action] = None,
                       session: Optional[Session] = None,
                       auth: Optional[Union[Authorization, AuthenticationToken]] = None,
                       original_request: Optional[Request] = None) -> Request:
        """
        Creates a message of type REQUEST. This function is a domain of active services.

        :param dst_ip: A destination IP address. If provided in the string form, it will attempt to convert it
            internally into the IPAddress.
        :type dst_ip: Union[str, IPAddress]

        :param dst_service: The name of the service this message should be routed to.
        :type dst_service: str

        :param action: An action that should be performed at the destination. Even though this function technically
            enables action-less message, it is an implementation detail and such message would be dropped at the first
            hop. TODO: Check it.
        :type action: Action

        :param session: An optional session to use for a routing of this message.
        :type session: Session

        :param auth: Either authentication or authorization token to use for this message. If an authentication token
            is provided and the type of action is _not_ meta:authenticate, then the system will internally attempt to
            obtain an authorization by means of the meta:authenticate action and the proceed with the original action.
            More in the description of the authentication/authorization framework.
        :type auth: Union[Authorization, AuthenticationToken]

        :param original_request: If provided, values from the original request are used to fill blanks in the new
            request. This is seldom needed in agent's code and is more useful when creating behavioral models.
        :type original_request: Request

        :return: A Request to be sent.
        """

    @abstractmethod
    @versionchanged(version="0.6.0", reason="Added original response parameter to enable response copying")
    def create_response(self, request: Request, status: Status, content: Optional[Any] = None, session: Optional[Session] = None,
                        auth: Optional[Union[Authorization, AuthenticationTarget]] = None,
                        original_response: Optional[Response] = None) -> Response:
        """
        Creates a message of type RESPONSE. This response is always created from a request.

        :param request: The request to which this response is created.
        :type request: Request

        :param status: A status code of the response.
        :type status: Status

        :param content: A message body. Currently anything can be sent in the response, but it is expected that in
            future updates, the content will have its taxonomy and domains, so that automated reasoning can be fully
            applied to message processing.
        :type content: Optional[Any]

        :param session: Either the original session that is inherited from the request, or a new session that is created
            as a part of request processing. If the request arrived through a session, a session must be present with
            the response. Otherwise, the message would not be correctly routed.
        :type session: Session

        :param auth: By convention, this parameter should be the original request's authorization token, unless the
            request resulted in a creation of a new authorization token, or unless the request-response is a part of
            a multi-factor authentication (in which case an Authenticationtarget is returned).
        :type auth: Optional[Union[Authorization, AuthenticationTarget]]

        :param original_response: If provided, values from the original response are used to fill blanks in the new
            request. This is seldom needed in agent's code and is more useful when creating behavioral models.
        :type original_response: Response

        :return: A response to be sent.
        """

    @abstractmethod
    def open_session(self, request: Request) -> Session:
        """
        Opens a session to the source of the request. If the request already contains a session, it will append the
        session, unless the current node is an endpoint of that session. In that case, the same session is returned.

        :param request: The request from which the session is established.
        :type request: Request

        :return: A session to the request source.
        """

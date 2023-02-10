import enum
import time
import importlib

import flags
import jsonpickle

from typing import Any

import semver
from netaddr import IPAddress, IPNetwork

import netaddr

from cyst.api.configuration.logic.access import AuthorizationDomainType
from cyst.api.configuration.network.elements import ConnectionConfig
from cyst.api.environment.configuration import ServiceParameter
from cyst.api.environment.control import EnvironmentState
from cyst.api.environment.message import MessageType, StatusOrigin, StatusValue, StatusDetail
from cyst.api.logic.access import AccessLevel, AuthenticationTokenType, AuthenticationTokenSecurity, AuthenticationProviderType
from cyst.api.logic.action import ActionParameterDomainType, ActionParameterType, ActionToken
from cyst.api.logic.exploit import ExploitCategory, ExploitLocality, ExploitParameterType
from cyst.api.logic.metadata import TCPFlags, Protocol, FlowDirection
from cyst.api.network.firewall import FirewallPolicy, FirewallChainType

# ----------------------------------------------------------------------------------------------------------------------
# Custom serialization handlers
# ----------------------------------------------------------------------------------------------------------------------


@jsonpickle.handlers.register(IPNetwork)
class IPSerializer(jsonpickle.handlers.BaseHandler):

    def flatten(self, obj, data):
        data["_value"] = str(obj)

    def restore(self, obj: str):
        return IPNetwork(obj)


@jsonpickle.handlers.register(IPAddress)
class IPSerializer(jsonpickle.handlers.BaseHandler):

    def flatten(self, obj, data):
        data["_value"] = str(obj)

    def restore(self, obj: str):
        return IPAddress(obj)


@jsonpickle.handlers.register(time.struct_time)
class TimeSerializer(jsonpickle.handlers.BaseHandler):

    def flatten(self, obj: time.struct_time, data):
        data["_value"] = time.mktime(obj)
        return data

    def restore(self, obj):
        return time.localtime(obj["_value"])


@jsonpickle.handlers.register(enum.Enum, base=True)
class EnumSerializer(jsonpickle.handlers.BaseHandler):

    def flatten(self, obj: enum.Enum, data):
        data["_value"] = obj.name
        return data

    def restore(self, obj):
        enum_name = obj["py/object"].split(".")[-1]
        return globals()[enum_name][obj["_value"]]


@jsonpickle.handlers.register(flags.Flags, base=True)
class FlagsSerializer(jsonpickle.handlers.BaseHandler):

    def flatten(self, obj: flags.Flags, data):
        data["_value"] = obj.to_simple_str()
        return data

    def restore(self, obj):
        flag_name = obj["py/object"].split(".")[-1]
        return globals()[flag_name].from_simple_str(obj["_value"])


@jsonpickle.handlers.register(semver.VersionInfo, base=True)
class VersionInfoSerializer(jsonpickle.handlers.BaseHandler):

    def flatten(self, obj: semver.VersionInfo, data):
        data["_value"] = str(obj)
        return data

    def restore(self, obj):
        return semver.VersionInfo.parse(obj["_value"])


# Environment
class Serializer:
    @staticmethod
    def serialize(obj: Any) -> str:
        return jsonpickle.encode(obj, make_refs=True, indent=2, keys=True)

    @staticmethod
    def deserialize(state: str) -> Any:
        obj = jsonpickle.decode(state, keys=True)
        return obj

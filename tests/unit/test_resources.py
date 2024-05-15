import pathlib
import os
import unittest

from typing import Tuple, Union, List

from cyst.api.configuration import NodeConfig, ActiveServiceConfig, AccessLevel

from cyst.api.environment.configuration import EnvironmentConfiguration
from cyst.api.environment.environment import Environment
from cyst.api.environment.message import Message, MessageType, Resource, Request, Response, Status, StatusOrigin, StatusValue
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.platform_specification import PlatformType, PlatformSpecification
from cyst.api.environment.policy import EnvironmentPolicy
from cyst.api.environment.resources import EnvironmentResources
from cyst.api.host.service import Service
from cyst.api.logic.action import Action, ActionDescription, ActionType
from cyst.api.logic.composite_action import CompositeActionManager
from cyst.api.logic.behavioral_model import BehavioralModel, BehavioralModelDescription
from cyst.api.network.node import Node

from cyst_services.scripted_actor.main import ScriptedActorControl, ScriptedActor


class DummyBehavioralModel(BehavioralModel):

    def __init__(self, configuration: EnvironmentConfiguration, resources: EnvironmentResources,
                 policy: EnvironmentPolicy, messaging: EnvironmentMessaging,
                 composite_action_manager: CompositeActionManager) -> None:
        self._resources = resources
        self._messaging = messaging
        self._test_file = pathlib.Path("test_file.txt").absolute()
        self._resources.action_store.add(
            ActionDescription(
                id="dummy:action_1",
                type=ActionType.COMPOSITE,
                platform=PlatformSpecification(PlatformType.SIMULATION, "CYST"),
                description="A dummy action to test asynchronous resource handling",
                parameters=[]
            )
        )

    async def action_flow(self, message: Request) -> Tuple[int, Response]:
        data = await self._resources.external.fetch_async(self._test_file.as_uri(), timeout=3)
        response = self._messaging.create_response(message, Status(StatusOrigin.SYSTEM, StatusValue.SUCCESS), content=data)
        return 0, response

    async def action_effect(self, message: Request, node: Node) -> Tuple[int, Response]:
        pass

    def action_components(self, message: Union[Request, Response]) -> List[Action]:
        pass


attacker = NodeConfig(
    active_services=[
        ActiveServiceConfig(
            type="scripted_actor",
            name="attacker",
            owner="attacker",
            access_level=AccessLevel.LIMITED,
            id="attacker_service"
        )
    ],
    passive_services=[],
    interfaces=[],
    shell="",
    traffic_processors=[],
    id="attacker_node"
)


class ResourceTests(unittest.TestCase):

    def setUp(self) -> None:
        self._env = Environment.create().configure(attacker)

        self._attacker_service = self._env.configuration.general.get_object_by_id("attacker_node.attacker", Service).active_service
        self._attacker_control = self._env.configuration.service.get_service_interface(self._attacker_service, ScriptedActorControl)

        # As usual, do not try this at home. It is brittle, but makes the tests soooo much clearer.
        self._model = self._env._behavioral_models["dummy"] = DummyBehavioralModel(self._env.configuration, self._env.resources,
                                                                                   None, self._env.messaging, self._env._cam)

        self._env.control.init()

        self._test_file = pathlib.Path("test_file.txt").absolute()
        if pathlib.Path.exists(self._test_file):
            os.remove("test_file.txt")

    def tearDown(self) -> None:
        self._env.control.commit()

    def test_0000_resources(self) -> None:

        self._test_count = 0

        def run_callback_1(messaging: EnvironmentMessaging, resources: EnvironmentResources):
            resources.external.send(self._test_file.as_uri(), "hello", params={"mode":"w"}, callback_service=self._attacker_service)

        def resource_callback_1(messaging: EnvironmentMessaging, resources: EnvironmentResources, message: Message) -> Tuple[bool, int]:
            self.assertTrue(pathlib.Path.exists(self._test_file), "File was written.")
            self.assertTrue(message.type == MessageType.RESOURCE, "Resource callback correctly fired")

            self._test_count += 2

            self._attacker_control.set_message_callback(MessageType.RESOURCE, resource_callback_2)
            resources.external.fetch(self._test_file.as_uri(), callback_service=self._attacker_service)
            return True, 1

        def resource_callback_2(messaging: EnvironmentMessaging, resources: EnvironmentResources, message: Message) -> Tuple[bool, int]:
            if isinstance(message, Resource):  # Just for the sake of code inspection
                data = message.data
                self.assertEqual(data, "hello", "Resource correctly read.")

            self._test_count += 1

            self._attacker_control.set_message_callback(MessageType.RESOURCE, resource_callback_3)
            resources.external.fetch(self._test_file.as_uri(), timeout=2, callback_service=self._attacker_service)
            return True, 1

        def resource_callback_3(messaging: EnvironmentMessaging, resources: EnvironmentResources, message: Message) -> Tuple[bool, int]:
            if isinstance(message, Resource):  # Just for the sake of code inspection
                data = message.data
                self.assertEqual(data, "hello", "Resource correctly read.")

            self.assertGreaterEqual(resources.clock.current_time(), 2.0, "Timeout for synchronous operation was correctly applied.")

            self._test_count += 2
            return True, 1

        self._attacker_control.set_run_callback(run_callback_1)
        self._attacker_control.set_message_callback(MessageType.RESOURCE, resource_callback_1)
        self._env.control.run()

        self.assertEqual(self._test_count, 5, "All synchronous test ran successfully")

        self._attacker_control.execute_action("192.168.0.1", "", self._env.resources.action_store.get("dummy:action_1"))
        self._env.control.run()
        self.assertGreaterEqual(self._env.resources.clock.current_time(), 5.0, "Timeout for asynchronous operation was correctly applied.")

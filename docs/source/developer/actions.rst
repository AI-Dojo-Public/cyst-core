New developer's guide
*********************

Code management
===============
The CYST framework is developed and distributed as a set of loosely-dependent packages (with the exception of cyst-core).
Thanks to the magic of pip, this is much less painful than it may seem, especially if you find yourself in a
situation when you need to do a parallel development of a subset of packages.

Each package should follow this directory structure. Note that those cyst_* directories need not be all present. Each
package can contain 0+ different extensions. Also, these directory names are convention-based to keep it tidy inside
your system. You can in principle use any name and directory structure, providing you correctly set up entry points
and package in your setup.py (more on that later).

.. code-block:: text

    package_name
    |
    │   .gitignore
    │   LICENSE.md
    │   README.md
    │   setup.py
    │
    ├───cyst_models
    │   └───model_name
    │           main.py
    │           __init__.py
    |
    ├───cyst_services
    │   └───service_name
    │           main.py
    │           __init__.py
    │
    ├───cyst_metadata_providers
    │   └───metadata_provider_name
    │           main.py
    │           __init__.py
    |
    ├───docs
    │       .gitignore
    │
    └───tests
            .gitignore

Package setup
-------------

The packages' setup.py files are normal setup files that are in detail described
`HERE <https://packaging.python.org/en/latest/guides/distributing-packages-using-setuptools/#setup-args>`_.

Two arguments, however, are worth pointing out:

    - packages:
        If you look at the cyst_* directories, you will see that they do not contain the __init__.py file. This
        means that they will not be automatically included by find_packages() function. Instead, they are treated as
        namespace packages (need to if you want it to work) and must be explicitly included via the find_namespace_packages()
        function. If you decide to use your own directory structure, you can add the __init__.py files and use the
        find_packages() functions as you are not likely to get a name clash, which would prevent correct importing of packages.

    - entry_points:
        The CYST framework relies on the mechanism of entry points to discover and correctly import the extensions.
        This is an example of entry points from the cyst-core:

        .. code-block:: python

                entry_points={
                    'cyst.models': [
                        'cyst=cyst_models.cyst.main:behavioral_model_description',
                        'meta=cyst_models.meta.main:behavioral_model_description'
                    ],
                    'cyst.services': [
                        'scripted_actor=cyst_services.scripted_actor.main:service_description'
                    ]
                },

        This configuration specifies that the cyst-core provides two models - cyst and meta, and one active service -
        scripted_actor. Their respective entry points are located at python.path.to.module:instance_name.


Actions
=======
An action is a central concept to CYST. An action represents an effect an actor is trying to exert on the environment.
Actions are represented by a set of values that may denote its effect, but an action does not carry any semantics. That
is the responsibility of behavioral models or particular actors (more on that later). But let's not drown ourselves
too much in abstract concepts...

This is the description of a single action, which is used to register it to the system:

    .. code-block:: python

        class ActionDescription
            id: str
            type: ActionType
            description: str
            parameters: List[ActionParameter]
            environment: Union[ExecutionEnvironment, List[ExecutionEnvironment]]

As you can see, the description is very declarative, with no associated functions. When an action is registered into the
system, it basically says "here is something that can be done and hopefully, there will be someone that will understand
it down the road." Whether there will be such someone can only be decided in runtime, though.

The primary blobs of concentrated understanding are behavioral models.

Behavioral models
=================
A behavioral models' main function is providing semantics to actions. Usually, they also define those actions, but that
is not strictly necessary. In the following text, you'll learn how to create your own behavioral model.


Setting it up
-------------
We will begin by creating a new package for the model. This will follow the package structure as described in one of the
previous sections, so consult the details there, if you are not sure.

The easiest way is to copy a template that is available at project's gitlab:

.. tabs::

    .. tab:: Windows CMD

        Clone the templates repository:

        .. code-block:: console

            ...> git clone https://<username>:<token>@gitlab.ics.muni.cz/cyst/cyst-templates.git

        Make a copy of the template:

        .. code-block:: console

            ...> mkdir my_awesome_model
            ...> xcopy ...\cyst-templates\model\ my_awesome_model\ /E/Y

    .. tab:: Linux shell

        Clone the templates repository:

        .. code-block:: console

            ...$ git clone https://<username>:<token>@gitlab.ics.muni.cz/cyst/cyst-templates.git

        Make a copy of the template:

        .. code-block:: console

            ...$ mkdir my_awesome_model
            ...$ cp -r .../cyst-templates/model/ my_awesome_model/

The template has almost everything needed to make it work from the get-go. However, to make it more explicit, we will
explore what is in the template stub (main.py).

Each model starts with a minimal set of imports. Currently we prefer explicit imports, although it may change in the
future:

    .. code-block:: python

        import asyncio
        from typing import Tuple, Callable, Union, List
        from netaddr import IPNetwork

        from cyst.api.environment.configuration import EnvironmentConfiguration
        from cyst.api.environment.message import Request, Response, Status, StatusOrigin, StatusValue, MessageType
        from cyst.api.environment.messaging import EnvironmentMessaging
        from cyst.api.environment.policy import EnvironmentPolicy
        from cyst.api.environment.resources import EnvironmentResources
        from cyst.api.logic.action import ActionDescription, ActionType, ActionParameter, ActionParameterType, Action, ExecutionEnvironment, ExecutionEnvironmentType
        from cyst.api.logic.behavioral_model import BehavioralModel, BehavioralModelDescription
        from cyst.api.logic.composite_action import CompositeActionManager
        from cyst.api.network.node import Node

As you can see, that is a quite a lot of imports. The reason is that behavioral models have a really extensive access
to the CYST, second only to the environments.

After that, there is the declaration of the model (we'll rename it to AwesomeModel).

    .. code-block:: python

        class AwesomeModel(BehavioralModel):

            def __init__(self, configuration: EnvironmentConfiguration, resources: EnvironmentResources,
                         policy: EnvironmentPolicy, messaging: EnvironmentMessaging,
                         composite_action_manager: CompositeActionManager) -> None:
                pass

            async def action_flow(self, message: Request) -> Tuple[int, Response]:
                pass

            def action_effect(self, message: Request, node: Node) -> Tuple[int, Response]:
                pass

            def action_components(self, message: Union[Request, Response]) -> List[Action]:
                pass


Once you have this model stub, you need to prepare the entry point, which is a structure that describes the model and
provides a factory function. Here is one way to do it.

    .. code-block:: python

        def create_awesome_model(configuration: EnvironmentConfiguration, resources: EnvironmentResources,
                                 policy: EnvironmentPolicy, messaging: EnvironmentMessaging,
                                 composite_action_manager: CompositeActionManager) -> BehavioralModel:
            model = AwesomeModel(configuration, resources, policy, messaging, composite_action_manager)
            return model


        behavioral_model_description = BehavioralModelDescription(
            namespace="awesome",
            description="A behavioral model that is without a doubt - awesome",
            creation_fn=create_awesome_model
        )

As the last thing, we need to correctly set the entry points (setup.py).

        .. code-block:: python

                entry_points={
                    'cyst.models': [
                        'awesome=cyst_models.awesome.main:behavioral_model_description',
                    ]
                },

You should already have a virtual environment set up (if not, do it) and now its time to register the model into CYST.

        .. code-block:: console

            ...$ (venv) pip install -e .

In addition to registering your model into CYST, this will install all the requirements and should make everything
ready.

Testing environment
-------------------
To test your newly developing behavioral model, you can either follow the user's documentation and prepare the
environment by yourself, or simply copy one from the templates repository. The easier one, the better.

Adding the first direct action
------------------------------
The code so far does nothing and is probably screaming because of the passes in the AwesomeModel class' functions.
First of all, you should make copies of the constructor parameters. You will need them later.

    .. code-block:: python

        def __init__(self, configuration: EnvironmentConfiguration, resources: EnvironmentResources,
                 policy: EnvironmentPolicy, messaging: EnvironmentMessaging,
                 composite_action_manager: CompositeActionManager) -> None:

            self._configuration = configuration
            self._action_store = resources.action_store
            self._exploit_store = resources.exploit_store
            self._policy = policy
            self._messaging = messaging
            self._cam = composite_action_manager

After that, you will start adding the actions, or at least their specifications. Their semantics will be implemented
later. The actions are added through the :class:`cyst.api.environment.stores.ActionStore`, which is accessed through
the :class:`cyst.api.environment.resources.EnvironmentResources` interface.

In this example we will add one parametrized action, which will represent a virtual punch of awesomeness. For the
details of action description and parameter domains, see their documentation starting from here:
:class:`cyst.api.logic.action.ActionDescription`.

    .. code-block:: python

        from cyst.api.logic.action import ActionParameterType, ActionParameterDomain, ActionParameterDomainType, ActionParameter, ActionType

        def __init__(self, configuration: EnvironmentConfiguration, resources: EnvironmentResources,
                 policy: EnvironmentPolicy, messaging: EnvironmentMessaging,
                 composite_action_manager: CompositeActionManager) -> None:

            # ...

            self._action_store.add(ActionDescription(id="awesome:punch",
                                                     type=ActionType.DIRECT,
                                                     description="Deliver a punch of pre-defined awesomeness",
                                                     parameters=[ActionParameter(ActionParameterType.NONE, "punch_strength",
                                                                                 configuration.action.create_action_parameter_domain_options("weak", ["weak", "super strong"]))],
                                                     ))

To recap, now you have your own behavioral model that defines one action, which is now accessible to any active service
in the simulation. But that action does not have any meaning and if a service were to use it, it would fail. That's why
we will now give the action its semantics.

The easiest way is to just copy the dispatch structure from the template. It takes care of wrong action names, such as
awesome:pumch and enables you to easily add new functions to handle new actions. No black magic, only convenience.

    .. code-block:: python

        def action_effect(self, message: Request, node: Node) -> Tuple[int, Response]:
            if not message.action:
                raise ValueError("Action not provided")

            action_name = "_".join(message.action.fragments)
            fn: Callable[[Request, Node], Tuple[int, Response]] = getattr(self, "process_" + action_name, self.process_default)
            return fn(message, node)

        def process_default_effect(self, message: Request, node: Node) -> Tuple[int, Response]:
            print("Could not evaluate message. Action in `awesome` namespace unknown. " + str(message))
            return 0, self._messaging.create_response(message, status=Status(StatusOrigin.SYSTEM, StatusValue.ERROR), session=message.session)

        def process_punch(self, message: Request, node: Node) -> Tuple[int, Response]:
            pass

As you can see, for each new added action of the form awesome:item1:item2 you need to add function
process_awesome_item1_item2().

To make this example as easy ass possible, we will make the process_awesome_punch function to return success or
failure depending on the punch strength. These returns are communicated to the system by means of messages that are
created by the implemented model in response to requests.

    .. code-block:: python

        def process_punch(self, message: Request, node: Node) -> Tuple[int, Response]:
            # No error checking. Don't do this at home!
            strength = message.action.parameters["punch_strength"].value
            if strength == "weak":
                return 1, self._messaging.create_response(message, status=Status(StatusOrigin.NODE, StatusValue.FAILURE), content="That's a weak punch, bro!")
            else:
                return 1, self._messaging.create_response(message, status=Status(StatusOrigin.NODE, StatusValue.SUCCESS), content="That's a good punch, bro!")

And that's it. You have just given the semantics to the action. Now, if a simulated actor were to execute the
awesome:punch action, it would be correctly executed.

Action types
------------
Let's now get back for a second to the action description used before:

    .. code-block:: python

            self._action_store.add(ActionDescription(id="awesome:punch",
                                                     type=ActionType.DIRECT,
                                                     description="Deliver a punch of pre-defined awesomeness",
                                                     parameters=[ActionParameter(ActionParameterType.NONE, "punch_strength",
                                                                                 configuration.action.create_action_parameter_domain_options("weak", ["weak", "super strong"]))],
                                                     ))

As you can see, there is a field called type, which was not really explained before. Starting from the version 0.6.0
there are three types of action, with completely different semantics and their respective
:class:`cyst.api.logic.action.ActionType`. These are:

1. **Direct actions**:
    represent the effect between two concreate nodes or services. Direct actions are atomic and carried by one Request
    and one or more Responses. These are the only actions that were available prior to the version 0.6.0.
2. **Composite actions**:
    represent a flow of multiple actions. They have one source at the beginning, but have virtually no limitations on
    number of targets or intermediate sources. They comprise of either direct actions or other composite actions.
    Composite actions enable creation of action hierarchies and offloading of complex processing from action users.
3. **Component actions**:
    are actions that intentionally do not have an environmental impact or actionable semantics and serve for enhancing
    the details of direct actions, especially for dataset creation.

A basic example of direct actions was already presented and the rest is described later in the documentation.

Adding composite actions
------------------------
If you recall how agents are implemented, you know that there exists a callback mechanism that gets executed, whenever
an agent receives a message, be it a Request or a Response. This callback mechanism let's you manage an inherently
asynchronous nature of simulated interactions, where Requests and Responses can intertwine without any predictable
pattern. However, this also means that to execute a more complex action flow, you have no other choice than to manage
a complex state machine that lets you express the flow within a callback system.

Composite actions come to the rescue! They enable you to define arbitrarily complex flow of arbitrary actions, while
acting as a simple, direct action on the user's side.

Let's start with a simplest case - action aliasing. We begin by defining a new strong punch action, which is just a
punch that is always strong.

    .. code-block:: python

            self._action_store.add(ActionDescription(id="awesome:strong_punch",
                                                     type=ActionType.COMPOSITE,
                                                     description="Deliver a punch of preset awesomeness",
                                                     parameters=[],
                                                     ))

As you can see, we have changed the action type and removed the punch strength parameter. To implement the effect, we
will have to relegate to one of the unused functions:

    .. code-block:: python
        :linenos:

        async def action_flow(self, message: Request) -> Tuple[int, Response]:
            if not message.action:
                raise ValueError("Action not provided")

            action_name = "_".join(message.action.fragments)
            task = getattr(self, "process_" + action_name, process_default_flow)

            return task(message)

        async def process_default_flow(self, message: Request) -> Tuple[int, Response]:
            print("Could not evaluate message. Action in `awesome` namespace unknown. " + str(message))
            return 0, self._messaging.create_response(message, status=Status(StatusOrigin.SYSTEM, StatusValue.ERROR), session=message.session)

        async def process_strong_punch(self, message: Request) -> Tuple[int, Response]:
            action = self._action_store.get("awesome:punch")
            action.parameters["punch_strength"].value = "super strong"

            request = self._messaging.create_request(action=action, original_request=message)
            response = await self._cam.call_action(request)

            return 0, self._messaging.create_response(message, status=message.status, session=message.session)

First of all, you probably noticed that all functions here have a keyword ``async`` in their declaration. That is
because CYST is internally using Python's asyncio framework to handle the callbacks and to provide an illusion of
serial processing.

Next, there is the dispatch pattern (1-12) that you saw earlier with direct actions. The principle is identical, but the
main difference is the lack of the ``node`` parameter in the declaration. We've already touched it before when
discussing different types of actions, but let's put some details here.

Direct actions get executed at the target, i.e., when a message with a given action reaches a node and/or a service (it
gets more complex with execution environment, but more on that later). On the other hand, composite actions are executed
the moment they are sent to the system, i.e., when an agent calls a ``send_message`` function. This means that a
composite action is never carried in a message through the simulated infrastructure - it is snatched by the system the
moment it gets sent.

This brings us to the ``process_strong_punch`` function. Within this function (and all composite processing functions)
you will be creating requests and processing responses and in the end you return one final response, which represent
the result of the entire action flow.

Within the function, an action ``awesome:punch`` is queried from the action store (15). You can select any available
action, but be careful to edit your setup script to include module dependency if the action is not from your file or
from cyst-core. Then the action parameter is set to the "super strong" value (16) and we are ready to stuff it into the
message.

As we are now just aliasing the request, we can do it the easy way and copy the original request and only exchange the
action (18). Copies made this way will assign a new ID to the message, so you don't have to worry about potential
clashes.

We then use the composite action manager that we got in the init call (19). The manager has only two functions that
concern you, one being a ``call_action()`` which will relay the request to the system and block the processing until a
response is collected. Don't forget that to make it work, you have to await that call.

Finally, we create a response to the original request, in which we relay the results (21).

On the agent's side, it would look as if the agent sent a direct action and after some time received the response as
usual. This whole processing is completely hidden from it.

Creating complex action flows
-----------------------------
Invocating all this machinery just for the sake of action renaming would be an overkill, so now we introduce a bit
more complex example.

We begin by adding a new action ``punch_flurry``.

    .. code-block:: python

            self._action_store.add(ActionDescription(id="awesome:punch_flurry",
                                                     type=ActionType.COMPOSITE,
                                                     description="Deliver a barrage of punches with a strong finishing one",
                                                     parameters=[],
                                                     ))

The action will deliver a preset number of punches with random strength, followed by a dramatic pause and finalized by a
strong punch. The action will return ``SUCCESS`` only when three or more strong punches landed. (Don't seek any logic
here, I got trapped in some twisted anime reality.)

    .. code-block:: python
        :linenos:

        async def process_punch_flurry(self, message: Request) -> Tuple[int, Response]:
            punch_count = message.parameters["punch_count"].value

            tasks = []
            for _ in range(punch_count):
                action = self._action_store.get("awesome:punch")
                action.parameters["punch_strength"].value = "super strong" if random.random() > 0.5 else "weak"

                request = self._messaging.create_request(action=action, original_request=message)
                tasks.append(self._cam.call_action(request))

            results = asyncio.gather(*tasks)

            await self._cam.delay(random.randint(1, 5))

            action = self._action_store.get("awesome:punch")
            action.parameters["punch_strength"].value = "super strong"

            request = self._messaging.create_request(action=action, original_request=message)
            results.append(await self._cam.call_action(request))

            success_count = sum(1 for r in results if r.status.value == StatusValue.SUCCESS)
            if success_count >= 3:
                status = Status(StatusOrigin.SERVICE, StatusValue.SUCCESS)
            else:
                status = Status(StatusOrigin.SERVICE, StatusValue.FAILURE)

            return 0, self._messaging.create_response(message, status=status, content=success_count, session=message.session)

We begin by querying the number of punches that should be attempted (2).

In an action flow, the actions can be executed either one after another, or in parallel. In essence, whenever you use
the await keyword or its equivalent, the preceding actions are executed in parallel. You can see it in our example. In
the for cycle (5) the action calling function is not awaited (10), but instead the tasks it produces are stored for
later use in the ``tasks`` array (4). These tasks are then awaited implicitly with the ``asyncio.gather`` call (12),
which waits until all tasks are finished, storing their results in the ``results`` array.

Be aware not to share an action between parallel requests if those actions have different parameters or associated
exploits. Always get a fresh copy from the action store (6) and set parameters separately (7). If done otherwise, the
action for each request would be the same with the last set parameters.

On line (14), we are using the second composite action manager function, ``delay``, which just lets the simulation
progress specified amount of time units.

Next (16-20) we simply execute a strong punch in the same way we did it in the previous example. Only this time, we
add its results to the others in the ``results`` array.

Finally, we count the successful hits (22), check if there is enough and prepare appropriate status (23-26), and send
the ultimate response to the caller with the correct status and the success count (28).

With this mechanism, you are free to execute arbitrarily complex action flows. You don't even need to have all messages
originating at the caller. If you correctly set up the messages with source IP, service, and origin, you are free to
execute whatever spooky action at the distance you like. However, tread carefully if you decide to do this as you are
throwing away many safeguards CYST usually provides.

Inter-actor actions
-------------------
Up until now, all the actions terminated at a passive target, i.e., their effect was evaluated by the behavioral model.
But active actors are free to exchange messages with actions that no behavioral model processes, as they themselves are
assigning semantics to those actions. In fact, for any serious multi-agent setting, this needs to be the case.

The actions that are exchanged between actors (active services) are defined in the same way as other actions, through
the :class:`cyst.api.environment.stores.ActionStore` interface. You could in theory define those actions on-the-fly in
the agent's code (and it would work), but the better option is to define it through a behavioral model which does not
implement action effects.

So the code may look like this:

    .. code-block:: python

        class InterActorModel(BehavioralModel):

            def __init__(self, configuration: EnvironmentConfiguration, resources: EnvironmentResources,
                         policy: EnvironmentPolicy, messaging: EnvironmentMessaging,
                         composite_action_manager: CompositeActionManager) -> None:

                self._action_store.add(ActionDescription(id="iam:action1", type=ActionType.DIRECT,
                                                         description="", parameters=[]))
                self._action_store.add(ActionDescription(id="iam:action2", type=ActionType.DIRECT,
                                                         description="", parameters=[]))
                ...

            def action_effect(self, message: Request, node: Node) -> Tuple[int, Response]:
                pass

Note that you are free to implement action flows even for inter-agent actions and they will work as intended. There is
no issue in combining ordinary actions with inter-agent ones.

Before we dive into the gory details of action components, it is necessary to explore how CYST can be used to turn
simulation artifacts into actionable datasets.

Metadata providers
==================
So far, we were mostly concerned with actions and direct reactions to them, such as attacker's activities. Something is
done and it plays out or not. But in a more realistic setting, these actions can be intercepted, scrutinized, and acted
upon.

Suppose, you aim to implement a defending service that should guard against network attacks. As of today, you could
set the service as a traffic processor on some router, intercept all the messages and look for nefarious actions. They
advertise what they are doing after all, just check the action property of a message... But this is as far detached from
the reality as possible. Virtually no attack wears a proud badge of being an attack. So, what now?

CYST currently gives access to the action property of a message to active services. But this is only temporary and
**will** change in future releases. The action will be masked and the only readable properties will be those that can
be read under normal, realistic situations.

In CYST Request and Responses are atomic. This means that either one can cover a number of network flows over an
arbitrary time span. To capture the statistical properties of these exchanges, each message contains a
:class:`cyst.api.logic.metadata.Metadata`. And these metadata are supplied by metadata providers.

A metadata provider, much like a behavioral model, can exist as a separate package that gets registered into the system.
As usual, copy it from the templates repository, or follow the code here.

.. tabs::

    .. tab:: Windows CMD

        Clone the templates repository:

        .. code-block:: console

            ...> git clone https://<username>:<token>@gitlab.ics.muni.cz/cyst/cyst-templates.git

        Make a copy of the template:

        .. code-block:: console

            ...> mkdir my_awesome_metadata_provider
            ...> xcopy ...\cyst-templates\model\ my_awesome_metadata_provider\ /E/Y

    .. tab:: Linux shell

        Clone the templates repository:

        .. code-block:: console

            ...$ git clone https://<username>:<token>@gitlab.ics.muni.cz/cyst/cyst-templates.git

        Make a copy of the template:

        .. code-block:: console

            ...$ mkdir my_awesome_metadata_provider
            ...$ cp -r .../cyst-templates/model/ my_awesome_metadata_provider/

We begin with imports.

        .. code-block:: python

                from cyst.api.environment.message import Message
                from cyst.api.environment.metadata_provider import MetadataProvider, MetadataProviderDescription
                from cyst.api.logic.action import Action
                from cyst.api.logic.metadata import Metadata, Flow, FlowDirection, TCPFlags, Protocol

As you can see, the number of imports is much smaller than for behavioral models. The reason is simple - metadata
providers can have only very small and indirect influence over the environment.

Their structure is similarly simple (renamed from template):

        .. code-block:: python

                class AwesomeMetadataProvider(MetadataProvider):

                        def get_metadata(self, action: Action, message: Message) -> Metadata:
                                pass

And their registration mechanism is mostly identical to behavioral models:

        .. code-block:: python

                def create_awesome_mp() -> MetadataProvider:
                    mp = AwesomeMetadataProvider()
                    return mp


                metadata_provider_description = MetadataProviderDescription(
                    namespace="awesome",
                    description="Metadata provider for awesome action namespace",
                    creation_fn=create_cam_mp
                )

As you can see, metadata providers are also bound to a certain namespace. The namespace, however, has a bit different
semantics this time. Unlike behavioral models, multiple metadata providers can act one one message. The namespace is
thus understood as a prefix and there can be multiple providers with the same namespace. If you are wondering why would
you want to have such thing then consider different providers supplying different information. One providing flow data,
one packet-level information, one aggregate statistics, etc.

But let's get back to the implementation. Here is an example of how to assign flow metadata to a scan (sorry, no
statistical properties for punches).

    .. code-block:: python
        :linenos:

        def get_metadata(self, action: Action, message: Message) -> Metadata:
            result = Metadata()
            if action.id == "awesome::tcp_syn_scan":
                if message.type == MessageType.REQUEST:
                    direction = FlowDirection.REQUEST
                    flags = TCPFlags.S | TCPFlags.F
                else:
                    direction = FlowDirection.RESPONSE
                    flags = TCPFlags.S | TCPFlags.A

                duration = randint(1, 5)  # Because, why not
                packet_count = randint(24, 36)

                f = Flow(
                    id=str(message.id),  # Just ignore this one please for now
                    direction=direction,
                    packet_count=packet_count,
                    duration=duration,
                    flags=flags,
                    protocol=Protocol.TCP
                )
                result.flows = [f]

            return result

As you can see, the whole point of the provider in this case is to create network flow information (14-21), according
to the action type (3), message direction (4-9), with just a hint of random tomfoolery (11, 12).

A word of warning - always make decisions based on the action provided in the function parameters, not on the action in
the input message. As you will see later, it can get a bit hairy and from this point of view, you will not be able to
tell which action is the correct one.

As we mentioned earlier, Requests and Responses are atomic, so the metadata is always assigned to those in full. This
means that metadata providers are invoked on each ``send_message`` call. Therefore, you can alter the metadata in case
of success, failure, or error, or any other message properties.

Behavioral models - contd.
==========================
Armed with the knowledge of the metadata processing, it is now time to move to the last missing concept of behavioral
models - action components.

Each action can consist of an arbitrary number of subactions that are of the type ``ActionType.COMPONENT``. These
components represent a logical subdivision of an action. Unlike action flows consisting of action and their temporal
dependencies, action components are static, provide no actionable semantics, and are not executed on their own. However,
they are still a full fledged actions.

Let's look at the code to make a sense of it...

We begin by defining a TCP scan action and TCP flow components:

    .. code-block:: python
        :linenos:

        self._action_store.add(ActionDescription(
            id="awesome:component:tcp_flow",
            type=ActionType.COMPONENT,
            description="A component message representing a single TCP flow",
            parameters=[
                ActionParameter(type=ActionParameterType.NONE, name="direction",
                                domain=configuration.action.create_action_parameter_domain_options("forward", ["forward", "reverse"])),
                ActionParameter(type=ActionParameterType.NONE, name="byte_size",
                                domain=configuration.action.create_action_parameter_domain_range(24, min=1, max=4096))
            ]
        ))

        self._action_store.add(ActionDescription(
            id="awesome:direct:tcp_scan_host",
            type=ActionType.DIRECT,
            description="Scan of a single host",
            parameters=[]
        ))

As you can see, these are just two ordinary action definitions and there is no apparent connection between them. This
connection is realized through the ``action_components()`` function.

    .. code-block:: python
        :linenos:

        def action_components(self, message: Union[Request, Response]) -> List[Action]:

            components = []
            if message.action.id == "awesome:direct:scan_host":
                if message.type == MessageType.REQUEST:
                    forward_flow = self._action_store.get("awesome:component:tcp_flow")
                    forward_flow.parameters["direction"].value = "forward"
                    forward_flow.parameters["byte_size"].value = 24

                    reverse_flow = self._action_store.get("awesome:component:tcp_flow")
                    reverse_flow.parameters["direction"].value = "reverse"
                    reverse_flow.parameters["byte_size"].value = 10

                    components.extend([forward_flow, reverse_flow])
                if message.type == MessageType.RESPONSE:
                    if message.status.value == StatusValue.SUCCESS:
                        forward_flow = self._action_store.get("awesome:component:tcp_flow")
                        forward_flow.parameters["direction"].value = "forward"
                        forward_flow.parameters["byte_size"].value = 36

                        reverse_flow = self._action_store.get("awesome:component:tcp_flow")
                        reverse_flow.parameters["direction"].value = "reverse"
                        reverse_flow.parameters["byte_size"].value = 12

                        components.extend([forward_flow, reverse_flow])
                    else:
                        forward_flow = self._action_store.get("awesome:component:tcp_flow")
                        forward_flow.parameters["direction"].value = "forward"
                        forward_flow.parameters["byte_size"].value = 8

                        reverse_flow = self._action_store.get("awesome:component:tcp_flow")
                        reverse_flow.parameters["direction"].value = "reverse"
                        reverse_flow.parameters["byte_size"].value = 4

                        components.extend([forward_flow, reverse_flow])

            return components

Just like with the metadata, components are assigned to Requests and Responses on ``send_message()`` call. This enables
you to set the components according to what is really going on.

You may question, why would you want to do it this way and what would be the advantages. If you take a closer look at
the code, you may notice that it is very similar to the example we were using for the metadata providers. This is no
coincidence. The component mechanism is done this way to enable adding finer structure to the actions, while getting the
data out of it "for free". While currently not implemented, CYST will provide standardized action components that you
can assign to your actions and will output correct flow records. That is, you can focus on creating behavioral models
only and let the in-built metadata provider do the job for you.

It is worth noting that component actions can also have components of their own. So, for example, TCP flows can also be
subdivided into packet streams.

Execution environments
======================
While you may have thought about CYST as only a cybersecurity simulation environment, it enables a smooth transition
between simulation and emulation by means of different environments adhering to the same APIs. This means that for
agents, the facade remains the same, whether they are in a simulation or in a real network. To make this work smoothly,
however, some additional effort must be done on the side of behavioral models.

**Warning!** Standardized execution environments are very much a work in progress, so much can change in the meantime.
The only non-simulation environment we are considering now is the Cryton-backed environment
(https://www.muni.cz/go/cryton).

The execution environments are using the same APIs, but when and how actions are executed can vary. In the case of
emulation, there are no messages traversing an emulated infrastructure. A message is used just as a means to express an
intent to the environment. So, action effects happen at the instant of ``send_message()`` call, just like action flows
in case of the simulation.

Code snippets and other will follow soon. But if you are building your own execution environment, know that there is a
parameter in action description that was not utilized yet. The full description of actions then look like this:

    .. code-block:: python
        :linenos:

        self._action_store.add(ActionDescription(
            id="awesome:tcp_scan_net",
            type=ActionType.COMPOSITE,
            description="Scan of a network subnet",
            parameters=[
                ActionParameter(type=ActionParameterType.NONE, name="net", domain=configuration.action.create_action_parameter_domain_any())
            ],
            environment=ExecutionEnvironment(ExecutionEnvironmentType.SIMULATION, "CYST")
        )

        self._action_store.add(ActionDescription(
            id="awesome:tcp_scan_net",
            type=ActionType.DIRECT,
            description="Scan of a network subnet",
            parameters=[
                ActionParameter(type=ActionParameterType.NONE, name="net", domain=configuration.action.create_action_parameter_domain_any())
            ],
            environment=ExecutionEnvironment(ExecutionEnvironmentType.EMULATION, "CRYTON")
        )

The environment parameter is used to distinguish, which actions can be executed in which environment. It is important
that the uniqueness of action id is only considered within an execution environment, because in different environments
the actions can be executed very differently. In the provided example, the subnet scanning in simulation is done as a
composite action of many singular host scans realized through 1:1 message exchanges. This is a limitation of CYST
simulation model. However, in emulation case, this can be done as a single action that is under the hood calling an
``nmap`` with the subnet parameter. If you implemented the scanning in the emulation the same way as in the simulation,
you would end with repeated invocation of the ``nmap`` process and the whole ordeal would take much much more real time.

Active services (actors)
========================
Active services are the actors of the simulation. They effect the events in the simulation by means of sending and
receiving the messages with other actors and the environment.

Currently, the services exist within the simulation in two places - as traffic processors, which inspect and act upon
any messages that arrive to the node which they reside on, and as ordinary services, which are specific targets of
messages. Here are some examples:

    - traffic processors:
        IDS, IPS, firewalls, antiviruses, port knocking mechanisms, honeypots, etc.
    - ordinary services:
        attacking/defending/user simulating agents

This difference, however, does not affect the code of the service much, and so the example service which will be
presented in this section can be used in both cases.

Each service must start with a minimal set of imports. Currently we prefer explicit imports, although it may change in
the future:

    .. code-block:: python

        from abc import ABC, abstractmethod
        from typing import Tuple, Optional, Dict, Any, Union

        from cyst.api.logic.action import Action
        from cyst.api.logic.access import Authorization, AuthenticationToken
        from cyst.api.environment.environment import EnvironmentMessaging
        from cyst.api.environment.message import Request, Response, MessageType, Message
        from cyst.api.environment.resources import EnvironmentResources
        from cyst.api.network.session import Session
        from cyst.api.host.service import ActiveService, ActiveServiceDescription, Service

You can either copy this verbatim, or use the imports provided by the service template.

After that, you need to create your own service (let's call it AwesomeService). It will not do anything, aside from
existing.

    .. code-block:: python

        class AwesomeService(ActiveService):

            def __init__(self, env: EnvironmentMessaging = None, res: EnvironmentResources = None, args: Optional[Dict[str, Any]] = None) -> None:
                pass

            def run(self) -> None:
                pass

            def process_message(self, message: Message) -> Tuple[bool, int]:
                pass

Once you have this service stub, you need to prepare the entry point, which is a structure that describes the service
and provides a factory function. Here is one way to do it.

    .. code-block:: python

        def create_awesome_service(msg: EnvironmentMessaging, res: EnvironmentResources, args: Optional[Dict[str, Any]]) -> ActiveService:
            service = AwesomeService(msg, res, args)
            return service


        service_description = ActiveServiceDescription(
            "awesome_service",
            "A service that is being awesome on its own.",
            create_awesome_service
        )

Provided you create an entry point in the setup.py like this, you will be able to instantiate the service in the
environment, after you execute ``pip install -e .``.

    .. code-block:: python

            entry_points={
                'cyst.services': [
                    'awesome_service=cyst_services.awesome_service.main:service_description'
                ]
            },

But as has been said, aside from existing, this service would not be able to do anything, so we will add a bit of
functionality to it. First, we begin with configuration. Let's say that the service enables setting the level of
awesomeness during the creation. The configuration would look like this:

    .. code-block:: python

        active_services=[
            ActiveServiceConfig(
                type="awesome_service",
                name="My first service",
                owner="owner",
                access_level=AccessLevel.LIMITED,
                configuration={"level":"super awesome"}
            )
        ],

The configuration is going to be accessed from the constructor. With it we will also store the access to the vital
interfaces - :class:`cyst.api.environment.messaging.EnvironmentMessaging` for communication with the service's exterior
and :class:`cyst.api.environment.resources.EnvironmentResources` for gaining access to behavioral models, exploits, etc.

    .. code-block:: python

        def __init__(self, env: EnvironmentMessaging = None, res: EnvironmentResources = None, args: Optional[Dict[str, Any]] = None) -> None:
            self._env = env
            self._res = res
            self._level = args["level"]

The next step is to add some activity of the service after it is run. You don't necessarily have to have it do anything,
however, the simulation usually ends when there are no actions on the stack. Therefore, you need at least one service in
a simulation scenario that does something after being run.

We assume that the previously developed awesome model is registered into the simulation framework, and so we adopt the
awesome:punch action and deliver a weak one to a target that, for the sake of the example, we assume exists.

    .. code-block:: python

        def run(self) -> None:

            action = self._res.action_store.get("awesome:punch")  # A weak punch is a default one
            request = self._env.create_request("192.168.0.2", "punchable_service", action)
            self._env.send_message(request)

The code in the run will be executed at time 0 when the simulation starts. If the time 0 is not the right one for you,
then you can either use the delay parameter of send_message(), or you can use the timeout() call of the
:class:`cyst.api.environment.Clock` interface that is accessible through the
:class:`cyst.api.environment.resources.EnvironmentResources` interface.

One way or another, you have sent your first punch. But if you checked the code of the model, you would know that a weak
punch will inevitably result in a failure. How will this information get to the service? Via the process_message()
function, where the service has to implement response processing (and also request processing if there is the
possibility of multiple active service communicating between each other). Let's do it.

    .. code-block:: python

        def process_message(self, message: Message) -> Tuple[bool, int]:
            # In the real code, you would have different processing for requests and responses, and error checks and stuff...
            response = message.cast_to(Response)
            if response.status.value == StatusValue.FAILURE:
                # We failed, let's punch harder
                action = self._res.action_store.get("awesome:punch")
                action.parameters["punch_strength"].value = "super strong"
                request = self._env.create_request("192.168.0.2", "punchable_service", action)
                self._env.send_message(request)
                return True, 1  # This just indicates that the processing went ok and that it took 1 virtual time unit
            else:
                # We succeeded, let's call it a day
                return True, 1

This implementation will repeat the action that was chosen in the run call, but this time it sets the parameter for
stronger punch to which it will finally receives a SUCCESS. After that, it will not add any new message to the stack
and the simulation will stop (assuming there is only this service running).

This is basically all there is to creation of active services. Everything revolves around sending messages with actions,
processing the responses and acting upon it. The amount of things the service can do is relatively limited
interface-wise and the complexity arise from the size of action spaces (behavioral models) and from the message
metadata. A good starting point is the following interfaces:

    - :class:`cyst.api.environment.message.Message`
    - :class:`cyst.api.environment.resources.EnvironmentResources`
    - :class:`cyst.api.environment.messaging.EnvironmentMessaging`

Here we append the complete code:

    .. code-block:: python

        from abc import ABC, abstractmethod
        from typing import Tuple, Optional, Dict, Any, Union

        from cyst.api.logic.action import Action
        from cyst.api.logic.access import Authorization, AuthenticationToken
        from cyst.api.environment.environment import EnvironmentMessaging
        from cyst.api.environment.message import Request, Response, MessageType, Message
        from cyst.api.environment.resources import EnvironmentResources
        from cyst.api.network.session import Session
        from cyst.api.host.service import ActiveService, ActiveServiceDescription, Service

        class AwesomeService(ActiveService):

            def __init__(self, env: EnvironmentMessaging = None, res: EnvironmentResources = None, args: Optional[Dict[str, Any]] = None) -> None:
                self._env = env
                self._res = res
                self._level = args["level"]

            def run(self) -> None:
                action = self._res.action_store.get("awesome:punch")  # A weak punch is a default one
                request = self._env.create_request("192.168.0.2", "punchable_service", action)
                self._env.send_message(request)

            def process_message(self, message: Message) -> Tuple[bool, int]:
                # In the real code, you would have different processing for requests and responses, and error checks and stuff...
                response = message.cast_to(Response)
                if response.status.value == StatusValue.FAILURE:
                    # We failed, let's punch harder
                    action = self._res.action_store.get("awesome:punch")
                    action.parameters["punch_strength"] = "super strong"
                    request = self._env.create_request("192.168.0.2", "punchable_service", action)
                    self._env.send_message(request)
                    return True, 1  # This just indicates that the processing went ok and that it took 1 virtual time unit
                else:
                    # We succeeded, let's call it a day
                    return True, 1

        def create_awesome_service(msg: EnvironmentMessaging, res: EnvironmentResources, args: Optional[Dict[str, Any]]) -> ActiveService:
            actor = AwesomeService(msg, res, args)
            return actor

        service_description = ActiveServiceDescription(
            "awesome_service",
            "A service that is being awesome on its own.",
            create_awesome_service
        )
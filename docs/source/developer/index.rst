-------------------------
Developer's documentation
-------------------------

Hacking on existing packages
============================
The CYST framework is developed and distributed as a set of loosely-dependent packages (with the exception of cyst-core).
Thanks to the magic of pip, this is much less painful than it may seem, especially if you find yourself in a
situation when you need to do a parallel development of a subset of packages.

In this guide, we will illustrate the needed steps on the example of developing the AIF behavioral model, which at
some point will necessitate changes to the cyst-core. The example of an existing package with model is chosen to ignore
the stuff needed to set up the package itself. This is covered later in the guide.

Getting the AIF package and setting it all up
---------------------------------------------

.. tabs::

    .. tab:: Windows CMD

        Requirements: Python 3.9+ and pip installed.

        Clone the AIF package

        .. code-block:: console

            ...> git clone https://<username>:<token>@gitlab.ics.muni.cz/cyst/cyst-models-aif.git

        Prepare and activate the virtual environment

        .. code-block:: console

            ...> cd cyst-models-aif
            ...\cyst-models-aif> python -m venv venv
            ...\cyst-models-aif> venv\Scripts\activate.bat

        Set up all the requirements. The following command will attempt to fetch the packages from both the official
        and test PYPI repositories and will also install cyst-models-aif as an editable package. This is necessary
        to enable correct loading of it by the cyst-core.

        .. code-block:: console

            (venv) ...\cyst-models-aif> pip install -i https://test.pypi.org/simple/ --extra-index-url=https://pypi.org/simple -e .

        Now, test if everything went smooth and the package is ready for hacking.

        .. code-block:: console

            (venv) ...\cyst-models-aif> cd tests
            (venv) ...\cyst-models-aif\tests> python -m unittest

        If you see something like this, everything is ready and correctly working.

        .. code-block:: console

            ----------------------------------------------------------------------
            Ran 9 tests in 0.749s

            OK


    .. tab:: Linux shell

        Requirements: Python 3.9+ and pip installed.

        Clone the AIF package

        .. code-block:: console

            ...$ git clone https://<username>:<token>@gitlab.ics.muni.cz/cyst/cyst-models-aif.git

        Prepare and activate the virtual environment

        .. code-block:: console

            ...$ cd cyst-models-aif
            .../cyst-models-aif$ python3 -m venv venv
            .../cyst-models-aif$ source venv/bin/activate

        Set up all the requirements. The following command will attempt to fetch the packages from both the official
        and test PYPI repositories and will also install cyst-models-aif as an editable package. This is necessary
        to enable correct loading of it by the cyst-core.

        .. code-block:: console

            (venv) .../cyst-models-aif$ pip3 install -i https://test.pypi.org/simple/ --extra-index-url=https://pypi.org/simple -e .

        Now, test if everything went smooth and the package is ready for hacking.

        .. code-block:: console

            (venv) .../cyst-models-aif$ cd tests
            (venv) .../cyst-models-aif/tests$ python3 -m unittest

        If you see something like this, everything is ready and correctly working.

        .. code-block:: console

            ----------------------------------------------------------------------
            Ran 9 tests in 0.749s

            OK

    .. tab:: PyCharm

        This is using the PyCharm


Using the package
-----------------

In the previous section the package was installed and the tests passed, so it must be working and you can start using it
right away? Well, surprisingly yes. Thanks to installing the package in pip development mode, any change you make to the
codebase is reflected in the virtual environment.

To run the code, you then either extend the test scripts and follow in their steps, or you create a new one. You don't
need to import the AIF package in any way. This is being done automagically and importing and running the Environment
from cyst-core is enough.

Shit! My change requires hacking on the core as well
----------------------------------------------------

The simulation framework is in a constant state of development, so its simulation model is best considered a
moving target unless the version 1.x is released and even then who knows. It can easily happen that during a development
of your package you are forced to modify or extend the cyst-core to support the package requirements. The following
guide shows how to hack on the core as well as your package in parallel. This approach is also applicable to parallel
development of any number of packages, although there should ideally be no transitive dependencies between the packages
and all should only depend on the cyst-core.

The following works only if you set up the packages as written earlier.

.. tabs::

    .. tab:: Windows CMD

        Clone the cyst-core package

        .. code-block:: console

            ...> git clone https://<username>:<token>@gitlab.ics.muni.cz/cyst/cyst-core.git

        Activate the virtual environment (skip if active)

        .. code-block:: console

            ...> cd cyst-models-aif
            ...\cyst-models-aif> venv\Scripts\activate.bat

        Install and activate cyst-core in development mode

        .. code-block:: console

            (venv) ...\cyst-models-aif> cd ..\cyst-core
            (venv) ...\cyst-core> pip install -i https://test.pypi.org/simple/ --extra-index-url=https://pypi.org/simple -e .

        Now, test if everything went smooth and the package is ready for hacking.

        .. code-block:: console

            (venv) ...\cyst-core> cd tests
            (venv) ...\cyst-core\tests> python -m unittest

        If you see something like this, everything is ready and correctly working. You can now start doing changes in
        both packages and they will be reflected in each.

    .. tab:: Linux shell

        Clone the cyst-core package

        .. code-block:: console

            ...> git clone https://<username>:<token>@gitlab.ics.muni.cz/cyst/cyst-core.git

        Activate the virtual environment (skip if active)

        .. code-block:: console

            ...$ cd cyst-models-aif
            .../cyst-models-aif$ source venv/bin/activate

        Install and activate cyst-core in development mode

        .. code-block:: console

            (venv) .../cyst-models-aif$ cd ../cyst-core
            (venv) .../cyst-core$ pip install -i https://test.pypi.org/simple/ --extra-index-url=https://pypi.org/simple -e .

        Now, test if everything went smooth and the package is ready for hacking.

        .. code-block:: console

            (venv) .../cyst-core$ cd tests
            (venv) .../cyst-core/tests$ python -m unittest

        If you see something like this, everything is ready and correctly working. You can now start doing changes in
        both packages and they will be reflected in each.

        .. code-block:: console

            ----------------------------------------------------------------------
            Ran 26 tests in 0.786s

            OK

        .. code-block:: console

            ----------------------------------------------------------------------
            Ran 26 tests in 0.786s

            OK

    .. tab:: PyCharm

        This is using the PyCharm


Creating a new package
======================

If you have decided to create your own package, the best way is to make a copy of a template that is available at
project's gitlab.

.. tabs::

    .. tab:: Windows CMD

        Clone the templates repository

        .. code-block:: console

            ...> git clone https://<username>:<token>@gitlab.ics.muni.cz/cyst/cyst-templates.git

        Make a copy of the template (in this example, we create a new model from scratch).

        .. code-block:: console

            ...> mkdir my_awesome_model
            ...> xcopy cyst-templates\model\ my_awesome_model\ /E/Y
            ...> cd my_awesome_model

    .. tab:: Linux shell

        Clone the templates repository

        .. code-block:: console

            ...$ git clone https://<username>:<token>@gitlab.ics.muni.cz/cyst/cyst-templates.git

        Make a copy of the template (in this example, we create a new model from scratch).

        .. code-block:: console

            ...$ mkdir my_awesome_model
            ...$ cp -r cyst-templates/model/ my_awesome_model/
            ...$ cd my_awesome_model


Package structure
-----------------

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
                        'cyst=cyst_models.cyst.main:action_interpreter_description',
                        'meta=cyst_models.meta.main:action_interpreter_description'
                    ],
                    'cyst.services': [
                        'scripted_actor=cyst_services.scripted_actor.main:service_description'
                    ]
                },

        This configuration specifies that the cyst-core provides two models - cyst and meta, and one active service -
        scripted_actor. Their respective entry points are located at python.path.to.module:instance_name.

Internal logic - models
-----------------------

Models are used to evaluate the impact of actions on the environment. They implement the behavioral model in form of
actions taxonomy, as well as the interpretation of their semantics. This section will guide you through the creation of
a minimal model and gives the explanation of particular parts.

Each model must start with a minimal set of imports. Currently we prefer explicit imports, although it may change in the
future:

    .. code-block:: python

        from typing import Tuple, Callable

        from cyst.api.environment.configuration import EnvironmentConfiguration
        from cyst.api.environment.interpreter import ActionInterpreter, ActionInterpreterDescription
        from cyst.api.environment.message import Request, Response, Status, StatusOrigin, StatusValue
        from cyst.api.environment.messaging import EnvironmentMessaging
        from cyst.api.environment.policy import EnvironmentPolicy
        from cyst.api.environment.resources import EnvironmentResources
        from cyst.api.logic.action import ActionDescription, ActionToken
        from cyst.api.network.node import Node

You can either copy this verbatim, or use the imports provided by the model template.

After that, you need to create your own model (let's call it AwesomeModel). This is the minimal code, which does not
provide any action definitions.

    .. code-block:: python

        class AwesomeModel(ActionInterpreter):
            def __init__(self, configuration: EnvironmentConfiguration, resources: EnvironmentResources,
                         policy: EnvironmentPolicy, messaging: EnvironmentMessaging) -> None:
                pass

            def evaluate(self, message: Request, node: Node) -> Tuple[int, Response]:
                pass


Once you have this model stub, you need to prepare the entry point, which is a structure that describes the model and
provides a factory function. Here is one way to do it.

    .. code-block:: python

        def create_awesome_model(configuration: EnvironmentConfiguration, resources: EnvironmentResources,
                                 policy: EnvironmentPolicy, messaging: EnvironmentMessaging) -> ActionInterpreter:
            model = AwesomeModel(configuration, resources, policy, messaging)
            return model


        action_interpreter_description = ActionInterpreterDescription(
            "awesome",
            "A behavioral model that is without a doubt - awesome",
            create_awesome_model
        )

Now, the code so far does nothing and is probably screaming because of the passes in the AwesomeModel class' functions.
First of all, you should make copies of the constructor parameters. You will need them later.

    .. code-block:: python

        def __init__(self, configuration: EnvironmentConfiguration, resources: EnvironmentResources,
                 policy: EnvironmentPolicy, messaging: EnvironmentMessaging) -> None:

            self._configuration = configuration
            self._action_store = resources.action_store
            self._exploit_store = resources.exploit_store
            self._policy = policy
            self._messaging = messaging

After that, you will start adding the actions, or at least their specifications. Their semantics will be implemented
later. The actions are added through the :class:`cyst.api.environment.stores.ActionStore`, which is accessed through
the :class:`cyst.api.environment.resources.EnvironmentResources` interface.

In this example we will add one parametrized action, which will represent a virtual punch of awesomeness. For the
details of action description and parameter domains, see their documentation starting from here:
:class:`cyst.api.logic.action.ActionDescription`.

    .. code-block:: python

        from cyst.api.logic.action import ActionParameterType, ActionParameterDomain, ActionParameterDomainType, ActionParameter

        def __init__(self, configuration: EnvironmentConfiguration, resources: EnvironmentResources,
                 policy: EnvironmentPolicy, messaging: EnvironmentMessaging) -> None:

            # ...

            self._action_store.add(ActionDescription("awesome:punch",
                                                     "Deliver a punch of pre-defined awesomeness",
                                                     [ActionParameter(ActionParameterType.NONE, "punch_strength",
                                                                      configuration.action.create_action_parameter_domain_options("weak", ["weak", "super strong"]))],
                                                     []))  # Tokens are currently ignored, wait for research update

To recap, now you have your own behavioral model that defines one action, which is now accessible to any active service
in the simulation. But that action does not have any meaning and if a service were to use it, it would fail. That's why
we will now give the action its semantics by means of the evaluation function.

The easiest way is to just copy the dispatch structure from the template. It takes care of wrong action names, such as
awesome:pumch and enables you to easily add new functions to handle new actions. No black magic, only convenience.

    .. code-block:: python

        def evaluate(self, message: Request, node: Node) -> Tuple[int, Response]:
            if not message.action:
                raise ValueError("Action not provided")

            action_name = "_".join(message.action.fragments)
            fn: Callable[[Request, Node], Tuple[int, Response]] = getattr(self, "process_" + action_name, self.process_default)
            return fn(message, node)

        def process_awesome_punch(self, message: Request, node: Node) -> Tuple[int, Response]:
            pass

As you can see, for each new added action of the form awesome:item1:item2 you need to add function
process_awesome_item1_item2().

To make this example as easy ass possible, we will make the process_awesome_punch function to return success or
failure depending on the punch strength. These returns are communicated to the system by means of messages that are
created by the implemented model in response to requests.

    .. code-block:: python

        def process_awesome_punch(self, message: Request, node: Node) -> Tuple[int, Response]:
            # No error checking. Don't do this at home!
            strength = message.action.parameters["punch_strength"].value
            if strength == weak:
                return 1, self._messaging.create_response(message, status=Status(StatusOrigin.NODE, StatusValue.FAILURE), content="That's a weak punch, bro!")
            else:
                return 1, self._messaging.create_response(message, status=Status(StatusOrigin.NODE, StatusValue.SUCCESS), content="That's a good punch, bro!")

And that's it. You have just given the semantics to the action.

There is however much more that you can do within the model:

    - environment changes:
        The :class:`cyst.api.environment.configuration.EnvironmentConfiguration` enables you to make changes to the
        entire simulation infrastructure from within the model.
    - authentication and authorization:
        The :class:`cyst.api.environment.policy.EnvironmentPolicy` enables you to evaluate and process complex
        authentication and authorization schemes.
    - exploit evaluation:
        The :class:`cyst.api.environment.stores.ExploitStore` enables you to evaluate impact of exploits on the services
        running in the infrastructure.

Here we append the complete code.

    .. code-block:: python

        from typing import Tuple, Callable

        from cyst.api.environment.configuration import EnvironmentConfiguration
        from cyst.api.environment.interpreter import ActionInterpreter, ActionInterpreterDescription
        from cyst.api.environment.message import Request, Response, Status, StatusOrigin, StatusValue
        from cyst.api.environment.messaging import EnvironmentMessaging
        from cyst.api.environment.policy import EnvironmentPolicy
        from cyst.api.environment.resources import EnvironmentResources
        from cyst.api.logic.action import ActionDescription, ActionToken, ActionParameterType, ActionParameterDomain, ActionParameterDomainType, ActionParameter
        from cyst.api.network.node import Node

        class AwesomeModel(ActionInterpreter):
            def __init__(self, configuration: EnvironmentConfiguration, resources: EnvironmentResources,
                         policy: EnvironmentPolicy, messaging: EnvironmentMessaging) -> None:
                self._configuration = configuration
                self._action_store = resources.action_store
                self._exploit_store = resources.exploit_store
                self._policy = policy
                self._messaging = messaging

                self._action_store.add(ActionDescription("awesome:punch",
                                                         "Deliver a punch of pre-defined awesomeness",
                                                         [ActionParameter(ActionParameterType.NONE, "punch_strength",
                                                                          configuration.action.create_action_parameter_domain_options("weak", ["weak", "super strong"]))],
                                                         []))  # Tokens are currently ignored, wait for research update

            def evaluate(self, message: Request, node: Node) -> Tuple[int, Response]:
                if not message.action:
                    raise ValueError("Action not provided")

                action_name = "_".join(message.action.fragments)
                fn: Callable[[Request, Node], Tuple[int, Response]] = getattr(self, "process_" + action_name, self.process_default)
                return fn(message, node)

            def process_awesome_punch(self, message: Request, node: Node) -> Tuple[int, Response]:
                # No error checking. Don't do this at home!
                strength = message.action.parameters["punch_strength"].value
                if strength == weak:
                    return 1, self._messaging.create_response(message, status=Status(StatusOrigin.NODE, StatusValue.FAILURE), content="That's a weak punch, bro!")
                else:
                    return 1, self._messaging.create_response(message, status=Status(StatusOrigin.NODE, StatusValue.SUCCESS), content="That's a good punch, bro!")

        def create_awesome_model(configuration: EnvironmentConfiguration, resources: EnvironmentResources,
                                 policy: EnvironmentPolicy, messaging: EnvironmentMessaging) -> ActionInterpreter:
            model = AwesomeModel(configuration, resources, policy, messaging)
            return model


        action_interpreter_description = ActionInterpreterDescription(
            "awesome",
            "A behavioral model that is without a doubt - awesome",
            create_awesome_model
        )


Internal logic - services
-------------------------

Services, or rather active services, are the actors of the simulation. They effect the events in the simulation by means
of sending and receiving the messages with other actors and the environment.

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
            actor = AwesomeService(msg, res, args)
            return actor


        service_description = ActiveServiceDescription(
            "awesome_service",
            "A service that is being awesome on its own.",
            create_awesome_service
        )

Provided you create an entry point in the setup.py like this, you will be able to instantiate the service in the
environment.

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
                action.parameters["punch_strength"] = "super strong"
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

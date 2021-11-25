import unittest
import statistics
from netaddr import *

import unittest

from netaddr import IPAddress, IPNetwork

from cyst.api.logic.access import AccessLevel
from cyst.api.logic.exploit import ExploitCategory, ExploitParameter, ExploitParameterType, ExploitLocality
from cyst.api.environment.environment import Environment
from cyst.api.environment.message import StatusOrigin, StatusValue, Status
from cyst.api.environment.configuration import ServiceParameter
from cyst.api.network.elements import Route
from cyst.api.network.firewall import Firewall, FirewallPolicy, FirewallRule, FirewallChainType

from cyst.services.scripted_attacker.main import ScriptedAttackerControl
from cyst.services.random_attacker.main import RandomAttackerControl, ReductionStrategy
from cyst.services.ucb_attacker.main import ModularAttackerControl

# The total runtime for evaluation can easily exceed a few hours, so this is the way to selectively turn them on and
# off without the need to scroll all the way down
enabled_tests = {
    "test_0000_cto_scenario_omniscient": False,
    "test_0001_cto_scenario_random": False,
    "test_0002_cto_scenario_modular": False,
    "test_0003_vpn_scenario_omniscient": False,
    "test_0004_vpn_scenario_random": False,
    "test_0005_vpn_scenario_modular": False,
    "test_0006_employee_scenario_omniscient": False,
    "test_0007_employee_scenario_random": False,
    "test_0008_employee_scenario_modular": True,
    "test_0009_simple_scenario_random_strategies": False
}

# Global number of runs for each test
number_of_runs = 1


class BronzeButlerScenarios(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls._env = Environment.create()

        # Function aliases to make it more readable
        create_node = cls._env.configuration.node.create_node
        create_router = cls._env.configuration.node.create_router
        create_active_service = cls._env.configuration.service.create_active_service
        create_passive_service = cls._env.configuration.service.create_passive_service
        add_service = cls._env.configuration.node.add_service
        set_service_parameter = cls._env.configuration.service.set_service_parameter
        create_interface = cls._env.configuration.node.create_interface
        add_node = cls._env.configuration.network.add_node
        add_connection = cls._env.configuration.network.add_connection
        add_route = cls._env.configuration.node.add_route
        add_interface = cls._env.configuration.node.add_interface
        create_session = cls._env.configuration.network.create_session
        public_data = cls._env.configuration.service.public_data
        private_data = cls._env.configuration.service.private_data
        sessions = cls._env.configuration.service.sessions
        create_data = cls._env.configuration.service.create_data
        create_authorization = cls._env.policy.create_authorization
        add_authorization = cls._env.policy.add_authorization
        private_authorizations = cls._env.configuration.service.private_authorizations
        add_exploit = cls._env.configuration.exploit.add_exploit
        create_exploit = cls._env.configuration.exploit.create_exploit
        create_vulnerable_service = cls._env.configuration.exploit.create_vulnerable_service
        create_exploit_parameter = cls._env.configuration.exploit.create_exploit_parameter
        set_shell = cls._env.configuration.node.set_shell
        add_routing_rule = cls._env.configuration.node.add_routing_rule

        cls._action_list = cls._env.resources.action_store.get_prefixed("aif")
        cls._actions = {}
        for action in cls._action_list:
            cls._actions[action.id] = action

        # List of nodes in the infrastructure:
        # -- DMZ --
        # Email server
        # Web server
        # VPN server
        # -- SRV --
        # Domain controller
        # DB server
        # API server
        # -- PC --
        # Employee
        # CTO
        # -- Routers --
        # Outside network - PerimeterRouter - DMZ - InternalRouter - SRV/PC

        # --- Email server ---------------------------------------------------------------------------------------------
        email_srv = create_node("email_srv")

        postfix = create_passive_service("postfix", owner="mail", version="3.5.0", local=False)
        bash = create_passive_service("bash", owner="bash", version="5.0.0", local=True, service_access_level=AccessLevel.LIMITED)
        add_service(email_srv, postfix, bash)

        add_node(email_srv)

        # --- Web server -----------------------------------------------------------------------------------------------
        web_srv = create_node("web_srv")

        iis = create_passive_service("iis", owner="Administrator", version="8.5.0")
        remote_desktop = create_passive_service("rdp", owner="Administrator", version="10.0.17666", local=False)
        set_service_parameter(remote_desktop.passive_service, ServiceParameter.ENABLE_SESSION, True)
        powershell = create_passive_service("powershell", owner="iis", version="6.2.2", local=True)
        emp_dc_auth = create_authorization("employee", ["dc_srv"], ["powershell", "rdp"], access_level=AccessLevel.LIMITED)
        add_authorization(emp_dc_auth)
        private_authorizations(powershell.passive_service).append(emp_dc_auth)
        add_service(web_srv, iis, remote_desktop, powershell)
        set_shell(web_srv, powershell)

        add_node(web_srv)

        # --- VPN server -----------------------------------------------------------------------------------------------
        vpn_srv = create_node("vpn_srv")

        skysea = create_passive_service("skysea_client_view", owner="skysea", version="11.221.3", local=False)
        set_service_parameter(skysea.passive_service, ServiceParameter.ENABLE_SESSION, True)
        add_service(vpn_srv, skysea, bash)

        add_node(vpn_srv)

        # --- Domain controller ----------------------------------------------------------------------------------------
        dc_srv = create_node("dc_srv")

        # Technically this is a number of services, but we are only going to allow remote connection and acquisition of
        # golden tickets. So we may as well keep it at two services
        windows_server = create_passive_service("windows_server_2019", owner="Administrator", version="10.0.17666", local=True)

        powershell_dc = create_passive_service("powershell", owner="web_srv", version="6.2.2", local=True)
        add_service(dc_srv, windows_server, remote_desktop, powershell_dc)
        set_shell(dc_srv, powershell_dc)

        add_node(dc_srv)

        # --- DB server ------------------------------------------------------------------------------------------------
        db_srv = create_node("db_srv")

        mssql = create_passive_service("mssql", owner="mssql", version="2019.0.0", local=False)
        add_service(db_srv, mssql)

        # Create secret data
        secret = create_data(None, owner="cto", description="Secret data")
        private_data(mssql.passive_service).append(secret)

        add_node(db_srv)

        # --- API server -----------------------------------------------------------------------------------------------
        api_srv = create_node("api_srv")

        # adding a powershell. This is the same as the one on the web srv, because employee credentials can be extracted
        # from the domain
        add_service(api_srv, skysea, powershell)
        add_node(api_srv)

        # --- Employee PC ----------------------------------------------------------------------------------------------
        emp_pc = create_node("emp_pc")

        # Probably... skysea is only described in japan, so it is hard to guess how the infrastructure is organized
        powershell = create_passive_service("powershell", owner="employee", version="6.2.2", local=True)
        add_service(emp_pc, skysea, powershell)
        set_shell(emp_pc, powershell)

        emp_web_auth = create_authorization("employee", ["web_srv"], ["rdp"], access_level=AccessLevel.LIMITED)
        add_authorization(emp_web_auth)
        private_authorizations(powershell.passive_service).append(emp_web_auth)

        add_node(emp_pc)

        # --- CTO PC ---------------------------------------------------------------------------------------------------
        cto_pc = create_node("cto_pc")

        # Create a far reaching authorization for the CTO (for every service in the infrastructure), which can be
        # extracted from the shell using exploit
        cto_auth = create_authorization("cto", ["*"], ["*"], access_level=AccessLevel.LIMITED)
        add_authorization(cto_auth)

        # Different instance of powershell needed, because this one contains authorizations
        powershell2 = create_passive_service("powershell", owner="cto", version="6.2.2", local=True)
        private_authorizations(powershell2.passive_service).append(cto_auth)
        add_service(cto_pc, powershell2)

        add_node(cto_pc)

        # --- Infrastructure router ------------------------------------------------------------------------------------
        # Infrastructure router connects three networks: DMZ, SRV and PC, each a separate 10.0.0.0/24 network
        # Routing within networks is unrestricted, cross-network routing is explicit
        infrastructure_router = create_router("infrastructure_router", cls._env.messaging)

        # DMZ
        web_srv_port = add_interface(infrastructure_router, create_interface("10.0.0.1", "255.255.255.0"))
        email_srv_port = add_interface(infrastructure_router, create_interface("10.0.0.1", "255.255.255.0"))
        vpn_srv_port = add_interface(infrastructure_router, create_interface("10.0.0.1", "255.255.255.0"))

        add_connection(web_srv, infrastructure_router, target_port_index=web_srv_port)
        add_connection(email_srv, infrastructure_router, target_port_index=email_srv_port)
        add_connection(vpn_srv, infrastructure_router, target_port_index=vpn_srv_port)

        # SRV
        dc_srv_port = add_interface(infrastructure_router, create_interface("10.0.1.1", "255.255.255.0"))
        db_srv_port = add_interface(infrastructure_router, create_interface("10.0.1.1", "255.255.255.0"))
        api_srv_port = add_interface(infrastructure_router, create_interface("10.0.1.1", "255.255.255.0"))

        add_connection(dc_srv, infrastructure_router, target_port_index=dc_srv_port)
        add_connection(db_srv, infrastructure_router, target_port_index=db_srv_port)
        add_connection(api_srv, infrastructure_router, target_port_index=api_srv_port)

        # PC
        cto_pc_port = add_interface(infrastructure_router, create_interface("10.0.2.1", "255.255.255.0"))
        emp_pc_port = add_interface(infrastructure_router, create_interface("10.0.2.1", "255.255.255.0"))

        add_connection(cto_pc, infrastructure_router, target_port_index=cto_pc_port)
        add_connection(emp_pc, infrastructure_router, target_port_index=emp_pc_port)

        # Explicit routes:
        # SRV -> DMZ
        add_routing_rule(infrastructure_router, FirewallRule(IPNetwork("10.0.1.1/24"), IPNetwork("10.0.0.1/24"), "*", FirewallPolicy.ALLOW))
        # DMZ -> SRV (not the wisest thing to do, but we don't want to make the scenario too complicated)
        add_routing_rule(infrastructure_router, FirewallRule(IPNetwork("10.0.0.1/24"), IPNetwork("10.0.1.1/24"), "*", FirewallPolicy.ALLOW))
        # PC -> DMZ
        add_routing_rule(infrastructure_router, FirewallRule(IPNetwork("10.0.2.1/24"), IPNetwork("10.0.0.1/24"), "*", FirewallPolicy.ALLOW))
        # cto_pc -> anywhere
        add_routing_rule(infrastructure_router, FirewallRule(IPNetwork("10.0.2.2/32"), IPNetwork("10.0.0.1/16"), "*", FirewallPolicy.ALLOW))
        # Inside -> Outside
        add_routing_rule(infrastructure_router, FirewallRule(IPNetwork("10.0.0.0/16"), IPNetwork("10.9.0.0/16"), "*", FirewallPolicy.ALLOW))

        add_node(infrastructure_router)

        # --------------------------------------------------------------------------------------------------------------
        # List of nodes on the outside (represented as a 10.9.0.0/16 network):
        # Attacker
        # Partner

        # --- Attacker -------------------------------------------------------------------------------------------------
        attacker_node = create_node("attacker_node")
        attacker_service = create_active_service("scripted_attacker", "attacker", "attacker_omniscient", attacker_node)
        add_service(attacker_node, attacker_service)
        cls._attacker: ScriptedAttackerControl = cls._env.configuration.service.get_service_interface(attacker_service.active_service, ScriptedAttackerControl)

        attacker_service = create_active_service("random_attacker", "attacker", "random_attacker", attacker_node)
        add_service(attacker_node, attacker_service)
        cls._random_attacker: RandomAttackerControl = cls._env.configuration.service.get_service_interface(attacker_service.active_service, RandomAttackerControl)

        attacker_service = create_active_service("ucb_attacker", "attacker", "ucb_attacker", attacker_node)
        add_service(attacker_node, attacker_service)
        cls._ucb_attacker: ModularAttackerControl = cls._env.configuration.service.get_service_interface(attacker_service.active_service, ModularAttackerControl)

        add_node(attacker_node)

        cls._env.control.add_pause_on_response("attacker_node.attacker_omniscient")

        # --- Partner PC ----------------------------------------------------------------------------------------------
        partner_pc = create_node("partner_pc")

        add_service(partner_pc, skysea, powershell)

        # --------------------------------------------------------------------------------------------------------------
        # Add an existing session from partner_pc to the api_srv
        s = create_session("partner", ["partner_pc", "perimeter_router", "vpn_srv", "infrastructure_router", "api_srv"],
                           defer=True, service="skysea_client_view", reverse=True)

        # sessions(powershell.passive_service).append(s)

        add_node(partner_pc)

        # --- Perimeter router -----------------------------------------------------------------------------------------
        # Router connects DMZ with the outside world. For easier simulation, the outside is modelled as local to
        # the perimeter router
        perimeter_router = create_router("perimeter_router", cls._env.messaging)

        attacker_port = add_interface(perimeter_router, create_interface("10.9.0.1", "255.255.255.0"))
        partner_port = add_interface(perimeter_router, create_interface("10.9.0.1", "255.255.255.0"))
        outside_web_srv_port = add_interface(perimeter_router, create_interface("10.9.0.1", "255.255.255.0"))
        outside_email_srv_port = add_interface(perimeter_router, create_interface("10.9.0.1", "255.255.255.0"))
        outside_vpn_srv_port = add_interface(perimeter_router, create_interface("10.9.0.1", "255.255.255.0"))

        add_connection(attacker_node, perimeter_router, target_port_index=attacker_port)
        add_connection(partner_pc, perimeter_router, target_port_index=partner_port)
        add_connection(web_srv, perimeter_router, target_port_index=outside_web_srv_port)
        add_connection(email_srv, perimeter_router, target_port_index=outside_email_srv_port)
        add_connection(vpn_srv, perimeter_router, target_port_index=outside_vpn_srv_port)

        # Outside -> DMZ
        add_routing_rule(perimeter_router, FirewallRule(IPNetwork("10.0.9.0/16"), IPNetwork("10.0.0.1/24"), "*", FirewallPolicy.ALLOW))
        # Inside -> Outside
        add_routing_rule(perimeter_router, FirewallRule(IPNetwork("10.0.0.0/16"), IPNetwork("10.9.0.0/16"), "*", FirewallPolicy.ALLOW))
        # Outside -> Outside (for those with outside addresses in DMZ
        add_routing_rule(perimeter_router, FirewallRule(IPNetwork("10.9.0.0/16"), IPNetwork("10.9.0.0/16"), "*", FirewallPolicy.ALLOW))

        add_node(perimeter_router)

        # Connect the routers together and enable one-way communication between infrastructure router and the DMZ router
        ir_port = add_interface(infrastructure_router, create_interface())
        pr_port = add_interface(perimeter_router, create_interface())

        add_connection(infrastructure_router, perimeter_router, source_port_index=ir_port, target_port_index=pr_port)
        add_route(infrastructure_router, Route(IPNetwork("10.9.0.1/24"), ir_port))

        # Uncomment to display the resulting network
        # cls._env.network.render()

        # --------------------------------------------------------------------------------------------------------------
        # Prepare available exploits, which the attacker can use
        # This is an exploit for credentials dumping
        e1 = create_exploit("e1", [create_vulnerable_service("powershell", "0.0.0", "6.2.2")], ExploitLocality.LOCAL, ExploitCategory.AUTH_MANIPULATION)

        # This is an exploit to get root access on any powershell-powered machine
        p2_1 = create_exploit_parameter(ExploitParameterType.ENABLE_ELEVATED_ACCESS, value="TRUE", immutable=True)
        p2_2 = create_exploit_parameter(ExploitParameterType.IDENTITY, value="Administrator", immutable=True)
        p2_3 = create_exploit_parameter(ExploitParameterType.IMPACT_SERVICE, value="ALL", immutable=True)
        e2 = create_exploit("e2", [create_vulnerable_service("powershell", "0.0.0", "6.2.2")], ExploitLocality.LOCAL,
                     ExploitCategory.AUTH_MANIPULATION, p2_1, p2_2, p2_3)

        # This is an exploit to get golden kerberos ticket at the DC controller
        p3_1 = create_exploit_parameter(ExploitParameterType.ENABLE_ELEVATED_ACCESS, value="TRUE", immutable=True)
        p3_2 = create_exploit_parameter(ExploitParameterType.IMPACT_IDENTITY, value="ALL", immutable=True)
        p3_3 = create_exploit_parameter(ExploitParameterType.IMPACT_NODE, value="ALL", immutable=True)
        p3_4 = create_exploit_parameter(ExploitParameterType.IMPACT_SERVICE, value="ALL", immutable=True)
        e3 = create_exploit("e3", [create_vulnerable_service("windows_server_2019", "0.0.0", "10.0.17666")], ExploitLocality.LOCAL,
                     ExploitCategory.AUTH_MANIPULATION, p3_1, p3_2, p3_3, p3_4)

        # This is an exploit of the skysea client view
        e4 = create_exploit("e4", [create_vulnerable_service("skysea_client_view", "0.0.0", "11.221.3")], ExploitLocality.LOCAL, ExploitCategory.CODE_EXECUTION)

        cls._env.configuration.exploit.add_exploit(e1, e2, e3, e4)

        cls._env.control.init()

        # This is the minimum number of actions, which is needed to successfully finish each of those three variants
        # of the Bronze butler scenario. They are used to compute the normalized action requirements
        cls._min_actions_cto = 2
        cls._min_actions_vpn = 6
        cls._min_actions_employee = 7

        # These are the values of particular runs for each scenario used to count the median
        cls._totals_random_cto = []
        cls._totals_random_vpn = []
        cls._totals_random_employee = []

        cls._totals_modular_cto = []
        cls._totals_modular_vpn = []
        cls._totals_modular_employee = []

    @staticmethod
    def rounded_div(dividend: int, divisor: int):
        return (dividend + divisor // 2) // divisor

    def test_0000_cto_scenario_omniscient(self) -> None:

        # short-circuiting the test
        if not enabled_tests["test_0000_cto_scenario_omniscient"]:
            return

        # Scenario prerequisite - the attacker successfully spearfished the CTO and got a session onto their PC
        #                       - the session is manually generated because spearphishng is not implemented as is
        #                         requires user modelling
        #                       - routing issues (i.e. not being able to pass from perimeter router to infrastructure
        #                         router) are resolved by the session, which models reverse shell following the
        #                         spearphishing exploit
        s = self._env.configuration.network.create_session("attacker", ["attacker_node", "perimeter_router", "infrastructure_router", "cto_pc"])

        # Scenario unfolding:
        # - T1003 Credentials Dumping (extracting authorization of CTO from the local system)
        # - T1018 Remote System Discovery (scanning of other infrastructure networks, identifying services)
        # -       Connection to the DB server
        # - T1005 Data from local system (access to private data using CTO's credentials

        # --------------------------------------------------------------------------------------------------------------
        # Test to show that without session an internal IP is not accessible
        action = self._actions["aif:active_recon:host_discovery"]
        self._attacker.execute_action("10.0.3.2", "", action)

        self._env.control.run()

        message = self._attacker.get_last_response()
        self.assertEqual(message.status, Status(StatusOrigin.NETWORK, StatusValue.FAILURE))

        # TODO: Missing meta action for getting information about the current node, namely the IP address and the shell
        # Right now I pretend I know it

        # --------------------------------------------------------------------------------------------------------------
        # Credentials Dumping
        action = self._actions["aif:active_recon:information_discovery"]

        e = self._env.resources.exploit_store.get_exploit(service="powershell", category=ExploitCategory.AUTH_MANIPULATION)[0]
        action.set_exploit(e)

        self._attacker.execute_action("10.0.2.2", "powershell", action, session=s)

        self._env.control.run()

        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS))

        cto_auth = None
        for a in message.content:
            if a.identity == "cto":
                cto_auth = a
                break

        self.assertIsNotNone(cto_auth, "Got authorization for CTO")
        # --------------------------------------------------------------------------------------------------------------
        # Remote System Discovery
        #
        # Get a list of hosts reachable from the CTO's computer
        action = self._actions["aif:active_recon:host_discovery"]

        nets_to_scan = [IPNetwork("10.0.0.0/24"), IPNetwork("10.0.1.0/24"), IPNetwork("10.0.2.0/24")]

        live_machines = []
        for net in nets_to_scan:
            for host in net.iter_hosts():
                self._attacker.execute_action(str(host), "", action, session=s)
                result, _ = self._env.control.run()

                self.assertTrue(result, "Environment correctly processed the request")

                message = self._attacker.get_last_response()

                if message.status == Status(StatusOrigin.NODE, StatusValue.SUCCESS):
                    live_machines.append(message.src_ip)

        # Identify services on accessible machines and look for MSSQL server
        action = self._actions["aif:active_recon:service_discovery"]
        mssql_ip = None

        for machine in live_machines:
            self._attacker.execute_action(str(machine), "", action, session=s)
            result, _ = self._env.control.run()

            self.assertTrue(result, "Environment correctly processed the request")

            message = self._attacker.get_last_response()

            if "mssql" in message.content:
                mssql_ip = machine
                break

        self.assertIsNotNone(mssql_ip, "Got the IP of the DB server")

        # --------------------------------------------------------------------------------------------------------------
        # Data exfiltration
        action = self._actions["aif:disclosure:data_exfiltration"]

        self._attacker.execute_action(str(mssql_ip), "mssql", action, session=s, auth=cto_auth)

        result, _ = self._env.control.run()

        self.assertTrue(result, "Environment correctly processed the request")

        message = self._attacker.get_last_response()

        data_found = False
        for datum in message.content:
            if datum.description == "Secret data":
                data_found = True
            break

        self.assertTrue(data_found, "Successfully extracted data from the DB")

    def test_0001_cto_scenario_random(self):

        # Configuration for evaluation
        filename = "cto_scenario_random.data"

        # Short-circuit scenario
        if not enabled_tests["test_0001_cto_scenario_random"]:
            return

        output = open(filename, "w")

        s = self._env.configuration.network.create_session("attacker", ["attacker_node", "perimeter_router", "infrastructure_router", "cto_pc"])

        # --------------------------------------------------------------------------------------------------------------
        # Let random attacker attempt the complex scenario
        for i in range(0, number_of_runs):
            self._random_attacker.reset()
            # --------------------------------------------------------------------------------------------------------------
            # Let random attacker attempt the simple scenario
            self._random_attacker.set_action_limit(150000)
            self._random_attacker.set_action_namespace("aif")
            self._random_attacker.add_targets(IPNetwork("10.0.0.0/24"))
            self._random_attacker.add_targets(IPNetwork("10.0.1.0/24"))
            self._random_attacker.add_targets(IPNetwork("10.0.2.0/24"))
            self._random_attacker.add_sessions(s)
            self._random_attacker.set_services("postfix", "bash", "apache", "skysea_client_view",
                                               "windows_server_2019",
                                               "rdp", "mssql", "powershell")

            self._random_attacker.set_reduction_strategy(ReductionStrategy.LIVE_TARGETS_ONLY)
            self._random_attacker.set_goal("Secret data")


            self._random_attacker.run()
            self._env.control.run()

            total = self._random_attacker.attack_stats()[0].total
            print("1 {} {}".format(str(total), str(self.rounded_div(total, self._min_actions_cto))), file=output)
            print("CTO scenario [random attacker]: run no. {}/{}, total actions: {}".format(str(i+1), str(number_of_runs), str(total)))
            self._totals_random_cto.append(total)

        output.close()

        # Store median in temporary file
        # median_output = open("median_random_1.data", "w")
        # median_random_cto = statistics.median_low(self._totals_random_cto)
        # print("1 {} {}".format(str(median_random_cto), str(self.rounded_div(median_random_cto, self._min_actions_cto))), file=median_output)
        # median_output.close()

    def test_0002_cto_scenario_modular(self):

        # Configuration for evaluation
        filename = "cto_scenario_modular.data"

        # Short-circuit scenario
        if not enabled_tests["test_0002_cto_scenario_modular"]:
            return

        # give the attacker the session and IP of a target
        attacked_ips = ["10.0.2.2"]
        s = self._env.configuration.network.create_session("attacker", ["attacker_node", "perimeter_router", "infrastructure_router", "cto_pc"])

        
        # output = open(filename, "w")

        test_mapping = None
        test_attempts = {}
        test_totals = []
        total_actions = 0

        for i in range(0, number_of_runs):
            self._ucb_attacker.reset()

            for ip in attacked_ips:
                self._ucb_attacker.new_host(IPAddress(ip))
                self._ucb_attacker.new_session(IPAddress(ip), s)

            # tell the attacker IPs of the routers - sadly currently unobtainable via simulator
            self._ucb_attacker.add_router_manually(0, IPNetwork("10.0.0.1/24"))
            self._ucb_attacker.add_router_manually(0, IPNetwork("10.0.1.1/24"))
            self._ucb_attacker.add_router_manually(0, IPNetwork("10.0.2.1/24"))

            self._ucb_attacker.set_target_services(["sql"])

            # let the attacker do its thing until it finds the secret data
            actions = 0
            while (True):
                actions += 1
                total_actions += 1
                self._ucb_attacker.run()
                self._env.control.run()
                if len(self._ucb_attacker.all_data()) > 0:
                    break

            # print("2 {} {}".format(str(actions), str(self.rounded_div(actions, self._min_actions_cto))), file=output)
            print("CTO scenario [modular attacker]: run no. {}/{}, total actions: {}".format(str(i+1), str(number_of_runs), str(actions)))
            self._totals_modular_cto.append(actions)
            print("path:")
            print("\n".join(str(x) for x in self._ucb_attacker._history.get_attack_path(self._ucb_attacker.all_data()[0][1])))
        print("Average actions per run: ", total_actions / number_of_runs)

        """
            # Get some statistics on action ratios
            mapping, attempts = self._ucb_attacker.action_stats()

            if test_mapping is None:
                test_mapping = mapping

            if len(mapping) > len(test_mapping):
                raise Exception("Got longer mapping than before")

            for j in range(0, len(test_mapping)):
                if j not in test_attempts:
                    test_attempts[j] = []
                test_attempts[j].append(0)

            for item, index in mapping.items():
                test_attempts[test_mapping[item]][-1] = attempts[index]

            test_totals.append(actions)
        """
    

        # output.close()

        # Store median in temporary file
        # median_output = open("median_modular_1.data", "w")
        # median_modular_cto = statistics.median_low(self._totals_modular_cto)
        # print("2 {} {}".format(str(median_modular_cto), str(self.rounded_div(median_modular_cto, self._min_actions_cto))), file=median_output)
        # median_output.close()

        # Store action distribution in a temporary file
        # action_distribution_cto = open("action_distribution_cto.data", "w")

        # reverse_mapping = [None] * len(test_mapping)
        # for k, v in test_mapping.items():
        #   reverse_mapping[v] = k

        # for i in range(0, len(reverse_mapping)):
        #     action_distribution_cto.write(reverse_mapping[i] + " ")
        # action_distribution_cto.write("\n")

        # for j in range(0, number_of_runs):
            #     for i in range(0, len(test_mapping)):
            #         action_distribution_cto.write(str(test_attempts[i][j] / test_totals[j]) + " ")
        #     action_distribution_cto.write("\n")

        # action_distribution_cto.close()

    def test_0003_vpn_scenario_omniscient(self) -> None:
        # short-circuiting the test
        if not enabled_tests["test_0003_vpn_scenario_omniscient"]:
            return

        # Scenario prerequisite - the attacker successfully spearfished the partner and got a session onto their PC
        #                       - the session is manually generated because spearphishng is not implemented as is
        #                         requires user modelling
        #                       - routing issues (i.e. not being able to pass from perimeter router to infrastructure
        #                         router) are resolved by the session, which models reverse shell following the
        #                         spearphishing exploit
        s = self._env.configuration.network.create_session("attacker", ["attacker_node", "perimeter_router", "partner_pc"])

        # Scenario unfolding:
        # - xxx   Exploiting skysea client to get access to API server
        # - T1003 Credentials Dumping (extracting authorization of employee to the dc from the local system)
        # - T1018 Remote System Discovery (scanning of other infrastructure networks, identifying services, discovering
        #         path to SRV network segment)
        # -       Connection to the dc
        # - T1088 User privilege escalation to Administrator account
        # - T1097 Creating the golden ticket
        # -       Connection to the db server using the golden ticket
        # - T1005 Data from local system (access to private data using CTO's credentials

        # --------------------------------------------------------------------------------------------------------------
        # Exploit of the skysea client and get the session to the API server
        action = self._actions["aif:targeted_exploits:exploit_remote_services"]

        e = self._env.resources.exploit_store.get_exploit(service="skysea_client_view", category=ExploitCategory.CODE_EXECUTION)[0]
        action.set_exploit(e)

        self._attacker.execute_action("10.9.0.3", "skysea_client_view", action, session=s)

        self._env.control.run()

        message = self._attacker.get_last_response()
        api_session = message.content[0]

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS))
        self.assertEqual(api_session.endpoint.id, "api_srv", "Got a session to the API server")

        # --------------------------------------------------------------------------------------------------------------
        # Credentials Dumping
        action = self._actions["aif:active_recon:information_discovery"]

        e = self._env.resources.exploit_store.get_exploit(service="powershell", category=ExploitCategory.AUTH_MANIPULATION)[0]
        action.set_exploit(e)

        # TODO: Sessions either need to carry information about IP addresses they are traversing, or that meta action
        #       for listing network information must be added. Right now, this is a bit of a cheating, but the
        #       attacker is omniscient, so...
        self._attacker.execute_action("10.0.1.4", "powershell", action, session=api_session)

        self._env.control.run()

        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS))

        dc_auth = None
        for a in message.content:
            if a.identity == "employee":
                dc_auth = a
                break

        self.assertIsNotNone(dc_auth, "Got DC authorization for an employee")

        # --------------------------------------------------------------------------------------------------------------
        # Remote System Discovery
        #
        # Get a list of hosts reachable from the web server (it should be different than from an employee computer)
        action = self._actions["aif:active_recon:host_discovery"]

        nets_to_scan = [IPNetwork("10.0.0.0/24"), IPNetwork("10.0.1.0/24"), IPNetwork("10.0.2.0/24")]

        live_machines = []
        for net in nets_to_scan:
            for host in net.iter_hosts():
                self._attacker.execute_action(str(host), "", action, session=api_session)
                result, _ = self._env.control.run()

                self.assertTrue(result, "Environment correctly processed the request")

                message = self._attacker.get_last_response()

                if message.status == Status(StatusOrigin.NODE, StatusValue.SUCCESS):
                    live_machines.append(message.src_ip)

        # Identify services on accessible machines
        action = self._actions["aif:active_recon:service_discovery"]
        mssql_ip = None
        dc_ip = None

        for machine in live_machines:
            self._attacker.execute_action(str(machine), "", action, session=api_session)
            result, _ = self._env.control.run()

            self.assertTrue(result, "Environment correctly processed the request")

            message = self._attacker.get_last_response()

            if "mssql" in message.content:
                mssql_ip = machine

            elif "windows_server_2019" in message.content:
                dc_ip = machine

        self.assertIsNotNone(mssql_ip, "The DB server is now accessible")
        self.assertIsNotNone(dc_ip, "The DC server is now accessible")

        # --------------------------------------------------------------------------------------------------------------
        # Connection to the DC using employee authentication
        action = self._actions["aif:ensure_access:command_and_control"]

        self._attacker.execute_action(str(dc_ip), "rdp", action, auth=dc_auth, session=api_session)

        result, _ = self._env.control.run()
        self.assertTrue(result, "Environment correctly processed the request")

        message = self._attacker.get_last_response()
        # New session established to the DC server
        dc_session = message.session

        self.assertEqual(dc_session.end, IPAddress("10.0.1.2"), "Successfully connected to the DC server")

        # --------------------------------------------------------------------------------------------------------------
        # Root privilege escalation to get full access to the DC
        action = self._actions["aif:privilege_escalation:root_privilege_escalation"]

        exploits = self._env.resources.exploit_store.get_exploit(service="powershell", category=ExploitCategory.AUTH_MANIPULATION)
        exploit = None

        # Get the exploit which enables elevated access
        for e in exploits:
            for p in e.parameters.values():
                if p.type == ExploitParameterType.ENABLE_ELEVATED_ACCESS and p.value == "TRUE":
                    exploit = e
                    break

        self.assertIsNotNone(exploit, "Found an exploit which enables elevation to root privileges")

        action.set_exploit(exploit)
        self._attacker.execute_action(str(dc_ip), "powershell", action, auth=dc_auth, session=dc_session)

        result, _ = self._env.control.run()
        self.assertTrue(result, "Environment correctly processed the request")

        message = self._attacker.get_last_response()

        dc_root_auth = message.authorization

        self.assertEqual(dc_root_auth.identity, "Administrator", "Got administrative access to the dc server")

        # --------------------------------------------------------------------------------------------------------------
        # Get root access to the entire infrastructure
        action = self._actions["aif:privilege_escalation:root_privilege_escalation"]

        e = self._env.resources.exploit_store.get_exploit(service="windows_server_2019", category=ExploitCategory.AUTH_MANIPULATION)[0]
        action.set_exploit(e)

        self._attacker.execute_action(str(dc_ip), "windows_server_2019", action, auth=dc_root_auth,
                                      session=dc_session)

        result, _ = self._env.control.run()
        self.assertTrue(result, "Environment correctly processed the request")

        message = self._attacker.get_last_response()

        infrastructure_root_auth = message.authorization

        self.assertEqual(self._env.policy.get_nodes(infrastructure_root_auth), ["*"], "Got administrative access to the infrastructure")

        # --------------------------------------------------------------------------------------------------------------
        # Data exfiltration
        action = self._actions["aif:disclosure:data_exfiltration"]

        self._attacker.execute_action(str(mssql_ip), "mssql", action, session=api_session,
                                      auth=infrastructure_root_auth)

        result, _ = self._env.control.run()

        self.assertTrue(result, "Environment correctly processed the request")

        message = self._attacker.get_last_response()

        data_found = False
        for datum in message.content:
            if datum.description == "Secret data":
                data_found = True
            break

        self.assertTrue(data_found, "Successfully extracted data from the DB")

    def test_0004_vpn_scenario_random(self) -> None:
        # Configuration for evaluation
        filename = "vpn_scenario_random.data"

        # Short-circuit scenario
        if not enabled_tests["test_0004_vpn_scenario_random"]:
            return

        # output = open(filename, "w")

        s = self._env.configuration.network.create_session("attacker", ["attacker_node", "perimeter_router", "partner_pc"])

        # --------------------------------------------------------------------------------------------------------------
        # Let random attacker attempt the complex scenario
        for i in range(0, number_of_runs):
            self._random_attacker.reset()
            # --------------------------------------------------------------------------------------------------------------
            # Let random attacker attempt the simple scenario
            self._random_attacker.set_action_limit(150000)
            self._random_attacker.set_action_namespace("aif")
            self._random_attacker.add_targets(IPNetwork("10.0.0.0/24"))
            self._random_attacker.add_targets(IPNetwork("10.0.1.0/24"))
            self._random_attacker.add_targets(IPNetwork("10.0.2.0/24"))
            self._random_attacker.add_targets(IPNetwork("10.9.0.3/32"))
            self._random_attacker.add_sessions(s)
            self._random_attacker.set_services("postfix", "bash", "apache", "skysea_client_view",
                                               "windows_server_2019",
                                               "rdp", "mssql", "powershell")

            self._random_attacker.set_reduction_strategy(ReductionStrategy.LIVE_TARGETS_ONLY)
            self._random_attacker.set_goal("Secret data")

            self._random_attacker.run()
            self._env.control.run()

            total = self._random_attacker.attack_stats()[0].total
            # print("3 {} {}".format(str(total), str(self.rounded_div(total, self._min_actions_vpn))), file=output)
            print("VPN scenario [random attacker]: run no. {}/{}, total actions: {}".format(str(i+1), str(number_of_runs), str(total)))
            self._totals_random_vpn.append(total)

        # output.close()

        # Store median in temporary file
        # median_output = open("median_random_2.data", "w")
        # median_random_vpn = statistics.median_low(self._totals_random_vpn)
        # print("3 {} {}".format(str(median_random_vpn), str(self.rounded_div(median_random_vpn, self._min_actions_vpn))), file=median_output)
        # median_output.close()

    def test_0005_vpn_scenario_modular(self) -> None:
        # Configuration for evaluation
        filename = "vpn_scenario_modular.data"

        # Short-circuit scenario
        if not enabled_tests["test_0005_vpn_scenario_modular"]:
            return

        # output = open(filename, "w")

        # give the attacker the session and IP of a target
        attacked_ips = ["10.9.0.3"]
        s = self._env.configuration.network.create_session("attacker", ["attacker_node", "perimeter_router", "partner_pc"])
        # s = self._env.add_session("attacker", ["attacker_node", "perimeter_router", "partner_pc"])

        test_mapping = None
        test_attempts = {}
        test_totals = []
        total_actions = 0

        # --------------------------------------------------------------------------------------------------------------
        # Let random attacker attempt the complex scenario
        for i in range(0, number_of_runs):
            self._ucb_attacker.reset()

            for ip in attacked_ips:
                self._ucb_attacker._memory.new_host(IPAddress(ip))
                self._ucb_attacker._memory.new_session(IPAddress(ip), s)

            # tell the attacker IPs of the routers - sadly currently unobtainable via simulator
            self._ucb_attacker.add_router_manually(0, IPNetwork("10.0.0.1/24"))
            self._ucb_attacker.add_router_manually(0, IPNetwork("10.0.1.1/24"))
            self._ucb_attacker.add_router_manually(0, IPNetwork("10.0.2.1/24"))

            self._ucb_attacker.set_target_services(["sql"])

            # let the attacker do its thing until it finds the secret data
            actions = 0
            while actions < 150000:
                actions += 1
                total_actions += 1
                self._ucb_attacker.run()
                self._env.control.run()
                if len(self._ucb_attacker._memory.all_data()) > 0:
                    break
            
            print("path:")
            print("\n".join(str(x) for x in self._ucb_attacker._history.get_attack_path(self._ucb_attacker.all_data()[0][1])))
            print("VPN scenario [modular attacker]: run no. {}/{}, total actions: {}".format(str(i+1), str(number_of_runs), str(actions)))
            self._totals_modular_vpn.append(actions)
            # Get some statistics on action ratios
            mapping, attempts = self._ucb_attacker.action_stats()

            if test_mapping is None:
                test_mapping = mapping

            if len(mapping) > len(test_mapping):
                raise Exception("Got longer mapping than before")

            for j in range(0, len(test_mapping)):
                if j not in test_attempts:
                    test_attempts[j] = []
                test_attempts[j].append(0)

            for item, index in mapping.items():
                test_attempts[test_mapping[item]][-1] = attempts[index]

            test_totals.append(actions)

        print("Average actions per run: ", total_actions / number_of_runs)
        """
        output.close()

        # Store median in temporary file
        median_output = open("median_modular_2.data", "w")
        median_modular_vpn = statistics.median_low(self._totals_modular_vpn)
        print("4 {} {}".format(str(median_modular_vpn), str(self.rounded_div(median_modular_vpn, self._min_actions_vpn))), file=median_output)
        median_output.close()

        # Store action distribution in a temporary file
        action_distribution_cto = open("action_distribution_vpn.data", "w")

        reverse_mapping = [None] * len(test_mapping)
        for k, v in test_mapping.items():
            reverse_mapping[v] = k

        for i in range(0, len(reverse_mapping)):
            action_distribution_cto.write(reverse_mapping[i] + " ")
        action_distribution_cto.write("\n")

        for j in range(0, number_of_runs):
            for i in range(0, len(test_mapping)):
                action_distribution_cto.write(str(test_attempts[i][j] / test_totals[j]) + " ")
            action_distribution_cto.write("\n")

        action_distribution_cto.close()
        """

    def test_0006_employee_scenario_omniscient(self) -> None:

        # short-circuiting the test
        if not enabled_tests["test_0006_employee_scenario_omniscient"]:
            return

        # Scenario prerequisite - the attacker successfully spearfished the employee and got a session onto their PC
        #                       - the session is manually generated because spearphishng is not implemented as is
        #                         requires user modelling
        #                       - routing issues (i.e. not being able to pass from perimeter router to infrastructure
        #                         router) are resolved by the session, which models reverse shell following the
        #                         spearphishing exploit
        s = self._env.configuration.network.create_session("attacker", ["attacker_node", "perimeter_router", "infrastructure_router", "emp_pc"])

        # Scenario unfolding:
        # - T1003 Credentials Dumping (extracting authorization of employee useful for the web server)
        # - T1018 Remote System Discovery (scanning of other infrastructure networks, identifying services)
        # -       Connection to the web server via rdp
        # - T1003 Credentials Dumping (extracting authorization of employee to the dc from the local system)
        # - T1018 Remote System Discovery (scanning of other infrastructure networks, identifying services, discovering
        #         path to SRV network segment)
        # -       Connection to the dc
        # - T1088 User privilege escalation to Administrator account
        # - T1097 Creating the golden ticket
        # -       Connection to the db server using the golden ticket
        # - T1005 Data from local system (access to private data using CTO's credentials

        # --------------------------------------------------------------------------------------------------------------
        # Credentials Dumping
        action = self._actions["aif:active_recon:information_discovery"]

        e = self._env.resources.exploit_store.get_exploit(service="powershell", category=ExploitCategory.AUTH_MANIPULATION)[0]
        action.set_exploit(e)

        self._attacker.execute_action("10.0.2.3", "powershell", action, session=s)

        self._env.control.run()

        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS))

        emp_auth = None
        for a in message.content:
            if a.identity == "employee":
                emp_auth = a
                break

        self.assertIsNotNone(emp_auth, "Got authorization for an employee")

        # --------------------------------------------------------------------------------------------------------------
        # Remote System Discovery
        #
        # Get a list of hosts reachable from the employee's computer
        action = self._actions["aif:active_recon:host_discovery"]

        nets_to_scan = [IPNetwork("10.0.0.0/24"), IPNetwork("10.0.1.0/24"), IPNetwork("10.0.2.0/24")]

        live_machines = []
        for net in nets_to_scan:
            for host in net.iter_hosts():
                self._attacker.execute_action(str(host), "", action, session=s)
                result, _ = self._env.control.run()

                self.assertTrue(result, "Environment correctly processed the request")

                message = self._attacker.get_last_response()

                if message.status == Status(StatusOrigin.NODE, StatusValue.SUCCESS):
                    live_machines.append(message.src_ip)

        # Identify services on accessible machines
        action = self._actions["aif:active_recon:service_discovery"]
        mssql_ip = None
        websrv_ip = None

        for machine in live_machines:
            self._attacker.execute_action(str(machine), "", action, session=s)
            result, _ = self._env.control.run()

            self.assertTrue(result, "Environment correctly processed the request")

            message = self._attacker.get_last_response()

            if "mssql" in message.content:
                mssql_ip = machine

            elif "iis" in message.content:
                websrv_ip = machine

        self.assertIsNone(mssql_ip, "The DB server was not accessible")
        self.assertIsNotNone(websrv_ip, "The DB server was not accessible")

        # --------------------------------------------------------------------------------------------------------------
        # Connection to the web server using employee authentication
        action = self._actions["aif:ensure_access:command_and_control"]

        self._attacker.execute_action(str(websrv_ip), "rdp", action, auth=emp_auth, session=s)

        result, _ = self._env.control.run()
        self.assertTrue(result, "Environment correctly processed the request")

        message = self._attacker.get_last_response()
        # New session established to the web server
        web_session = message.session

        # This is going to be more sensible, when there is a visibility separation in session elements (i.e., user
        # sees only the IP addresses along the session)
        self.assertEqual(web_session.end, IPAddress(websrv_ip), "Successfully connected to the web server")

        # --------------------------------------------------------------------------------------------------------------
        # Credentials Dumping
        action = self._actions["aif:active_recon:information_discovery"]

        e = self._env.resources.exploit_store.get_exploit(service="powershell", category=ExploitCategory.AUTH_MANIPULATION)[0]
        action.set_exploit(e)

        self._attacker.execute_action(str(websrv_ip), "powershell", action, session=web_session)

        self._env.control.run()

        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS))

        dc_auth = None
        for a in message.content:
            if a.identity == "employee":
                dc_auth = a
                break

        self.assertIsNotNone(dc_auth, "Got DC authorization for an employee")

        # --------------------------------------------------------------------------------------------------------------
        # Remote System Discovery
        #
        # Get a list of hosts reachable from the web server (it should be different than from an employee computer)
        action = self._actions["aif:active_recon:host_discovery"]

        nets_to_scan = [IPNetwork("10.0.0.0/24"), IPNetwork("10.0.1.0/24"), IPNetwork("10.0.2.0/24")]

        live_machines = []
        for net in nets_to_scan:
            for host in net.iter_hosts():
                self._attacker.execute_action(str(host), "", action, session=web_session)
                result, _ = self._env.control.run()

                self.assertTrue(result, "Environment correctly processed the request")

                message = self._attacker.get_last_response()

                if message.status == Status(StatusOrigin.NODE, StatusValue.SUCCESS):
                    live_machines.append(message.src_ip)

        # Identify services on accessible machines
        action = self._actions["aif:active_recon:service_discovery"]
        mssql_ip = None
        dc_ip = None

        for machine in live_machines:
            self._attacker.execute_action(str(machine), "", action, session=web_session)
            result, _ = self._env.control.run()

            self.assertTrue(result, "Environment correctly processed the request")

            message = self._attacker.get_last_response()

            if "mssql" in message.content:
                mssql_ip = machine

            elif "windows_server_2019" in message.content:
                dc_ip = machine

        self.assertIsNotNone(mssql_ip, "The DB server is now accessible")
        self.assertIsNotNone(dc_ip, "The DC server is now accessible")

        # --------------------------------------------------------------------------------------------------------------
        # Connection to the web server using employee authentication
        action = self._actions["aif:ensure_access:command_and_control"]

        self._attacker.execute_action(str(dc_ip), "rdp", action, auth=dc_auth, session=web_session)

        result, _ = self._env.control.run()
        self.assertTrue(result, "Environment correctly processed the request")

        message = self._attacker.get_last_response()
        # New session established to the DC server
        dc_session = message.session

        self.assertEqual(dc_session.end, IPAddress(dc_ip), "Successfully connected to the web server")

        # --------------------------------------------------------------------------------------------------------------
        # Root privilege escalation to get full access to the DC
        action = self._actions["aif:privilege_escalation:root_privilege_escalation"]

        exploits = self._env.resources.exploit_store.get_exploit(service="powershell", category=ExploitCategory.AUTH_MANIPULATION)
        exploit = None

        # Get the exploit which enables elevated access
        for e in exploits:
            for p in e.parameters.values():
                if p.type == ExploitParameterType.ENABLE_ELEVATED_ACCESS and p.value == "TRUE":
                    exploit = e
                    break

        self.assertIsNotNone(exploit, "Found an exploit which enables elevation to root privileges")

        action.set_exploit(exploit)
        self._attacker.execute_action(str(dc_ip), "powershell", action, auth=dc_auth, session=dc_session)

        result, _ = self._env.control.run()
        self.assertTrue(result, "Environment correctly processed the request")

        message = self._attacker.get_last_response()

        dc_root_auth = message.authorization

        self.assertEqual(dc_root_auth.identity, "Administrator", "Got administrative access to the dc server")

        # --------------------------------------------------------------------------------------------------------------
        # Get root access to the entire infrastructure
        action = self._actions["aif:privilege_escalation:root_privilege_escalation"]

        e = self._env.resources.exploit_store.get_exploit(service="windows_server_2019", category=ExploitCategory.AUTH_MANIPULATION)[0]
        action.set_exploit(e)

        self._attacker.execute_action(str(dc_ip), "windows_server_2019", action, auth=dc_root_auth, session=dc_session)

        result, _ = self._env.control.run()
        self.assertTrue(result, "Environment correctly processed the request")

        message = self._attacker.get_last_response()

        infrastructure_root_auth = message.authorization

        self.assertEqual(self._env.policy.get_nodes(infrastructure_root_auth), ["*"], "Got administrative access to the infrastructure")

        # --------------------------------------------------------------------------------------------------------------
        # Data exfiltration
        action = self._actions["aif:disclosure:data_exfiltration"]

        self._attacker.execute_action(str(mssql_ip), "mssql", action, session=web_session, auth=infrastructure_root_auth)

        result, _ = self._env.control.run()

        self.assertTrue(result, "Environment correctly processed the request")

        message = self._attacker.get_last_response()

        data_found = False
        for datum in message.content:
            if datum.description == "Secret data":
                data_found = True
            break

        self.assertTrue(data_found, "Successfully extracted data from the DB")

    def test_0007_employee_scenario_random(self) -> None:

        # Configuration for evaluation
        filename = "employee_scenario_random.data"

        # Short-circuit scenario
        if not enabled_tests["test_0007_employee_scenario_random"]:
            return

        # output = open(filename, "w")

        s = self._env.configuration.network.create_session("attacker", ["attacker_node", "perimeter_router", "infrastructure_router", "emp_pc"])

        # --------------------------------------------------------------------------------------------------------------
        # Let random attacker attempt the complex scenario
        for i in range(0, number_of_runs):
            self._random_attacker.reset()
            # --------------------------------------------------------------------------------------------------------------
            # Let random attacker attempt the simple scenario
            self._random_attacker.set_action_limit(150000)
            self._random_attacker.set_action_namespace("aif")
            self._random_attacker.add_targets(IPNetwork("10.0.0.0/24"))
            self._random_attacker.add_targets(IPNetwork("10.0.1.0/24"))
            self._random_attacker.add_targets(IPNetwork("10.0.2.0/24"))
            self._random_attacker.add_sessions(s)
            self._random_attacker.set_services("postfix", "bash", "apache", "skysea_client_view",
                                               "windows_server_2019",
                                               "rdp", "mssql", "powershell")

            self._random_attacker.set_reduction_strategy(ReductionStrategy.LIVE_TARGETS_ONLY)
            self._random_attacker.set_goal("Secret data")

            self._random_attacker.run()
            self._env.control.run()

            # total = self._random_attacker.attack_stats()[0].total
            # print("5 {} {}".format(str(total), str(self.rounded_div(total, self._min_actions_employee))), file=output)
            # print("Employee scenario [random attacker]: run no. {}/{}, total actions: {}".format(str(i+1), str(number_of_runs), str(total)))
            # self._totals_random_employee.append(total)

        # output.close()

        # Store median in temporary file
        # median_output = open("median_random_3.data", "w")
        # median_random_employee = statistics.median_low(self._totals_random_employee)
        # print("5 {} {}".format(str(median_random_employee), str(self.rounded_div(median_random_employee, self._min_actions_employee))), file=median_output)
        # median_output.close()

    def test_0008_employee_scenario_modular(self) -> None:

        # Configuration for evaluation
        filename = "employee_scenario_modular.data"

        # Short-circuit scenario
        if not enabled_tests["test_0008_employee_scenario_modular"]:
            return

        # give the attacker the session and IP of a target
        attacked_ips = ["10.0.2.3"]
        s = self._env.configuration.network.create_session("attacker", ["attacker_node", "perimeter_router", "infrastructure_router", "emp_pc"])

        # output = open(filename, "w")

        test_mapping = None
        test_attempts = {}
        test_totals = []
        total_actions = 0

        for i in range(0, number_of_runs):
            self._ucb_attacker.reset()

            for ip in attacked_ips:
                self._ucb_attacker._memory.new_host(IPAddress(ip))
                self._ucb_attacker._memory.new_session(IPAddress(ip), s)

            # tell the attacker IPs of the routers - sadly currently unobtainable via simulator
            self._ucb_attacker.add_router_manually(0, IPNetwork("10.0.0.1/24"))
            self._ucb_attacker.add_router_manually(0, IPNetwork("10.0.1.1/24"))
            self._ucb_attacker.add_router_manually(0, IPNetwork("10.0.2.1/24"))

            self._ucb_attacker.set_target_services(["sql"])

            # let the attacker do its thing until it finds the secret data
            actions = 0
            while (True):
                actions += 1
                total_actions += 1
                self._ucb_attacker.run()
                self._env.control.run()
                if len(self._ucb_attacker.all_data()) > 0:
                    break

            # print("6 {} {}".format(str(actions), str(self.rounded_div(actions, self._min_actions_employee))), file=output)
            print("path:" + str(len(self._ucb_attacker._history.get_attack_path(self._ucb_attacker.all_data()[0][1]))))
            print("\n".join(str(x) for x in self._ucb_attacker._history.get_attack_path(self._ucb_attacker.all_data()[0][1])))
            print("Employee scenario [modular attacker]: run no. {}/{}, total actions: {}".format(str(i+1), str(number_of_runs), str(actions)))
            """
            self._totals_modular_employee.append(actions)
            
            # Get some statistics on action ratios
            mapping, attempts = self._modular_attacker.action_stats()

            if test_mapping is None:
                test_mapping = mapping

            if len(mapping) > len(test_mapping):
                raise Exception("Got longer mapping than before")

            for j in range(0, len(test_mapping)):
                if j not in test_attempts:
                    test_attempts[j] = []
                test_attempts[j].append(0)

            for item, index in mapping.items():
                test_attempts[test_mapping[item]][-1] = attempts[index]

            test_totals.append(actions)
            """
        
        print("Average actions per run: ", total_actions / number_of_runs)

        """
        output.close()

        # Store median in temporary file
        median_output = open("median_modular_3.data", "w")
        median_modular_employee = statistics.median_low(self._totals_modular_employee)
        print("6 {} {}".format(str(median_modular_employee), str(self.rounded_div(median_modular_employee, self._min_actions_employee))), file=median_output)
        median_output.close()

        # Store action distribution in a temporary file
        action_distribution_cto = open("action_distribution_employee.data", "w")

        reverse_mapping = [None] * len(test_mapping)
        for k, v in test_mapping.items():
            reverse_mapping[v] = k

        for i in range(0, len(reverse_mapping)):
            action_distribution_cto.write(reverse_mapping[i] + " ")
        action_distribution_cto.write("\n")

        for j in range(0, number_of_runs):
            for i in range(0, len(test_mapping)):
                action_distribution_cto.write(str(test_attempts[i][j] / test_totals[j]) + " ")
            action_distribution_cto.write("\n")

        action_distribution_cto.close()
        """

    def test_0009_simple_scenario_random_strategies(self) -> None:

        # Configuration for evaluation
        filename = "random_strategies.data"

        # Short-circuit scenario
        if not enabled_tests["test_0009_simple_scenario_random_strategies"]:
            return

        output = open(filename, "w")

        s = self._env.add_session("attacker", ["attacker_node", "perimeter_router", "infrastructure_router", "cto_pc"])

        # --------------------------------------------------------------------------------------------------------------
        # Let random attacker attempt the simple scenario
        strategies = [ReductionStrategy.NO_STRATEGY, ReductionStrategy.NO_DUPLICATE_ACTIONS,
                      ReductionStrategy.KNOWN_SERVICES_ONLY, ReductionStrategy.LIVE_TARGETS_ONLY,
                      ReductionStrategy.NO_DUPLICATE_ACTIONS | ReductionStrategy.KNOWN_SERVICES_ONLY,
                      ReductionStrategy.NO_DUPLICATE_ACTIONS | ReductionStrategy.LIVE_TARGETS_ONLY,
                      ReductionStrategy.KNOWN_SERVICES_ONLY | ReductionStrategy.LIVE_TARGETS_ONLY,
                      ReductionStrategy.KNOWN_SERVICES_ONLY | ReductionStrategy.LIVE_TARGETS_ONLY | ReductionStrategy.NO_DUPLICATE_ACTIONS]

        for i in range(0, number_of_runs):
            print("Run no. {}".format(str(i)))
            for strat in strategies:
                self._random_attacker.reset()
                # --------------------------------------------------------------------------------------------------------------
                # Let random attacker attempt the simple scenario
                self._random_attacker.set_action_limit(150000)
                self._random_attacker.set_action_namespace("rit")
                self._random_attacker.add_targets(IPNetwork("10.0.0.0/24"))
                self._random_attacker.add_targets(IPNetwork("10.0.1.0/24"))
                self._random_attacker.add_targets(IPNetwork("10.0.2.0/24"))
                self._random_attacker.add_sessions(s)
                self._random_attacker.set_services("postfix", "bash", "apache", "skysea_client_view", "windows_server_2019",
                                                   "rdp", "mssql", "powershell")

                self._random_attacker.set_reduction_strategy(strat)
                self._random_attacker.set_goal("Secret data")

                self._random_attacker.run()
                self._env.control.run()

                total = self._random_attacker.attack_stats()[0].total
                output.write("{} ".format(str(total)))
                print("-- strategy: {}, actions: {}".format(str(strat), str(total)))
            output.write("\n")

        output.close()

if __name__ == '__main__':
    unittest.main()
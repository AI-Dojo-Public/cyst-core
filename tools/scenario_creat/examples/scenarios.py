from tools.scenario_creat.action_mapper.constraints import TokensAccounting, Tables, ActionToken, ExploitType
from tools.scenario_creat.scenario.base import Scenario
import networkx as nx

# -------------------------------------------------------------------------------------------------------- #
class Path(Scenario):
    def __init__(self):
        super().__init__()

    def _add_nodes(self):
        self.graph.add_node("start", cluster=-1)
        self.graph.add_node("aim", cluster=-1)
        self.graph.add_node("node1", cluster=-1)
        self.graph.add_node("node2", cluster=-1)
        self.graph.add_node("node3", cluster=-1)
        self.graph.add_edge("start", "node1")
        self.graph.add_edge("node1", "node2")
        self.graph.add_edge("node2", "node3")
        self.graph.add_edge("node3", "aim")

    def _add_tables(self):
        path_host = 5
        path_service = 5
        path_action = 5
        path_token = 7
        Path_AS = [[1, 0, 0, 0, 0],
                   [0, 1, 0, 0, 0],
                   [0, 0, 1, 0, 0],
                   [0, 0, 0, 1, 0],
                   [0, 0, 0, 0, 1]]

        Path_AT = [ActionToken.NONE]

        self.tables = Tables(path_host, path_service, path_action, path_token)
        self.tables.nnm = nx.to_numpy_matrix(self.graph).tolist()
        self.tables.asm = Path_AS
        self.tables.atm = Path_AT

    def _add_actions(self):
        self.accounting.add(0, ActionToken.DATA, ActionToken.DATA)
        self.accounting.add(1, ActionToken.NONE, ActionToken.NONE)
        self.accounting.add(2, ActionToken.NONE, ActionToken.SESSION)
        self.accounting.add(3, ActionToken.SESSION, ActionToken.AUTH_LIMITED)
        self.accounting.add(4, ActionToken.AUTH_LIMITED, ActionToken.DATA)

    def _add_translator(self):
        pass

    def solve_one(self):
        super()._solve_one(service=4, action=4, tokens=[ActionToken.DATA])

    def solve_all(self):
        super()._solve_all(service=4, action=4, tokens=[ActionToken.DATA])


# -------------------------------------------------------------------------------------------------------- #
class Diamond(Scenario):
    def __init__(self):
        super().__init__()

    def _add_nodes(self):
        self.graph.add_node("start", cluster=-1)
        self.graph.add_node("aim", cluster=-1)
        self.graph.add_node("node1", cluster=-1)
        self.graph.add_node("node2", cluster=-1)
        self.graph.add_node("node3", cluster=-1)
        self.graph.add_node("node4", cluster=-1)
        self.graph.add_edge("start", "node1")
        self.graph.add_edge("node1", "node2")
        self.graph.add_edge("node1", "node3")
        self.graph.add_edge("node2", "node4")
        self.graph.add_edge("node3", "node4")
        self.graph.add_edge("node4", "aim")

    def _add_tables(self):
        Diamond_host = 6
        Diamond_service = 6
        Diamond_action = 6
        Diamond_token = 7
        Diamond_AS = [[1, 0, 0, 0, 0, 0],
                      [0, 1, 0, 0, 0, 0],
                      [0, 0, 1, 0, 0, 0],
                      [0, 0, 0, 1, 0, 0],
                      [0, 0, 0, 0, 1, 0],
                      [0, 0, 0, 0, 0, 1]]
        Diamond_AT = [ActionToken.NONE]

        self.tables = Tables(Diamond_host, Diamond_service, Diamond_action, Diamond_token)
        self.tables.nnm = self.tables.nnm = nx.to_numpy_matrix(self.graph).tolist()
        self.tables.asm = Diamond_AS
        self.tables.atm = Diamond_AT

    def _add_actions(self):
        self.accounting = TokensAccounting()
        self.accounting.add(0, ActionToken.DATA, ActionToken.DATA)
        self.accounting.add(1, ActionToken.NONE, ActionToken.NONE)
        self.accounting.add(2, ActionToken.NONE, ActionToken.SESSION)
        self.accounting.add(3, ActionToken.NONE, ActionToken.EXPLOIT)
        self.accounting.add(4, ActionToken.SESSION | ActionToken.EXPLOIT, ActionToken.AUTH_LIMITED)
        self.accounting.add(5, ActionToken.AUTH_LIMITED, ActionToken.DATA)

    def _add_translator(self):
        pass

    def solve_one(self):
        super()._solve_one(service=5, action=5, tokens=[ActionToken.DATA])

    def solve_all(self):
        super()._solve_all(service=5, action=5, tokens=[ActionToken.DATA])


# -------------------------------------------------------------------------------------------------------- #
class CrossDiamond(Scenario):
    def __init__(self):
        super().__init__()

    def _add_nodes(self):
        self.graph.add_node("start", cluster=-1)
        self.graph.add_node("aim", cluster=-1)
        self.graph.add_node("node2", cluster=-1)
        self.graph.add_node("node3", cluster=-1)
        self.graph.add_node("node4", cluster=-1)
        self.graph.add_node("node5", cluster=-1)
        self.graph.add_node("node6", cluster=-1)
        self.graph.add_edge("start", "node2")
        self.graph.add_edge("start", "node3")
        self.graph.add_edge("node2", "node4")
        self.graph.add_edge("node3", "node5")
        self.graph.add_edge("node3", "node4")
        self.graph.add_edge("node4", "node6")
        self.graph.add_edge("node5", "node6")
        self.graph.add_edge("node6", "aim")

    def _add_tables(self):
        CRD_tokens = 7
        CRD_actions = 7
        CRD_services = 7
        CRD_hosts = 7

        CRD_AS = [[0 for i in range(0, 7)] for j in range(0, 7)]
        for i in range(0, 7):
            CRD_AS[i][i] = 1
        # diagonal

        CRD_AT = [ActionToken.NONE]

        self.tables = Tables(CRD_hosts, CRD_services, CRD_actions, CRD_tokens)
        self.tables.nnm = nx.to_numpy_matrix(self.graph).tolist()
        self.tables.asm = CRD_AS
        self.tables.atm = CRD_AT

    def _add_actions(self):
        self.accounting = TokensAccounting()
        self.accounting.add(0, ActionToken.START, ActionToken.START)
        self.accounting.add(1, ActionToken.NONE, ActionToken.EXPLOIT)
        self.accounting.add(2, ActionToken.NONE, ActionToken.SESSION)
        self.accounting.add(3, ActionToken.EXPLOIT | ActionToken.SESSION, ActionToken.AUTH_LIMITED)
        self.accounting.add(4, ActionToken.SESSION, ActionToken.SESSION)
        self.accounting.add(5, ActionToken.AUTH_LIMITED | ActionToken.SESSION, ActionToken.DATA)
        self.accounting.add(6, ActionToken.DATA, ActionToken.END)

    def _add_translator(self):
        pass

    def solve_one(self):
        super()._solve_one(service=6, action=6, tokens=[ActionToken.END])

    def solve_all(self):
        super()._solve_all(service=6, action=6, tokens=[ActionToken.END])


# -------------------------------------------------------------------------------------------------------- #
class DoubleCrossDiamond(Scenario):
    def __init__(self):
        super().__init__()

    def _add_nodes(self):
        self.graph.add_node("start", cluster=-1)
        self.graph.add_node("aim", cluster=-1)
        self.graph.add_node("node2", cluster=-1)
        self.graph.add_node("node3", cluster=-1)
        self.graph.add_node("node4", cluster=-1)
        self.graph.add_node("node5", cluster=-1)
        self.graph.add_edge("start", "node2")
        self.graph.add_edge("start", "node3")
        self.graph.add_edge("node2", "node5")
        self.graph.add_edge("node2", "node4")
        self.graph.add_edge("node3", "node4")
        self.graph.add_edge("node3", "node5")
        self.graph.add_edge("node4", "aim")
        self.graph.add_edge("node5", "aim")

    def _add_tables(self):
        DCD_tokens = 7
        DCD_actions = 7
        DCD_services = 7
        DCD_hosts = 6

        DCD_AS = [[0 for i in range(0, 7)] for j in range(0, 7)]
        for i in range(0, 7):
            DCD_AS[i][i] = 1

        DCD_AT = [ActionToken.NONE]

        self.tables = Tables(DCD_hosts, DCD_services, DCD_actions, DCD_tokens)
        self.tables.nnm = nx.to_numpy_matrix(self.graph).tolist()
        self.tables.asm = DCD_AS
        self.tables.atm = DCD_AT

    def _add_actions(self):
        self.accounting = TokensAccounting()
        self.accounting.add(0, ActionToken.START, ActionToken.START)
        self.accounting.add(1, ActionToken.NONE, ActionToken.EXPLOIT)
        self.accounting.add(2, ActionToken.NONE, ActionToken.SESSION)
        self.accounting.add(3, ActionToken.EXPLOIT | ActionToken.SESSION, ActionToken.AUTH_LIMITED)
        self.accounting.add(4, ActionToken.SESSION | ActionToken.EXPLOIT, ActionToken.DATA)
        self.accounting.add(5, ActionToken.AUTH_LIMITED | ActionToken.DATA, ActionToken.NONE)
        self.accounting.add(6, ActionToken.DATA, ActionToken.END)

    def _add_translator(self):
        pass

    def solve_one(self):
        super()._solve_one(service=5, action=5, tokens=[ActionToken.NONE])

    def solve_all(self):
        super()._solve_all(service=5, action=5, tokens=[ActionToken.NONE])


# -------------------------------------------------------------------------------------------------------- #
class AlternativePaths(Scenario):
    def __init__(self):
        super().__init__()

    def _add_nodes(self):
        self.graph.add_node("start", cluster=-1)
        self.graph.add_node("aim", cluster=-1)
        self.graph.add_node("node2", cluster=-1)
        self.graph.add_node("node3", cluster=-1)
        self.graph.add_node("node4", cluster=-1)
        self.graph.add_node("node5", cluster=-1)
        self.graph.add_node("node6", cluster=-1)
        self.graph.add_node("node7", cluster=-1)
        self.graph.add_edge("start", "node2")
        self.graph.add_edge("start", "node4")
        self.graph.add_edge("start", "node5")
        self.graph.add_edge("node2", "node3")
        self.graph.add_edge("node3", "node6")
        self.graph.add_edge("node4", "node7")
        self.graph.add_edge("node5", "node7")
        self.graph.add_edge("node6", "node7")
        self.graph.add_edge("node7", "aim")

    def _add_tables(self):
        AP_tokens = 7
        AP_actions = 8
        AP_services = 8
        AP_hosts = 8

        AP_AS = [[0 for i in range(0, 8)] for j in range(0, 8)]
        for i in range(0, 8):
            AP_AS[i][i] = 1

        AP_AT = [ActionToken.NONE]

        self.tables = Tables(AP_hosts, AP_services, AP_actions, AP_tokens)
        self.tables.nnm = nx.to_numpy_matrix(self.graph).tolist()
        self.tables.asm = AP_AS
        self.tables.atm = AP_AT

    def _add_actions(self):
        self.accounting = TokensAccounting()
        self.accounting.add(0, ActionToken.START, ActionToken.START)
        self.accounting.add(1, ActionToken.NONE, ActionToken.SESSION)
        self.accounting.add(2, ActionToken.SESSION, ActionToken.SESSION)
        self.accounting.add(2, ActionToken.SESSION, ActionToken.EXPLOIT)
        self.accounting.add(2, ActionToken.SESSION, ActionToken.SESSION | ActionToken.EXPLOIT)
        self.accounting.add(3, ActionToken.NONE, ActionToken.SESSION)
        self.accounting.add(4, ActionToken.NONE, ActionToken.EXPLOIT)
        self.accounting.add(5, ActionToken.SESSION | ActionToken.EXPLOIT, ActionToken.AUTH_LIMITED)
        self.accounting.add(6, ActionToken.SESSION | ActionToken.EXPLOIT, ActionToken.DATA)
        self.accounting.add(6, ActionToken.AUTH_LIMITED, ActionToken.DATA)
        self.accounting.add(7, ActionToken.DATA, ActionToken.END)

    def solve_one(self):
        super()._solve_one(service=7, action=7, tokens=[ActionToken.END])

    def solve_all(self):
        super()._solve_all(service=7, action=7, tokens=[ActionToken.END])


# -------------------------------------------------------------------------------------------------------- #
class AlternativePaths2(Scenario):
    def __init__(self):
        super().__init__()

    def _add_nodes(self):
        self.graph.add_node("start", cluster=-1)
        self.graph.add_node("aim", cluster=-1)
        self.graph.add_node("node2", cluster=-1)
        self.graph.add_node("node3", cluster=-1)
        self.graph.add_node("node4", cluster=-1)
        self.graph.add_node("node5", cluster=-1)
        self.graph.add_node("node6", cluster=-1)
        self.graph.add_node("node7", cluster=-1)
        self.graph.add_edge("start", "node2")
        self.graph.add_edge("start", "node4")
        self.graph.add_edge("start", "node5")
        self.graph.add_edge("node2", "node3")
        self.graph.add_edge("node3", "node6")
        self.graph.add_edge("node3", "node7")
        self.graph.add_edge("node4", "node7")
        self.graph.add_edge("node5", "node7")
        self.graph.add_edge("node6", "node7")
        self.graph.add_edge("node7", "aim")

    def _add_tables(self):
        AP_tokens = 7
        AP_actions = 8
        AP_services = 8
        AP_hosts = 8

        AP_AS = [[0 for i in range(0, 8)] for j in range(0, 8)]
        for i in range(0, 8):
            AP_AS[i][i] = 1

        AP_AT = [ActionToken.NONE]

        self.tables = Tables(AP_hosts, AP_services, AP_actions, AP_tokens)
        self.tables.nnm = nx.to_numpy_matrix(self.graph).tolist()
        self.tables.asm = AP_AS
        self.tables.atm = AP_AT

    def _add_actions(self):
        self.accounting = TokensAccounting()
        self.accounting.add(0, ActionToken.START, ActionToken.START)
        self.accounting.add(1, ActionToken.NONE, ActionToken.SESSION)
        self.accounting.add(2, ActionToken.SESSION, ActionToken.SESSION)
        self.accounting.add(2, ActionToken.SESSION, ActionToken.EXPLOIT)
        self.accounting.add(2, ActionToken.SESSION, ActionToken.SESSION | ActionToken.EXPLOIT)
        self.accounting.add(3, ActionToken.NONE, ActionToken.SESSION)
        self.accounting.add(4, ActionToken.NONE, ActionToken.EXPLOIT)
        self.accounting.add(5, ActionToken.SESSION | ActionToken.EXPLOIT, ActionToken.AUTH_LIMITED)
        self.accounting.add(6, ActionToken.SESSION | ActionToken.EXPLOIT, ActionToken.DATA)
        self.accounting.add(6, ActionToken.AUTH_LIMITED, ActionToken.DATA)
        self.accounting.add(7, ActionToken.DATA, ActionToken.END)

    def _add_translator(self):
        pass

    def solve_one(self):
        super()._solve_one(service=7, action=7, tokens=[ActionToken.END])

    def solve_all(self):
        super()._solve_all(service=7, action=7, tokens=[ActionToken.END])


# -------------------------------------------------------------------------------------------------------- #
class Speartip(Scenario):
    def __init__(self):
        super().__init__()

    def _add_nodes(self):
        self.graph.add_node("start", cluster=-1)
        self.graph.add_node("aim", cluster=-1)
        self.graph.add_node("node2", cluster=-1)
        self.graph.add_node("node3", cluster=-1)
        self.graph.add_node("node4", cluster=-1)
        self.graph.add_node("node5", cluster=-1)
        self.graph.add_node("node6", cluster=-1)
        self.graph.add_edge("start", "node2")
        self.graph.add_edge("node2", "node3")
        self.graph.add_edge("node2", "node4")
        self.graph.add_edge("node2", "node5")
        self.graph.add_edge("node3", "node6")
        self.graph.add_edge("node4", "node6")
        self.graph.add_edge("node5", "node6")
        self.graph.add_edge("node6", "aim")

    def _add_tables(self):
        ST_tokens = 7
        ST_actions = 7
        ST_services = 7
        ST_hosts = 7

        ST_AS = [[0 for i in range(0, 7)] for j in range(0, 7)]
        for i in range(0, 7):
            ST_AS[i][i] = 1

        ST_AT = [ActionToken.NONE]

        self.tables = Tables(ST_hosts, ST_services, ST_actions, ST_tokens)
        self.tables.nnm = nx.to_numpy_matrix(self.graph).tolist()
        self.tables.asm = ST_AS
        self.tables.atm = ST_AT

    def _add_actions(self):
        self.accounting = TokensAccounting()
        self.accounting.add(0, ActionToken.START, ActionToken.START)
        self.accounting.add(1, ActionToken.NONE, ActionToken.SESSION)
        self.accounting.add(2, ActionToken.SESSION, ActionToken.SESSION)
        self.accounting.add(2, ActionToken.SESSION, ActionToken.EXPLOIT)
        self.accounting.add(2, ActionToken.SESSION, ActionToken.SESSION | ActionToken.EXPLOIT)
        self.accounting.add(3, ActionToken.SESSION, ActionToken.SESSION)
        self.accounting.add(3, ActionToken.SESSION, ActionToken.EXPLOIT)
        self.accounting.add(3, ActionToken.SESSION, ActionToken.SESSION | ActionToken.EXPLOIT)
        self.accounting.add(4, ActionToken.SESSION, ActionToken.SESSION)
        self.accounting.add(4, ActionToken.SESSION, ActionToken.EXPLOIT)
        self.accounting.add(4, ActionToken.SESSION, ActionToken.SESSION | ActionToken.EXPLOIT)
        self.accounting.add(5, ActionToken.SESSION | ActionToken.EXPLOIT, ActionToken.AUTH_LIMITED)
        self.accounting.add(6, ActionToken.AUTH_LIMITED, ActionToken.DATA)

    def _add_translator(self):
        pass

    def solve_one(self):
        super()._solve_one(service=6, action=6, tokens=[ActionToken.DATA])

    def solve_all(self):
        super()._solve_all(service=6, action=6, tokens=[ActionToken.DATA])


# -------------------------------------------------------------------------------------------------------- #
class Trident(Scenario):
    def __init__(self):
        super().__init__()

    def _add_nodes(self):
        self.graph.add_node("start", cluster=-1)
        self.graph.add_node("aim", cluster=-1)
        self.graph.add_node("node2", cluster=-1)
        self.graph.add_node("node3", cluster=-1)
        self.graph.add_node("node4", cluster=-1)
        self.graph.add_edge("start", "node2")
        self.graph.add_edge("node2", "node3")
        self.graph.add_edge("node2", "node4")
        self.graph.add_edge("node2", "aim")

    def _add_tables(self):
        trident_hosts = 5
        trident_services = 5
        trident_actions = 5
        trident_tokens = 7

        trident_AS = [[0 for i in range(0, 5)] for j in range(0, 5)]
        for i in range(0, 5):
            trident_AS[i][i] = 1

        trident_AT = [ActionToken.NONE]
        trident_dummies = [3, 4]

        self.tables = Tables(trident_hosts, trident_services, trident_actions, trident_tokens)
        self.tables.nnm = nx.to_numpy_matrix(self.graph).tolist()
        self.tables.asm = trident_AS
        self.tables.atm = trident_AT
        self.tables.dummies = trident_dummies

    def _add_actions(self):
        self.accounting = TokensAccounting()
        self.accounting.add(0, ActionToken.START, ActionToken.START)
        self.accounting.add(1, ActionToken.NONE, ActionToken.SESSION)
        self.accounting.add(2, ActionToken.SESSION, ActionToken.EXPLOIT)
        self.accounting.add(3, ActionToken.SESSION, ActionToken.AUTH_LIMITED)
        self.accounting.add(4, ActionToken.SESSION, ActionToken.AUTH_LIMITED)

    def _add_translator(self):
        pass

    def solve_one(self):
        super()._solve_one(service=4, action=4, tokens=[ActionToken.AUTH_LIMITED])

    def solve_all(self):
        super()._solve_all(service=4, action=4, tokens=[ActionToken.AUTH_LIMITED])


# -------------------------------------------------------------------------------------------------------- #
class LongTrident(Scenario):
    def __init__(self):
        super().__init__()

    def _add_nodes(self):
        self.graph.add_node("start", cluster=-1)
        self.graph.add_node("aim", cluster=-1)
        self.graph.add_node("node2", cluster=-1)
        self.graph.add_node("node3", cluster=-1)
        self.graph.add_node("node4", cluster=-1)
        self.graph.add_node("node5", cluster=-1)
        self.graph.add_node("node6", cluster=-1)
        self.graph.add_edge("start", "node2")
        self.graph.add_edge("node2", "node3")
        self.graph.add_edge("node2", "node4")
        self.graph.add_edge("node2", "aim")
        self.graph.add_edge("node3", "node6")
        self.graph.add_edge("node4", "node5")

    def _add_tables(self):
        lt_hosts = 7
        lt_services = 6
        lt_actions = 6
        lt_tokens = 7

        lt_AS = [[0 for i in range(0, 6)] for j in range(0, 6)]
        for i in range(0, 6):
            lt_AS[i][i] = 1

        lt_AT = [ActionToken.NONE]
        lt_dummies = [3, 4, 5, 6]

        self.tables = Tables(lt_hosts, lt_services, lt_actions, lt_tokens)
        self.tables.nnm = nx.to_numpy_matrix(self.graph).tolist()
        self.tables.asm = lt_AS
        self.tables.atm = lt_AT
        self.tables.dummies = lt_dummies

    def _add_actions(self):
        self.accounting = TokensAccounting()
        self.accounting.add(0, ActionToken.START, ActionToken.START)
        self.accounting.add(1, ActionToken.NONE, ActionToken.SESSION)
        self.accounting.add(2, ActionToken.SESSION, ActionToken.EXPLOIT)
        self.accounting.add(3, ActionToken.SESSION, ActionToken.AUTH_LIMITED)
        self.accounting.add(4, ActionToken.SESSION, ActionToken.AUTH_LIMITED)
        self.accounting.add(5, ActionToken.EXPLOIT, ActionToken.DATA)

    def _add_translator(self):
        pass

    def solve_one(self):
        super()._solve_one(service=4, action=4, tokens=[ActionToken.AUTH_LIMITED])

    def solve_all(self):
        super()._solve_all(service=4, action=4, tokens=[ActionToken.AUTH_LIMITED])


class BronzeButler(Scenario):
    def __init__(self):
        super().__init__()

    def _add_nodes(self):
        self.graph.add_node("start")
        self.graph.add_node("aim")
        self.graph.add_node("node2")
        self.graph.add_node("node3")
        self.graph.add_node("node4")
        self.graph.add_node("node5")
        self.graph.add_node("node6")
        self.graph.add_node("node7")
        self.graph.add_node("node8")
        self.graph.add_node("node9")
        self.graph.add_node("node10")
        self.graph.add_edge("start", "node2")
        self.graph.add_edge("start", "node3")
        self.graph.add_edge("start", "node4")
        self.graph.add_edge("node2", "aim")
        self.graph.add_edge("node3", "node5")
        self.graph.add_edge("node4", "node6")
        self.graph.add_edge("node5", "node8")
        self.graph.add_edge("node6", "node7")
        self.graph.add_edge("node7", "node8")
        self.graph.add_edge("node8", "node9")
        self.graph.add_edge("node9", "node10")
        self.graph.add_edge("node10", "node2")
        self.graph.add_edge("node10", "aim")

    def _add_tables(self):
        bb_nodes =  11
        bb_services = 8
        bb_actions = 5
        bb_tokens = 7

        bb_AT = [ActionToken.SESSION]


        bb_AS = [[0 for i in range(0, bb_services)] for j in range(0, bb_actions) ]
        #bb_AS[0][1] = 1
        bb_AS[0][2] = 1
        bb_AS[1][3] = 1
        bb_AS[2][4] = 1
        #bb_AS[3][1] = 1
        bb_AS[3][2] = 1
        bb_AS[3][7] = 1
        bb_AS[4][5] = 1

        self.tables = Tables(bb_nodes, bb_services, bb_actions, bb_tokens)
        self.tables.nnm = nx.to_numpy_matrix(self.graph).tolist()
        self.tables.asm = bb_AS
        self.tables.atm = bb_AT

    def _add_actions(self):
        self.accounting = TokensAccounting()
        self.accounting.add(0, ActionToken.SESSION, ActionToken.SESSION | ActionToken.AUTH_LIMITED)  # info discovery
        self.accounting.add(0, ActionToken.SESSION, ActionToken.SESSION | ActionToken.AUTH_ELEVATED)  # info discovery
        self.accounting.add(1, ActionToken.SESSION | ActionToken.AUTH_LIMITED,
                            ActionToken.SESSION | ActionToken.AUTH_LIMITED)  # c2c
        self.accounting.add(1, ActionToken.SESSION | ActionToken.AUTH_ELEVATED,
                            ActionToken.SESSION | ActionToken.AUTH_ELEVATED)  # c2c
        self.accounting.add(2, ActionToken.SESSION, ActionToken.SESSION)  # exploit remote
        self.accounting.add(3, ActionToken.SESSION | ActionToken.AUTH_LIMITED,
                            ActionToken.SESSION | ActionToken.AUTH_ELEVATED)  # privilege escalation
        self.accounting.add(3, ActionToken.SESSION | ActionToken.AUTH_ELEVATED,
                            ActionToken.SESSION | ActionToken.AUTH_ELEVATED)  # privilege escalation
        self.accounting.add(4, ActionToken.SESSION | ActionToken.AUTH_ELEVATED, ActionToken.DATA)  # data extraction

    def _add_translator(self):
        self.translator.add_action(0, "information discovery", ExploitType.NONE, True, True)
        self.translator.add_action(1, "c2c", ExploitType.NONE, False, False)
        self.translator.add_action(2, "exploit remote service", ExploitType.REMOTE, False, True)
        self.translator.add_action(3, "privilege escalation", ExploitType.LOCAL, True, True)
        self.translator.add_action(4, "data exfiltration", ExploitType.NONE, False, False)

        self.translator.add_service(0, "postfix")
        self.translator.add_service(1, "bash")
        self.translator.add_service(2, "powershell")
        self.translator.add_service(3, "rdp")
        self.translator.add_service(4, "skysea")
        self.translator.add_service(5, "mssql")
        self.translator.add_service(6, "iis")
        self.translator.add_service(7, "windows server 2019")

    def solve_one(self):
        super()._solve_one(node=1, service=5,action=4, tokens=[ActionToken.DATA])

    def solve_all(self):
        super()._solve_all(node=1, service=5, action=4, tokens=[ActionToken.DATA])


class BrBuCto(Scenario):
    def __init__(self):
        super().__init__()

    def _add_nodes(self):
        self.graph.add_node("start")
        self.graph.add_node("aim")
        self.graph.add_node("node2")
        self.graph.add_edge("start", "node2")
        self.graph.add_edge("node2", "aim")

    def _add_tables(self):
        bb_nodes =  3
        bb_services = 8
        bb_actions = 5
        bb_tokens = 7

        bb_AT = [ActionToken.SESSION]


        bb_AS = [[0 for i in range(0, bb_services)] for j in range(0, bb_actions) ]
        #bb_AS[0][1] = 1
        bb_AS[0][2] = 1
        bb_AS[1][3] = 1
        bb_AS[2][4] = 1
        #bb_AS[3][1] = 1
        bb_AS[3][2] = 1
        bb_AS[3][7] = 1
        bb_AS[4][5] = 1

        self.tables = Tables(bb_nodes, bb_services, bb_actions, bb_tokens)
        self.tables.nnm = nx.to_numpy_matrix(self.graph).tolist()
        self.tables.asm = bb_AS
        self.tables.atm = bb_AT

    def _add_actions(self):
        self.accounting = TokensAccounting()
        self.accounting.add(0, ActionToken.SESSION, ActionToken.SESSION | ActionToken.AUTH_LIMITED)  # info discovery
        self.accounting.add(0, ActionToken.SESSION, ActionToken.SESSION | ActionToken.AUTH_ELEVATED)  # info discovery
        self.accounting.add(1, ActionToken.SESSION | ActionToken.AUTH_LIMITED,
                            ActionToken.SESSION | ActionToken.AUTH_LIMITED)  # c2c
        self.accounting.add(1, ActionToken.SESSION | ActionToken.AUTH_ELEVATED,
                            ActionToken.SESSION | ActionToken.AUTH_ELEVATED)  # c2c
        self.accounting.add(2, ActionToken.SESSION, ActionToken.SESSION)  # exploit remote
        self.accounting.add(3, ActionToken.SESSION | ActionToken.AUTH_LIMITED,
                            ActionToken.SESSION | ActionToken.AUTH_ELEVATED)  # privilege escalation
        self.accounting.add(3, ActionToken.SESSION | ActionToken.AUTH_ELEVATED,
                            ActionToken.SESSION | ActionToken.AUTH_ELEVATED)  # privilege escalation
        self.accounting.add(4, ActionToken.SESSION | ActionToken.AUTH_ELEVATED, ActionToken.DATA)  # data extraction

    def _add_translator(self):
        self.translator.add_action(0, "information discovery", ExploitType.NONE, True, True)
        self.translator.add_action(1, "c2c", ExploitType.NONE, False, False)
        self.translator.add_action(2, "exploit remote service", ExploitType.REMOTE, False, True)
        self.translator.add_action(3, "privilege escalation", ExploitType.LOCAL, True, True)
        self.translator.add_action(4, "data exfiltration", ExploitType.NONE, False, False)

        self.translator.add_service(0, "postfix")
        self.translator.add_service(1, "bash")
        self.translator.add_service(2, "powershell")
        self.translator.add_service(3, "rdp")
        self.translator.add_service(4, "skysea")
        self.translator.add_service(5, "mssql")
        self.translator.add_service(6, "iis")
        self.translator.add_service(7, "windows server 2019")

    def solve_one(self):
        super()._solve_one(node=1, service=5,action=4, tokens=[ActionToken.DATA])

    def solve_all(self):
        super()._solve_all(node=1, service=5, action=4, tokens=[ActionToken.DATA])


class BrBuVPN(Scenario):
    def __init__(self):
        super().__init__()

    def _add_nodes(self):
        self.graph.add_node("start")
        self.graph.add_node("aim")
        self.graph.add_node("node3")
        self.graph.add_node("node5")
        self.graph.add_node("node8")
        self.graph.add_node("node9")
        self.graph.add_node("node10")
        self.graph.add_node("node11")
        self.graph.add_edge("start", "node3")
        self.graph.add_edge("node3", "node5")
        self.graph.add_edge("node5", "node8")
        self.graph.add_edge("node8", "node9")
        self.graph.add_edge("node9", "node10")
        self.graph.add_edge("node10", "node11")
        self.graph.add_edge("node11", "aim")

    def _add_tables(self):
        bb_nodes = 8
        bb_services = 8
        bb_actions = 5
        bb_tokens = 7

        bb_AT = [ActionToken.SESSION]


        bb_AS = [[0 for i in range(0, bb_services)] for j in range(0, bb_actions)]
        # bb_AS[0][1] = 1
        bb_AS[0][2] = 1
        bb_AS[1][3] = 1
        bb_AS[2][4] = 1
        # bb_AS[3][1] = 1
        bb_AS[3][2] = 1
        bb_AS[3][7] = 1
        bb_AS[4][5] = 1

        self.tables = Tables(bb_nodes, bb_services, bb_actions, bb_tokens)
        self.tables.nnm = nx.to_numpy_matrix(self.graph).tolist()
        self.tables.asm = bb_AS
        self.tables.atm = bb_AT


    def _add_actions(self):
        self.accounting = TokensAccounting()
        self.accounting.add(0, ActionToken.SESSION, ActionToken.SESSION | ActionToken.AUTH_LIMITED) # info discovery
        self.accounting.add(0, ActionToken.SESSION, ActionToken.SESSION | ActionToken.AUTH_ELEVATED) # info discovery
        self.accounting.add(1, ActionToken.SESSION | ActionToken.AUTH_LIMITED, ActionToken.SESSION | ActionToken.AUTH_LIMITED) # c2c
        self.accounting.add(1, ActionToken.SESSION | ActionToken.AUTH_ELEVATED,
                            ActionToken.SESSION | ActionToken.AUTH_ELEVATED)  # c2c
        self.accounting.add(2, ActionToken.SESSION, ActionToken.SESSION) # exploit remote
        self.accounting.add(3, ActionToken.SESSION | ActionToken.AUTH_LIMITED, ActionToken.SESSION | ActionToken.AUTH_ELEVATED) # privilege escalation
        self.accounting.add(3, ActionToken.SESSION | ActionToken.AUTH_ELEVATED,
                            ActionToken.SESSION | ActionToken.AUTH_ELEVATED)  # privilege escalation
        self.accounting.add(4, ActionToken.SESSION | ActionToken.AUTH_ELEVATED, ActionToken.DATA) # data extraction

    def _add_translator(self):
        self.translator.add_action(0, "information discovery", ExploitType.NONE, True, True)
        self.translator.add_action(1, "c2c", ExploitType.NONE, False, False)
        self.translator.add_action(2, "exploit remote service", ExploitType.REMOTE, False, True)
        self.translator.add_action(3, "privilege escalation", ExploitType.LOCAL, True, True)
        self.translator.add_action(4, "data exfiltration", ExploitType.NONE, False, False)

        self.translator.add_service(0, "postfix")
        self.translator.add_service(1, "bash")
        self.translator.add_service(2, "powershell")
        self.translator.add_service(3, "rdp")
        self.translator.add_service(4, "skysea")
        self.translator.add_service(5, "mssql")
        self.translator.add_service(6, "iis")
        self.translator.add_service(7, "windows server 2019")


    def solve_one(self):
        super()._solve_one(node=1, service=5,action=4, tokens=[ActionToken.DATA])

    def solve_all(self):
        super()._solve_all(node=1, service=5, action=4, tokens=[ActionToken.DATA])




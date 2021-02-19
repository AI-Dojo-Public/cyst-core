from tools.scenario_creat.action_mapper.constraints import TokensAccounting, ActionToken
from tools.scenario_creat.action_mapper.solver import Solver
from tools.scenario_creat.clustering.clusterer import Clusterer
import matplotlib.pyplot as plt
import networkx as nx
from abc import abstractmethod, ABC

class Scenario(ABC):
    def __init__(self):
        self.graph = nx.DiGraph()
        self.tables = None
        self.accounting = TokensAccounting()
        self._add_nodes()
        self._add_tables()
        self._add_actions()
        self.solver = Solver(self.tables, self.accounting)

    ### BUILDING ###
    @abstractmethod
    def _add_nodes(self):
        """
        Implement this method, where you create or assign your graph.
        :return: NIL
        """
        pass

    @abstractmethod
    def _add_tables(self):
        """
        Implement this method so it creates or assigns the associations needed for mapping actions.
        :return:
        """
        pass

    @abstractmethod
    def _add_actions(self):
        """
        Implement this method so it creates or assigns the action-token accounting.
        :return:
        """
        pass

    ### API ###
    @abstractmethod
    def solve_one(self):
        """
        Hardcode the parameters for the _solve_one method.
        :return:
        """
        pass

    @abstractmethod
    def solve_all(self):
        """
        Hardcode the parameters for the _solve_all method.
        :return:
        """
        pass

    def show_graph(self):
        self._show_graph()

    ### IMPLEMENTATION ###
    def _show_graph(self):
        color_map = []
        for node in self.graph.nodes:
            color_map.append("yellow" if node == "start" else ("green" if node == "aim" else "blue"))
        nx.draw(self.graph, node_size=25, node_color=color_map, width=1, with_labels=True)
        plt.show()


    def _solve_one(self, node=1, service=1, action=1, tokens=None):
        self.result = self.solver.solve_one(node, service, action, tokens)
        self.solver.mappings(self.result)
        clusterer = Clusterer(self.graph, self.solver.mappings(self.result), 0.9)
        print(clusterer.cluster())

    def yield_mappings(self, node=1, service=1, action=1, tokens=None):
        self.results = self.solver.solve_all(node, service, action, tokens)
        for i, sol in enumerate(self.results):
            mapping = self.solver.mappings(sol)
            clusterer = Clusterer(self.graph, mapping, 0.9)
            yield clusterer.cluster(), mapping

    def _solve_all(self, node=1, service=1, action=1, tokens=None):
        self.results = self.solver.solve_all(node, service, action, tokens)
        for i, sol in enumerate(self.results):
            print(i+1)
            self.solver.show(sol)
            clusterer = Clusterer(self.graph, self.solver.mappings(sol), 0.9)
            print(clusterer.cluster())
            inp = "n"
            inp = str(input("Push n to show next."))
            if inp == "n":
                continue
            return

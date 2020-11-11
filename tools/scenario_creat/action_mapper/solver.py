import itertools
from math import log2
from tools.scenario_creat.action_mapper.constraints import Tables, TokensAccounting, ActionToken, combine
from pyeda.inter import *
from typing import List, Tuple, Set, Optional, Iterable, Dict
from deprecated import deprecated

def compute_token(action: int, actions: List[int], tokens: List[ActionToken]) -> Tuple[int, Tuple[ActionToken]]:
    """
    Computes which tokens are provided by each action in a combination.

    :param action: The action ID we are looking for.
    :param actions: The actions in the combination.
    :param tokens: The tokens - used to match combination order to provided tokens.

    :return: A tuple of the action and the tokens it provides.
    """
    providing = []
    for i in range(0, len(actions)):
        if actions[i] == action:
            providing.append(tokens[i])
    return action, tuple(providing)


def satisfy_node_count(combination: Tuple, max_population: int, tokens: List[List[ActionToken]]) \
        -> Tuple[bool, Optional[Set[Tuple[int, Tuple[ActionToken]]]]]:
    """
    Decides whether a combination of possible combinations of actions needs the same number of nodes,
     as the number of connected nodes.

    :param combination: The combination of action combinations.
    :param max_population: The number of connected nodes.
    :param tokens: The tokens provided (gives ordering).
    :return: True on equality, plus a set of action : tokens provided pairs.
    """
    result = set()
    for e in combination:
        for action in e[0]:
            result.add(compute_token(action, e[0], tokens[e[1]]))
    if len(result) == max_population:
        return True, result
    return False, None


def create_combinations(providers: List[Tuple[List[int], int]], max_population: int, tokens: List[List[ActionToken]]) \
        -> Iterable[Set[Tuple[int, Tuple[ActionToken]]]]:
    """
    Computes all combinations of combinations needing equal number of nodes as available.

    :param providers: Action combinations.
    :param max_population: Nodes available.
    :param tokens: Tokens for their ordering.
    :return: A set of Tuples, consisting of actions and the tokens they provide.
    """
    for i in range(1, max_population + 1):  # i = 1 -- one combination uses all nodes;
        # i = max -- all combinations are one action only
        for e in itertools.combinations(providers, i):
            success, result = satisfy_node_count(e, max_population, tokens)
            if success:
                yield result


class Solver(object):
    """
    A class capable of mapping actions into attack graphs.
    """
    def __init__(self, tables: Tables, token_accounting: TokensAccounting) -> None:
        """

        :param tables: Object representing relations(nodes, action-service, ...).
        :param token_accounting: Object representing action-action associations via tokens.
        """
        self._tables = tables
        self._accounting = token_accounting
        self._node_service_matrix = exprvars('nsa', (0, tables.nodes), (0, tables.services),
                                             (0, tables.actions), (0, tables.tokens))
        self._subformulas = {}  # to save computed formulas
        self._all_needed_tokens = set()
        self._all_needed_tokens.add(ActionToken.NONE)
        self._all_needed_tokens.add(ActionToken.START)

    @property
    def tables(self):
        return self._tables

    @property
    def nsa(self):
        return self._node_service_matrix

    @property
    def all_needed_tokens(self) -> Set[ActionToken]:
        return self._all_needed_tokens

    ### API ###
    def solve_one(self, aim_node: int = 1, aim_service: int = 1, aim_action: int = 1, aim_tokens=None):
        """
        Compute one possible mapping for the attack graph and given goal.

        :param aim_tokens: The list of tokens we want to get from the aim action.
        :param aim_node: the target nodes index in the adjacency matrix
        :param aim_service: the service we want to use in the ultimate goal of the simulation
        :param aim_action:  the action to be carried out as the goal

        :return: The result computed by the SAT solver.
        """
        # the pseudo-random graphs have their target node on index 1
        if aim_tokens is None:
            aim_tokens = [ActionToken.NONE]
        formula = self._construct(aim_node, aim_service, aim_action, aim_tokens)

        if formula is not None:
            result = formula.satisfy_one()
            if result is not None:
                return result

        print("Unsolvable.")

    def solve_all(self, aim_node: int = 1, aim_service: int = 1, aim_action: int = 1, aim_tokens=None):
        """
        Compute all possible mappings for the attack graph and given goal.

        :param aim_tokens: The list of tokens we want to get from the aim action.
        :param aim_node: the target nodes index in the adjacency matrix
        :param aim_service: the service we want to use in the ultimate goal of the simulation
        :param aim_action:  the action to be carried out as the goal
        :return: A set of results computed by the SAT solver.
        """
        if aim_tokens is None:
            aim_tokens = [ActionToken.NONE]
        formula = self._construct(aim_node, aim_service, aim_action, aim_tokens)
        print(formula)

        if formula is not None:
            result = formula.satisfy_all()
            if result is not None:
                return result
        print("Unsolvable.")

    def show(self, result) -> None:
        """
        Combines the utility matrix and the result from the SAT solver into a 2D matrix.

        :param result: result from SAT solver
        :return: A matrix representing the node-service-action associations.
        """
        tokens = {}
        for n in range(0, self.tables.nodes):
            tokens[n] = []
        if result is None:
            print("nothing to show")
            return None
        outmatrix = {}


        for n in range(0, self.tables.nodes):
            for s in range(0, self.tables.services):
                for a in range(0, self.tables.actions):
                    for t in range(0, self.tables.tokens):
                        if self.nsa[n,s,a,t] == expr(1) or result.get(self.nsa[n,s,a,t], 0) == 1:
                            outmatrix[n] = (s , a)
                            tokens[n].append(ActionToken(2**t))
        for node in range(1, self.tables.nodes):
            print("node: {} - service: {} - action: {} - tokens: {}".format(
                node, outmatrix[node][0], outmatrix[node][1], tokens[node]
            ))



    def mappings(self, result) -> Dict[int, Tuple[int, int]]:
        output = {}
        output[0] = (-1,-1)
        for n in range(0, self.tables.nodes):
            for s in range(0, self.tables.services):
                for a in range(0, self.tables.actions):
                    for t in range(0, self.tables.tokens):
                        if self.nsa[n, s, a, t] == expr(1) or result.get(self.nsa[n, s, a, t], 0) == 1:
                            output[n] = (s, a)
        return output


    ### IMPLEMENTATION ###
    def _solve_first_level(self) -> None:
        """
        For each node that is accessible from the root in one step, set every unusable combination of
        service - action to expr(0). Unusability is defined by the needed tokens, and the tokens available
        to the attacker at the beginning.

        :return: NIL
         """
        # create a formula describing the poss   ible mappings
        first_level = And(*[Equal(self.nsa[n, s, a, t],
                                  And(
                                      self._accounting.needs_met(a, self.tables.atm),
                                      self.tables.asm[a, s]
                                  )
                                  )
                            for n in range(1, self.tables.nodes) if self.tables.nnm[0, n]
                            for s in range(0, self.tables.services)
                            for a in range(0, self.tables.actions)
                            for t in range(0, self.tables.tokens)])

        res = first_level.satisfy_one()  # solve the formula
        for n in range(1, self.tables.nodes):  # and apply result to the utility matrix
            if self.tables.nnm[0, n]:
                for s in range(0, self.tables.services):
                    for a in range(0, self.tables.actions):
                        for t in range(0, self.tables.tokens):
                            if res[self.nsa[n, s, a, t]] == 0:
                                self.nsa[n, s, a, t] = expr(0)

    def _set_constraints(self, aim_node: int, aim_service: int, aim_action: int, tokens: List[ActionToken]) -> None:
        """
        Creates simple constraints that limit the results of the mapping.

        :param aim_node: the target nodes index in the adjacency matrix
        :param aim_service: the service we want to use in the ultimate goal of the simulation
        :param aim_action:  the action to be carried out as the goal
        :return: NIL
        """
        for s in range(0, self.tables.services):
            for a in range(0, self.tables.actions):  # sets root node and target nodes variables to expr(0)
                for t in range(0, self.tables.tokens):
                    self.nsa[aim_node, s, a, t] = expr(0)
                    self.nsa[0, s, a, t] = expr(0)
        for token in tokens:
            self.nsa[aim_node, aim_service, aim_action, int(log2(token))] = expr(1)  # sets variable representing the goal to expr(1)
                                    # log2 gives the order of the token as they are flags with values power(2, x)
        self._first_level = [n for n in range(0, self.tables.nodes) if self.tables.nnm[0, n]]  # nodes in 1 hop
        # distance from root
        self._solve_first_level()  # prepare the utility matrix

        # constraint saying that each node has to be associated with one service
        self._one_service = \
            And(*[
                OneHot(*[
                    Or(*[
                        And(
                            Or(*[self.nsa[n, s, a, t] for t in range(0, self.tables.tokens)]),
                            self.tables.asm[a, s])
                    for a in range(0, self.tables.actions)])
                for s in range(0, self.tables.services)])
            for n in range(1, self.tables.nodes)])

        # constraint saying that each node-service pair has to be associated with one action
        self._one_action_per_node = \
            And(*[
                And(*[
                    OneHot0(*[
                        And(
                            Or(*[self.nsa[n, s, a, t] for t in range(0, self.tables.tokens)]),
                                self.tables.asm[a, s])
                    for a in range(0, self.tables.actions)])
                for s in range(0, self.tables.services)])
            for n in range(1, self.tables.nodes)])

    def _useless_dummies(self) -> 'pyeda.boolalg.expression':  # must be computed after the core
        """

        :return: A formula saying that nodes on blind branches must be associated with actions, which DO NOT give any
        tokens needed on ANY possible path from the root to aim.
        """
        return And(*[
            Or(*[self.nsa[dummy, s, a, t]
                 for a in range(0, self._tables.services)
                 if self._accounting.gives_none_of(a, list(self._all_needed_tokens))
                 for t in range(0, self.tables.tokens)
                 for s in range(0, self._tables.services) if self._tables.asm[a, s]
                 ])
            for dummy in self._tables.dummies
        ])

    def _dummies_unneeded_tokens(self):
        """

        :return: A formula that makes the SAT exclude dummy associations with tokens that are needed, or with tokens
         which the associated action does not grant.
        """
        return And(*[
            Not(self.nsa[dummy, s, a, t])
            for dummy in self._tables.dummies
            for s in range(0, self._tables.services)
            for a in range(0, self._tables.actions) if self._tables.asm[a, s]
            for t in range(0, self._tables.tokens) if 2 ** t in self._all_needed_tokens or
                                                      not self._accounting.check_if_provides(a, [2 ** t])
        ])

    def _create(self, aim_node: int, aim_service: int, aim_action: int, aim_tokens) -> 'pyeda.boolalg.expr':
        """
        Wraps the call for the recursive core formula creation.

        ::param aim_node: the target nodes index in the adjacency matrix
        :param aim_service: the service we want to use in the ultimate goal of the simulation
        :param aim_action:  the action to be carried out as the goal
        :return: The created formula.
        """
        return self._create_core(aim_node, aim_service, aim_action, aim_tokens)

    def _construct(self, aim_node: int, aim_service: int, aim_action: int, aim_tokens: Optional[List[ActionToken]])\
            -> 'pyeda.boolalg.expr':
        """
        Constructs the whole formula, combining the core and the constraints.

        :param aim_node: the target nodes index in the adjacency matrix
        :param aim_service: the service we want to use in the ultimate goal of the simulation
        :param aim_action:  the action to be carried out as the goal
        :return: The created formula.
        """
        if not self.tables.asm[aim_action, aim_service]:  # goal is erroneously defined
            print("action unavailable for service")
            return
        if aim_tokens is None or not isinstance(aim_tokens, list):
            print("output token not defined, or not a list")
            return
        if not self._accounting.check_if_provides(aim_action, aim_tokens):
            print("specified action can not provide wanted tokens")
            return

        self._set_constraints(aim_node, aim_service, aim_action, aim_tokens)

        return And(self._create(aim_node, aim_service, aim_action, aim_tokens), self._one_service,
                   self._one_action_per_node, self._useless_dummies(), self._dummies_unneeded_tokens())

    def _create_core(self, aim_node: int, aim_service: int, aim_action: int,
                                  tokens: List[ActionToken], depth = 0) -> 'pyeda.boolalg.expr':
        """
        Creates the core formula representing all valid sequences that lead
        from the root to reaching the ultimate goal of the scenario

        :param aim_node: the host we want to reach
        :param aim_service: the service we want to use on that host
        :param aim_action: the action to carry out on the host and service
        :param tokens: list of tokens aim_action must provide
        :param depth: debug only

        :return: The created formula.
        """
        #print(depth * "\t" , aim_node, aim_service, aim_action, tokens)
        for token in tokens:
            self._all_needed_tokens.add(token)
        if aim_node in self._first_level:  # we reached the nodes 1 hop from the root, stop recursion
            return expr(1)

        new_formula = self._subformulas.get((aim_node, aim_service, aim_action, combine(tokens)),
                                            None)  # if we have already computed
        if new_formula is not None:
            return new_formula

        needed_tokens = self._accounting.get_needed(tokens,
                                                    aim_action)  # compute needed input combinations for this action to give wanted output
        parents = [n for n in range(1, self.tables.nodes) if self.tables.nnm[n, aim_node]]  # gather connected nodes

        new_formula =  self._create_for_all_token_sets(parents, needed_tokens, depth)

        self._subformulas[(aim_node, aim_service, aim_action, combine(tokens))] = new_formula

        return new_formula


    def _create_for_all_token_sets(self, nodes: List[int], token_set: List[List[ActionToken]]
                                   , depth) -> 'pyeda.boolalg.expression':
        """

        :param nodes: List of nodes we ca connect to.
        :param token_set: The precise set of tokens we calculate for.

        :return: A pyeda expresion representing all the possible paths to the root,
         for the specific set of needed tokens.
        """
        providers = []
        for i in range(0, len(token_set)):
            prov = self._accounting.get_providing(token_set[i])
            for e in prov:
                providers.append((e, i))
        return Or(*[  # one combination of providing action combinations must be satisfied
            self._create_for_action_set(nodes, combo,depth)
            for combo in create_combinations(providers, len(nodes), token_set)])
        # for each combination of the combinations that satisfy node count

    def _create_for_action_set(self, nodes: List[int], combo: Set[Tuple[int, Tuple[ActionToken]]],
                                depth) -> 'pyeda.boolalg.expression':
        """
        Creates the formula for one possible combination of combinations of actions providing all needed tokens.

        :param nodes: List of nodes we ca connect to.
        :param combo: The combination of actions and tokens provided we must use simultaneously.

        :return: A pyeda expression representing all the possible paths to the root,
         using the actions and tokens from combo, in this step.
        """
        return Or(*[  # one node-to-action mapping must be used
            self._create_for_one_mapping(list(combo), perm, depth)
            for perm in itertools.permutations(nodes)])
        # for all possible node to action mappings

    def _create_for_one_mapping(self, combo: List[Tuple[int, Tuple[ActionToken]]], nodes: Tuple[int]
                                , depth) -> 'pyeda.boolag.expression':
        """
         Creates the formula for on possible node-action mapping - the mapping is represented
         by the order of the list "nodes".

        :param combo: The list of action - provided token pairs.
        :param nodes: The list of nodes to connect to, the i-th node gets associated with the i-th action from combo.
        :return: A pyeda expression representing the path to the root, using tha actions from combo, mapped to the nodes
        in order of "nodes". Each node must be associated with an action.
        """
        return And(*[  # all branchings have to be mapped
            Or(*[  # we may choose between more services -- one is necessary
                And(
                    *[Equal(self.nsa[nodes[i], s, combo[i][0], t], 2**t in list(combo[i][1]))
                      for t in range(0, self.tables.tokens)],
                    self._valid_dummies(nodes[i], list(combo[i][1])),
                    self._create_core(nodes[i], s, combo[i][0], list(combo[i][1]), depth+1)) # recursive dive
                for s in range(0, self._tables.services) if self._tables.asm[combo[i][0], s]])
            for i in range(0, len(nodes))])

    def _valid_dummies(self, host_from: int, tokens_from: List[ActionToken])\
           -> 'pyeda.boolalg.expression':
        """

        :param host_from: The node the dummies are reachable from.
        :param tokens_from: The tokens the reachable node provides.
        :return: A formula defining that for each connected dummy node, on possibility of mapping must be true,
            the mappings are restricted to actions that are doable with the tokens the from node provides.
        """

        connected_dummies = [dummy for dummy in self._tables.dummies if self._tables.nnm[host_from, dummy]]
        return And(*[
                    Or(*[
                        And(self.nsa[dummy, s, a, int(log2(t))], self._valid_dummies(dummy, self._accounting.action_grants(a)))
                        for a in range(0, self._tables.actions) if self._accounting.needs_met(a, tokens_from)
                        for s in range(0, self._tables.services) if self._tables.asm[a, s]
                        for t in self._accounting.action_grants(a)
                    ])
                    for dummy in connected_dummies
                ])


    ### OLD ###
    """@deprecated(reason="The way actions and their tokens are represented changed.")
    def _create_formula(self, aim_node: int, aim_service: int, aim_action: int, depth: int) -> 'pyeda.boolalg.expr':
  
        if aim_node in self._first_level:  # we reached the nodes 1 hop from the root
            return self.nsa[aim_node, aim_service, aim_action]  # return the value from the utility matrix

        new_formula = self._subformulas.get((aim_node, aim_service, aim_action), None)  # if we have already computed
        if new_formula is not None:
            return new_formula

        print(depth * '\t', aim_node, aim_service, aim_action)
        new_formula = expr(1)
        for h in range(1, self.tables.nodes):  # for each parent of the actual node
            if h != aim_node and self.tables.nnm[h, aim_node]:
                # construct the possible sequences
                new_subformula = Or(*[
                    And(self.nsa[h, s, a],
                        self._create_formula(h, s, a, depth + 1))  # recursive dive
                    for s, a in itertools.product(range(self.tables.services), range(self.tables.actions))
                    if self.tables.asm[a, s] and  # if action is usable for the service and
                       # the action a provides all needed tokens for aim_action -- or aim_Action needs no tokens
                       Or(
                           Nor(*[self.tables.ainm[aim_action, t]
                                 for t in range(0, self.tables.tokens)]),
                           Or(*[
                               And(self.tables.ainm[aim_action, t], self.tables.aoutm[a, t])
                               for t in range(0, self.tables.tokens)]
                              )
                       )
                ])

                new_formula = And(new_formula, new_subformula)  # all paths must be evaluated

                self._subformulas[
                    (aim_node, aim_service, aim_action)] = new_formula  # save so it can be simply found if needed again

        return new_formula"""

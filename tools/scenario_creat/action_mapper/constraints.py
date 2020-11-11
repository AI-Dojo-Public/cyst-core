from collections import namedtuple

import pyeda
import itertools
from pyeda.inter import *
from typing import List, Dict, Set, Optional
from enum import IntFlag
from deprecated import deprecated


class ActionToken(IntFlag):
    NONE = 1,
    SESSION = 2,
    EXPLOIT = 4,
    AUTH = 8,
    DATA = 16,
    START = 32,
    END = 64


TokenFlow = namedtuple("TokenFlow", ["IN", "OUT"], defaults=[ActionToken.NONE, ActionToken.NONE])


def decompose(token: ActionToken) -> List[ActionToken]:
    """
    Decomposes a complex token into a set of base tokens.

    :param token: A complex token.
    :return: A set of base tokens.
    """
    result = list()
    if token & ActionToken.NONE:
        result.append(ActionToken.NONE)
    if token & ActionToken.SESSION:
        result.append(ActionToken.SESSION)
    if token & ActionToken.EXPLOIT:
        result.append(ActionToken.EXPLOIT)
    if token & ActionToken.AUTH:
        result.append(ActionToken.AUTH)
    if token & ActionToken.DATA:
        result.append(ActionToken.DATA)
    if token & ActionToken.START:
        result.append(ActionToken.START)
    if token & ActionToken.END:
        result.append(ActionToken.END)
    return result


def combine(tokens: List[ActionToken]) -> ActionToken:
    """
    Combines a list of base tokens into one complex.

    :param tokens: A nonempty list of tokens.
    :return: A complex token.
    """
    result = tokens[0]
    for e in tokens:
        result |= e
    return result


def fill(raw: List[List[int]], exprmatrix: 'pyeda.boolalg.bfarray.farray') -> None:
    """
    Translates a simple matrix (list of lists) into a pyeda expression matrix.

    :param raw: the simple matrix
    :param exprmatrix: the expression matrix to be filled
    :return: NIL
    """

    if len(raw) != len(exprmatrix):
        raise ValueError("Nonmatching matrices.")
    for r in range(0, len(raw)):
        if len(raw[r]) != len(exprmatrix[r]):
            raise ValueError("Nonmatching matrices.")
        for c in range(0, len(raw[r])):
            if raw[r][c] not in [0, 1]:
                raise ValueError("Not a truth matrix")
    for r in range(0, len(raw)):
        for c in range(0, len(raw[r])):
            exprmatrix[r, c] = expr(raw[r][c])


class Tables(object):
    def __init__(self, nodes: int, services: int, actions: int, tokens: int) -> None:
        """
        Creates an object of all needed matrices, these matrices are empty after construction, they need to be filled.

        :param hosts: number of hosts available for scenario
        :param services: number of services available for scenario
        :param actions: number of actions available for scenario
        :param tokens: number of tokens available for scenario
        """
        self._nodes = nodes
        self._services = services
        self._actions = actions
        self._tokens = tokens
        self._node_matrix = exprvars("nn", (0, self.nodes), (0, self.nodes))
        self._action_service_matrix = exprvars("as", (0, self.actions), (0, self.services))
        self._available_token_matrix = []
        self._dummies = set()


    @property
    def nodes(self) -> int:
        return self._nodes

    @property
    def services(self) -> int:
        return self._services

    @property
    def actions(self) -> int:
        return self._actions

    @property
    def tokens(self) -> int:
        return self._tokens

    @property
    def nnm(self) -> 'pyeda.boolalg.bfarray.farray':
        return self._node_matrix

    @property
    def asm(self) -> 'pyeda.boolalg.bfarray.farray':
        return self._action_service_matrix

    @property
    def atm(self) -> List[ActionToken]:
        return self._available_token_matrix

    @property
    def dummies(self) -> Set[int]:
        return self._dummies

    @nnm.setter
    def nnm(self, base_matrix: List[List[int]]) -> None:
        fill(base_matrix, self._node_matrix)

    @asm.setter
    def asm(self, base_matrix: List[List[int]]) -> None:
        fill(base_matrix, self.asm)

    @atm.setter
    def atm(self, base_matrix: List[ActionToken]) -> None:
        self._available_token_matrix = base_matrix

    @dummies.setter
    def dummies(self, values: Set[int]) -> None:
        self._dummies = values


class TokensAccounting(object):
    def __init__(self):
        self._action_tokens = dict()
        # A constraint for this dictionary: if for an action tokens (in -> out):
        # 1 -> 2
        # 3 -> 4 hold, then
        # 1,3 -> 2,4 must hold too, this must be taken care of at filling the class with associations.

    ### API ###
    def add(self, action: int, in_token: ActionToken, out_token: ActionToken) -> None:
        """
        Places the action, token-in, token-out association into the memory.

        :param action: The action's ID.
        :param in_token: Token needed for the action.
        :param out_token:  Token provided by the action and the specific needed token.
        :return: NIL
        """
        target = self._action_tokens.get(action, None)
        if target is None:
            self._action_tokens[action] = [TokenFlow(in_token, out_token)]
            return
        target.append(TokenFlow(in_token, out_token))


    def get_providing(self, tokens: List[ActionToken]) -> List[List[int]]:
        """
        Computes all combinations of actions that provide all needed tokens.

        :param tokens: Needed tokens.
        :return: Combinations in the form of list of lists.
        """
        return self._products(self._get(tokens))

    def get_needed(self, tokens: List[ActionToken], action: int) -> List[List[ActionToken]]:
        """
        For an action and a list of tokens needed to be provided by it, computes the compulsory inputs.

        :param tokens: Tokens to provide.
        :param action: ID of the action.
        :return: A list of possible token combinations needed.
        """
        token = combine(tokens)
        target = self._action_tokens.get(action, None)
        result = []
        if target is None:
            return result
        for e in target:
            if e.OUT  == token:  # exact token, partially fitting dont count, supersets either
                result.append(decompose(e.IN))
        return result

    def needs_met(self, action: int, available_tokens) -> 'pyeda.boolalg.expression':
        """
        Checks whether the available_tokens provide all the tokens for at least one input for the action.

        :param action: The action's ID.
        :param available_tokens: The tokens available.
        :return: True if the available tokens suffice.
        """
        available_token = combine(available_tokens)
        for e in self._action_tokens[action]:
            if e.IN & ActionToken.NONE or e.IN == available_token:
                return expr(1)
        return expr(0)

    def check_if_provides(self, action:int, tokens: List[ActionToken]) -> bool:
        """
        Checks whether the given action provides the given tokens.

        :param action: Action ID.
        :param tokens: List of tokens
        :return: True if action provides all needed tokens.
        """
        token = combine(tokens)
        for e in self._action_tokens[action]:
            if token == e.OUT:
                return True
        return False

    def gives_none_of(self, action: int, tokens: List[ActionToken]) -> bool:
        for e in self._action_tokens[action]:
            for token in tokens:
                if e.OUT & token:
                    return False
        return True

    def action_grants(self, action: int) -> List[ActionToken]:
        tokens = set()
        for e in self._action_tokens[action]:
            for token in decompose(e.OUT):
                tokens.add(token)
        return list(tokens)


    ### IMPLEMENTATION ###
    def _get(self, tokens: List[ActionToken]) -> Optional[Dict[ActionToken, Set[int]]]:
        """
        Computes all actions providing one of the tokens needed.

        :param tokens: The tokens needed.
        :return: A dictionary of tokens: actions that provide them.
        """
        results = dict()
        for token in tokens:
            sub_result = set()
            for key, value in self._action_tokens.items():
                for e in value:
                    if e.OUT & token == token:
                        sub_result.add(key)
                        break  # no need to check other possibilities if once provides
            results[token] = sub_result
        return results

    @staticmethod
    def _products(providing: Dict[ActionToken, Set[int]]) -> List[List[int]]:
        """
        Computes combinations of actions providing all the needed tokens at once.

        :param providing: A dictionary of tokens: actions that provide them.
        :return: A list of lists, the sublist include action ID's providing the token based on their index in the list.
        """
        products = [list(h) for h in itertools.product(*providing.values())]
        return products

    ### OLD ###
    @deprecated(reason="We decided not to prefer minimal sets of actions."
                       "Might be useful in the future tho.")
    def _remove_supersets(self, products: List[List[int]]) -> List[List[int]]:
        """
        Removes combinations that are supersets of others.
        :param products:  A List of combinations.
        :return: The list without subsets.
        """
        for e in products:
            for o in products:
                set_e = set(e)
                set_o = set(o)
                if set_e != set_o and set_e.issubset(set_o):
                    products.remove(o)
        return products

    @deprecated(reason="The way possible combinations are computed changed, no need for categorizing."
                       " Might be useful in the future tho.")
    def _categorize(self, results: List[List[int]]) -> Dict[int, List[List[int]]]:
        """
        Categorizes the combinations based on how many action are needed for them,
         for example: {3:[[1,2,3]], 2:[[1,2,2]]}.

        :param results: The combinations.
        :return: A dictionary of  actions needed: combinations.
        """
        categorized = dict()
        for e in results:
            num = len(set(e))
            target = categorized.get(num, None)
            if target is None:
                categorized[num] = [e]
            else:
                target.append(e)
        return categorized

import pickle
from fractions import Fraction
from typing import Dict, Set

import z3
from z3 import RealVal

from pric3.oracles.oracle import Oracle
from pric3.state_graph import StateGraph, StateId

_SerializedData = Dict[str, Fraction]


def save_oracle_dict(state_graph: StateGraph,
                     oracle_dict: Dict[StateId, z3.ExprRef],
                     filename="oracle.pr"):
    """
    Save an oracle's dict to a file.
    """
    fd = open(filename, "wb")
    data: _SerializedData = {
        str(state_graph.get_state_valuation(state_id)): value.as_fraction()
        for state_id, value in oracle_dict.items()
    }
    pickle.dump(data, fd)
    fd.close()


def _load_oracle_dict(state_graph: StateGraph,
                      filename="oracle.pr") -> Dict[StateId, z3.ExprRef]:
    """
    Load an oracle's dict from a file.

    Note that the state ids are different on each load!
    """
    fd = open(filename, "rb")
    data: _SerializedData = pickle.load(fd)
    fd.close()

    oracle: Dict[StateId, z3.ExprRef] = dict()

    to_consider: Set[StateId] = {state_graph.get_initial_state_id()}
    seen: Set[StateId] = set()

    while len(data) != 0:
        to_consider = to_consider - seen
        to_add: Set[StateId] = set()

        for state_id in to_consider:
            seen.add(state_id)

            state_val_str = str(state_graph.get_state_valuation(state_id))
            if state_val_str in oracle:
                oracle[state_id] = RealVal(data[state_val_str])
                del data[state_val_str]

            to_add = to_add.union({
                state
                for state, prob in state_graph.get_successor_distribution(
                    state_id)
            })

    return oracle


class FileOracle(Oracle):
    """
    A static oracle loaded from a file.
    """
    def initialize(self):
        self.oracle = _load_oracle_dict(self.state_graph)

from abc import ABC, abstractmethod
import logging
from fractions import Fraction
from typing import Set, Dict

import z3
from z3 import Real, RealVal, Solver, Sum, sat, Optimize

from pric3.state_graph import StateGraph, StateId
from pric3.statistics import Statistics
from pric3.settings import Settings

from stormpy.storage import PrismModelType

logger = logging.getLogger(__name__)

class Oracle(ABC):
    """
    An oracle is a dict from state_ids to values (not neccessarily probabilities since o.w. the eq system does not always have a solution).

    This is an abstract base class.
    Concrete sub-classes must overwrite `initialize`.

    Attributes:
        state_graph (StateGraph): the associated state graph
        default_value (Fraction): The default value is the oracle value returned if the given state_id is not a key of the oracle
        statistics (Statistics): access to the global statistics
        settings (Settings): all settings
        solver (Solver): a solver for the equation system
        oracle_states (Set[StateId]): states in this oracle
        oracle (Dict[StateId, z3.ExprRef]): the oracle's internal value dict
    """

    def __init__(self,
                 state_graph: StateGraph,
                 default_value: Fraction,
                 statistics: Statistics,
                 settings: Settings,
                 model_type: PrismModelType):

        self.state_graph = state_graph
        self.statistics = statistics
        self.settings = settings
        self.model_type = model_type

        if default_value < 0:
            raise ValueError("Oracle values must be greater or equal to 0")

        self.default_value = RealVal(default_value)

        self.solver = Solver()
        self.solver_mdp = Optimize()

        # The way we refine the Oracle depends on the model type
        if model_type == PrismModelType.DTMC:
            self.refine_oracle = self.refine_oracle_mc

        elif model_type == PrismModelType.MDP:
            self.refine_oracle = self.refine_oracle_mdp

        else:
            raise Exception("Oracle: Unsupported model type")


        self.oracle_states: Set[StateId] = set()

        self.oracle: Dict[StateId, z3.ExprRef] = dict()


        # self.save_oracle_on_disk()

    def _ensure_value_in_oracle(self, state_id: StateId):
        """
        Used to override standard behaviour. Takes a state id, ensures that self.oracle contains this value.
        :param state_id:
        :return:
        """
        pass

    def get_oracle_value(self, state_id: StateId) -> z3.ExprRef:
        if state_id not in self.oracle:
            self._ensure_value_in_oracle(state_id)
        return self.oracle.get(state_id, self.default_value)


    def refine_oracle_mc(self, visited_states: Set[StateId]) -> Set[StateId]:

        self.statistics.inc_refine_oracle_counter()
        # First ensure progress
        if visited_states <= self.oracle_states:
            # Ensure progress by adding all non-target successors of states in oracle_states to the set
            self.oracle_states = self.oracle_states.union({
                succ_id
                for state_id in self.oracle_states
                for succ_id, prob in self.state_graph.get_filtered_successors(state_id)
                if succ_id != -1
            })

        else:
            self.oracle_states = self.oracle_states.union(visited_states)

        # TODO: A lot of optimization potential
        self.solver.push()

        # We need a variable for every oracle state
        variables = {
            state_id: Real("x_%s" % state_id)
            for state_id in self.oracle_states
        }

        # Set up EQ - System
        for state_id in self.oracle_states:
            self.solver.add(variables[state_id] == Sum([
                RealVal(1) *
                prob if succ_id == -1 else  # Case succ_id target state
                (
                    variables[succ_id] * prob if succ_id in
                    self.oracle_states else  # Case succ_id oracle state
                    self.get_oracle_value(succ_id) *
                    prob)  # Case sycc_id no target and no oracle state
                for succ_id, prob in self.state_graph.get_filtered_successors(state_id)
            ]))

            self.solver.add(variables[state_id] >= RealVal(0))

        #print(self.solver.assertions())

        if self.solver.check() == sat:

            m = self.solver.model()

            # update oracle
            for state_id in self.oracle_states:
                self.oracle[state_id] = m[variables[state_id]]

            logger.info("Refined oracle.")
            #logger.info(self.oracle)

            self.solver.pop()

            return self.oracle_states

        else:

            # The oracle solver is unsat. In this case, we solve the LP.
            self.solver.pop()

            self.statistics.refine_oracle_counter = self.statistics.refine_oracle_counter - 1

            return self.refine_oracle_mdp(visited_states)


    def refine_oracle_mdp(self, visited_states: Set[StateId]) -> Set[StateId]:

        self.statistics.inc_refine_oracle_counter()
        # First ensure progress
        if visited_states <= self.oracle_states:
            # Ensure progress by adding all non-target successors of states in oracle_states to the set (for every action)
            self.oracle_states = self.oracle_states.union({succ[0] for state_id in self.oracle_states for choice in
                      self.state_graph.get_successors_filtered(state_id).choices for succ in
                      choice.distribution if succ[0] != -1})

        else:
            self.oracle_states = self.oracle_states.union(visited_states)

        # TODO: A lot of optimization potential
        self.solver_mdp.push()

        # We need a variable for every oracle state
        variables = {
            state_id: Real("x_%s" % state_id)
            for state_id in self.oracle_states
        }

        # Set up EQ - System
        for state_id in self.oracle_states:
            for choice in self.state_graph.get_successors_filtered(state_id).choices:
                self.solver_mdp.add(variables[state_id] >= Sum([
                    RealVal(1) *
                    prob if succ_id == -1 else  # Case succ_id target state
                    (
                        variables[succ_id] * prob if succ_id in
                                                 self.oracle_states else  # Case succ_id oracle state
                        self.get_oracle_value(succ_id) *
                        prob)  # Case sycc_id no target and no oracle state
                    for succ_id, prob in choice.distribution
                ]))

            self.solver_mdp.add(variables[state_id] >= RealVal(0))

        # Minimize value for initial state
        self.solver_mdp.minimize(variables[self.state_graph.get_initial_state_id()])

        if self.solver_mdp.check() == sat:

            m = self.solver_mdp.model()

            # update oracle
            for state_id in self.oracle_states:
                self.oracle[state_id] = m[variables[state_id]]

            logger.info("Refined oracle.")
            # logger.info(self.oracle)

            self.solver_mdp.pop()

            return self.oracle_states

        else:
            logger.error("Oracle solver unsat")
            raise RuntimeError("Oracle solver inconsistent.")


    @abstractmethod
    def initialize(self):
        """
        Stub to be overwritten by concrete oracles.
        :return:
        """
        pass

    def save_oracle_on_disk(self):
        """
        Save this oracle to disk using `save_oracle_dict` from `pric3.oracles.file_oracle`.
        """
        from pric3.oracles.file_oracle import save_oracle_dict
        save_oracle_dict(self.state_graph, self.oracle)

    def _get_prism_program(self):
        return self.state_graph.input_program.prism_program

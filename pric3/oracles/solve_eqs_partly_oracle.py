
from pric3.oracles.simulator import simulate, simulate_cpp
from fractions import Fraction
from pric3.oracles.oracle import Oracle
from stormpy.storage import PrismModelType
from z3 import RealVal
import numpy as np


class SolveEQSPartlyOracle(Oracle):
    def initialize(self):
        states = set()
        self.oracle = dict()

        states.add(self.state_graph.get_initial_state_id())

        new_states = {succ[0] for state_id in states for succ in
                      self.state_graph.get_filtered_successors(state_id) if succ[0] != -1}

        limit = self.settings.depth_for_partly_solving_lqs
        i=0

        while (not new_states <= states) and len(states)< limit:
            i=i+1
            states = states.union(new_states)
            new_states = {succ[0] for state_id in states for succ in
                          self.state_graph.get_filtered_successors(state_id) if succ[0] != -1}

        print("Limit reached. len if states: %s" % len(states))

        # Create exact oracle (easy using refine_oracle)
        if self.settings.oracle_type == "solveeqspartly_exact":
            self._create_exact_arithmetic_oracle(states)

        elif self.settings.oracle_type == "solveeqspartly_inexact":

            # If we check an MDP, then this would require to solve an LP. TODO
            if self.model_type == PrismModelType.MDP:
                raise NotImplementedError("Ineaxt Partly-Solving-EQS-Oracle is not implemented.")

            else:
                self._create_inexact_arithmetic_oracle(states)

    def _create_exact_arithmetic_oracle(self, states):

        self.refine_oracle(states)
        self.oracle_states = {self.state_graph.get_initial_state_id()}
        self.statistics.refine_oracle_counter = self.statistics.refine_oracle_counter - 1

    def _ensure_value_in_oracle(self, state_id):
        """
        Used to override standard behaviour. Takes a state id, ensures that self.oracle contains this value.
        Invoked by get_oracle_value(state) in case state is no oracle state.
        :param state_id:
        :return:
        """

        #Design choice:
        self.oracle[state_id] = RealVal(self.settings.default_oracle_value)


    def _create_inexact_arithmetic_oracle(self, states):

        # Numpy needs a coefficient list. Build a map from indices to states.
        index_to_state = dict()
        state_to_index = dict()

        rhs_list = []
        coeff_list = []  # A list of lists, each element is a coefficient list

        i = 0
        for state in states:
            index_to_state[i] = state
            state_to_index[state] = i
            i = i+1

            succ_dist = self.state_graph.get_filtered_successors(state)

            # The rhs of the equation for the state is -(sum of probs leading to a goal state)
            rhs = sum([float(prob) for state_id, prob in succ_dist if state_id == -1])
            rhs_list.append(-rhs)

            coeff_list.append([0 for j in range(0, len(states))])


        # Now go through every state again and build its coefficient list
        for state in states:
             # First set the coefficient of state to -1
            coeff_list[state_to_index[state]][state_to_index[state]] = -1

            succ_dist = self.state_graph.get_filtered_successors(state)

            #Now add the probability for every non-target succ to its coefficient
            for succ_id, prob in succ_dist:
                if succ_id != -1 and succ_id in states:
                    coeff_list[state_to_index[state]][state_to_index[succ_id]] += float(prob)


        coeff_matrix = np.array(coeff_list)
        rhs = np.array(rhs_list)

        solution = np.linalg.solve(coeff_matrix, rhs)
        #print(solution[state_to_index[self.state_graph.get_initial_state_id()]])

        solution = solution.astype(float)
        
        # Update oracle
        for state in states:
            self.oracle[state] = RealVal(solution[state_to_index[state]])

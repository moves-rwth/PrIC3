import random
from fractions import Fraction
from typing import Dict, List, Set, Tuple, Union

from z3 import ExprRef, RealVal

import stormpy
from pric3.state_graph import Probability, StateGraph, StateId
from stormpy import PrismProgram

StateStatsSource = Dict[StateId, Tuple[int, int]]
"""
Input format for a SimulationResult.
"""


class SimulationResult:
    def __init__(self, state_stats: Union[StateStatsSource, None] = None):
        self._state_stats: StateStatsSource = state_stats or dict()

    def add_sample(self, visited_states: Set[StateId], *, hit_goal: bool):
        """Increment hit/visit counter for all states in the set."""
        for state in visited_states:
            (hits, visits) = self._state_stats.get(state, (0, 0))
            if hit_goal:
                hits += 1
            self._state_stats[state] = (hits, visits + 1)

    def to_hit_probability_dict(self) -> Dict[StateId, ExprRef]:
        """Return the hit probability for each state."""
        return {
            state: RealVal(hits / visits)
            for state, (hits, visits) in self._state_stats.items()
        }


def simulate_cpp(prism_program: PrismProgram, total_samples: int,
                 max_steps: int) -> SimulationResult:
    stats = stormpy.simulate(prism_program, total_samples, max_steps)
    return SimulationResult(stats)


def simulate(state_graph: StateGraph, total_samples: int,
             max_steps: int) -> SimulationResult:
    result = SimulationResult()

    for i in range(total_samples):
        if i % 200 == 0:
            print("%s samples" % i)

        state = state_graph.get_initial_state_id()
        steps = 0
        visited_states: Set[StateId] = set()
        hit_goal = False

        while steps <= max_steps:
            steps += 1
            visited_states.add(state)

            hit_goal = state_graph.is_goal_state(state)
            if hit_goal:
                result.add_sample(visited_states, hit_goal=hit_goal)
                break

            if state_graph.is_terminal_state(state):
                result.add_sample(visited_states, hit_goal=False)
                break

            succs = state_graph.get_successor_distribution(state)
            state = _sample_from_distribution(succs)

    return result


def _sample_from_distribution(dist: List[Tuple[StateId, Probability]]
                              ) -> StateId:
    """Choose a random state from a distribution according to the probabilities."""
    rnd = random.random()
    for state, prob in dist:
        # TODO: This is dirty
        prob = Fraction( # type:ignore
            str(prob.numerator) + "/" + # type:ignore
            str(prob.denominator)) # type:ignore
        if rnd <= prob:
            return state
        rnd -= prob

    raise Exception("unreachable")

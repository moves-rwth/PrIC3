"""
Interactively explore the state space of a program using :py:class:`StateGraph`.

It is implemented using :py:class:`stormpy.StateGenerator`.
"""
from collections.abc import Sequence
from typing import Dict, List, NewType, Set, Tuple

import z3
from graphviz import Digraph

import stormpy
from pric3.input_program import InputProgram, InputCommand, InputVariable
from pric3.utils import attach_newtype_declaration_module, concat_generators

StateId = NewType('StateId', int)
"""
States in the state graph are accessed through opaque IDs.
"""
attach_newtype_declaration_module(StateId, __name__)

Probability = NewType('Probability', float)
"""
A type representing probabilities.

Note: a Probability is not, in fact, represented by a float, but by
a `stormpy.Rational`. As this type is not subclassable, we must lie to
the type checker and pretend it's a float.
"""
attach_newtype_declaration_module(Probability, __name__)

StateDistribution = List[Tuple[StateId, Probability]]
"""
A probability distribution of choices.
"""


class StateGraphChoice:
    """
    A choice as a result of a nondeterministic program.

    Similar to `stormpy.GeneratorChoice` in structure, but without the C++ binding stuff
    and with proper references to the origins (commands) of the choice.

    Attributes:
        origins (List[InputCommand]): the commands that generated this choice.
        distribution (StateDistribution): the probability distribution associated with this choice.
    """

    def __init__(self, input_program: InputProgram, choice: stormpy.GeneratorChoice):
        # pylint: disable=cell-var-from-loop
        self.origins = [next(filter(lambda command: command.global_index == global_index, input_program.module.commands)) for global_index in choice.origins]
        self.distribution = choice.distribution

class StateGraphBehavior(Sequence):
    """
    A list of `StateGraphChoice`s that represent the nondeterministic successors of a state.

    This object is iterable, and returns an iterator over `choices`.

    Attributes:
        choices (List[StateGraphChoice]): the choices that can be done from a state.
    """

    def __init__(self, input_program: InputProgram, choices: List[StateGraphChoice]):
        self._input_program = input_program
        self.choices = choices

    def __getitem__(self, index):
        return self.choices[index]

    def __len__(self):
        return len(self.choices)

    def __iter__(self):
        return iter(self.choices)

    def is_deterministic(self) -> bool:
        """
        Return true if there is at most one choice in this behavior.
        """
        return len(self.choices) <= 1

    def extract_deterministic(self) -> StateDistribution:
        """
        If there is one choice, return the choice's distribution.
        If there is no choice, return the empty distribution.
        Otherwise throw an exception.
        """
        if len(self.choices) == 1:
            return self.choices[0].distribution
        elif len(self.choices) == 0:
            return []
        else:
            raise Exception("StateGraphBehavior: nondeterminism!")

    def by_command(self, command: InputCommand) -> StateDistribution:
        """
        Return the distribution associated with the given command.
        Throws an exception if there is none.
        """
        for choice in self.choices:
            if command in choice.origins:
                return choice.distribution
        raise Exception("StateGraphBehavior: command has no corresponding choice")

    def by_command_index(self, command_index: int) -> StateDistribution:
        """
        Return the distribution associated with the command's index.
        Throws an exception if there is none.

        Note: this is not storm's `global_index` but rather just the command position in the InputProgram list.
        """
        command = self._input_program.module.commands[command_index]
        return self.by_command(command)


class StateGraph:
    """
    Interactive exploration of the state graph of an InputProgram.

    Attributes:
        input_program (InputProgram): The program this graph is for.
    """
    def __init__(self, input_program: InputProgram):
        self.input_program = input_program
        self.state_generator = stormpy.StateGenerator(
            input_program.prism_program)
        self._successors_filtered_cache: Dict[StateId, StateGraphBehavior] = dict()

    def get_initial_state_id(self) -> StateId:
        """
        Return the initial state's ID.
        """
        return self.state_generator.load_initial_state()

    def _get_state_valuation_list(self, state_id: StateId) -> List[Tuple[stormpy.PrismVariable, z3.ExprRef]]:
        self.state_generator.load(state_id)
        storm_valuation = self.state_generator.current_state_to_valuation()
        all_valuations = concat_generators(
            storm_valuation.boolean_values.items(),
            storm_valuation.integer_values.items())
        all_valuations = filter(
            lambda pair: pair[0].name not in self.input_program.constants,
            all_valuations)
        return all_valuations

    def get_state_valuation(self, state_id: StateId
                            ) -> Dict[InputVariable, z3.ExprRef]:
        """
        Return a dict that maps variables to Z3 expressions for the given state ID.
        """
        all_valuations = self._get_state_valuation_list(state_id)

        return {
            self.input_program.module.lookup_variable(var):
            self.input_program.module.translate_expression(value)
            for var, value in all_valuations
        }

    def get_successors(self, state_id: StateId) -> StateGraphBehavior:
        """
        Generate the successor states of a state.
        """
        self.state_generator.load(state_id)
        choices = [StateGraphChoice(self.input_program, choice) for choice in self.state_generator.expand()]
        return StateGraphBehavior(self.input_program, choices)

    def get_successor_distribution(self, state_id: StateId) -> StateDistribution:
        """
        Use `self.get_successors(state_id).extract_deterministic()` instead.
        """
        return self.get_successors(state_id).extract_deterministic()

    def is_state_nondeterministic(self, state_id: StateId) -> bool:
        # TODO: efficiency
        # TODO: this seems wrong!
        return len(self.get_successor_distribution(state_id)) == 1

    def filter_choice(self, choice: StateGraphChoice):
        """
        Changes the choice's distribution in two ways:
            * goal states are mapped to ID -1,
            * terminal states are not included in the the distributions.
        """
        def gen_distribution():
            # pylint: disable=cell-var-from-loop
            for succ_id, prob in choice.distribution:
                # goal states get ID = -1
                if self.is_goal_state(succ_id):
                    yield (-1, prob)
                # filter terminal states
                elif not self.is_terminal_state(succ_id):
                    yield (succ_id, prob)

        choice.distribution = list(gen_distribution())

    def get_successors_filtered(self, state_id: StateId) -> StateGraphBehavior:
        """
        Like `get_successors`, but with `filter_choice` applied to each choice, and with a cache.
        """
        cache_hit = self._successors_filtered_cache.get(state_id)
        if cache_hit is not None:
            return cache_hit

        behavior = self.get_successors(state_id)
        for choice in behavior:
            self.filter_choice(choice)

        self._successors_filtered_cache[state_id] = behavior
        return behavior

    def get_filtered_successors(self, state_id: StateId) -> StateDistribution:
        """
        Use `self.get_successors_filtered(state_id).extract_deterministic()` instead.
        """
        return self.get_successors_filtered(state_id).extract_deterministic()

    def is_goal_state(self, state_id: StateId) -> bool:
        """
        Checks whether this is a goal state.
        """
        self.state_generator.load(state_id)
        return self.state_generator.current_state_satisfies(
            self.input_program.prism_goal)

    def is_terminal_state(self, state_id: StateId) -> bool:
        """
        Checks whether this state is terminal, i.e. it has a self-loop with probability one in each successor choice.
        """
        behavior = self.get_successors(state_id)
        for choice in behavior:
            distribution = choice.distribution
            if not (len(distribution) == 0 or (len(distribution) == 1 and distribution[0][0] == state_id)):
                return False
        return True

    def to_dot(self, node_limit: int, *, view: bool = False, show_state_valuations: bool = False) -> Digraph:
        """
        Create a graphviz Digraph from the state space.

        Parameters:
            node_limit: how many proper nodes to add to the graph.
            view: whether to show the generated image in an image viewer.
            show_state_valuations: whether to show the state valuations (true) or the state ids (false).
        """
        queue = [self.get_initial_state_id()]
        seen: Set[StateId] = set()
        added = 0
        dot = Digraph()

        while added <= node_limit and len(queue) > 0:
            state_id = queue.pop()
            val_string = "("

            if show_state_valuations:
                for var, val in self.get_state_valuation(state_id).items():
                    val_string = val_string + str(val) + ", "

            val_string = val_string + ")"

            dot.node(
                str(state_id),
                label=(val_string if show_state_valuations else  str(state_id)) +
                (" (Goal)" if self.is_goal_state(state_id) else
                 " (Terminal)" if self.is_terminal_state(state_id) else ""),
                shape=None)
            added += 1
            if not self.is_goal_state(state_id):
                for succ_id, prob in self.get_successor_distribution(state_id):
                    dot.edge(str(state_id), str(succ_id), label=str(prob))
                    if succ_id not in seen:
                        seen.add(succ_id)
                        queue.append(succ_id)

        description_string = "States: ("
        for var in self.get_state_valuation(self.get_initial_state_id()).keys():
            description_string = description_string + var.name + ", "

        if show_state_valuations:
            description_string = description_string + ")"

            dot.attr(label=description_string)
            dot.attr(fontsize='20')

            dot.render("model.dot", view=view)
        return dot

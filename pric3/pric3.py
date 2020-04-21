# pylint: disable-all
import logging
from fractions import Fraction

import z3
from z3 import (BoolRef, Q, Real, RealVal, Solver, Sum, Z3_mk_ge, sat, And, Implies)

from pric3.settings import Settings
from pric3.pric3_solver import PrIC3Solver
from pric3.proof_obligations.obligation_queue import ObligationQueue
from pric3.proof_obligations.repushing_obligation_queue import RepushingObligationQueue
from pric3.proof_obligations.naive_repushing_obligation_queue import NaiveRepushingObligationQueue
from pric3.smt_program import SmtProgram, ForallMode
from pric3.state_graph import StateGraph
from pric3.state_probability_generator import StateProbabilityGenerator
from pric3.statistics import Statistics
from pric3.generalization.generalizer import Generalizer
from pric3.utils import *
from pric3.generalization.state_of_the_same_kind_cache import StatesOfTheSameKindCache
from collections import Counter


logger = logging.getLogger(__name__)

z3.Z3_DEBUG = False

class PrIC3:
    """
    An instance of the PrIC3 algorithm.
    """

    def __init__(self, smt_program: SmtProgram, threshold: Fraction, settings: Settings, statistics: Statistics):
        """
        Construct a PrIC3 instance.

        Parameters:
            smt_program: the program to check
            threshold: the threshold
            settings: the settings
            statistics: the statistics to use
        """
        self.smt_program = smt_program
        self.input_program = smt_program.input_program
        self.state_graph = StateGraph(smt_program.input_program)

        self.settings = settings
        self.statistics = statistics

        self.obligation_queue_class = self.settings.get_obligation_queue_class()

        if self.settings.generalize and self.settings.forall_mode != "globals":
            print('We cannot employ generalization using uninterpreted functions. Use --forall-mode globals instead.')
            raise

        # Also initializes F_0
        self.p_solver = PrIC3Solver(smt_program, self.statistics.pric3solverstats, settings.store_smt_calls, settings)

        if not isinstance(threshold, Fraction):
            raise TypeError("Threshold must be a fraction")

        if not (threshold >= 0 and threshold <= 1):
            raise ValueError("Threshold must be a probability")

        self.threshold_frac = threshold

        # convert given threshold to a z3 rational
        self.threshold_z3 = Q(threshold.numerator, threshold.denominator)

        # obtain initial state
        self.initial_state_id = self.state_graph.get_initial_state_id()

        logger.info("Initialize various auxiliary objects...")
        logger.debug("Initialize refutation solver...")
        # Intialize solver for refutation check
        self.refutation_solver = Solver()

        logger.debug("Initialize state probability generator...")
        self._state_probability_generator = StateProbabilityGenerator(self.state_graph, self.statistics, self.settings, self.input_program.model_type)

        logger.debug("Initialize generalizer...")
        self._generalizer = Generalizer(self.state_graph, self.smt_program, self.p_solver, self.statistics, self.settings)

    def run(self) -> bool:
        self.statistics.start_total_timer()

        logger.info("Start IC3")
        result = self._run_ic3()
        if result:
            logger.critical("Property holds.")
        else:
            logger.critical("Property does not hold.")
        self.statistics.property_holds = result
        self.statistics.number_considered_states = len(self.statistics.considered_states)
        if hasattr(self, 'inductiveness_verified'):
            self.statistics.inductiveness_verified = self.inductiveness_verified
        self._state_probability_generator.finalize_statistics()
        return result

    def reset(self):
        self.p_solver = PrIC3Solver(self.smt_program, self.statistics.pric3solverstats, self.settings.store_smt_calls, self.settings)

        self.k = 1

        # Add new solver for Frame F_1
        self.p_solver.add_new_solver()

        # store frames explicitly as sets of assertions
        self.frames = [None, set()]

        # Store pairs (state_id,   z3_check_arg_list (see relative inductiveness calls in pric3_solver) as tuple,  probability expressions as string   ) for efficient membership check
        self.frames_explicit_set = [None, set()]

        RepushingObligationQueue.smallest_probability_for_state = dict()
        ObligationQueue.smallest_probability_for_state = dict()

        self._generalizer.reset()


    def print_details(self):
        # self.state_graph.to_dot(1000000)
        self.statistics.print_statistics()

    def _run_ic3(self):
        """

        :return: True if property holds
        """

        self.k = 1

        # Add new solver for Frame F_1
        self.p_solver.add_new_solver()

        # store frames explicitly as sets of assertions
        self.frames = [None, set()]

        # Store pairs (state_id, expressions) for efficient membership check
        self.frames_explicit_set = [None, set()]

        while True:
            refute = self.strengthen()

            logger.info("")
            logger.info("New iteration k=%s" % self.k)
            logger.info("Rel ind checks so far: %s" % self.statistics.check_relative_inductive_counter)
            logger.info("Propagated assertions so far: %s" % self.statistics.propagation_counter)
            logger.info("")

            if refute:
                return False

            # Initialize new Solver for F_{k+1}
            self.p_solver.add_new_solver()

            self.frames.append(set())
            self.frames_explicit_set.append(set())

            # Increase counter
            self.k = self.k + 1

            if self.propagate():
                self.statistics.stop_total_timer()

                logger.info("")
                logger.info("Equal Frames %s and %s" % (self.inductive_frame_index, self.inductive_frame_index + 1))

                #logger.info("Inductive invariant:")
                #logger.info(self.p_solver.solvers[self.inductive_frame_index].sexpr())
                #logger.info("")
                #logger.info(self.frames_explicit_set[self.inductive_frame_index])
                #print(self.p_solver.solvers[self.inductive_frame_index].sexpr())

                #print("Final Frames:")
                #print(self.frames_explicit_set)


                if self.settings.check_inductiveness_if_property_holds:
                    if self.is_inductive(self.inductive_frame_index):
                        logger.info("Inductiveness verified :)")
                        self.inductiveness_verified = "Yes"

                    else:
                        logger.info("Inductiveness refuted :(")
                        self.inductiveness_verified = "No"

                else:
                    self.inductiveness_verified = "Unkown"

                #self.state_graph.to_dot(100000, view= True, show_state_valuations=True)

                return True


            #print('Frames after iteration %s' % (self.k-1))
            #print(self.frames_explicit_set)
            #print("")
            #print("")


            # ------ IC3-Invariant checks -----
            if self.settings.check_relative_inductiveness_of_frames:
                for i in range(0, self.k):
                    if not self.is_frames_relative_inductive(i):
                        logger.info("Frame %s not inductive relative to frame %s" %
                              (i + 1, i))
                        raise
            # ---------------------------------




    def strengthen(self):
        """

        :return: True if the property is refuted and False if it was possible to establish the IC3-Invariants
                      for all frames in self.frames
        """

        # Initialize obligation queue with the first proof obligation: Proof that the probability to reach a goal
        # state from the initial state in at most k steps is at most lambda

        Q = self.obligation_queue_class()
        Q.push_obligation(self.k, self.initial_state_id, self.threshold_z3, {self.initial_state_id})

        #visited_states = Counter()


        while not Q.is_empty():
            # While Q is not empty

            # Pop obligation with smallest index
            (i, s, delta, history) = Q.pop_obligation()
            self.statistics.add_considered_states(s)
            #visited_states.update({s})
            state_valuation = self.state_graph.get_state_valuation(s)

            if i == 0:
                # Need to repair F_0. Either refute or repair oracle and reset queue.
                logger.debug("Need to repair F_0.")

                states_for_refutation_test = self._state_probability_generator.refine_oracle(history)

                if self.check_refutation(states_for_refutation_test):
                    self.statistics.stop_total_timer()
                    return True

                self.reset()

                Q = self.obligation_queue_class()
                Q.push_obligation(self.k, self.initial_state_id, self.threshold_z3, {self.initial_state_id})
                #visited_states = Counter()

            else:
                # check Whetehr \Phi(F_{i-1})[s] > delta, i.e., whether updating frames would violate relative inductiveness.

                state_args = state_valuation_to_z3_check_args(state_valuation)

                check_result = self.p_solver.is_relative_inductive(i - 1, state_args, delta)
                relative_inductive =  check_result == True

                if not relative_inductive:

                    # Get responsible command from solver model
                    chosen_command = check_result[self.smt_program.chosen_command]

                    # Get probabilities for refining successors of s and action chosen_command in F_{i-1}
                    (possible,
                        dict_of_probs_for_succs) = self.get_probabilities(
                            s, chosen_command, delta, history)

                    if possible:
                        # Push obligation for every (non-target) successor
                        for succ_id in dict_of_probs_for_succs:
                            Q.push_obligation(i - 1, succ_id,
                                            dict_of_probs_for_succs[succ_id], history.union({succ_id}))

                        # The relative_inductiveness_check for this obligation is necessarry iff state s is nondeterministic (i.e., if it has more than one enabled action)
                        Q.push_obligation(i, s, delta, history)

                    else:

                        # It is not possible to get such probabilities, refine oracle and reset queue
                        logger.debug("Not possible: getProbabilities(%s, %s)." %
                                (state_valuation, delta))
                        logger.debug(history)
                        states_for_refutation_test = self._state_probability_generator.refine_oracle(history)

                        if self.check_refutation(states_for_refutation_test):
                            self.statistics.stop_total_timer()
                            return True

                        self.reset()
                        Q = self.obligation_queue_class()

                        Q.push_obligation(
                            self.k, self.initial_state_id, self.threshold_z3, {self.initial_state_id})

                # If relative_inductiveness check was not necessary or if updating frames does not violate relative inductiveness,
                # we update the frames
                # We do not check 'relative inductiveness check necessary' since this is unsound in the presence of cycles
                if relative_inductive:

                    if i < self.k and (type(Q) == RepushingObligationQueue or type(Q) == NaiveRepushingObligationQueue):
                        Q.repush_obligation(i+1, s, delta, history)

                    if self.settings.generalize:
                        # We want to generalize the constraint (s,delta) and this generalization must
                        # be inductive relative to F_{i-1}
                        generalization_result = self._generalizer.generalize(i-1, s, delta)

                    else:
                        generalization_result = [(state_args, delta)]

                    self.update_frames(i, s, state_valuation, generalization_result)

                    # Consider this state for caching "States of the same kind) (generalization)
                    if self.settings.generalize:
                        self._generalizer.consider_state(s)

        return False




    def update_frames(self, up_to_frame_index, state_id, state_valuation, state_args_probability_expression_pairs):
        """
        Updates all frames {1, ..., up_to_frame_index}. Updates are obtained due to an obligation for state_id.
        The state_valuation is passed for the uninterpreted function case. State_args_probability_expression_pairs
        consits of pairs (state_args, probability expressions), which are to be added to the frames.


        :param up_to_frame_index:
        :param state_id:
        :param state_valuation:
        :param state_args_probability_expression_pairs:
        :return:
        """

        # print("Res : %s" % generalization_result)
        for (state_args_of_gen, probability_expression) in state_args_probability_expression_pairs:

            frame_applied = self.smt_program.env.apply_to_state_valuation(self.smt_program.frame, state_valuation)
            state_args_as_tuple = tuple(state_args_of_gen)

            # frame_applied = self.smt_program.env.apply_to_state_args(self.smt_program.frame,
            # state_args_of_gen)

            for j in range(up_to_frame_index, 0, -1):
                # TODO: as string is faster than anything else, but still is super slow.
                # TODO: use ordering between frames to reduce lookups?
                # Note: As soon as we have a generalization, the deltas will be polynomials in the Z3 (program) variables.
                if (state_id, state_args_as_tuple, probability_expression) not in self.frames_explicit_set[j]:

                    if self.smt_program.settings.forall_mode != ForallMode.FORALL_GLOBALS:
                        to_add = self._ge_no_coerce(probability_expression, frame_applied)
                        self.p_solver.add_assertion(j, to_add)

                    else:
                        state_constr = And(state_args_as_tuple)
                        to_add = Implies(state_constr,
                                         self._ge_no_coerce(probability_expression, frame_applied))
                        #print("Adding assertion: %s" % self.smt_program.get_frame_leq_constraint_from_state_args(
                        #    state_args_of_gen, probability_expression))
                        self.p_solver.add_assertion(j, self.smt_program.get_frame_leq_constraint_from_state_args(
                            state_args_of_gen, probability_expression))

                    self.frames[j].add(to_add)

                    # TODO: What if frame_explicit contains "generalized" assertions?
                    self.frames_explicit_set[j].add((state_id, state_args_as_tuple, probability_expression))

    def _ge_no_coerce(self, left, right):
        # TODO: add assertions for noncoerce
        return BoolRef(Z3_mk_ge(left.ctx_ref(), left.as_ast(), right.as_ast()), left.ctx)

    def get_probabilities(self, state_id, chosen_command, delta, states_where_probability_is_fixed = set()):
        return self._state_probability_generator.run(state_id, int(chosen_command.as_long()), delta, states_where_probability_is_fixed)


    def _is_nondeterministic_state(self, s):
        """
        Has the state s multiple outgoing actions?

        :param s: A state
        :return: True iff |Act(s)| > 1
        """
        return self.state_graph.is_state_nondeterministic(s)


    def propagate(self):
        """
        Propagation Phase of IC3.

        :return: True iff after propagation there is an i \in {1, ...,k-1} such that F_i = F_{i+1}
        """

        # TODO: What if frame_explicit contains "generalized" assertions?
        # TODO: The deltas in frames_explicit are strings. Make this more efficient?
        # TODO: Use "probability_expression encoding" of frames. Obviates need to go through all assertions of a frame

        self.statistics.start_propagation_timer()

        # For every frame F_i (except for the frontier(
        for i in range(1, self.k):

            if self.settings.propagate:
                # For every assertion A in F_i ...
                for (s, state_args_as_tuple, probability_expression) in self.frames_explicit_set[i]:
                    #... which is not in F_{i+1}
                    if (s, state_args_as_tuple, probability_expression) not in self.frames_explicit_set[i+1]:
                        state_valuation = self.state_graph.get_state_valuation(s)

                        # If adding A to F_{i+1} does not violate inductiveness ...
                        #state_args = state_valuation_to_z3_check_args(state_valuation)
                        #print('TRY to Propagate (%s, %s) to F_%s' % (state_args_as_tuple, probability_expression, i + 1))
                        if self.p_solver.is_relative_inductive(i, state_args_as_tuple, probability_expression) == True:
                            # Add it to F_{i+1}

                            frame_applied = self.smt_program.env.apply_to_state_valuation(self.smt_program.frame, state_valuation)

                            to_add = self._ge_no_coerce(probability_expression, frame_applied)

                            #print('Propagate (%s, %s) to F_%s' % (state_args_as_tuple, to_add, i+1))

                            if self.smt_program.settings.forall_mode != ForallMode.FORALL_GLOBALS:
                                self.p_solver.add_assertion(i+1, to_add)

                            else:
                                state_constr = And(state_args_as_tuple)
                                to_add = Implies(state_constr,
                                                 self._ge_no_coerce(probability_expression, frame_applied))

                                self.p_solver.add_assertion(i+1,
                                                            self.smt_program.get_frame_leq_constraint_from_state_args(
                                                                state_args_as_tuple, probability_expression))
                            self.frames[i+1].add(to_add)

                            #TODO: What if frame_explicit contains "generalized" assertions?
                            self.frames_explicit_set[i+1].add((s, state_args_as_tuple, probability_expression))

                            self.statistics.inc_propagation_counter()


            if len(self.frames[i]) == len(self.frames[i+1]):
                if self.frames[i] == self.frames[i+1]:
                    self.inductive_frame_index = i
                    self.statistics.stop_propagation_timer()
                    return True

                else:
                    pass
                    #logger.debug("Frames %s and %s are not equal. Difference: %s" % (i, i+1, (self.frames_explicit_set[i] - self.frames_explicit_set[i+1])))

        self.statistics.stop_propagation_timer()

        return False



    # --------------------- Solver Operations ----------------------------------


    # Returns True iff the following holds
    #   There exists a program state s satisfying state_formula (a formula over the free z3_variables) such that
    #              \Phi(frame_index)[s] > expression


    # TODO: Make use of incrementality of solver
    # Returns True iff refute-eq-system for states_for_refutation_test is sat
    def check_refutation(self, states_for_refutation_test):

        self.statistics.start_check_refutation_timer()
        self.refutation_solver.push()

        vars = {}
        # Need a variable for each state in states_for_refutation_test
        for state_id in states_for_refutation_test:
            vars[state_id] = Real("x_%s" % state_id)

        # Build up InEQ system
        for state_id in states_for_refutation_test:
            for choice in self.state_graph.get_successors_filtered(state_id).choices:
                self.refutation_solver.add(vars[state_id] >= Sum([
                        vars[succ_id] * prob if succ_id in states_for_refutation_test
                        else  # Case succ_id in states for test
                        prob if succ_id == -1 else  # Case succ is goal state
                        0  # all other cases
                        for succ_id, prob in choice.distribution
                ]))

        # It must be possible to assign a value <= threshold to the initial state
        self.refutation_solver.add(
            vars[self.initial_state_id] <= self.threshold_z3)

        #print(len(self.refutation_solver.assertions()))

        # Finally, assert that initial state is greater than threshold
        logger.debug(states_for_refutation_test)
        logger.debug(vars)

        if self.refutation_solver.check() == unsat:
            self.refutation_solver.pop()

            self.statistics.stop_check_refutation_timer()
            return True

        else:
            self.statistics.stop_check_refutation_timer()
            self.refutation_solver.pop()
            return False

    # --------------- Invariant Checks ---------------
    def is_inductive(self, frame_index):
        """
        Receives a frame_index and checks whether the corresponding frame is inductive.

        :param frame_index:
        :return:
        """
        # Iterate over each (state, delta) in the frame and check whether \Phi(frame)[state] > delta
        # If there is such a pair, then the frame is no inductive invariant
        for (s, state_args_as_tuple, probability_expression) in self.frames_explicit_set[frame_index]:
            #state_args = state_valuation_to_z3_check_args(self.state_graph.get_state_valuation(state_valuation))
            if not self.p_solver.is_relative_inductive(frame_index, state_args_as_tuple, probability_expression, ignore_stats=True) == True:
                logger.debug("Assertion (%s, %s) is not inductive." % (state_args_as_tuple, probability_expression))
                return False

        return True

    def is_frames_relative_inductive(self, frame_index):
        """
        Receives a frame_index and checks whether frame_index + 1 is inductive relative to frame_index

        :param frame_index:
        :return:
        """
        for (s, state_args_as_tuple, delta) in self.frames_explicit_set[frame_index + 1]:
            #state_args = state_valuation_to_z3_check_args(self.state_graph.get_state_valuation(state_valuation))
            if not self.p_solver.is_relative_inductive(frame_index, state_args_as_tuple, RealVal(delta), ignore_stats=True) == True:
                return False

        return True

    def export_smt(self, prefix):
        self.p_solver.export_solver_stacks(prefix)

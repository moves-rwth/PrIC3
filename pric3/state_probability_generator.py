import logging

from z3 import ArithRef, Ast, If, Optimize, Real, RealVal, Sum, Z3_mk_mul, sat

from pric3.proof_obligations.obligation_cache import ObligationCache
from pric3.oracles.simulation_oracle import SimulationOracle
from pric3.oracles.exact_oracle import ExactOracle
from pric3.oracles.model_checking_oracle import ModelCheckingOracle
from pric3.oracles.solve_eqs_partly_oracle import SolveEQSPartlyOracle
from pric3.oracles.file_oracle import FileOracle
from pric3.proof_obligations.repushing_obligation_queue import RepushingObligationQueue

logger = logging.getLogger(__name__)

class StateProbabilityGenerator:

    def __init__(self, state_graph, statistics, settings, model_type):
        self.statistics = statistics
        self.state_graph = state_graph
        self.model_type = model_type

        logger.debug("Initialize oracle...")

        self._initialize_oracle(settings)

        logger.debug("Initialize obligation cache...")
        self._obligation_cache = ObligationCache()
        logger.debug("Initialize optimization solver...")
        # Initialize solver for optimization queries
        self.opt_solver = Optimize()

        self._realval_zero = RealVal(0)
        self._realval_one = RealVal(1)

        self.obligation_queue_class = settings.get_obligation_queue_class()

    def _initialize_oracle(self, settings):

        self.statistics.start_initialize_oracle_timer()

        args = [self.state_graph,settings.default_oracle_value,self.statistics,settings, self.model_type]
        if settings.oracle_type == "simulation":
            self.oracle = SimulationOracle(*args)
        elif settings.oracle_type == "perfect":
            self.oracle = ExactOracle(*args)
        elif settings.oracle_type == "modelchecking":
            self.oracle = ModelCheckingOracle(*args)
        elif settings.oracle_type == "solveeqspartly_exact" or settings.oracle_type == "solveeqspartly_inexact":
            self.oracle = SolveEQSPartlyOracle(*args)
        elif settings.oracle_type == "file":
            self.oracle = FileOracle(*args)
        else:
            raise RuntimeError("Unclear which oracle to use.")
        self.oracle.initialize()

        self.statistics.stop_initialize_oracle_timer()

    def refine_oracle(self, visited_states):
        res = self.oracle.refine_oracle(visited_states)
        self.reset_cache()
        return res

    def reset_cache(self):
        logger.debug("Reset obligation cache ...")
        self._obligation_cache.reset_cache()

    def finalize_statistics(self):
        self.statistics.set_number_oracle_states(len(self.oracle.oracle_states))

    def run(self, state_id, chosen_command, delta, states_with_fixed_probabilities = set()):
        """

        :param state_id: 
        :param delta: 
        :return: (1) True iff it is possible to find probabilities for the successors of the given state_id and delta.
                 (2) If True, then it returns a dict form succ_ids to probabilities. This dict does not contain goal states.
        """
        # TODO consider changing to None if not possible, and dict otherwise.
        self.statistics.inc_get_probability_counter()
        self.statistics.start_get_probability_timer()

        # First check whether we have cached the corresponding obligation
        res = self._obligation_cache.get_cached(state_id, chosen_command, delta)

        if res != False:
            self.statistics.stop_get_probability_timer()
            return (True, res)

        # If not, we have to ask the SMT-Solver
        succ_dist = self.state_graph.get_successors_filtered(state_id).by_command_index(chosen_command)

        succ_dist_without_target_states = [(state_id, prob)
                                           for (state_id, prob) in succ_dist
                                           if state_id != -1]

        # Check if there is at least one non-target state. Otherwise, repairing is not possible (smt solver would return unsat if we continued, so checking this is an optimization).
        if len(succ_dist_without_target_states) == 0:
            self.statistics.stop_get_probability_timer()
            return (False, None)

        self.opt_solver.push()
        vars = {}

        # We need a variable for each successor
        for (succ_id, prob) in succ_dist:
            if succ_id != -1:
                vars[succ_id] = Real("x_%s" % succ_id)

                # all results must of be probabilities
                self.opt_solver.add(vars[succ_id] >= self._realval_zero)
                self.opt_solver.add(vars[succ_id] <= self._realval_one)

        # \Phi(F)[s] = delta constraint
        # TODO: Type of porb is pycarl.gmp.gmp.Rational. Z3 magically deals with this
        self.opt_solver.add(
            Sum([
                (vars[succ_id] if succ_id != -1 else RealVal(1)) * prob
                # Note: Keep in mind that you need to check whether succ is a target state
                for (succ_id, prob) in succ_dist
            ]) == delta)

        for (succ_id, prob) in succ_dist:
            if succ_id in states_with_fixed_probabilities:
                self.opt_solver.add(vars[succ_id] == self.obligation_queue_class.smallest_probability_for_state[succ_id])


        # If we have more than one non-target successor, we have to optimize
        if len(succ_dist_without_target_states) > 1:

            # first check whether all oracle values are 0 (note that we do not have to do this if there is only one succ without target)

            if len(succ_dist_without_target_states) > 1 and sum([self.oracle.get_oracle_value(state_id).as_fraction() for state_id, prob in
                    succ_dist_without_target_states]) == 0:

                # In this case, we require that the probability mass is distributed equally
                for i in range(0, len(succ_dist_without_target_states) - 1):
                    self.opt_solver.add(
                        vars[succ_dist_without_target_states[i][0]] == vars[succ_dist_without_target_states[i + 1][0]])

            else:

                # First Try to solve the eq system
                # TODO: Do not use opt_solver for this
                if self._get_probabilities_by_solving_eq_system(succ_dist_without_target_states, vars):

                    self.statistics.inc_solved_eq_system_instead_of_optimization_counter()
                    m = self.opt_solver.model()

                    result = {
                        succ_id: m[vars[succ_id]]
                        for (succ_id, prob) in succ_dist_without_target_states
                    }

                    # Because get_probabilities_by_solving_eq_system pushes
                    # TODO: This is ugly
                    # TODO: Compare solve-eq-system-time with optimization-problem-time
                    self.opt_solver.pop()
                    self.opt_solver.pop()

                    self._obligation_cache.cache(state_id, chosen_command, delta, result)
                    self.statistics.stop_get_probability_timer()
                    return (True, result)

                else:

                    self.statistics.inc_had_to_solve_optimization_problem_counter()
                    # for each non-target-succ, we need n opt-var
                    opt_vars = {}

                    # For every non-target successor, we need an optimization variable
                    for (succ_id, prob) in succ_dist_without_target_states:
                        opt_vars[succ_id] = Real("opt_var_%s" % succ_id)

                    # Now assert that opt_var_i = |var_i \ (var_1 + ... + var_n)   -   oracle(s_i) \ ( oracle(s_1) + ... + oracle(s_n ) |
                    # for every opt_var_i
                    for (succ_id, prob) in succ_dist_without_target_states:
                        # opt_var is the absolute value of the ratio
                        self.opt_solver.add(
                            If(((vars[succ_id] * Sum([
                                self.oracle.get_oracle_value(succ_id_2) for
                                (succ_id_2, prob) in succ_dist_without_target_states
                            ])) - ((self.oracle.get_oracle_value(succ_id) * Sum([
                                vars[succ_id_2] for
                                (succ_id_2, prob) in succ_dist_without_target_states
                            ])))) < 0, opt_vars[succ_id] ==
                               (((self.oracle.get_oracle_value(succ_id) * Sum([
                                   vars[succ_id_2] for
                                   (succ_id_2, prob) in succ_dist_without_target_states
                               ]))) - (vars[succ_id] * Sum([
                                   self.oracle.get_oracle_value(succ_id_2) for
                                   (succ_id_2, prob) in succ_dist_without_target_states
                               ]))), opt_vars[succ_id] == ((vars[succ_id] * Sum([
                                self.oracle.get_oracle_value(succ_id_2) for
                                (succ_id_2, prob) in succ_dist_without_target_states
                            ])) - ((self.oracle.get_oracle_value(succ_id) * Sum([
                                vars[succ_id_2] for
                                (succ_id_2, prob) in succ_dist_without_target_states
                            ]))))))

                        # minimize sum of opt-vars
                        opt = self.opt_solver.minimize(
                            Sum([
                                opt_vars[succ_id]
                                for (succ_id, prob) in succ_dist_without_target_states
                            ]))

        if self.opt_solver.check() == sat:
            # We found probabilities or the successors
            m = self.opt_solver.model()

            result = {
                succ_id: m[vars[succ_id]]
                for (succ_id, prob) in succ_dist_without_target_states
            }
            self.opt_solver.pop()

            self._obligation_cache.cache(state_id, chosen_command, delta, result)

            self.statistics.stop_get_probability_timer()

            return (True, result)

        else:
            # There are no such probabilities
            self.opt_solver.pop()
            self.statistics.stop_get_probability_timer()

            return (False, None)

    def _get_probabilities_by_solving_eq_system(self, succ_dist_without_target_states, vars):

        self.opt_solver.push()
        #TODO is this correct?
        lhs_sum = Sum([
                    self.oracle.get_oracle_value(succ_id_2) for
                    (succ_id_2, _) in succ_dist_without_target_states
                ])
        rhs_sum = Sum([
                    vars[succ_id_2] for
                    (succ_id_2, _) in succ_dist_without_target_states
                ])

        def _multiply(left,right):
            args = (Ast * 2)()
            args[0] = left.as_ast()
            args[1] = right.as_ast()
            return ArithRef(Z3_mk_mul(left.ctx.ref(), 2, args), left.ctx)


        for (succ_id, prob) in succ_dist_without_target_states:
            # opt_var is the absolute value of the ratio
            lhs = _multiply(vars[succ_id], lhs_sum)
            rhs = _multiply(self.oracle.get_oracle_value(succ_id), rhs_sum)
            equality = lhs == rhs
            self.opt_solver.add(equality)

        if self.opt_solver.check() == sat:
            return True

        else:
            self.opt_solver.pop()
            return False

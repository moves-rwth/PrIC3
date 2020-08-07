import logging


from z3 import *

logger = logging.getLogger(__name__)


class PrIC3Solver:

    def __init__(self, smt_program, stats, store_smt_calls, settings):

        self.smt_program = smt_program
        self.settings = settings

        self.solvers = []
        self.opt_solvers = []
        
        self.initialize_f0()
        # Phi Applied remains constant.
        self._phi_applied = self.smt_program.env.apply_to_state_valuation(self.smt_program.phi)
        self._fresh_initialized_solver = Solver()
        self.initialize_solver(self._fresh_initialized_solver)
        self.stats = stats
        self._calls = 0
        self._store_check_calls = store_smt_calls
        self._stored_calls = []

    def add_new_solver(self):
        solver = self._fresh_initialized_solver.translate(self._fresh_initialized_solver.ctx)
        #solver = SolverFor("QF_NRA")
        self.solvers.append(solver)
        #print(solver.sexpr())

    def initialize_f0(self):
        solver = Solver()
        #solver = SolverFor("QF_NRA")
        self.solvers.append(solver)

        self.initialize_solver(solver)
        solver.add(self.get_f_0())
        #print(solver.sexpr())



    # Adds all formulas onto the solver that remain their all the time
    def initialize_solver(self, solver):
        for formula in self.smt_program.get_all_initial_formulas():
            _solver_add(solver, formula)


    # Keep in mind: 0-step probability is 1 if goal and var range, 0 otherwise
    def get_f_0(self):
        env = self.smt_program.env
        return env.forall(
            env.apply_to_state_valuation(self.smt_program.frame) == If(
                And([
                    self.smt_program.goal_expr,
                    self.smt_program.get_bounds_formula()
                ]), RealVal(1), RealVal(0)))


    def add_assertion(self, frame_index, assertion):
        _solver_add(self.solvers[frame_index], assertion)

    def is_relative_inductive(self, frame_index, state_args, expression, ignore_stats = False):
        """
        Checks for relative inductiveness.
        A frame index is not relative inductive iff
            there is a state s satsifying state_args such that Phi(F_{frame_index})[s] > expression(s)
        Expression can depend on that state

        :param frame_index:
        :param state_args:
        :param expression:
        :return: If not return_model_if_sat: If relative inductivity holds, we return True. Otherwise, we return the command-index of a
        """

        if not ignore_stats:
            self.stats.start_check_relative_inductiveness_timer()
        # Assert that the free z3_program_variables satisfy state_formula
        # Assert that \Phi(frame)[state represented by free z3 variables] > expression
        # If SAT, then there is such a state, so we return False

        #TODO: use assumptions again.

        if self.settings.generalize:
            self.solvers[frame_index].push()
            self.solvers[frame_index].add(And(_lt_no_coerce(expression,self._phi_applied), *state_args))
            res = self.solvers[frame_index].check()

        else:
            res = self.solvers[frame_index].check(_lt_no_coerce(expression,self._phi_applied), *state_args)
            #Sometimes, this call yields unkown!



        if res == unknown:
            print(self.solvers[frame_index].sexpr())
            raise Exception("is_relative_inductive: Result of SMT Call is UNKOWN")

        if not ignore_stats:
            self.stats.stop_check_relative_inductiveness_timer(res != sat)

        self._calls += 1
        if self._store_check_calls != 0 and self._calls % self._store_check_calls == 0:
            self._store_call(frame_index, state_args, not res, _lt_no_coerce(expression,self._phi_applied), *state_args)



        # In case we generalize and use reals instead of ints, we have to ensure that the program variables are assgined integer values.
        if res == sat and (self.settings.generalize and self.settings.int_to_real):

            model = self.solvers[frame_index].model()

            if self.settings.generalize:
                self.solvers[frame_index].pop()

            # If we generalize and use real numbers, then we have to ensure that we get an integer solution as a counter example to inductivity
            # If we do not generalize or do not use reals, then this is ensured.
            if self.settings.int_to_real and self.settings.generalize:
                to_assert = []

                while True:
                    #print("In check-if-integer-loop.")
                    # Check if every variable is an integer solution
                    is_int = True
                    for var in self.smt_program.input_program.module.integer_variables:
                        if not float(model[var.variable].as_fraction()).is_integer():
                            is_int = False
                            break

                    if is_int:
                        return model

                    # Exclude the current non-integer-solutions
                    to_assert = to_assert + [Or(var.variable >= RealVal(math.ceil(model[var.variable].as_fraction())),
                                                var.variable <= RealVal(math.floor(model[var.variable].as_fraction()))) for var in self.smt_program.input_program.module.integer_variables]

                    self.solvers[frame_index].push()
                    self.solvers[frame_index].add(And(_lt_no_coerce(expression, self._phi_applied), *state_args))
                    self.solvers[frame_index].add(And(to_assert))

                    res = self.solvers[frame_index].check(And(_lt_no_coerce(expression, self._phi_applied), *state_args))

                    # Check if counterexample still exists
                    if res == sat:
                        model = self.solvers[frame_index].model()
                        self.solvers[frame_index].pop()
                        continue

                    else:
                        if res == unknown:
                            print(self.solvers[frame_index].sexpr())
                            assert False
                        self.solvers[frame_index].pop()
                        return True

            return model

        else:
            if res == sat: model = self.solvers[frame_index].model()
            if self.settings.generalize:
                self.solvers[frame_index].pop()

        return True if res == unsat else model


    def get_highest_phi(self, frame_index, state_args):
        opt = Optimize()
        opt.add(self.solvers[frame_index].assertions())
        opt.add(state_args)
        opt_var = Real('opt')
        opt.add(opt_var == self._phi_applied)
        opt.maximize(opt_var)
        res = opt.check()
        if res == unknown or res == unsat:
            raise
        else:
            m = opt.model()
            return m[opt_var]

    def _store_call(self, frame_index, state_valuation, satisfiable, *assumptions):
        self._stored_calls.append((";Frame index {}\n;State valuation {}\n;Satisfiable:{}\n".format(frame_index, state_valuation,satisfiable)+ self.solvers[frame_index].sexpr() + "\n" + _to_sexpr(assumptions), satisfiable))

    def print_solver_assertions(self, solver):
        for ass in solver.assertions():
            print(ass)

    def export_solver_stacks(self, prefix):
        for i, stored in enumerate(self._stored_calls):
            _smt_formula_to_file(prefix + "_stored_" + str(i) + ".smt2", stored[0], stored[1])
        for i, solver in enumerate(self.solvers):
            _export_solver_stack(solver, prefix + "_stack_" + str(i) + ".smt2")

def _smt_formula_to_file(path, formula, satisfiable):
    with open(path, 'w') as file:
        logger.debug("Writing to %s... (satisfiable problem: %s)" % (path, satisfiable))
        file.write(formula)
        file.write("(check-sat)")
        if satisfiable:
            file.write("\n(get-model)")
        logger.debug("done.")

def _export_solver_stack(solver, path):
    _smt_formula_to_file(path, solver.sexpr(), True)

def _to_sexpr(self, *expr):
    # Somehow, this seems necessary on some low-level formulae
    tmpsolve = z3.Solver()
    tmpsolve.add(expr)
    return tmpsolve.sexpr()



def _eq_no_coerce(left,right):
    #TODO add assertion for coercion-free
    return BoolRef(Z3_mk_eq(left.ctx_ref(), left.as_ast(), right.as_ast()), left.ctx)

def _lt_no_coerce(left,right):
    #TODO add assertion for coercion-free
    return BoolRef(Z3_mk_lt(left.ctx_ref(), left.as_ast(), right.as_ast()), left.ctx)

def _solver_add(solver,expr):
    #TODO add assertions for bool type
    Z3_solver_assert(solver.ctx.ref(), solver.solver, expr.as_ast())

def _solver_add_it(solver,exprs):
    #TODO add assertions for bool type
    for expr in exprs:
        _solver_add(solver,expr)

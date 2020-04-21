# pylint: disable=misplaced-comparison-constant
"""
Translate a PRISM program into a bunch of SMT commands.

.. autosummary::
    SmtEnv.function
    SmtEnv.forall
    SmtEnv.apply
    SmtProgram
"""

from typing import Any, Dict, List, Union, NamedTuple
from enum import Enum, unique

import z3
from z3 import (And, Or, Xor, Ast, Bool, BoolRef, BoolSort, ForAll, Function, Implies,
                Int, Not, RatNumRef, RealSort, Sum, Z3_mk_app, Z3_mk_ge, is_bool,
                substitute, BoolVal, Real, IntSort, IntNumRef, BitVec)

from pric3.input_program import InputModule, InputProgram, InputVariable
from pric3 import input_program as INPUTPROGRAM
from pric3.utils import next_or_value

@unique
class ForallMode(Enum):
    """
    Choose between three modes to implement forall quantifiers.

    * `FORALL_QUANTIFIER`: Use a forall quantifier (but use different variable names for clarity).
    * `FORALL_MACRO`:
        Replace every occurence of quantified variables with all possible right-hand sides
        of all possible updates in the program, thus avoiding the use of the forall quantifier.
        This speeds the solving process greatly.
    * `FORALL_GLOBALS`:
        Like `FORALL_MACRO`, but all parameters are global, thus all functions created have arity zero.
    """
    FORALL_QUANTIFIER = "quantifier"
    FORALL_MACRO = "macro"
    FORALL_GLOBALS = "globals"

    @classmethod
    def from_str(cls, text: str) -> 'ForallMode':
        """Convert a string to a ForallMode."""
        return next(mode for mode in cls.__members__.values() if mode.value == text)

class SmtEnv:
    """
    The SmtEnv has helper functions to create and apply SMT functions over the program state.

    Attributes:
        variables (list[InputVariable]): list of all variables in the program.
        macro_substs (List[List[Tuple[z3.ExprRef, z3.ExprRef]]]): list of substitutions applied to each ForAll if `forall_mode` is not `FORALL_QUANTIFIER`.

    Example:
            .. testsetup::

                >>> from stormpy import parse_prism_program
                >>> from z3 import RealSort
                >>> program = parse_prism_program("pric3/prism_models/MCs/grid.pm")
                >>> input_program = InputProgram(program)
                >>> env = SmtEnv(input_program.module, ForallMode.FORALL_QUANTIFIER, None) # TODO!

            Consider an environment ``env`` that contains variables ``a`` and ``b``, both of type ``Int``.

            .. testcode::

                >>> bla = env.function('bla', RealSort())
                >>> bla.sexpr()
                '(declare-fun bla (Int Int) Real)'
                >>> env.forall(env.apply_to_state_valuation(bla) >= 1)
                ForAll([var_a, var_b], bla(var_a, var_b) >= 1)
    """
    def __init__(self, input_module: InputModule, forall_mode: ForallMode, smt_program):
        self.variables = input_module.variables.values()
        self.forall_mode = forall_mode
        self.input_module = input_module
        self.smt_program = smt_program
        self._function_types: Dict[int, Any] = dict()
        self._z3_var_list = [var.variable for var in self.variables]
        self._z3_sorts = [
            z3_variable.sort() for z3_variable in self._z3_var_list
        ]

        self._z3_local_var_list = [
            Bool("var_" + str(var)) if is_bool(var) else INPUTPROGRAM.INT_CTOR("var_" + str(var))
            for var in self._z3_var_list
        ]
        self._z3_local_subst = [(old_var, self._z3_local_var_list[i])
                                for i, old_var in enumerate(self._z3_var_list)]
        self.macro_substs = self._get_macro_substs(input_module)

    def function(self, name, return_sort: z3.SortRef) -> z3.ExprRef:
        """Return a new function that receives all environment variables as arguments."""
        params = self._z3_sorts if self.forall_mode != ForallMode.FORALL_GLOBALS else []
        func = Function(name, params + [return_sort])

        # Registering types for faster apply.
        if str(return_sort) == "Real":
            Ref = RatNumRef
        elif str(return_sort) == "Int":
            Ref = IntNumRef
        else:
            assert str(return_sort) == "Bool"
            Ref = BoolRef
        self._function_types[func.get_id()] = Ref

        return func

    def forall(self, z3_formula: z3.ExprRef) -> z3.ExprRef:
        """
        See `ForallMode` documentation.
        """
        if self.forall_mode == ForallMode.FORALL_QUANTIFIER:
            return ForAll(self._z3_local_var_list,
                          substitute(z3_formula, *self._z3_local_subst))
        elif self.forall_mode in [ForallMode.FORALL_MACRO, ForallMode.FORALL_GLOBALS]:
            return And([
                substitute(z3_formula, substitution)
                for substitution in self.macro_substs
            ])
        else:
            raise ValueError("invalid forall_mode: %s" % self.forall_mode)

    def command_specific_forall(self, z3_formula: z3.ExprRef) -> z3.ExprRef:
        """
        See `ForallMode` documentation.
        """
        if self.forall_mode == ForallMode.FORALL_QUANTIFIER:
            return ForAll(self._z3_local_var_list,
                          substitute(z3_formula, *self._z3_local_subst))
        elif self.forall_mode in [ForallMode.FORALL_MACRO, ForallMode.FORALL_GLOBALS]:

            result = []

            for command in self.input_module.commands:
                # For every command, we add a conjunct
                # "No goal" AND "guard of command" >=   (conjunction of substituted formulae for corresponding frame variables)
                result.append(Implies(And(Not(self.smt_program.goal_expr), command.guard),

                                      And([
                                          substitute(z3_formula, substitution)
                                          for substitution in self.command_to_substs[command]
                                      ])
                                      ))

            return And(result)
        else:
            raise ValueError("invalid forall_mode: %s" % self.forall_mode)


    def apply_to_state_valuation(self,
                                 z3_function: z3.ExprRef,
                                 valuation: Union[Dict[InputVariable, z3.ExprRef]] = None
                                 ) -> z3.ExprRef:
        """
        Apply a function that takes all environment variables with optional valuations.
        Functions have to registered with function method.
        """
        if self.forall_mode != ForallMode.FORALL_GLOBALS:
            valuation = valuation or dict()
            valuation = {var.name: value for var, value in valuation.items()}
            args = [
                valuation.get(var.name, var.variable) for var in self.variables
            ]
        else:
            args = []

        return self.apply_to_state_args(z3_function, args)




    def apply_to_state_args(self,
                                 z3_function: z3.ExprRef,
                                 state_args = None
                                 ) -> z3.ExprRef:
        """
        Apply a function that takes all environment variables with optional valuations.
        Functions have to registered with function method.
        """
        if self.forall_mode != ForallMode.FORALL_GLOBALS:
            args = state_args or list()
        else:
            args = []

        def _funccall(func, args):
            num = len(args)
            _args = (Ast * num)()
            for i in range(num):
                # self.domain(i).cast(args[i]) may create a new Z3 expression, which may then become garbage collected.
                # TODO: check whether assert is correct.
                #assert args[i] == func.domain(i).cast(args[i])
                _args[i] = args[i].as_ast()
            return self._function_types[func.get_id()](Z3_mk_app(
                func.ctx_ref(), func.ast, num, _args), func.ctx)

        return _funccall(z3_function, args)





    def _get_macro_substs(self, input_module: InputModule, specific_command = None):

        assignments = (update.assignments for command in input_module.commands
                        for update in command.updates)


        self.command_to_substs: Dict[Any, Any] = dict()
        self.subst_index_to_command: Dict[Any, Any] = dict()

        result = []
        index = 0

        for command in input_module.commands:
            self.command_to_substs[command] = list()

            for update in command.updates:
                self.subst_index_to_command[index] = command
                assignments = (update.assignments, ) # type: ignore

                to_add = [(var.variable, new_expr)
                                            for assignment in assignments for var, new_expr in assignment.items()]
                result.append(to_add)

                self.command_to_substs[command].append(to_add)

                index += 1


        return result

class SmtSettings(NamedTuple):
    """
    Various settings related to the SmtProgram translation for optimization purposes.
    """
    forall_mode: ForallMode
    inline_goal: bool

class SmtProgram:
    """
    Representation of a program by three z3 functions: :py:attr:`frame`, :py:attr:`phi`, and :py:attr:`goal`.
    All three can be used via methods of :py:attr:`SmtProgram.env`.

    Use :py:func:`get_bounds_formula` and :py:func:`get_all_initial_formulas` to create SMT constraints for the program state.

    Attributes:
        input_program (InputProgram): the input program.
        settings (SmtSettings): the settings for this program.
        env (SmtEnv): the environment with all variables in the program.
        frame (z3.ExprRef): z3 uninterpreted function that represents Frame.
        phi (z3.ExprRef): z3 uninterpreted function that represents Phi.
        goal_expr (z3.ExprRef): z3 expression that represents the goal.
        chosen_command (z3.ExprRef): the variable that contains the chosen command's index.
    """
    def __init__(self, input_program: InputProgram, settings: SmtSettings):
        self.input_program = input_program
        self.settings = settings
        env = SmtEnv(input_program.module, settings.forall_mode, self)
        self.env = env

        self.frame = env.function("Frame", RealSort())
        if settings.forall_mode == ForallMode.FORALL_GLOBALS:
            self.frames: List[z3.ExprRef] = []

            old_command = None
            j = 0

            for i, subst in enumerate(env.macro_substs):

                frame_i = env.function("F%s" % i, RealSort())
                self.frames.append(frame_i)
                subst.append((env.apply_to_state_valuation(self.frame), env.apply_to_state_valuation(frame_i)))

                cur_command = self.env.subst_index_to_command[i]
                if cur_command != old_command:
                    old_command = cur_command
                    j = 0

                else:
                    j = j + 1

                self.env.command_to_substs[cur_command][j].append((env.apply_to_state_valuation(self.frame), env.apply_to_state_valuation(frame_i)))

        self.phi = env.function("Phi", RealSort())
        self.goal_expr = input_program.goal if settings.inline_goal else env.apply_to_state_valuation(env.function("Goal", BoolSort()))
        self.chosen_command = INPUTPROGRAM.INT_CTOR("ChosenCommand")
        self._initial_formulae: Union[None, List[z3.ExprRef]] = None

    def get_bounds_formula(self) -> z3.ExprRef:
        """
        Return the formula that bounds all program variables.
        """
        return And(*(var.bounds
                     for var in self.env.variables if var.bounds is not None))

    def _get_chosen_command_bounds_formula(self):
        return And(self.chosen_command >= 0, self.chosen_command <= len(self.input_program.module.commands))

    # not a goal state + no guard active => frame = 0
    def _get_frame_zero_formula(self):
        not_goal = Not(self.goal_expr)
        no_guard_active = And([
            Not(command.guard)
            for command in self.input_program.module.commands
        ])
        return self.env.forall(
            Implies(And(not_goal, no_guard_active),
                    0 == self.env.apply_to_state_valuation(self.frame)))

    # frame is bounded by 1
    def _get_frame_at_most_one_formula(self):
        return self.env.forall(1 >= self.env.apply_to_state_valuation(self.frame))

    # define goal
    def _get_goal_def_formula(self):
        if self.settings.inline_goal:
            return BoolVal(True)
        return And([
            self.env.forall(
                self.goal_expr == self.input_program.goal),
            self.goal_expr == self.input_program.goal
        ])

    # Goal state => frame var is one
    def _get_frame_one_if_goal_formula(self):
        vars_in_range = self.get_bounds_formula()
        return self.env.forall(Implies(And(vars_in_range, self.goal_expr)  , 1 == self.env.apply_to_state_valuation(self.frame)))

    # vars in range && goal => phi = 1
    def _get_phi_one_if_goal_formula(self):
        vars_in_range = self.get_bounds_formula()
        return Implies(And(vars_in_range, self.goal_expr),
                       1 == self.env.apply_to_state_valuation(self.phi))

    # vars in range && not goal && guard of command => phi(F)[s] = wp[command](F)[s]
    def _get_commands_formula(self):
        if self.settings.forall_mode == ForallMode.FORALL_GLOBALS:
            return self._get_commands_formula_deterministic()
        else:
            return self._get_commands_formula_nondeterministic()

    def _get_updates_formula(self, updates, frames):
        return Sum([
            update.probability *
            self.env.apply_to_state_valuation(next_or_value(frames), update.assignments)
            for update in updates
        ])

    def _get_commands_formula_nondeterministic(self):
        vars_in_range = self.get_bounds_formula()
        phi_applied = self.env.apply_to_state_valuation(self.phi)

        return And([
            Implies(
                And([
                    vars_in_range,
                    Not(self.goal_expr),
                    command.guard,
                    self.chosen_command == i
                ]),
                And([
                    phi_applied == self._get_updates_formula(command.updates, self.frame)
                ])
            )
            for i, command in enumerate(self.input_program.module.commands)
        ])

    def _get_commands_formula_deterministic(self):
        phi_applied = self.env.apply_to_state_valuation(self.phi)
        frames_iter = iter(self.frames)
        return And([
            Implies(And(Not(self.goal_expr), command.guard, self.chosen_command == i),
                phi_applied == self._get_updates_formula(command.updates, frames_iter)
            )
            for i, command in enumerate(self.input_program.module.commands)
        ])

    # Ensure that the solver chooses a correct chosen_command if a corresponding guard holds.
    def _get_if_at_least_one_guard_holds_choose_exactly_one_command_formula(self):

        at_least_one_guard_holds_formula = Or([command.guard for command in self.input_program.module.commands])

        choose_exactly_one_guard_formula = Or([And(command.guard, self.chosen_command ==i)
                                                for i, command in enumerate(self.input_program.module.commands)])

        return Implies(at_least_one_guard_holds_formula, choose_exactly_one_guard_formula)


    # vars in range && not goal && no guard => phi(F)[s] = 0
    def _get_sink_phi_zero_formula(self):
        vars_in_range = self.get_bounds_formula()
        not_goal = Not(self.goal_expr)
        no_guard_active = And([
            Not(command.guard)
            for command in self.input_program.module.commands
        ])
        return Implies(And(vars_in_range, not_goal, no_guard_active),
                       0 == self.env.apply_to_state_valuation(self.phi))

    # vars not in range => phi(F)[s] = 0
    def _get_not_in_range_phi_zero_formula(self):
        return BoolVal(True) # TODO: is this necessary?
        # vars_in_range = self.get_bounds_formula()
        # return Implies(Not(vars_in_range), 0 == self.env.apply(self.phi))

    def get_all_initial_formulas(self) -> List[z3.ExprRef]:
        """
        Return a list of all inital program assertions.
        """
        if self._initial_formulae is None:
            self._initial_formulae = [
                self.get_bounds_formula(),
                self._get_chosen_command_bounds_formula(),
                self._get_frame_zero_formula(),
                self._get_frame_at_most_one_formula(),
                self._get_goal_def_formula(),
                self._get_phi_one_if_goal_formula(),
                self._get_if_at_least_one_guard_holds_choose_exactly_one_command_formula(),
                self._get_commands_formula(),
                self._get_sink_phi_zero_formula(),
                self._get_not_in_range_phi_zero_formula(),
                #self._get_frame_one_if_goal_formula() We do not need these (I guess)
            ]
        return self._initial_formulae

    def get_frame_constraints(self, z3_state_constraints, z3_probability_expr):
        """
        Create a forall-quantified implication.
        """
        return self.env.forall(Implies(z3_state_constraints, z3_probability_expr))


    #TODO: Does no_coerce help here?
    def get_frame_leq_constraint(self, state_valuation, z3_probability_expr):

        state_constr = And([var.variable == state_valuation[var] for var in state_valuation])
        return self.env.forall(Implies(state_constr, self._ge_no_coerce(z3_probability_expr, self.env.apply_to_state_valuation(self.frame))))


    def get_frame_leq_constraint_from_state_args(self, state_args, z3_probability_expr):

        state_constr = And([arg for arg in state_args])
        return self.env.command_specific_forall(Implies(state_constr, self._ge_no_coerce(z3_probability_expr, self.env.apply_to_state_valuation(self.frame))))

    def _ge_no_coerce(self, left, right):
        # TODO: add assertions for noncoerce
        return BoolRef(Z3_mk_ge(left.ctx_ref(), left.as_ast(), right.as_ast()), left.ctx)

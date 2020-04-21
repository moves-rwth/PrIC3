"""
Representation of an input PRISM program.
Expressions are Z3 expressions generated from the PRISM expressions.

* An :class:`InputProgram` consists of:
    * :py:attr:`InputProgram.program`,
    * :py:attr:`InputProgram.goal`,
    * :py:attr:`InputProgram.module` -- one single :class:`InputModule`:
        * :py:attr:`InputModule.variables`,
        * :py:attr:`InputModule.commands` -- a list of :class:`InputCommand`:
            * :py:attr:`InputCommand.guard`,
            * :py:attr:`InputCommand.updates` -- a list of :class:`InputUpdate`:
                * :py:attr:`InputUpdate.probability`,
                * :py:attr:`InputUpdate.assignments`.

"""

import operator
from collections import OrderedDict
from fractions import Fraction
from typing import Dict, Union

import z3
from z3 import And, Bool, BoolVal, Int, IntVal, Or, RealVal, Real

import stormpy
from stormpy import (PrismBooleanVariable, PrismIntegerVariable,
                     PrismVariable, PrismCommand, PrismModule, PrismProgram,
                     PrismUpdate, PrismModelType)


def _get_main_module(program: PrismProgram) -> PrismModule:
    """
    Retrieve the program's single module, which is not necessarily called "main".
    """
    assert len(program.modules) == 1
    main = program.modules[0]
    return main


INT_CTOR = Int
"""Constructor for Int variables. Can also be Real."""
INTVAL_CTOR = IntVal
"""Constructor for Int values. Can also be RealVal."""


class InputProgram:
    """
    Representation of an input PRISM program consisting of a goal expression
    and a main module.

    Attributes:
        program (PrismProgram): the prism program.
        model_type (PrismModelType): the model type of the program, probably `stormpy.PrismModelType.DTMC` or `stormpy.PrismModelType.MDP`.
        module (InputModule): the main module of the program.
        goal (ExprRef): the z3 expression labelled "goal".
        prism_goal (stormpy.Expression): the prism goal expression.
        constants (set(str)): set of constants.
    """
    def __init__(self, program: PrismProgram):
        program = program.substitute_constants()
        self.prism_program = program
        self.model_type = program.model_type
        self.module = InputModule(_get_main_module(program))
        self.goal = _translate_expression(self.module.variables,
                                          program.get_label_expression("goal"))
        self.prism_goal = program.get_label_expression("goal")
        self.constants = set((constant.name for constant in program.constants))

        if not (self.model_type == stormpy.storage.PrismModelType.DTMC or self.model_type == stormpy.storage.PrismModelType.MDP):
            raise Exception("The model type must be either a DTMC or an MDP.")


class InputModule:
    """
    Represents one input PRISM module.

    Attributes:
        integer_variables (list(InputVariable)): list of all integer variables.
        boolean_variables (list(InputVariable)): list of all boolean variables.
        variables (dict(str, InputVariable)): dict of variable names to variables.
        commands (list(InputCommand)): list of commands in this module.
    """
    def __init__(self, prism_module: PrismModule):
        # variables are created in two steps:
        # first, create all (incomplete variable objects).
        self.variables: Dict[str, 'InputVariable'] = OrderedDict()

        self.integer_variables = [InputVariable(var) for var in prism_module.integer_variables]
        self.boolean_variables = [InputVariable(var) for var in prism_module.boolean_variables]
        for var in self.integer_variables + self.boolean_variables:
            self.variables[var.name] = var

        # second, initialize bounds expressions when all z3 variables are created.
        for var in self.variables.values():
            var._init_bounds(self.variables)

        self.commands = [
            InputCommand(self.variables, command)
            for command in prism_module.commands
        ]

    def lookup_variable(self,
                        variable: Union[str, 'InputVariable', PrismVariable]
                        ) -> 'InputVariable':
        """
        Lookup a variable in this module.
        """
        if isinstance(variable, str):
            return self.variables[variable]
        return self.variables[variable.name]

    def translate_expression(self,
                             prism_expr: stormpy.Expression) -> z3.ExprRef:
        """
        Translate a PRISM expression to Z3.
        """
        return _translate_expression(self.variables, prism_expr)

class InputVariable:

    """
    Represents a PRISM variable by a reference to its Z3 variable instance and optional bounds.

    Attributes:
        name (str): the variable name.
        variable (z3.ExprRef): z3 variable.
        bounds (Union[z3.ExprRef, None]): optional z3 bounding expression for this variable.
        lower_bound (Union[z3.ExprRef, None]): optional z3 expression for the lower bound of this variable.
        upper_bound (Union[z3.ExprRef, None]): optional z3 expression for the upper bound of this variable.
    """
    def __init__(self, prism_variable):
        self._prism_variable = prism_variable
        self.name = prism_variable.name
        self.bounds = None
        self.lower_bound = None
        self.upper_bound = None
        if isinstance(prism_variable, PrismBooleanVariable):
            self.variable = Bool(prism_variable.name)
        elif isinstance(prism_variable, PrismIntegerVariable):
            self.variable = INT_CTOR(prism_variable.name)
        else:
            raise NotImplementedError()

    def _init_bounds(self, variables: Dict[str, 'InputVariable']):
        """
        Initialize the bounds field.
        """
        prism_variable = self._prism_variable
        if isinstance(prism_variable, PrismIntegerVariable):
            lower_bound = _translate_expression(
                variables, prism_variable.lower_bound_expression)
            upper_bound = _translate_expression(
                variables, prism_variable.upper_bound_expression)
            self.bounds = And(lower_bound <= self.variable,
                              self.variable <= upper_bound)
            self.lower_bound = lower_bound
            self.upper_bound = upper_bound

    def get_prism_variable(self):
        return self._prism_variable

    def __repr__(self):
        return "[InputVariable: %s]" % self.name


class InputCommand:
    """
    Represents a PRISM command with a guard and a list of updates.

    Attributes:
        global_index (int): an identifier that can be used to find this command from a choice's origin.
        guard (z3.ExprRef): Z3 expression for the command's guard.
        updates (list[InputUpdate]): list of updates in this command.
    """
    def __init__(self, variables, prism_command: PrismCommand):
        self.global_index = prism_command.global_index
        self.guard = _translate_expression(variables,
                                           prism_command.guard_expression)
        self.updates = [
            InputUpdate(variables, update) for update in prism_command.updates
        ]


class InputUpdate:
    """
    Represents a PRISM update with a list of assignments and a probability expression.

    Attributes:
        assignments (dict[InputVariable, z3.ExprRef]): dict of individual assignments.
        probability (z3.ExprRef): a Z3 expression for the probability of the update.
    """
    def __init__(self, variables, prism_update: PrismUpdate):
        self.assignments = {
            variables[assignment.variable.name]:
            _translate_expression(variables, assignment.expression)
            for assignment in prism_update.assignments
        }
        self.probability = _translate_expression(
            variables, prism_update.probability_expression)

class _ExpressionTranslator:
    def __init__(self):
        self._int_cache: Dict[stormpy.Expression, z3.ExprVal] = dict()

    def translate_expression(self,
                             variables,
                             prism_expr: stormpy.Expression) -> z3.ExprRef:
        # Translate primitive types.
        # TODO: missing types!
        if isinstance(prism_expr, bool):
            # Note: the order of comparing bool and int types is significant,
            # as bool is a subtype of int in Python.
            return BoolVal(prism_expr)
        elif isinstance(prism_expr, int):
            cache_hit = self._int_cache.get(prism_expr)
            if cache_hit is not None:
                return cache_hit
            z3intval = INTVAL_CTOR(prism_expr)
            self._int_cache[prism_expr] = z3intval
            return z3intval
        # If we have a variable from the environment, look up its z3 variable.
        elif prism_expr.is_variable() and variables[prism_expr.identifier()]:
            return variables[prism_expr.identifier()].variable
        # Otherwise, evaluate the value if it is a variable or a literal.
        elif prism_expr.is_variable() or prism_expr.is_literal():
            if prism_expr.has_boolean_type():
                return BoolVal(prism_expr.evaluate_as_bool())
            elif prism_expr.has_integer_type():
                intval = prism_expr.evaluate_as_int()
                cache_hit = self._int_cache.get(intval)
                if cache_hit is not None:
                    return cache_hit
                z3intval = INTVAL_CTOR(intval)
                self._int_cache[intval] = z3intval
                return z3intval
            elif prism_expr.has_rational_type():
                rational_value = prism_expr.evaluate_as_rational()
                return RealVal(
                    Fraction(Fraction(str(rational_value.numerator)),
                             Fraction(str(rational_value.denominator))))
        # special case for sot.Divide: we intentionally only support division for constant values
        elif prism_expr.is_function_application and prism_expr.operator == stormpy.OperatorType.Divide:
            return Fraction(
                Fraction(prism_expr.get_operand(0).evaluate_as_int()),
                Fraction(prism_expr.get_operand(1).evaluate_as_int()))
        # Lastly, handle function applications.
        elif prism_expr.is_function_application:
            sot = stormpy.OperatorType
            operators = {
                sot.And:
                    And,
                sot.Or:
                    Or,
                sot.Xor:
                    operator.xor,
                sot.Implies:
                    z3.Implies,
                sot.Iff:
                    operator.eq,
                sot.Plus:
                    operator.add,
                sot.Minus:
                    operator.sub,
                sot.Times:
                    operator.mul,
                # sot.Divide is handled above
                # sot.Min: z3.Min,
                # sot.Max: z3.Max,
                # TODO: Power, Modulo missing
                sot.Equal:
                    operator.eq,
                sot.NotEqual:
                    operator.ne,
                sot.Less:
                    operator.lt,
                sot.LessOrEqual:
                    operator.le,
                sot.Greater:
                    operator.gt,
                sot.GreaterOrEqual:
                    operator.ge,
                sot.Not:
                    operator.neg,
                # TODO: Floor and Ceil missing
                sot.Ite:
                    z3.If
            }
            op_fn = operators[prism_expr.operator]

            operands = (_translate_expression(variables, prism_expr.get_operand(i))
                        for i in range(prism_expr.arity))

            return op_fn(*operands)

        raise NotImplementedError()

_EXPR_TRANSLATOR = _ExpressionTranslator()
def _translate_expression(variables,
                          prism_expr: stormpy.Expression) -> z3.ExprRef:
    """
    Translate a PRISM expression to a Z3 expression.
    """
    return _EXPR_TRANSLATOR.translate_expression(variables, prism_expr)

def set_global_expression_int_to_real(int_to_real: bool):
    """
    Set the option whether to convert integer variables to reals globally.
    """
    global INT_CTOR
    global INTVAL_CTOR
    INT_CTOR = Int if not int_to_real else Real
    INTVAL_CTOR = IntVal if not int_to_real else RealVal
    _EXPR_TRANSLATOR = _ExpressionTranslator() # pylint: disable=invalid-name

from pric3.oracles.oracle import Oracle
from pric3.state_graph import StateId
import logging

import z3
import stormpy
import stormpy.storage as stormpyst # type:ignore

logger = logging.getLogger(__name__)

class ModelCheckingOracle(Oracle):

    def __init__(self, *args):
        super().__init__(*args)
        self._model = None
        self._mc_result = None

    def initialize(self):
        logger.debug("Initialize oracle...")
        formula_str = "Pmax=? [F \"goal\"]"
        properties = stormpy.parse_properties(formula_str, self._get_prism_program())
        logger.debug("...building model...")
        self._model = stormpy.build_symbolic_model(self._get_prism_program(), properties)
        env = stormpy.Environment()
        env.solver_environment.set_linear_equation_solver_type(stormpy.EquationSolverType.native)
        env.solver_environment.native_solver_environment.method = stormpy.NativeLinearEquationSolverMethod.power_iteration
        env.solver_environment.native_solver_environment.maximum_iterations = 100
        logger.debug("...doing model checking...")
        self._mc_result = stormpy.model_checking(self._model, properties[0], environment=env)
        logger.debug("Initialization done.")

    #TODO
    def refine_oracle(self, visited_states):
        """
        Refines the oracle for the states in oracle_states + visited_states
        :param visited_states:
        :return:
        """
        pass
    #TODO
    def _ensure_value_in_oracle(self, state_id: StateId):
        state_mapping_bools, state_mapping_ints = self._state_id_to_prism_variable_to_value(state_id)
        expr_manager = self._get_prism_program().expression_manager
        characteristic_expressions_int = [stormpyst.Expression.Eq(var.expression_variable.get_expression(),expr_manager.create_integer(val))
                                      for var,val in state_mapping_ints.items()]
        characteristic_expressions_bools = [var.expression_variable.get_expression() for var, val in state_mapping_bools.items()]
        state_expression = stormpy.storage.Expression.Conjunction(characteristic_expressions_int + characteristic_expressions_bools)
        #print(str(state_expression))
        cached_res = self._mc_result.clone()
        cached_res.filter(stormpy.create_filter_symbolic(self._model, state_expression))

        if cached_res.min > cached_res.max:
            self.oracle[state_id] = self._from_mc_result_to_z3_ref(self.settings.default_oracle_value)
        else:
            assert cached_res.min == cached_res.max
            self.oracle[state_id] = self._from_mc_result_to_z3_ref(cached_res.min)

    def _from_mc_result_to_z3_ref(self, val):
        #TODO super nasty.
        return z3.RealVal(str(val))


    def _state_id_to_prism_variable_to_value(self, state_id):
        """
            Returns a dict from prism variables to z3 values representing the valuation of state_id.
        :param state_id:
        :return:
        """
        state_valuation = self.state_graph.get_state_valuation(state_id)
        return {input_variable.get_prism_variable(): z3.is_true(z3_value) for input_variable, z3_value in state_valuation.items() if not (z3.is_int_value(z3_value) or z3.is_rational_value(z3_value))}, {input_variable.get_prism_variable() : z3_value.as_long() for input_variable, z3_value in state_valuation.items() if (z3.is_int_value(z3_value) or z3.is_rational_value(z3_value))}


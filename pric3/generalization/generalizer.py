"""
Caches "states of the same kind".
Computes a generalization, if available.
"""

from pric3.generalization.state_of_the_same_kind_cache import StatesOfTheSameKindCache
from pric3.generalization.interpolator import Interpolator
from pric3.utils import *
from pric3.proof_obligations.repushing_obligation_queue import RepushingObligationQueue
from z3 import RealVal, IntVal, Solver

class Generalizer:

    def __init__(self, state_graph, smt_program, p_solver, statistics, settings):

        self.state_graph = state_graph
        self.smt_program = smt_program
        self.input_program = self.smt_program.input_program
        self.p_solver = p_solver
        self.statistics = statistics

        self._state_of_the_same_kind_cache = StatesOfTheSameKindCache(self.state_graph, self.input_program,
                                                                      self.statistics)
        self._interpolator = Interpolator()

        # For checking whether generalizations are probabilities
        self.solver = Solver()

        self.settings = settings

        Generalizer.split_limit = 0

    def consider_state(self, state_id):
        """
            Invoked by PrIC3 upon popping an obligation for state_id.
            Computes the state valuation of state_id and checks for each variable whether "dropping" it
            yields a new state of this kind. If so, store it. If not, discard.

        :param state_id: The id of the state to consider.
        :return:
        """
        self._state_of_the_same_kind_cache.consider_state(state_id)




    def approximate_phi_value_for_state(self, frame_id, state_args):
        return self.p_solver.get_highest_phi(frame_id, state_args)

    def is_generalization_possible(self, frame_index, state_args, var_to_drop, ge_value, delta):

        return self.p_solver.is_relative_inductive(frame_index, state_args, delta)


    def reset(self):
        self._state_of_the_same_kind_cache.reset_state_of_the_same_kind_cache()

    def replace_or_add(self, data_points, value, probability):

        for i in range(0, len(data_points)):
            if data_points[i][0] == value:
                #print("Replace")
                data_points[i] = (value, probability)
                return data_points

        #print("NO REPLACE")
        data_points.append((value, probability))
        return data_points


    # The following generalization using states of the same kind and works for the chain and sometimes for the double chain.
    # Since it uses polynomials, it slows down the solver alot. Observations hint at the fact the we have to focus more
    # on inductivity rather than relative inductivity.
    def generalize(self, frame_id, state_id, delta):
        """
        This procedure tries to find a list of generalization of the constraint state_id <= delta (at most one per integer variable),
        which is rel. ind. to frame_id, . (See get_polynomial)

        :param state_id: The ID of the state the constraint that is to be generalized is talking about.
        :param delta: The delta (probability) of the constraint that is to be generalized.
        :return: A set of generalizations (or a singleton containing the original constraint, if generalization not possible).

        """

        # result = frozenset()

        # for integer_var in self.input_program.module.get_integer_variables():
        #    result.add(self.get_polynomial(frame_id, state_id, delta, integer_var))

        #frame_index, state_id, start_value, start_delta, end_value, end_delta, input_variable
        #TODO: We compute this too often
        state_valuation = self.state_graph.get_state_valuation(state_id)

        res = []

        for integer_var in self.input_program.module.integer_variables:
            add = self.get_generalization_for_variable(frame_id, state_id, state_valuation[integer_var], delta, integer_var)
            res = res + add

        #print("Overall result: %s" % res)
        return res

    def get_generalization_for_variable(self, frame_index, state_id, start_value, start_delta, input_variable):
        """
        This procedure tries to find an univariate polynomial in (the z3 variable of) input variable, which is a valid generalization
        (i.e. rel. ind. to frame_id) of the constraint
               state_vars = stat_val_of(state_id)      =>      Frame <= delta.


        :param state_id: The ID of the state the constraint that is to be generalized is talking about.
        :param delta: The delta (probability) of the constraint that is to be generalized.
        :param input_variable: The correpsonding variable that is to be "dropped" by the genralization.
        :return: A pair (state_args_describing_the_states_the_generalization_talks_about, corresponding_polyomial), if generalization possible,
                (state_args, original_delta) otherwhise.
        """
        #print("")
        state_valuation = self.state_graph.get_state_valuation(state_id)

        # we do not generalize if delta = 1
        if start_delta == RealVal(1):
            return [([eq_no_coerce(var.variable, val) if var != input_variable
                      else eq_no_coerce(var.variable, start_value)
                      for var, val in state_valuation.items()], start_delta)]


        #Generalize only if we have a state of the same kind different form the current one
        same_kind_id = self._state_of_the_same_kind_cache.get_first_state_of_this_kind(state_id, input_variable)
        if same_kind_id != -1:
            same_kind_valuation = self.state_graph.get_state_valuation(same_kind_id)[input_variable]
            #
            # If the same kind valuation sits between low-val and high-val
            if not z3_values_check_neq(same_kind_valuation, state_valuation[input_variable]):
                return [([eq_no_coerce(var.variable, val) if var != input_variable
                          else eq_no_coerce(var.variable, start_value)
                          for var, val in state_valuation.items()], start_delta)]

        else:
            return [([eq_no_coerce(var.variable, val) if var != input_variable
                      else eq_no_coerce(var.variable, start_value)
                      for var, val in state_valuation.items()], start_delta)]




        # --------tes
        # if input_variable.name == "cur_package":
        #    return (state_valuation_to_z3_check_args(state_valuation), delta)
        end_value = input_variable.upper_bound
        end_delta = self.approximate_phi_value_for_state(frame_index, [
                                        eq_no_coerce(var.variable, val) if var != input_variable
                                            else eq_no_coerce(var.variable, input_variable.upper_bound)
                                            for var, val in state_valuation.items()])

        #print("Trying to generalize %s by dropping var %s   (starte_value = %s, start_delta = %s, end_value = %s, end_delta = %s, for frame %s)" % (
        #state_valuation, input_variable.name, start_value, float(start_delta.as_fraction()), end_value, float(end_delta.as_fraction()), frame_index + 1))


        # Continue only if value_of_input_variable_of_state_id is not the variables max value!
        if z3_values_check_geq(start_value, end_value):
            #print("not possible (start >= end)")
            return [([eq_no_coerce(var.variable, val) if var != input_variable
                      else eq_no_coerce(var.variable, start_value)
                      for var, val in state_valuation.items()], start_delta)]

        state_args = [eq_no_coerce(var.variable, val) if var != input_variable
                      else ge_no_coerce(var.variable, start_value)
                      for var, val in state_valuation.items()] + [input_variable.variable <= end_value]

        if self.is_generalization_possible(frame_index, state_args, input_variable,
                                           start_value, start_delta):


            (generalization_possible, generalization_result) = self.settings.get_generalization_method()(self, frame_index, state_id, state_valuation, start_value,
                                                                    start_delta, end_value, end_delta, input_variable)


            # Try at least to generalize by a value iteration step. might make further generalizations possible

            if generalization_possible:
                return generalization_result

            else:
                return generalization_result #+ self.generalize_by_value_iteration_step(frame_index, [eq_no_coerce(var.variable, val) if var != input_variable
                                             #   else eq_no_coerce(var.variable, start_value)
                                              #  for var, val in state_valuation.items()], state_args)


        else:
            #print("not possbible (dropping doesnt work)")
            return [([eq_no_coerce(var.variable, val) if var != input_variable
                      else eq_no_coerce(var.variable, start_value)
                      for var, val in state_valuation.items()], start_delta)]


    def generalize_by_value_iteration_step(self, frame_index, state_args_of_state, state_args_ge_state):

        approx_phi_value = self.approximate_phi_value_for_state(frame_index, state_args_of_state)

        #print('Value from value iteration step: %s' % approx_phi_value)

        rel_ind_result = self.p_solver.is_relative_inductive(frame_index, state_args_ge_state, approx_phi_value) == True

        if rel_ind_result:
            return [(state_args_ge_state, approx_phi_value)]

        else:
            return []




    def get_generalization_polynomials(self, frame_id, state_id, low_val, low_delta, high_val, high_delta, input_variable, splits = 0):

        data_points = []


        if self.settings.use_states_of_same_kind:
            same_kind_id = self._state_of_the_same_kind_cache.get_first_state_of_this_kind(state_id, input_variable)
            if same_kind_id != -1:
                same_kind_valuation = self.state_graph.get_state_valuation(same_kind_id)[input_variable]
            #
                #If the same kind valuation sits between low-val and high-val
                if z3_values_check_neq(same_kind_valuation, low_val) and z3_values_check_lt(same_kind_valuation, high_val):
                    data_points.append((same_kind_valuation, RepushingObligationQueue.smallest_probability_for_state[same_kind_id]))


            same_kind_id = self._state_of_the_same_kind_cache.get_last_state_of_this_kind(state_id, input_variable)
            if same_kind_id != -1:
               same_kind_valuation = self.state_graph.get_state_valuation(same_kind_id)[input_variable]

                #If the same kind valuation sits between low-val and high-val
               if z3_values_check_neq(same_kind_valuation, low_val) and z3_values_check_lt(same_kind_valuation, high_val):
                   data_points.append(
                       (same_kind_valuation, RepushingObligationQueue.smallest_probability_for_state[same_kind_id]))


        data_points = data_points + [(low_val, low_delta), (high_val, high_delta)]


        state_valuation = self.state_graph.get_state_valuation(state_id)

        polynomial = self._interpolator.get_interpolating_polynomial(data_points, input_variable.variable)

        state_args = [eq_no_coerce(var.variable, val) if var != input_variable
                      else ge_no_coerce(var.variable, low_val)
                      for var, val in state_valuation.items()] + [input_variable.variable <= high_val]

        rel_ind_result = self.p_solver.is_relative_inductive(frame_id, state_args, polynomial)
        if rel_ind_result == True:
            #print("We were able to generalize! (inputvar:  %s)" % (input_variable.name))
            #print('Polynomial for %s in [%s, %s]:  %s  (for frame %s)' % (
            #input_variable.name, low_val, high_val, polynomial, frame_id + 1))

            if self.is_poly_probability(polynomial, low_val, high_val, input_variable.variable):
                return [(low_val, low_delta, high_val, high_delta, polynomial)]

            else:
                return []

        else:

            i = 1
            while i <= self.settings.max_num_ctgs:

                #if len(data_points) == 4:
                 #   del data_points[3]


                value_of_input_variable_from_ctg = rel_ind_result[input_variable.variable]

                #print('CTG: Value of input var %s   (CTG %s):    %s' % (
                #    input_variable.name, i, value_of_input_variable_from_ctg))

                approx_phi_value = self.approximate_phi_value_for_state(frame_id, [
                    eq_no_coerce(var.variable, val) if var != input_variable
                    else eq_no_coerce(var.variable, value_of_input_variable_from_ctg)
                    for var, val in state_valuation.items()])


                data_points = self.replace_or_add(data_points, value_of_input_variable_from_ctg,
                                                  approx_phi_value)

                polynomial = self._interpolator.get_interpolating_polynomial(data_points,
                                                                             input_variable.variable)
                #print('Current values for input var: %s' % [x[0] for x in data_points])
                #print('Current polynomial:    %s' % polynomial)

                # print('Data points after interpol: %s' % data_points)

                rel_ind_result = self.p_solver.is_relative_inductive(frame_id, state_args, polynomial)
                if rel_ind_result == True:

                    if self.is_poly_probability(polynomial, low_val, high_val, input_variable.variable):
                        return [(low_val, low_delta, high_val, high_delta, polynomial)]

                    else:
                        return []

                i = i + 1

            if self.settings.int_to_real:
                intermediate_val = low_val + z3_real_floored_division(high_val - low_val, IntVal(2))

            else:
                intermediate_val = low_val + z3_integer_division(high_val - low_val, IntVal(2))

            #intermediate_val  = IntVal(2)
            intermediate_delta = self.approximate_phi_value_for_state(frame_id, [
                    eq_no_coerce(var.variable, val) if var != input_variable
                    else eq_no_coerce(var.variable, intermediate_val)
                    for var, val in state_valuation.items()])

            splits = splits +1

            if splits <= Generalizer.split_limit:
                res_1 = self.get_generalization_polynomials(frame_id, state_id, low_val, low_delta, intermediate_val, intermediate_delta, input_variable, splits)
                res_2 = self.get_generalization_polynomials(frame_id, state_id, intermediate_val, intermediate_delta, high_val,
                                                            high_delta, input_variable, splits)

                return res_1 + res_2

            else:
                return []

    def get_generalization_linear_functions(self, frame_id, state_id, low_val, low_delta, high_val, high_delta,
                                       input_variable):

        data_points = [(low_val, low_delta), (high_val, high_delta)]


        if z3_values_check_eq(low_val, high_val):
            return []

        state_valuation = self.state_graph.get_state_valuation(state_id)

        linear_function = self._interpolator.get_interpolating_polynomial(data_points, input_variable.variable)

        state_args = [eq_no_coerce(var.variable, val) if var != input_variable
                      else ge_no_coerce(var.variable, low_val)
                      for var, val in state_valuation.items()] + [input_variable.variable <= high_val]

        rel_ind_result = self.p_solver.is_relative_inductive(frame_id, state_args, linear_function)

        if rel_ind_result == True:
           # print("We were able to generalize! (inputvar:  %s)" % (input_variable.name))
           # print('Linear function for %s in [%s, %s]:  %s  (for frame %s)' % (
           #     input_variable.name, low_val, high_val, linear_function, frame_id + 1))

            if self.is_poly_probability(linear_function, low_val, high_val, input_variable.variable):
                return [(low_val, low_delta, high_val, high_delta, linear_function)]

            else:
                return []

        else:
            i=1
            while i <= self.settings.max_num_ctgs:
                i = i+1
                # interpolate from start_val to intermediate val and from intermediate val to ctg
                # but do so only if start_val != intermediate val

                value_of_input_variable_from_ctg = rel_ind_result[input_variable.variable]

                #print('CTG: Value of input var %s   (CTG %s):    %s' % (
                   # input_variable.name, i, value_of_input_variable_from_ctg))

                ctg_delta = self.approximate_phi_value_for_state(frame_id, [
                    eq_no_coerce(var.variable, val) if var != input_variable
                    else eq_no_coerce(var.variable, value_of_input_variable_from_ctg)
                    for var, val in state_valuation.items()])

                if z3_values_check_eq(ctg_delta, RealVal(1)):
                    #print('delta is 1')
                    return []

                if z3_values_check_eq(value_of_input_variable_from_ctg, low_val):
                    return []

                data_points.pop()
                data_points.append((value_of_input_variable_from_ctg, ctg_delta))

                linear_function = self._interpolator.get_interpolating_polynomial(data_points, input_variable.variable)

                state_args = [eq_no_coerce(var.variable, val) if var != input_variable
                              else ge_no_coerce(var.variable, low_val)
                              for var, val in state_valuation.items()] + [input_variable.variable <= value_of_input_variable_from_ctg]

                rel_ind_result = self.p_solver.is_relative_inductive(frame_id, state_args, linear_function)
                if rel_ind_result == True:
                    #print("We were able to generalize! (inputvar:  %s)" % (input_variable.name))
                    #print('Linear function for %s in [%s, %s]:  %s  (for frame %s)' % (
                     #   input_variable.name, low_val, value_of_input_variable_from_ctg, linear_function, frame_id + 1))

                    if self.is_poly_probability(linear_function, low_val, high_val, input_variable.variable):
                        return [(low_val, low_delta, value_of_input_variable_from_ctg, ctg_delta, linear_function)]

                    else:
                        return []


            return []

    def get_quadratic_splines_from_polynomial(self, frame_id, state_id,  polynomial, low_val, high_val, integer_var):
        # Assumes that polynomial is rel ind to frame_id!

        state_valuation= self.state_graph.get_state_valuation(state_id)

        low_delta = z3_evaluate_polynomial_at_point(polynomial, integer_var.variable, low_val)
        high_delta = z3_evaluate_polynomial_at_point(polynomial, integer_var.variable, high_val)

        # add relative inductive polynomials only
        state_args = [eq_no_coerce(var.variable, val) if var != integer_var
                        else ge_no_coerce(var.variable, low_val)
                        for var, val in state_valuation.items()] + [integer_var.variable <= high_val]

        if z3_values_check_eq(low_val, high_val):
            return [(state_args, low_delta)]


        if self.settings.int_to_real:
            intermediate_val = low_val + z3_real_floored_division(high_val - low_val, IntVal(2))

        else:
            intermediate_val = low_val + z3_integer_division(high_val - low_val, IntVal(2))

        intermediate_delta = z3_evaluate_polynomial_at_point(polynomial, integer_var.variable, intermediate_val)


        # We can stop to recurse
        data_points = [(low_val, low_delta), (intermediate_val, intermediate_delta), (high_val, high_delta)]
        quadratic_spline = self._interpolator.get_interpolating_polynomial(data_points, integer_var.variable)


        rel_ind_result = self.p_solver.is_relative_inductive(frame_id, state_args, quadratic_spline)

        if rel_ind_result == True:
                return [(state_args, quadratic_spline)]

        else:
            res_1 = self.get_quadratic_splines_from_polynomial(frame_id, state_id, polynomial, low_val, intermediate_val,integer_var)
            res_2 = self.get_quadratic_splines_from_polynomial(frame_id, state_id, polynomial, intermediate_val, high_val, integer_var)
            return res_1 + res_2


    def get_linear_splines_from_polynomial(self, frame_id, state_id,  polynomial, low_val, high_val, integer_var):
        # Assumes that polynomial is rel ind to frame_id!

        state_valuation= self.state_graph.get_state_valuation(state_id)

        low_delta = z3_evaluate_polynomial_at_point(polynomial, integer_var.variable, low_val)
        high_delta = z3_evaluate_polynomial_at_point(polynomial, integer_var.variable, high_val)

        # add relative inductive polynomials only
        state_args = [eq_no_coerce(var.variable, val) if var != integer_var
                        else ge_no_coerce(var.variable, low_val)
                        for var, val in state_valuation.items()] + [integer_var.variable <= high_val]

        if z3_values_check_eq(low_val, high_val):
            return [(state_args, low_delta)]

        # We can stop to recurse
        data_points = [(low_val, low_delta), (high_val, high_delta)]
        linear_spline = self._interpolator.get_interpolating_polynomial(data_points, integer_var.variable)


        rel_ind_result = self.p_solver.is_relative_inductive(frame_id, state_args, linear_spline)

        if rel_ind_result == True:
                return [(state_args, linear_spline)]

        else:

            if self.settings.int_to_real:
                intermediate_val = low_val + z3_real_floored_division(high_val - low_val, IntVal(2))

            else:
                intermediate_val = low_val + z3_integer_division(high_val - low_val, IntVal(2))

            #intermediate_val = rel_ind_result[integer_var.variable]

            res_1 = self.get_linear_splines_from_polynomial(frame_id, state_id, polynomial, low_val, intermediate_val,integer_var)
            res_2 = self.get_linear_splines_from_polynomial(frame_id, state_id, polynomial, intermediate_val, high_val, integer_var)

            return res_1 + res_2




    def polynomial_generalization(self, frame_index, state_id, state_valuation, start_value, start_delta, end_value, end_delta, input_variable, approximate_polynomial_by_linea_splines = False):

        # get_linear_splines_from_polynomial(self, frame_id, state_id,  polynomial, low_val, low_delta, high_val, high_delta, integer_var, num_splits):

        polynomials = self.get_generalization_polynomials(frame_index, state_id, start_value, start_delta, end_value,
                                                          end_delta, input_variable)

        result = []
        for (low_val, low_delta, high_val, high_delta, polynomial) in polynomials:

            if approximate_polynomial_by_linea_splines:
                result = result + self.get_linear_splines_from_polynomial(frame_index, state_id, polynomial, low_val,
                                                                        high_val, input_variable)

            else:
                state_args = [eq_no_coerce(var.variable, val) if var != input_variable
                                        else ge_no_coerce(var.variable, low_val)
                                        for var, val in state_valuation.items()] + [input_variable.variable <= high_val]

                result = result + [(state_args, polynomial)]

        if len(result) == 0:
            return (False, [([eq_no_coerce(var.variable, val) if var != input_variable
                              else eq_no_coerce(var.variable, start_value)
                              for var, val in state_valuation.items()], start_delta)])

        else:
            return (True, result + [([eq_no_coerce(var.variable, val) if var != input_variable
                              else eq_no_coerce(var.variable, start_value)
                              for var, val in state_valuation.items()], start_delta)])


    def is_poly_probability(self, polynomial, low_val, high_val, variable):

        self.solver.push()

        self.solver.add(variable >= low_val)
        self.solver.add(variable <= high_val)

        self.solver.push()

        self.solver.add(polynomial < 0)

        if self.solver.check() == sat:
            self.solver.pop()
            self.solver.pop()
            #print("Discarded poly %s < 0" % polynomial)
            return False

        self.solver.pop()
        self.solver.add(polynomial > 1)

        if self.solver.check() == sat:
            self.solver.pop()
            #print("Discarded poly %s > 1" % polynomial)
            return False

        return True




    def linear_generalization(self, frame_index, state_id, state_valuation, start_value, start_delta, end_value, end_delta, input_variable):

        linear_functions = self.get_generalization_linear_functions(frame_index, state_id, start_value, start_delta, end_value,
                                                          end_delta, input_variable)

        result = []
        for (low_val, low_delta, high_val, high_delta, polynomial) in linear_functions:

            state_args = [eq_no_coerce(var.variable, val) if var != input_variable
                              else ge_no_coerce(var.variable, low_val)
                              for var, val in state_valuation.items()] + [input_variable.variable <= high_val]

            result = result + [(state_args, polynomial)]

            #print('Res: %s' % result)

        if len(result) == 0:
            return (False, [([eq_no_coerce(var.variable, val) if var != input_variable
                           else eq_no_coerce(var.variable, start_value)
                           for var, val in state_valuation.items()], start_delta)])

        else:
            return (True, [([eq_no_coerce(var.variable, val) if var != input_variable
                           else eq_no_coerce(var.variable, start_value)
                           for var, val in state_valuation.items()], start_delta)])


    def hybrid_generalization(self, frame_index, state_id, state_valuation, start_value, start_delta, end_value, end_delta, input_variable):
        return self.polynomial_generalization(frame_index, state_id, state_valuation, start_value, start_delta, end_value, end_delta, input_variable, approximate_polynomial_by_linea_splines=True)


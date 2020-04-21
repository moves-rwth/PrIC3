"""
Maintains information about "states of the same kind" used for generalization.
This class always stores the *first* state of one kind it has seen.
Two program states are of the same kind iff they differ in exactly one program variable.
That is, the states (represented as a tuple) (v_1, v_2, v_3) and (v_1, v_2', v_3) with v_2 != v_2' are of the same kind.
"""


class StatesOfTheSameKindCache:

    def __init__(self, state_graph, input_program, statistics):

        self._state_graph = state_graph
        self._input_program = input_program
        self._statistics = statistics

        # For every program variable x, we maintain a Dict_x.
        # Let val be some state_valuation of type dict. Let list_val_without_x be the result of state_valuation_to_list_without_variable(val, x).
        # Then dict_x[list_val_without_x] gives the first state of this kind the algorithm has seen, i.e., the first state
        # where all values except for the value of variable x coincide.

        # Maps Input variabes to their corresponding dict
        self._first_state_of_kind_dicts = {}
        self._last_state_of_kind_dicts = {}

        self._all_of_same_kind_dicts = {}

        self.reset_state_of_the_same_kind_cache()


    def reset_state_of_the_same_kind_cache(self):
        for var in self._input_program.module.variables.values():
            self._first_state_of_kind_dicts[var.name] = {}
            self._last_state_of_kind_dicts[var.name] = {}
            self._all_of_same_kind_dicts[var.name] = {}



    def consider_state(self, state_id):
        """
            Invoked by PrIC3 upon popping an obligation for state_id.
            Computes the state valuation of state_id and checks for each variable whether "dropping" it
            yields a new state of this kind. If so, store it. If not, discard.

        :param state_id: The id of the state to consider.
        :return:
        """
        self._statistics.start_cache_states_of_same_kind_timer()

        val = self._state_graph.get_state_valuation(state_id)

        # For every variable x:
        #    * Obtain state valuation val_x with variable x dropped.
        #    * use self._dicts[x][val_x] and check whether we have seen a state of this kind already
        #    * If yes, do nothing. If not, this is the first state of this kind seen

        for var in self._input_program.module.variables.values():

            val_without_var = self._state_valuation_to_tuple_without_variable(val, var)

            self._last_state_of_kind_dicts[var.name][val_without_var] = state_id

            same_kind_set = self._all_of_same_kind_dicts[var.name].get(val_without_var, set())
            same_kind_set.add(state_id)
            self._all_of_same_kind_dicts[var.name][val_without_var] = same_kind_set


            if val_without_var not in self._first_state_of_kind_dicts[var.name]:
                self._first_state_of_kind_dicts[var.name][val_without_var] = state_id


        self._statistics.stop_cache_states_of_same_kind_timer()


    def get_first_state_of_this_kind(self, state_id, variable):
        """

        :param state_id: The state_id whose valuation we have to consider.
        :param variable: The variable we want to "drop"
        :return: The resulting_state_id of the first state of the same kind (when dropping variable) seen. If resulting_state_id == state_id
        or if resulting_state_id does not exist
        (i.e. there is no other state of the same kind), we return -1  (since 0 is identified with False and 0 might be a valid state_id).
        """

        val = self._state_graph.get_state_valuation(state_id)
        val_without_var = self._state_valuation_to_tuple_without_variable(val, variable)

        #Note: We use -1 since 0 is identified with false
        resulting_state = self._first_state_of_kind_dicts[variable.name].get(val_without_var, -1)

        if resulting_state == state_id or resulting_state == -1:
            return -1

        else:
            return resulting_state



    def get_last_state_of_this_kind(self, state_id, variable):
        """

        :param state_id: The state_id whose valuation we have to consider.
        :param variable: The variable we want to "drop"
        :return: The resulting_state_id of the LAST state of the same kind (when dropping variable) seen. If resulting_state_id == state_id
        or if resulting_state_id does not exist
        (i.e. there is no other state of the same kind), we return -1  (since 0 is identified with False and 0 might be a valid state_id).
        """

        val = self._state_graph.get_state_valuation(state_id)
        val_without_var = self._state_valuation_to_tuple_without_variable(val, variable)

        #Note: We use -1 since 0 is identified with false
        resulting_state = self._last_state_of_kind_dicts[variable.name].get(val_without_var, -1)

        if resulting_state == state_id or resulting_state == -1:
            return -1

        else:
            return resulting_state


    def get_same_kind_set(self, state_id, variable):
        """

        :param state_id: The state_id whose valuation we have to consider.
        :param variable: The variable we want to "drop"
        :return: The resulting_state_id of the LAST state of the same kind (when dropping variable) seen. If resulting_state_id == state_id
        or if resulting_state_id does not exist
        (i.e. there is no other state of the same kind), we return -1  (since 0 is identified with False and 0 might be a valid state_id).
        """

        val = self._state_graph.get_state_valuation(state_id)
        val_without_var = self._state_valuation_to_tuple_without_variable(val, variable)

        #Note: We use -1 since 0 is identified with false
        resulting_state = self._all_of_same_kind_dicts[variable.name].get(val_without_var, -1)

        return resulting_state

    def _state_valuation_to_tuple_without_variable(self, state_valuation, variable_to_drop):
        """
        Gets a program state (dict from input variables to values) and returns a tuple (for hashing) of these values
        (order is determined by order of InputVariables), where the entry for variable_to_drop is omitted.s
        :param state_valuation:
        :param variable_to_drop:
        :return:
        """

        result = ()
        for var in self._input_program.module.variables.values():
            if var.name != variable_to_drop.name:
                result = result + (state_valuation[var], )

        return result
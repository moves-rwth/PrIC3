from pric3.oracles.oracle import Oracle

class ExactOracle(Oracle):
    def initialize(self):
        self.oracle = dict()
        all_states = set()

        all_states.add(self.state_graph.get_initial_state_id())


        #new_states = {succ[0] for state_id in all_states for succ in
        #              self.state_graph.get_filtered_successors(state_id) if succ[0] != -1}

        new_states = {succ[0] for state_id in all_states for choice in
                      self.state_graph.get_successors_filtered(state_id).choices for succ in
                      choice.distribution if succ[0] != -1}

        while not new_states <= all_states:
           all_states = all_states.union(new_states)
           new_states = {succ[0] for state_id in all_states for choice in
                      self.state_graph.get_successors_filtered(state_id).choices for succ in
                      choice.distribution if succ[0] != -1}

        self.refine_oracle(all_states)

        self.oracle_states = set()


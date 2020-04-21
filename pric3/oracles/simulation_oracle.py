
from pric3.oracles.simulator import simulate, simulate_cpp
from pric3.oracles.oracle import Oracle

class SimulationOracle(Oracle):
    def initialize(self):
        if self.settings.simulator == "cpp":
            self.oracle = simulate_cpp(self.state_graph.input_program.prism_program, self.settings.number_simulations_for_oracle,
                               self.settings.max_number_steps_per_simulation).to_hit_probability_dict()
        else:
            self.oracle = simulate(self.state_graph, self.settings.number_simulations_for_oracle,
                                   self.settings.max_number_steps_per_simulation).to_hit_probability_dict()

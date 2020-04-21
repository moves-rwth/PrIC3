from fractions import Fraction

from pric3.input_program import InputProgram
from pric3.pric3 import PrIC3
from pric3.settings import Settings
from pric3.smt_program import SmtProgram, ForallMode
from pric3.statistics import Statistics
from stormpy import parse_prism_program


def _run_pric3(filename, threshold):
    settings = Settings(default_oracle_value=Fraction(0),
                        check_inductiveness_if_property_holds=True,
                        check_relative_inductiveness_of_frames=False,
                        obligation_queue_class="RepushingObligationQueue",
                        oracle_type="perfect",
                        number_simulations_for_oracle=100000,
                        max_number_steps_per_simulation=1000000,
                        simulator="cpp",
                        propagate=True,
                        forall_mode=ForallMode.FORALL_GLOBALS.value,
                        inline_goal=True,
                        int_to_real=False,
                        export_to_smt2=False,
                        store_smt_calls=False,
                        generalize=False,
                        depth_for_partly_solving_lqs=200,
                        generalization_method="Hybrid",
                        max_num_ctgs=1,
                        use_states_of_same_kind=True)
    prism_program = parse_prism_program(filename)
    input_program = InputProgram(prism_program)
    smt_program = SmtProgram(input_program, settings.get_smt_settings())
    ic3 = PrIC3(smt_program, Fraction(threshold), settings, Statistics(dict()))
    return ic3.run()

def test_grid():
   assert _run_pric3("pric3/prism_models/MCs/grid.pm", "0.3") == True
   assert _run_pric3("pric3/prism_models/MCs/grid.pm", "0.2") == True


def test_chain():
    _run_pric3("pric3/prism_models/MCs/chain.pm", "0.8")

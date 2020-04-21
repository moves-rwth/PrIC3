import json
from fractions import Fraction
from typing import Any, Dict, NamedTuple

from pric3.smt_program import ForallMode, SmtSettings
from pric3.proof_obligations.obligation_queue import ObligationQueue
from pric3.proof_obligations.repushing_obligation_queue import RepushingObligationQueue
from pric3.proof_obligations.naive_repushing_obligation_queue import NaiveRepushingObligationQueue
from pric3.generalization.generalizer import Generalizer

OBLIGATION_QUEUE_CLASSES = {"ObligationQueue": ObligationQueue, "RepushingObligationQueue" : RepushingObligationQueue, "NaiveRepushingObligationQueue" : NaiveRepushingObligationQueue}
GENERALIZATION_METHOD = {"Polynomial": Generalizer.polynomial_generalization, "Linear": Generalizer.linear_generalization, "Hybrid": Generalizer.hybrid_generalization}

# Adding new settings: Add a setting here in the Settings class,
# and also a new parameter in cmd.py.

class Settings(NamedTuple):
    default_oracle_value: Fraction
    check_inductiveness_if_property_holds: bool
    check_relative_inductiveness_of_frames: bool
    obligation_queue_class: str
    oracle_type: str # either [perfect, simulation, modelchecking, solveeqspartly, file]
    depth_for_partly_solving_lqs: int
    simulator: str # with python 3.8: Literal["cpp", "py"]
    number_simulations_for_oracle: int
    max_number_steps_per_simulation: int
    propagate: bool
    forall_mode: str
    inline_goal: bool # with python 3.8: Literal["quantifier", "macro", "globals"]
    int_to_real: bool
    export_to_smt2: str
    store_smt_calls: int
    generalize: bool
    generalization_method: str
    use_states_of_same_kind: bool
    max_num_ctgs: int

    @staticmethod
    def load(filename: str, args: Dict[str, Any]) -> 'Settings':
        """
        Construct Settings with `args` like `build`, but extend with settings
        loaded from file with the given name.

        The `args` settings have higher precendence than those from the settings file.
        """
        with open(filename) as file:
            data = json.load(file)
            if data.default_oracle_value:
                data.default_oracle_value = Fraction(data.default_oracle_value)
            return Settings.build(**{**data, **args})

    @staticmethod
    def build(args: Dict[str, Any]) -> 'Settings':
        """
        Create a new Settings instance, but do not throw errors if the args object
        contains fields that are not relevant for the Settings.
        """
        args = {k: v for k, v in args.items() if k in Settings._fields}
        return Settings(**args)

    def get_obligation_queue_class(self):
        return OBLIGATION_QUEUE_CLASSES[self.obligation_queue_class]

    def get_smt_settings(self) -> SmtSettings:
        return SmtSettings(forall_mode=ForallMode.from_str(self.forall_mode), inline_goal=self.inline_goal)

    def save_to(self, filename):
        """
        Save the current settings to a file.
        """
        with open(filename, 'w') as file:
            # ignore pylint bug below: https://github.com/PyCQA/pylint/issues/1418
            data = self._asdict() # pylint:disable=no-member
            data["default_oracle_value"] = str(data["default_oracle_value"])
            json.dump(data, file, indent=4)

    def get_generalization_method(self):
        return GENERALIZATION_METHOD[self.generalization_method]

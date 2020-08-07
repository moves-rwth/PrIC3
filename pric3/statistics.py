# pylint: disable-all
import time
import pickle
from pric3.utils import create_binary_file_with_incremental_name, unpickle_all_in_directory
from pric3.state_graph import StateId
from typing import List, Dict, Any, Set, BinaryIO, Tuple, Optional
import pandas as pd
from pandas.io.json import json_normalize
from datetime import datetime
import shlex
import sys
from z3 import sat, unsat, unknown

class Pric3SolverStatistics:
    """

    """
    def __init__(self):
        self.check_relative_inductive_counter_inductive = 0
        self.check_relative_inductive_counter_not_inductive = 0
        self.check_relative_inductive_time_inductive = 0
        self.check_relative_inductive_time_not_inductive = 0
        self._check_relative_inductiveness_timer = None
        self.fast_sat_query: Tuple[float, str] = (float('inf'), "")
        self.slow_sat_query: Tuple[float, str] = (float('-inf'), "")
        self.fast_unsat_query: Tuple[float, str] = (float('inf'), "")
        self.slow_unsat_query: Tuple[float, str] = (float('-inf'), "")
        self.unknown_query: Optional[str] = None

    def start_check_relative_inductiveness_timer(self):
        assert self._check_relative_inductiveness_timer is None
        self._check_relative_inductiveness_timer = time.time()

    def stop_check_relative_inductiveness_timer(self, is_inductive):
        assert self._check_relative_inductiveness_timer is not None
        time_passed = time.time() - self._check_relative_inductiveness_timer
        if is_inductive:
            self.check_relative_inductive_time_inductive += time_passed
            self.check_relative_inductive_counter_inductive += 1
        else:
            self.check_relative_inductive_time_not_inductive += time_passed
            self.check_relative_inductive_counter_not_inductive += 1
        self._check_relative_inductiveness_timer = None

    @property
    def check_relative_inductive_counter(self):
        return self.check_relative_inductive_counter_inductive + self.check_relative_inductive_counter_not_inductive

    @property
    def check_relative_inductive_time(self):
        return self.check_relative_inductive_time_inductive + self.check_relative_inductive_time_not_inductive

    def add_query(self, solver, time_seconds: float, result):
        print(time_seconds, result)
        if time_seconds > 3:
            print(solver.sexpr())
        if result == sat:
            if time_seconds < self.fast_sat_query[0]:
                self.fast_sat_query = (time_seconds, solver.sexpr())
            if time_seconds > self.slow_sat_query[0]:
                self.slow_sat_query = (time_seconds, solver.sexpr())
        if result == unsat:
            if time_seconds < self.fast_unsat_query[0]:
                self.fast_unsat_query = (time_seconds, solver.sexpr())
            if time_seconds > self.slow_unsat_query[0]:
                self.slow_unsat_query = (time_seconds, solver.sexpr())
        if result == unknown and self.unknown_query is None:
            self.unknown_query = solver.sexpr()

class Statistics:
    """
    Statistics for the PrIC3 loop.
    """

    def __init__(self, args: Dict[str, Any]):
        self.command_str = " ".join(map(shlex.quote, sys.argv))
        self.start_timestamp = datetime.now()
        self.made_no_progress_in_oracle_states_after_bellman_counter = 0
        self.frame_push_time = 0
        self.smt_oracle_solver_time = 0
        self.total_time = 0
        self.solved_eq_system_instead_of_optimization_counter = 0
        self.had_to_solve_optimization_problem_counter = 0
        self.get_probability_counter = 0
        self.get_probability_time = 0
        self.refine_oracle_counter = 0
        self.number_oracle_states = 0
        self.considered_states: Set[StateId] = set()
        self.number_considered_states = -1
        self.propagation_counter = 0
        self.propagation_time = 0
        self.cache_states_of_same_kind_time = 0
        self.pric3solverstats =  Pric3SolverStatistics()
        self.args = args
        self.property_holds = None
        self.initialize_oracle_time = 0
        self.status = "started"
        self.inductiveness_verified = "Unkown"
        self.check_refutation_time = 0

    def start_check_refutation_timer(self):
        self.check_refutation_timer = time.time()

    def stop_check_refutation_timer(self):
        self.check_refutation_time += time.time() - self.check_refutation_timer

    def inc_propagation_counter(self):
        self.propagation_counter += 1

    def add_considered_states(self, state: StateId):
        self.considered_states.add(state)

    def set_number_oracle_states(self, number):
        self.number_oracle_states = number

    def inc_refine_oracle_counter(self):
        self.refine_oracle_counter += 1

    def inc_get_probability_counter(self):
        self.get_probability_counter += 1

    def inc_solved_eq_system_instead_of_optimization_counter(self):
        self.solved_eq_system_instead_of_optimization_counter +=1

    def inc_had_to_solve_optimization_problem_counter(self):
        self.had_to_solve_optimization_problem_counter += 1

    def inc_made_no_progress_in_oracle_states_after_bellman_counter(self):
        self.made_no_progress_in_oracle_states_after_bellman_counter = +1

    @property
    def check_relative_inductive_counter(self):
        return self.pric3solverstats.check_relative_inductive_counter

    def print_statistics(self):
        print("-------------------- Statistics ---------------")
        print("Made no progress in oracle states: %s" %
              self.made_no_progress_in_oracle_states_after_bellman_counter)
        print("Total Time: %s" % self.total_time)
        print("Inductiveness check time (SMT) for %s checks: %s" % (self.pric3solverstats.check_relative_inductive_counter, self.pric3solverstats.check_relative_inductive_time))
        print("\tof which for %s successful instances: %s" % (self.pric3solverstats.check_relative_inductive_counter_inductive, self.pric3solverstats.check_relative_inductive_time_inductive))
        print("\tand of which for %s unsuccessful instances: %s" % (self.pric3solverstats.check_relative_inductive_counter_not_inductive, self.pric3solverstats.check_relative_inductive_time_not_inductive))
        #print("SMT Solver (oracle) Time: %s" % self.smt_oracle_solver_time)
        print("Frame Push Time: %s" % self.frame_push_time)
        print("Time to initialize oracle: %s" % self.initialize_oracle_time)
        print("Time for getting probabilties: %s" % self.get_probability_time)
        print("Calls to get_Probabilities: %s" % self.get_probability_counter)
        print("\tEQ System==Sat: %s" % self.solved_eq_system_instead_of_optimization_counter)
        print("\tHad to solve optimization problem: %s" % self.had_to_solve_optimization_problem_counter)
        print("Number refine_oracle/Check Refutation calls: %s" % self.refine_oracle_counter)
        print("Number oracle states: %s" % self.number_oracle_states)
        print("Number propagated assertions: %s" % self.propagation_counter)
        print("Propagation Time: %s" % self.propagation_time)
        print("Time for caching states of the same kind: %s" % self.cache_states_of_same_kind_time)
        print("Considered states: %s" % len(self.considered_states))
        print("Check Refutation Time: %s" % self.check_refutation_time)
        print("Percentage of time spent in Check Refutation: %s" % ("-" if self.check_refutation_time == 0 else str(((self.check_refutation_time/self.total_time)*100)) + "%"))

    def start_smt_oracle_timer(self):
        self.smt_oracle_timer = time.time()

    def stop_smt_oracle_timer(self):
        self.smt_oracle_solver_time += time.time() - self.smt_oracle_timer

    def start_total_timer(self):
        self.total_timer = time.time()

    def stop_total_timer(self):
        self.total_time += time.time() - self.total_timer

    def start_frame_push_timer(self):
        self.frame_push_timer = time.time()

    def stop_frame_push_timer(self):
        self.frame_push_time += time.time() - self.frame_push_timer

    def start_get_probability_timer(self):
        self.get_probability_timer = time.time()

    def stop_get_probability_timer(self):
        self.get_probability_time += time.time() - self.get_probability_timer

    def start_propagation_timer(self):
        self.propagation_timer = time.time()

    def stop_propagation_timer(self):
        self.propagation_time += time.time() - self.propagation_timer

    def start_cache_states_of_same_kind_timer(self):
        self.cache_states_of_same_kind_timer = time.time()

    def stop_cache_states_of_same_kind_timer(self):
        self.cache_states_of_same_kind_time += time.time() - self.cache_states_of_same_kind_timer

    def start_initialize_oracle_timer(self):
        self.initialize_oracle_timer = time.time()

    def stop_initialize_oracle_timer(self):
        self.initialize_oracle_time += time.time() - self.initialize_oracle_timer

    def to_file(self, handle: BinaryIO):
        """
        Dump this statistics object into a file using pickle.
        """
        pickle.dump(self, handle)

    def to_file_incremental(self, filename_pattern: str):
        """
        Dump this statistics object to a file with a filename from a pattern with an incremental index.
        """
        self.to_file(create_binary_file_with_incremental_name(filename_pattern))

    def to_pandas(self) -> pd.Series:
        """
        Convert this to a pandas Series.
        """
        self_dict = self.__dict__
        self_dict["pric3solverstats"] = self.pric3solverstats.__dict__
        df = json_normalize(self_dict)
        # df is a DataFrame with one row
        return df.T.squeeze() # transform to a Series.


def load_all_statistics(directory_path: str) -> List[Statistics]:
    """
    Load all statistics in a directory.

    Important: This assumes all file in the directory are pickled statistics objects!
    """
    stats = unpickle_all_in_directory(directory_path)
    for stat in stats:
        assert isinstance(stat, Statistics)
    return stats


def statistics_to_pandas(stats: List[Statistics]) -> pd.DataFrame:
    """
    Converts a list of pandas objects to a pandas DataFrame.
    """
    df = pd.DataFrame([d.to_pandas() for d in stats])
    df.reset_index(inplace=True, drop=True)
    return df


def average_pandas_statistics(stats: pd.DataFrame, select: List[str]) -> pd.DataFrame:
    """
    Aggregate benchmark runs with same parameters (i.e. same args), select only the given columns and average those.
    """
    groupby_cols = [name for name in stats.columns.values if name.startswith("args.")]
    groupby_cols.append("property_holds")

    # groupby silently discards rows with 'None' or 'NaN' values.
    # We replace 'None" with a placeholder string.
    #
    # See also:
    #  * https://stackoverflow.com/a/18431417 (Post from 2013)
    #  * https://github.com/pandas-dev/pandas/pull/30584 (WIP PR from 2020)
    stats = stats.copy()
    for col in groupby_cols:
        stats[col].replace(to_replace=[None], value='None', inplace=True)
    aggregated = stats.groupby(groupby_cols).mean()
    return aggregated[select].reset_index()

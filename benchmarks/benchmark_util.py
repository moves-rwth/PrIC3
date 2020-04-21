"""
This file contains functions to execute benchmarks of PrIC3 with a Python supervisor process and
format results nicely.
"""

from typing import NamedTuple, List, Tuple, Union, Optional, Sequence, TypeVar, Callable
import subprocess
import resource
import shlex
import time
from itertools import chain
from pric3.statistics import load_all_statistics, Statistics
from inspect import cleandoc
import os


class Model(NamedTuple):
    """A Model has a name, a file path, and a number of states."""
    name: str
    file_path: str
    num_states: float
    actual_probability: str


RuntimeResult = Union[str, float]
"""A RuntimeResult is either "MO", "TO", or a runtime in seconds."""


def best_result(results: List[RuntimeResult]) -> RuntimeResult:
    """Return the best result of the list. If there are only MO/TOs, return that."""
    times = [result for result in results if isinstance(result, float)]
    if len(times) == 0:
        res = results[0]
        for other_res in results:
            assert other_res == res
        return res
    return min(times)


def human_runtime_result(result: RuntimeResult) -> str:
    """Round numbers and write "<0.1" if values are small."""
    if isinstance(result, str):
        return result
    if result < 0.1:
        return "<0.1"
    return f"{result:.2f}"


class Limits:
    """Limits on execution time and memory."""
    runtime_seconds: int
    memory_mb: int

    def __init__(self, runtime_seconds: int, memory_mb: int):
        self.runtime_seconds = runtime_seconds
        self.memory_mb = memory_mb

    def run_with_limits(self, command: str) -> RuntimeResult:
        """Execute a command with the limits and time the execution."""
        def preexec_setlimits():
            # For now, we only set a memory limit via setrlimit.
            # We also don't set a hard upper limit, so the child process can handle the error
            # and write the current state to a file. PrIC3 does this.
            resource.setrlimit(
                resource.RLIMIT_AS,
                (self.memory_mb * 1024 * 1024, resource.RLIM_INFINITY))

        command_list = shlex.split(command)

        # Now start the process, and measure the time.
        start_time = time.time()

        # We (hopefully) use preexec_fn safely.
        # pylint: disable=subprocess-popen-preexec-fn
        process = subprocess.Popen(command_list,
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL,
                                   preexec_fn=preexec_setlimits)

        try:
            process.communicate(timeout=self.runtime_seconds)
            if process.returncode != 0:
                # Assume we've hit the memory limit...
                print("Memory limit hit with returncode %s: %s" %
                      (process.returncode, command))
                return "MO"
            time_diff = time.time() - start_time
            print("Process returned after %s seconds: %s" %
                  (time_diff, command))
            return time_diff
        except subprocess.TimeoutExpired:
            print("Timeout: %s" % command)

            # First, allow a graceful exit.
            process.terminate()

            try:
                process.communicate(timeout=4)
            except subprocess.TimeoutExpired:
                # print("Process did not exit after SIGTERM following a timeout, sending SIGKILL: %s" % command)
                process.kill()
            process.communicate()

            assert process.returncode is not None
            return "TO"


class Pric3Checker:
    """The checker that calls PrIC3."""

    name: str
    _args: str
    oracle_type: str
    _stats_output: str

    def __init__(self,
                 name: str,
                 args: str,
                 *,
                 oracle_type: str = "solveeqspartly_inexact",
                 stats_output: str = "total_time"):
        self.name = name
        self._args = args
        self.oracle_type = oracle_type
        self._stats_output = stats_output

    def run(self, limits: Limits, model: Model, lam: float) -> RuntimeResult:
        repeat_count = 5 if self.oracle_type == "simulation" else 1
        results = [
            self._run_once(limits, model, lam) for _i in range(repeat_count)
        ]
        return best_result(results)

    def _run_once(self, limits: Limits, model: Model,
                  lam: float) -> RuntimeResult:
        tag = str(int(time.time()))

        solving_depth = min(5000, model.num_states)
        command = "python3 ../../pric3.py ../../Benchmarks_CAV/%s --lam %s --depth-for-partly-solving-lqs %s --oracle-type %s %s --save-stats --tag %s" % (
            model.file_path, lam, solving_depth, self.oracle_type, self._args,
            tag)
        result = limits.run_with_limits(command)

        if isinstance(result, str):
            return result

        stats = Pric3Checker._load_statistics_for_tag(tag)
        if stats is None:
            raise Exception("Could not find statistics for PrIC3 run: %s" %
                            command)
        assert stats.status == "done"

        if self._stats_output == "table2":
            return "%s %s" % (stats.refine_oracle_counter,
                              human_runtime_result(stats.total_time))

        if self._stats_output == "rebuttal":
            if stats.check_refutation_time > 0:
                frac = (stats.check_refutation_time / stats.total_time) * 100
                frac_str = f"{frac:.1f}"
            else:
                frac_str = "-"
            return "%s/%s/%s" % (stats.refine_oracle_counter,
                                 stats.number_oracle_states, frac_str)

        assert self._stats_output == "total_time"
        return stats.total_time

    @staticmethod
    def _load_statistics_for_tag(tag: str) -> Optional[Statistics]:
        for stats in load_all_statistics("stats"):
            if stats.args["tag"] == tag:
                return stats
        return None


class StormChecker:
    """The checker that calls Storm."""

    name: str
    is_dd: bool

    def __init__(self, name: str, *, is_dd: bool):
        self.name = name
        self.is_dd = is_dd

    def run(self, limits: Limits, model: Model) -> RuntimeResult:
        dd_arg = "-e dd" if self.is_dd else ""
        command = "../../deps/storm/build/bin/storm %s --prism ../../Benchmarks_CAV/%s --prop \"P=? [F \\\"goal\\\"]\"" % (
            dd_arg, model.file_path)
        return limits.run_with_limits(command)


def _multirow(text: str, rows: int) -> str:
    return "\\multirow{%s}{*}{%s}" % (rows, text)


def _latex_table_join_cells(table: Sequence[Sequence[str]]) -> str:
    return " \\\\\n    ".join((" & ".join(row) for row in table))


class ModelBenchmarkResults(NamedTuple):
    """Benchmark results on a single model."""
    model: Model
    pric3_results: List[Tuple[float, List[Tuple[Pric3Checker,
                                                Optional[RuntimeResult]]]]]
    storm_results: List[Tuple[StormChecker, Optional[RuntimeResult]]]

    @staticmethod
    def to_latex_document(results: List["ModelBenchmarkResults"]) -> str:
        """
        Return a skeleton latex document with the result of to_latex_table.
        """
        preamble = cleandoc(r"""
            \documentclass[paper=landscape,a4paper,parskip=half-,DIV=15,fontsize=11pt]{scrartcl}
            \usepackage[utf8]{inputenc}
            \usepackage[T1]{fontenc}
            \usepackage{lmodern}
            \usepackage{multirow}
            \begin{document}
                \centering
                \small{}
        """)
        epilogue = cleandoc(r"""
            \end{document}
        """)
        return preamble + ModelBenchmarkResults.to_latex_table(
            results) + epilogue

    @staticmethod
    def to_latex_table(results: List["ModelBenchmarkResults"]) -> str:
        """
        Combine a list of benchmark results for different models.
        The results must have the exact same shape!
        """
        oracles = results[0].pric3_oracles()
        pric3_checkers = [
            checker
            for checker, _ in results[0].pric3_results_by_oracle()[0][1][0][1]
        ]

        storm_checkers = [checker for checker, _ in results[0].storm_results]

        oracle_tablespec = "r" if len(oracles) > 1 else ""
        tablespec = "ccrr" + oracle_tablespec + "||" + (
            "c" * len(pric3_checkers)) + "|" + ("c" * len(storm_checkers))

        query_header = [
            " ", "$|S|$", "$Pr^{max}(s_I \\models \\diamond B)$", "$\\lambda$"
        ]
        oracle_header = ["$\\Omega$"] if len(oracles) > 1 else []
        header = query_header + oracle_header + [
            checker.name for checker in pric3_checkers
        ] + [checker.name for checker in storm_checkers]

        block = _latex_table_join_cells(
            [header] +
            [row for result in results for row in result.to_latex_rows()])
        return "\\begin{tabular}{%s} \n%s\n\\end{tabular}" % (tablespec, block)

    def pric3_oracles(self) -> List[str]:
        oracles = [
            checker.oracle_type for checker, _ in self.pric3_results[0][1]
        ]
        oracle_set = set()
        res = []
        for oracle in oracles:
            if oracle not in oracle_set:
                res.append(oracle)
                oracle_set.add(oracle)
        return res

    def pric3_results_by_oracle(
        self
    ) -> List[Tuple[float, List[Tuple[str, List[Tuple[
            Pric3Checker, Optional[RuntimeResult]]]]]]]:
        oracles = self.pric3_oracles()
        return [(lam, [(oracle_type, [(checker, result)
                                      for checker, result in lambda_results
                                      if checker.oracle_type == oracle_type])
                       for oracle_type in oracles])
                for lam, lambda_results in self.pric3_results]

    def to_latex_rows(self) -> List[List[str]]:
        oracles = self.pric3_oracles()
        multirow_fn = lambda s: _multirow(
            s,
            len(self.pric3_results) * len(oracles))

        # Construct the first three cells for the model
        model = self.model
        model_cols = list(
            map(multirow_fn,
                [model.name, model.num_states, model.actual_probability]))

        # The next cells are for the results
        def format_result(result: Optional[RuntimeResult]) -> str:
            return (human_runtime_result(result)
                    if result is not None else "/")

        if len(oracles) <= 1:
            pric3_cols = [
                [str(lam)] +
                [format_result(result) for _, result in lambda_results]
                for lam, lambda_results in self.pric3_results
            ]
        else:
            pric3_cols = [
                [str(lam), oracle] +
                [format_result(result) for _, result in oracle_results]
                for lam, lambda_results in self.pric3_results_by_oracle()
                for oracle, oracle_results in lambda_results
            ]

        storm_cols = [
            multirow_fn(format_result(result))
            for _, result in self.storm_results
        ]

        # In the latex table, the multirow cells only appear on the first line,
        # then the corresponding cells in the next lines are blank.
        first_row = list(chain(model_cols, pric3_cols[0], storm_cols))
        model_cols_spaces = [" " for _col in model_cols]
        storm_cols_spaces = [" " for _col in storm_cols]
        other_rows = [
            model_cols_spaces + pric3_col + storm_cols_spaces
            for pric3_col in pric3_cols[1:]
        ]

        return [first_row] + other_rows


def benchmark_model(limits: Limits, pric3_checkers: List[Pric3Checker],
                    storm_checkers: List[StormChecker], model: Model,
                    lambdas: List[float], *,
                    omit_list: Optional[List[bool]]) -> ModelBenchmarkResults:
    """
    Benchmark the given model with the checkers and with all lambdas.

    The optional `omit_list` can be used to omit benchmark runs (e.g. to omit TOs/MOs).
    The list must contain a bool whether to execute the n-th benachmark at the resp. position.
    PrIC3 benchmarks are executed first, then Storm.
    (Yes, this is very ugly.)
    """

    T = TypeVar("T")

    if omit_list is not None:
        omit_list = list(omit_list)

    def optional(value_fn: Callable[[], T]) -> Optional[T]:
        if omit_list is None or omit_list.pop(0):
            return value_fn()
        return None

    pric3_results = [(lam, [(checker,
                             optional(lambda: checker.run(limits, model, lam)))
                            for checker in pric3_checkers]) for lam in lambdas]
    storm_results = [(checker, optional(lambda: checker.run(limits, model)))
                     for checker in storm_checkers]

    assert omit_list is None or len(omit_list) == 0

    return ModelBenchmarkResults(model=model,
                                 pric3_results=pric3_results,
                                 storm_results=storm_results)


def compile_latex_document(name: str, document: str) -> str:
    """
    Compile a latex document with a name and source code.

    Make sure the name does not contain any path characters such as `/`.

    Returns: Path to the pdf file.
    """
    directory = "%s_%s" % (name, int(time.time()))
    os.mkdir(directory)

    tex_file_name = "%s.tex" % name
    tex_file_path = os.path.join(directory, tex_file_name)
    with open(tex_file_path, 'w') as file:
        file.write(document)

    subprocess.run(["latexmk", "-pdf", tex_file_name],
                   cwd=directory,
                   check=True)

    return os.path.join(directory, "%s.pdf" % name)

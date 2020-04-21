import sys
import os
from itertools import chain
from typing import List, Optional

sys.path.insert(0, os.path.abspath('../'))
# pylint: disable=wrong-import-position
from benchmarks.benchmark_util import Model, Pric3Checker, StormChecker, Limits, benchmark_model, ModelBenchmarkResults, compile_latex_document

## ---------------------------
## Specify jobs below
## ---------------------------

zerconf_benchmark = [
    (Model("ZeroConf", "zero_conf_medium.pm", 10**4,
           "0.5"), [0.75, 0.52, 0.45]),
]

chain_benchmark = [
    (Model("Chain", "chain_small.pm", 1001, "0.394"), [0.9, 0.4, 0.35]),
]

double_chain_benchmark = [
    (Model("DoubleChain", "double_chain_small.pm", 1002,
           "0.215"), [0.3, 0.216, 0.15]),
]

pric3_common = "--forall-mode globals --int-to-real"
pric3_oracles = ["perfect", "simulation", "modelchecking"]
pric3_checkers = list(
    chain(*[[
        Pric3Checker("w/o",
                     pric3_common + " --no-generalize",
                     oracle_type=oracle_type,
                     stats_output="table2"),
        Pric3Checker(
            "lin",
            pric3_common +
            " --generalize --generalization-method Linear --max-num-ctgs 0",
            oracle_type=oracle_type,
            stats_output="table2"),
        Pric3Checker(
            "pol",
            pric3_common +
            " --generalize --generalization-method Polynomial --max-num-ctgs 2",
            oracle_type=oracle_type,
            stats_output="table2"),
        Pric3Checker(
            "hyb",
            pric3_common +
            " --generalize --generalization-method Hybrid --max-num-ctgs 2",
            oracle_type=oracle_type,
            stats_output="table2")
    ] for oracle_type in pric3_oracles]))

storm_checkers: List[StormChecker] = []

omit_specs = [
    """
    0000
    0011
    0011

    0000
    0011
    0011

    0000
    1111
    1111
""", """
    1111
    1111
    1111

    1110
    1110
    1110

    1100
    1100
    1100
    """, """

    0001
    0011
    1111

    0000
    0010
    0000

    0000
    1100
    0000
"""
]

limits = Limits(runtime_seconds=15 * 60, memory_mb=8 * 1024)

if "--selected" in sys.argv[1:]:
    omit_lists: Optional[List[List[bool]]] = [[
        (c == "1") for c in omit_spec.replace(" ", "").replace("\n", "")
    ] for omit_spec in omit_specs]
else:
    omit_lists = None

all_results = list()

for benchmark in [zerconf_benchmark, chain_benchmark, double_chain_benchmark]:
    for model, lambdas in benchmark:
        omit_list = omit_lists.pop(0) if omit_lists is not None else None
        results = benchmark_model(limits,
                                  pric3_checkers,
                                  storm_checkers,
                                  model,
                                  lambdas,
                                  omit_list=omit_list)
        print(ModelBenchmarkResults.to_latex_table([results]))
        all_results.append(results)

latex_doc = ModelBenchmarkResults.to_latex_document(all_results)
print(latex_doc)
results_pdf = compile_latex_document("table2", latex_doc)
print("The above results have been written to %s" % results_pdf)

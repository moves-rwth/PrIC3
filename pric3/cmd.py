"""
.. click:: pric3.cmd:main
   :prog: pric3
   :show-nested:
"""

import logging
from fractions import Fraction
from functools import partial

import sys
import signal
from os import environ

import click
from z3 import get_version_string

import stormpy
from pric3.input_program import InputProgram, set_global_expression_int_to_real
from pric3.pric3 import PrIC3
from pric3.settings import OBLIGATION_QUEUE_CLASSES, GENERALIZATION_METHOD, Settings
from pric3.smt_program import SmtProgram
from pric3.state_graph import StateGraph
from pric3.utils import setup_sigint_handler
from pric3.statistics import Statistics


def _setup_logger(logfile, cmd_loglevel, file_loglevel):
    logger = logging.getLogger("pric3")
    logger.setLevel(cmd_loglevel)

    # create file handler which logs even debug messages
    fh = logging.FileHandler(logfile)
    fh.setLevel(file_loglevel)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(file_loglevel)
    # create formatter and add it to the handlers
    fileformatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    consoleformatter = logging.Formatter('%(name)s: %(message)s')

    ch.setFormatter(consoleformatter)
    fh.setFormatter(fileformatter)
    # add the handlers to logger
    logger.addHandler(ch)
    logger.addHandler(fh)


def _print_environment_info():
    print("Using z3 version {}".format(get_version_string()))
    print("Using stormpy version {}".format(stormpy.__version__))


# always show defaults in the help text
click.option = partial(click.option, show_default=True)  # type:ignore

# How to add a new setting: See settings.py.


@click.command()
@click.argument('program', type=click.Path(exists=True))
@click.option('--lam',
              required=True,
              help='Lambda, the threshold.',
              type=Fraction)
@click.option('--render-state-graph',
              default=False,
              type=int,
              help='With how many nodes to render the state graph')
@click.option('--save-settings',
              type=click.Path(),
              help='A file to save the current settings in')
@click.option('--settings',
              type=click.Path(exists=True),
              help='Load settings from file. Note that command-line parameters override all settings loaded from a file.')
@click.option('--default-oracle-value', type=Fraction, default=Fraction("0"))
@click.option(
    '--check-inductiveness-if-property-holds/--no-check-inductiveness-if-property-holds',
    default=False)
@click.option(
    '--check-relative-inductiveness-of-frames/--no-check-relative-inductiveness-of-frames',
    default=False)
@click.option('--obligation-queue-class',
              type=click.Choice(OBLIGATION_QUEUE_CLASSES.keys()),
              default="RepushingObligationQueue")
@click.option('--simulator',
              type=click.Choice(["py", "cpp"]),
              default="cpp",
              help="which simulator to use for the simulation oracle")
@click.option("--oracle-type",
              type=click.Choice(["simulation", "perfect", "modelchecking", "solveeqspartly_exact","solveeqspartly_inexact", "file"]),
              default="perfect",
              help="which oracle to use")
@click.option("--depth-for-partly-solving-lqs",
              default=1000,
              help="how many times to unroll the markov chain")
@click.option('--number-simulations-for-oracle', type=int, default=10000)
@click.option('--max-number-steps-per-simulation', type=int, default=1000000)
@click.option('--propagate/--no-propagate', default=True)
@click.option('--forall-mode', type=str, default="globals")
@click.option('--inline-goal/--no-inline-goal', default=True)
@click.option('--int-to-real/--no-int-to-real', default=False)
@click.option('--export-to-smt2', type=str)
@click.option('--store-smt-calls', type=int, default=0)
@click.option('--generalize/--no-generalize', default=False)
@click.option('--generalization-method',
              type = click.Choice(GENERALIZATION_METHOD.keys()),
              default="Hybrid")
@click.option('--max-num-ctgs', type=int, default=1)
@click.option('--use-states-of-same-kind/--no-use-states-of-same-kind', default=True)
@click.option('--save-stats/--no-save-stats', default=True)
@click.option('--tag', type=str, help="a tag which is saved in the stats entry")
@click.option('--exit-stats-error/--no-exit-stats-error', default=False, help="directly exit with an error; this is used to record a crash in the statistics")
def main(program, **args):
    """
    Execute PrIC3.

    PROGRAM is a path to a program describing the model.

    Use `--save-settings PATH` to save the current settings to a JSON file,
    and use `--settings PATH` to load a settings file.

    `--render-state-graph COUNT` may be useful to render a graph of the current model
    to a file, where `COUNT` is the maximum number of nodes to be drawn.
    """
    _setup_logger(logfile='pric3.log',
                  cmd_loglevel=logging.INFO,
                  file_loglevel=logging.INFO)
    _print_environment_info()

    setup_sigint_handler()

    # record more stuff in the args object, this is recorded
    # in the statistics object and can be later filtered on.
    args["program"] = program
    slurm_array_task_id = environ.get("SLURM_ARRAY_TASK_ID")
    if slurm_array_task_id is not None:
        args["slurm_array_task_id"] = slurm_array_task_id

    statistics = Statistics(args)

    if args["exit_stats_error"]:
        if not args["save_stats"]:
            raise Exception("must use --exit-stats-error with --save-stats!")
        statistics.status = "exit_stats_error"
        statistics.to_file_incremental("stats/stats_%s.p")
        sys.exit(0)
        return

    settings = Settings.load(
        args["settings"], args) if args["settings"] else Settings.build(args)
    print(settings)
    if args["save_settings"]:
        settings.save_to(args["save_settings"])

    storm_program = stormpy.parse_prism_program(program)  # pylint: disable=no-member
    set_global_expression_int_to_real(settings.int_to_real)
    input_program = InputProgram(storm_program)

    if args["render_state_graph"]:
        state_graph = StateGraph(input_program)
        state_graph.to_dot(args["render_state_graph"], view=True).render(format='svg')

    smt_program = SmtProgram(input_program, settings.get_smt_settings())

    ic3 = PrIC3(smt_program, args["lam"], settings, statistics)

    def sigterm_handler(signum, frame):
        if args["save_stats"]:
            statistics.status = "sigterm"
            statistics.to_file_incremental("stats/stats_%s.p")
        sys.exit(1)

    signal.signal(signal.SIGTERM, sigterm_handler)

    try:
        ic3.run()
    except MemoryError:
        if args["save_stats"]:
            statistics.status = "oom"
            statistics.to_file_incremental("stats/stats_%s.p")
        sys.exit(1)

    ic3.print_details()
    if settings.export_to_smt2:
        ic3.export_smt(settings.export_to_smt2)

    if args["save_stats"]:
        statistics.status = "done"
        statistics.to_file_incremental("stats/stats_%s.p")

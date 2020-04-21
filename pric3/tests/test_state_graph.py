from pric3.input_program import InputProgram
from pric3.state_graph import StateGraph
from pric3.utils import parse_prism_program_string
from stormpy import parse_prism_program

EX_REACH_TRUE_GOLDEN = r"""
digraph {
    0 [label=0]
    0 -> 1 [label="1/5"]
    0 -> 2 [label="4/5"]
    2 [label=2]
    2 -> 3 [label="1/5"]
    2 -> 4 [label="4/5"]
    4 [label=4]
    4 -> 5 [label="1/5"]
    4 -> 6 [label="4/5"]
    6 [label=6]
    6 -> 7 [label="1/5"]
    6 -> 8 [label="4/5"]
    8 [label=8]
    8 -> 9 [label="1/5"]
    8 -> 10 [label="4/5"]
    10 [label=10]
    10 -> 11 [label="1/5"]
    10 -> 12 [label="4/5"]
    12 [label=12]
    12 -> 13 [label="1/5"]
    12 -> 14 [label="4/5"]
    14 [label=14]
    14 -> 15 [label="1/5"]
    14 -> 16 [label="4/5"]
    16 [label=16]
    16 -> 17 [label="1/5"]
    16 -> 18 [label="4/5"]
    18 [label=18]
    18 -> 19 [label="1/5"]
    18 -> 20 [label="4/5"]
    20 [label=20]
    20 -> 21 [label="1/5"]
    20 -> 22 [label="4/5"]
}
"""

def test_reach_true_to_dot():
    prism_program = parse_prism_program("models/ex_reach_true.pm")
    input_program = InputProgram(prism_program)
    state_graph = StateGraph(input_program)
    image = str(state_graph.to_dot(10)).replace("\t", "    ")
    assert image == str(EX_REACH_TRUE_GOLDEN).strip()


def test_grid_to_dot():
    prism_program = parse_prism_program("pric3/prism_models/MCs/grid.pm")
    input_program = InputProgram(prism_program)
    state_graph = StateGraph(input_program)
    print(state_graph.to_dot(10))

NONDET_MODEL = """
mdp

const N = 10;

module grid

	c : [0..N] init 0;
	f : bool init false;

	[] (c < N & c <= N) -> (0.001): (f'=true) + (0.999) : (c'=c+1);
	[] (c < N) -> (0.001): (f'=true) + (0.999) : (c'=c+1);

endmodule


label "goal" = f=true;
"""

def test_nondeterministic():
    prism_program = parse_prism_program_string(NONDET_MODEL)
    input_program = InputProgram(prism_program)
    state_graph = StateGraph(input_program)
    initial_id = state_graph.get_initial_state_id()
    behavior = state_graph.get_successors_filtered(initial_id)
    assert len(behavior) == 2
    assert len(behavior[0].origins) == 1
    assert str(behavior[0].origins[0].guard) == "And(10 > c, 10 >= c)"
    assert str(behavior[1].origins[0].guard) == "10 > c"

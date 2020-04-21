from heapq import *

from pric3.utils import *

from z3 import *


class ObligationQueue():
    smallest_probability_for_state = None

    def __init__(self):
        self.Q = []
        heapify(self.Q)

        # TODO: We might want to avoid a static dict here. However, this dict shall survive multiple instances of this class as long as we do not refine the oracle.
        # On Refining the oracle, this dict is reset
        # Stores for each state the smallest probability seen

        if ObligationQueue.smallest_probability_for_state is None:
            ObligationQueue.smallest_probability_for_state = dict()

        self.compare_solver = Solver()

        # Store pairs (frame_index, state) to indicate that there is an obligation of this form in the queue
        self.obligations_for_frame = set()

    def push_obligation(self, i, s, delta, history):

        # TODO: Does this take too much time?
        # First check whether delta is the new smallest probability for that state.
        if s in ObligationQueue.smallest_probability_for_state:
            if z3_values_check_gt(ObligationQueue.smallest_probability_for_state[s], delta):
                # This makes relative inductivity checks necesarry again
                ObligationQueue.smallest_probability_for_state[s] = delta
        else:
            ObligationQueue.smallest_probability_for_state[s] = delta

        # We must only push this obligation if it does not exist
        if (i, s) not in self.obligations_for_frame:
            self.obligations_for_frame.add((i, s))
            heappush(self.Q, (i, s, history))

    def pop_obligation(self):
        (i, s, history) = heappop(self.Q)
        self.obligations_for_frame.remove((i, s, history))

        return (i, s, ObligationQueue.smallest_probability_for_state[s])

    def get_length(self):
        return len(self.Q)

    def is_empty(self):
        return len(self.Q) == 0

    def repush_obligation(self, i, s, delta, history):
        # This obligation queue does not repush
        pass
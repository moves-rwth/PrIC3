"""
   ObligationQueue for the fastest version of PrIC3 if combined with propagation.
   Ensures that we have at most one obligation per frame and state.
   Stores the minimum probability seen for each state and always returns that probability.
"""

from heapq import *
from pric3.utils import *

from z3 import *

# TODO: We do not need to store the delta in obligations anymore
# Note: We do not have to store the delta in the obligations anymre since they are taken from RepushingObligationQueue.smallest_probability_for_state
class RepushingObligationQueue():


    smallest_probability_for_state = None

    def __init__(self):
        self.Q = []
        heapify(self.Q)

        # TODO: We might want to avoid a static dict here. However, this dict shall survive multiple instances of this class as long as we do not refine the oracle.
        # On Refining the oracle, this dict is reset
        # Stores for each state the smallest probability seen

        if RepushingObligationQueue.smallest_probability_for_state is None:
            RepushingObligationQueue.smallest_probability_for_state = dict()

        self.compare_solver = Solver()

        # Store pairs (frame_index, state) to indicate that there is an obligation of this form in the queue
        self.obligations_for_frame = set()
        self.history_for_obligation= dict()


    def push_obligation(self, i, s, delta, history):

        #TODO: Does this take too much time?
        # First check whether delta is the new smallest probability for that state.

        # Note: it suffices to store the history for the state with the smallest delta.
        if s in RepushingObligationQueue.smallest_probability_for_state:
            if z3_values_check_gt(RepushingObligationQueue.smallest_probability_for_state[s], delta):
                    # This makes relative inductivity checks necesarry again
                    RepushingObligationQueue.smallest_probability_for_state[s] = delta

                    self.history_for_obligation[(i,s)] = history

            else:
                if (i,s) not in self.history_for_obligation:
                    self.history_for_obligation[(i,s)] = history

        else:
            RepushingObligationQueue.smallest_probability_for_state[s] = delta
            self.history_for_obligation[(i,s)] = history


        # We must only push this obligation if it does not exist
        if (i, s) not in self.obligations_for_frame:
            self.obligations_for_frame.add((i, s))
            heappush(self.Q, (i, s))


    def pop_obligation(self):
        (i, s) = heappop(self.Q)
        history = self.history_for_obligation[(i,s)]
        self.obligations_for_frame.remove((i, s))
        del self.history_for_obligation[(i,s)]

        return (i, s, RepushingObligationQueue.smallest_probability_for_state[s], history)

    def get_length(self):
        return len(self.Q)

    def is_empty(self):
        return len(self.Q) == 0


    def repush_obligation(self, i, s, delta, history):
        # When repushing an obligation, it is always necessary to check for relative inductiveness.
        self.push_obligation(i, s, delta, history)




"""
   Naive implementation of RepushingObligationQueue. Neither cares about multiple obligations for state and frame,
   nor about returning the smallest probability seen so far.
"""

from heapq import *


class NaiveRepushingObligationQueue():

    def __init__(self):
        self._tie_breaker = 0
        self.Q = []
        heapify(self.Q)


    def push_obligation(self, i, s, delta, history):
        self._tie_breaker += 1
        heappush(self.Q, (i, self._tie_breaker, s, delta, history))



    def pop_obligation(self):
        (i, _tie, s, delta, history) = heappop(self.Q)
        return (i, s, delta, history)

    def get_length(self):
        return len(self.Q)

    def is_empty(self):
        return len(self.Q) == 0


    def repush_obligation(self, i, s, delta, history):
        # When repushing an obligation, it is always necessary to check for relative inductiveness.
        self.push_obligation(i, s, delta, history)




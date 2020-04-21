"""
Simple implementation of a class for computing a polynomial interpolant of N data points.
This is a singleton.
"""

from z3 import *

class Interpolator:

    class __Interpolatopr:

        def __init__(self):

            self._vars = []
            self._extend_vars(5)

            self._solver = Solver()


        def _extend_vars(self, amount):

            # self._vars[i] is for the monomial of degree i
            self._vars = self. _vars + [Real("x_%s" % i) for i in range(len(self._vars), len(self._vars) + amount)]


        def get_interpolating_polynomial(self, data_points, variable):
            """
            Returns a polynomial (a Z3Expression) in variable interpolating the data points.

            :param data_points: The data points (a list of pairs (x,y) to interpolate).
                   variable: The variable of the resulting polynomial
            :return: The interpolating polynomial.
            """

            if len(data_points) < 2:
                raise

            # we need a variable for every data point
            if len(data_points) > len(self._vars):
                self._extend_vars(len(data_points) - len(self._vars))

            # TODO: Check that the polynomial contains values in [0,1] only for all values of correpsponding variable.
                     # This is a simple SMT query.
            # TODO: What if data_points contains integer value? Is it faster/slower to generate the polynomial?

            degree_of_poly = len(data_points) - 1

            self._solver.push()

            # For every data point (a,b), we need an equation
            for (a, b) in data_points:
                self._solver.add(
                        Sum([self._vars[i] * Product([a for j in range(0,i)])
                        for i in range(0, degree_of_poly + 1) ])
                    == b
                )

            if self._solver.check() == sat:

                # Build polynomial
                m = self._solver.model()
                polynomial = Sum([m[self._vars[i]] * Product([variable for j in range(0,i)]) for i in range(0, degree_of_poly + 1)])

                self._solver.pop()
                return polynomial

            else:
                raise

    instance = None

    def __init__(self):
        if not Interpolator.instance:
            Interpolator.instance = Interpolator.__Interpolatopr()

    def __getattr__(self, item):
        return getattr(self.instance, item)

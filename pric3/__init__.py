"""

Overview
--------

Creating a PrIC3 instance
#########################

.. autosummary::
    stormpy.parse_prism_program
    pric3.input_program.InputProgram
    pric3.smt_program.SmtProgram
    pric3.smt_program.SmtEnv
    pric3.pric3.PrIC3

1. Load a PRISM program using :func:`stormpy.parse_prism_program`.
2. Put that in a :class:`pric3.input_program.InputProgram`, which represents everything as Z3 :class:`z3.ExprRef`.
3. With that, create a :class:`pric3.smt_program.SmtProgram` that represents the Z3 query's components corresponding to the program: `Frame`, `Phi`, and `Goal`.
   Queries can be created easily using :py:attr:`pric3.smt_program.SmtProgram.env` (of type :class:`pric3.smt_program.SmtEnv`).
4. Create an instance of :class:`pric3.pric3.PrIC3` using the SMT program and run the main algorithm.
"""

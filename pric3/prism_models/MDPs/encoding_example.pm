mdp

module example

	c : [0..20] init 0;
	f : bool init false;

	[] (c < 20) -> (0.1): (f'=true) + 0.9: (c'=c+1);
	[] (c < 10) -> (0.05): (f'=true) + 0.95: (c'=c+2);

endmodule

label "goal" = f=true;


class SmtProgram:
    """
    Representation of a program by three z3 functions: :py:attr:`frame`, :py:attr:`phi`, and :py:attr:`goal`.
    All three can be used via methods of :py:attr:`SmtProgram.env`.

    Use :py:func:`get_bounds_formula` and :py:func:`get_all_initial_formulas` to create SMT constraints for the program state.

    Attributes:
        input_program (InputProgram): the input program.
        settings (SmtSettings): the settings for this program.
        env (SmtEnv): the environment with all variables in the program.
        frame (z3.ExprRef): z3 uninterpreted function that represents Frame.
        phi (z3.ExprRef): z3 uninterpreted function that represents Phi.
        goal_expr (z3.ExprRef): z3 expression that represents the goal.
        chosen_command (z3.ExprRef): the variable that contains the chosen command's index.
    """
    def __init__(self, input_program: InputProgram, settings: SmtSettings):
        self.input_program = input_program
        self.settings = settings
        env = SmtEnv(input_program.module, settings.forall_mode, self)
        self.env = env

        self.frame = env.function("Frame", RealSort())
        if settings.forall_mode == ForallMode.FORALL_GLOBALS:
            self.frames: List[z3.ExprRef] = []

            old_command = None
            j = 0

            for i, subst in enumerate(env.macro_substs):

                frame_i = env.function("F%s" % i, RealSort())
                self.frames.append(frame_i)
                subst.append((env.apply_to_state_valuation(self.frame), env.apply_to_state_valuation(frame_i)))

                cur_command = self.env.subst_index_to_command[i]
                if cur_command != old_command:
                    old_command = cur_command
                    j = 0

                else:
                    j = j + 1

                self.env.command_to_substs[cur_command][j].append((env.apply_to_state_valuation(self.frame), env.apply_to_state_valuation(frame_i)))

        self.phi = env.function("Phi", RealSort())
        self.goal_expr = input_program.goal if settings.inline_goal else env.apply_to_state_valuation(env.function("Goal", BoolSort()))
        self.chosen_command = INPUTPROGRAM.INT_CTOR("ChosenCommand")
        self._initial_formulae: Union[None, List[z3.ExprRef]] = None

    def get_bounds_formula(self) -> z3.ExprRef:
        """
        Return the formula that bounds all program variables.
        """
        return And(*(var.bounds
                     for var in self.env.variables if var.bounds is not None))

    def _get_chosen_command_bounds_formula(self):
        return And(self.chosen_command >= 0, self.chosen_command <= len(self.input_program.module.commands))

    # not a goal state + no guard active => frame = 0
    def _get_frame_zero_formula(self):
        not_goal = Not(self.goal_expr)
        no_guard_active = And([
            Not(command.guard)
            for command in self.input_program.module.commands
        ])
        return self.env.forall(
            Implies(And(not_goal, no_guard_active),
                    0 == self.env.apply_to_state_valuation(self.frame)))

    # frame is bounded by 1
    def _get_frame_at_most_one_formula(self):
        return self.env.forall(1 >= self.env.apply_to_state_valuation(self.frame))

    # define goal
    def _get_goal_def_formula(self):
        if self.settings.inline_goal:
            return BoolVal(True)
        return And([
            self.env.forall(
                self.goal_expr == self.input_program.goal),
            self.goal_expr == self.input_program.goal
        ])

    # Goal state => frame var is one
    def _get_frame_one_if_goal_formula(self):
        vars_in_range = self.get_bounds_formula()
        return self.env.forall(Implies(And(vars_in_range, self.goal_expr)  , 1 == self.env.apply_to_state_valuation(self.frame)))

    # vars in range && goal => phi = 1
    def _get_phi_one_if_goal_formula(self):
        vars_in_range = self.get_bounds_formula()
        return Implies(And(vars_in_range, self.goal_expr),
                       1 == self.env.apply_to_state_valuation(self.phi))

    # vars in range && not goal && guard of command => phi(F)[s] = wp[command](F)[s]
    def _get_commands_formula(self):
        if self.settings.forall_mode == ForallMode.FORALL_GLOBALS:
            return self._get_commands_formula_deterministic()
        else:
            return self._get_commands_formula_nondeterministic()

    def _get_updates_formula(self, updates, frames):
        return Sum([
            update.probability *
            self.env.apply_to_state_valuation(next_or_value(frames), update.assignments)
            for update in updates
        ])

    def _get_commands_formula_nondeterministic(self):
        vars_in_range = self.get_bounds_formula()
        phi_applied = self.env.apply_to_state_valuation(self.phi)

        return And([
            Implies(
                And([
                    vars_in_range,
                    Not(self.goal_expr),
                    command.guard,
                    self.chosen_command == i
                ]),
                And([
                    phi_applied == self._get_updates_formula(command.updates, self.frame)
                ])
            )
            for i, command in enumerate(self.input_program.module.commands)
        ])

    def _get_commands_formula_deterministic(self):
        phi_applied = self.env.apply_to_state_valuation(self.phi)
        frames_iter = iter(self.frames)
        return And([
            Implies(And(Not(self.goal_expr), command.guard, self.chosen_command == i),
                phi_applied == self._get_updates_formula(command.updates, frames_iter)
            )
            for i, command in enumerate(self.input_program.module.commands)
        ])

    # Ensure that the solver chooses a correct chosen_command if a corresponding guard holds.
    def _get_if_at_least_one_guard_holds_choose_exactly_one_command_formula(self):

        at_least_one_guard_holds_formula = Or([command.guard for command in self.input_program.module.commands])

        choose_exactly_one_guard_formula = Or([And(command.guard, self.chosen_command ==i)
                                                for i, command in enumerate(self.input_program.module.commands)])

        return Implies(at_least_one_guard_holds_formula, choose_exactly_one_guard_formula)


    # vars in range && not goal && no guard => phi(F)[s] = 0
    def _get_sink_phi_zero_formula(self):
        vars_in_range = self.get_bounds_formula()
        not_goal = Not(self.goal_expr)
        no_guard_active = And([
            Not(command.guard)
            for command in self.input_program.module.commands
        ])
        return Implies(And(vars_in_range, not_goal, no_guard_active),
                       0 == self.env.apply_to_state_valuation(self.phi))

    # vars not in range => phi(F)[s] = 0
    def _get_not_in_range_phi_zero_formula(self):
        return BoolVal(True) # TODO: is this necessary?
        # vars_in_range = self.get_bounds_formula()
        # return Implies(Not(vars_in_range), 0 == self.env.apply(self.phi))

    def get_all_initial_formulas(self) -> List[z3.ExprRef]:
        """
        Return a list of all inital program assertions.
        """
        if self._initial_formulae is None:
            self._initial_formulae = [
                self.get_bounds_formula(),
                self._get_chosen_command_bounds_formula(),
                self._get_frame_zero_formula(),
                self._get_frame_at_most_one_formula(),
                self._get_goal_def_formula(),
                self._get_phi_one_if_goal_formula(),
                self._get_if_at_least_one_guard_holds_choose_exactly_one_command_formula(),
                self._get_commands_formula(),
                self._get_sink_phi_zero_formula(),
                self._get_not_in_range_phi_zero_formula(),
                #self._get_frame_one_if_goal_formula() We do not need these (I guess)
            ]
        return self._initial_formulae

    def get_frame_constraints(self, z3_state_constraints, z3_probability_expr):
        """
        Create a forall-quantified implication.
        """
        return self.env.forall(Implies(z3_state_constraints, z3_probability_expr))


    #TODO: Does no_coerce help here?
    def get_frame_leq_constraint(self, state_valuation, z3_probability_expr):

        state_constr = And([var.variable == state_valuation[var] for var in state_valuation])
        return self.env.forall(Implies(state_constr, self._ge_no_coerce(z3_probability_expr, self.env.apply_to_state_valuation(self.frame))))


    def get_frame_leq_constraint_from_state_args(self, state_args, z3_probability_expr):

        state_constr = And([arg for arg in state_args])
        return self.env.command_specific_forall(Implies(state_constr, self._ge_no_coerce(z3_probability_expr, self.env.apply_to_state_valuation(self.frame))))

    def _ge_no_coerce(self, left, right):
        # TODO: add assertions for noncoerce
        return BoolRef(Z3_mk_ge(left.ctx_ref(), left.as_ast(), right.as_ast()), left.ctx)

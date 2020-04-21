mdp

const N=200;

module grid

	c : [0..N] init 0;
	g : bool init false;

	[] (c < N) -> (0.0001): (g'=true) + 0.9999: (c'=c+1);
	[] (c < N) -> (0.005): (g'=true) + 0.995: (c'=c+1);

endmodule


label "goal" = g=true;

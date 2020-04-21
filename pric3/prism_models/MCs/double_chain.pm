dtmc

const N = 1000;

module double_chain

	c : [0..N] init 0;
	f : bool init false;
	g : bool init false;

	[] (c < N & f = false) -> (0.1): (f'=true) + (0.0001): (g'=true) + 0.8999: (c'=c+1);
	[] (c < N & f = true) -> (0.001): (g'=true) + 0.999: (c'=c+1);

endmodule


label "goal" = g=true;

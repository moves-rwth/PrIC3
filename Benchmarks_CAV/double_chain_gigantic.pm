dtmc

const N = 2500000;

module grid

	c : [0..N] init 0;
	f : bool init false;
	g : bool init false;

	[] (c < N & f = false) -> (0.1): (f'=true) + (0.000001): (g'=true) + 0.899999: (c'=c+1);
	[] (c < N & f = true) -> (0.0000000001): (g'=true) + 0.9999999999: (c'=c+1);

endmodule


label "goal" = g=true;

dtmc

const N = 10;
const M = 5;

module grid

	c : [0..N] init 0;
	d : bool init false;

	[] (c < N) -> (0.001): (f'=true) + (0.999) : (c'=c+1);

endmodule


label "goal" = f=true;


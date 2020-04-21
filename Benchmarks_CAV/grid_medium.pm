dtmc

const N = 100;
const M = 100;

module grid

	a : [0..N] init 0;
	b : [0..M] init 0;

	[] (a < N & b < M) -> (0.55): (a'=a+1) + (0.45) : (b'=b+1);

endmodule


label "goal" = b=M&a<N;


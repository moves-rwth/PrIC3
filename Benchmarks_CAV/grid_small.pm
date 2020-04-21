dtmc

const N = 32;
const M = 32;

module grid

	a : [0..N] init 0;
	b : [0..M] init 0;

	[] (a < N & b < M) -> (0.7): (a'=a+1) + (0.3) : (b'=b+1);

endmodule


label "goal" = b=M&a<N;


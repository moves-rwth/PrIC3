dtmc

const int maxx = 25;

module grid

	x : [0..maxx] init 2;
	c : [0..maxx] init 0;

	[] (x = 1 & c>=0 & c<= maxx ) -> 1 : (x'=0) & (c'=c+1);
	[] (x > 1 & c>=0 & c<= maxx ) -> (0.5) : (x'=x-1) & (c'=c+1) + (0.5) : (x'=x+1) & (c'=c+1);

endmodule

label "goal" = x=0;



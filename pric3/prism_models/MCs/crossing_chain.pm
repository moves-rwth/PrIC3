dtmc

const lengthchains = 10;

module crossing_chain

	c : [0..lengthchains] init 0;
	f : bool init false;
	g : bool init false;

	[] (c < lengthchains & f=false) -> (0.5): (c'=c+1) + (0.5): (c'=c+1)&(f'=true);
	[] (c < lengthchains & f=true ) ->  (0.1): (g'=true) + 0.2:(c'=c+1) + 0.7: (c'=c+1)&(f'=false);


endmodule


label "goal" = g=true;
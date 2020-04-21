dtmc

const numchains = 3;
const lengthchains = 100;

module crossing_chain

	c : [0..lengthchains] init 0;
	curchain : [1..numchains] init numchains;
	g : bool init false;

	[] (c < lengthchains & curchain < numchains & curchain > 1) -> (0.1): (curchain'=curchain+1)&(c'=c+1) + (0.001): (curchain'=curchain-1)&(c'=c+1) + (0.899): (c'=c+1);
	[] (c < lengthchains & curchain = numchains ) ->  (0.001): (curchain'=curchain-1)&(c'=c+1) + 0.999: (c'=c+1);

	[] (c < lengthchains & curchain = 1) -> (0.1): (curchain'=curchain+1)&(c'=c+1) + (0.0001): (g' = true) + 0.8999: (c'=c+1);

endmodule


label "goal" = g=true;
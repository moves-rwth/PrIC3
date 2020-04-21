mdp

module runningex

	x0 : bool init true;
	x1 : bool init false;
	x2 : bool init false;
	x3 : bool init false;
	xg : bool init false;
	xsink: bool init false;


	[] (x0=true) -> (0.5): (x1'=true)&(x0'=false) + 0.5: (x2'=true)&(x0'=false);
	[] (x1=true) -> (0.5): (x0'=true)&(x1'=false) + 0.5: (x3'=true)&(x1'=false);
	[] (x3=true) -> (2/3): (xg'=true)&(x3'=false) + (1/3): (xsink'=true)&(x3'=false);
	[] (x2=true) -> (1/2): (xg'=true)&(x2'=false) + (1/2): (xsink'=true)&(x2'=false);
	[] (x2=true) -> 1: (x0'=true)&(x2'=false);

endmodule


label "goal" = xg=true;

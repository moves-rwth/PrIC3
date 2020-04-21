dtmc

const int N=5000;

module main
    start : bool init true;
    side : bool init false;
	x : [0..N] init 0;

	[] start = true ->  0.7 : (start'=false)&(side'=false) + 0.3 : (start'=false)&(side'=true);
	[] start = false & side = false & x < N -> 0.499 : (x'=x+1) + 0.501 : (start'=true)&(side'=false)&(x'=0);
	[] start = false & side = true & x < N -> 0.5 : (x'=x+1) + 0.5 : (start'=true)&(side'=false)&(x'=0);


endmodule

label "goal" = x=N&side=false;


//the example chain from the board

dtmc


// number of tries to set f to true
const int N = 90;
const double p = 0.8; // TODO: is this right?

module main

    c : [0..(N+2)] init 0;
    f : bool init false;


	 [] (c <= N) -> (1-p) : (c'=c+1) & (f' = true) + p : (c'=c+1) & (f'=false);

endmodule


label "guard" = (c < N) & ( f = false);
label "goal" = (f= true);


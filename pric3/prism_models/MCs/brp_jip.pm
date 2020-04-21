dtmc


const maxx = 4;
const to_send = 10;
const package_size = 5;


module brp

	sent : [0..to_send] init 0;
	failed : [0..maxx] init 0;
	cur_package : [0..package_size] init 0;

	[] (cur_package=package_size & sent < to_send) -> 1 : (failed'=0)&(sent'=sent+1)&(cur_package'=0);
    [] (cur_package < package_size & sent < to_send) -> 0.2 : (failed'=failed+1) + 0.8: (cur_package'=cur_package+1);

endmodule


label "goal" = failed=maxx;


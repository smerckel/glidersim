behavior_name=Goto_list
<start:b_arg>
	b_arg: start_when(enum) 0
	b_arg: list_stop_when(enum) 7
	b_arg: list_when_wpt_dist(m) 500
	b_arg: initial_wpt(enum)     -1 # -1 ==> one after last one achieved
                                                        # -2 ==> closest
	b_arg: num_waypoints(nodim) 2
	b_arg: num_legs_to_run(nodim) -1
<end:b_arg>
<start:waypoints>
#729.430  5414.300
#723.500  5422.400
#711.600  5434.000
#646.200   5438.400
#642.100  5439.100 #sw of NSB3
#639.200 5434.250
#713.000 5433.500
725.800 5418.000
726.000 5418.00
<end:waypoints>

behavior_name=Goto_list

<start:b_arg>
	b_arg: start_when(enum) 0
	b_arg: list_stop_when(enum) 7
	b_arg: list_when_wpt_dist(m) 50
	b_arg: initial_wpt(enum)     -2 # -1 ==> one after last one achieved
                                                        # -2 ==> closest
	b_arg: num_waypoints(nodim) 1
	b_arg: num_legs_to_run(nodim) -1
<end:b_arg>
<start:waypoints>
801 5400
<end:waypoints>

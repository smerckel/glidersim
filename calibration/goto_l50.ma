behavior_name=goto_list
# lmm=lucas.merckelbach@gkss.de
# 29 Apr 2011 lmm: list of waypoints for second helgo mission.
# 8 Jun 2011  lmm: changed waypoints to leave 12 nm zone
# 8 Jun 2011  lmm: changed initial waypoint from -2 to 0, as
# DB was closer 
# 19 Jun 2011, going to change yo file, make sure reloading glider goes 
# to correct waypoint -1 should do
<start:b_arg>
b_arg: start_when(enum)       0     # BAW_IMMEDIATELY
b_arg: list_stop_when(enum)   7 # BAW_WHEN_WPT_DIST
b_arg: list_when_wpt_dist(m) 50  # used if list_stop_when == 7
b_arg: initial_wpt(enum)     -1  # 
                                 # >=0: start with this waypoint,
                                 # -1 the after the  last achieved	
	                         # -2 closest
b_arg: num_waypoints(nodim)   3
b_arg: num_legs_to_run(nodim) -1  # Number of waypoints to sequence thru
                              	    #  1-N    exactly this many waypoints
                                    #  0      illegal
                                    # -1      loop forever
                                    # -2      traverse list once (stop at last in list)
                                    # <-2     illegal
<end:b_arg>
<start:waypoints>
#735.000 5420.000 # outside 12 nm zone virtual mooring
#735.000 5420.500 # outside 12 nm zone
#707.000 5426.000 # middle transect
647.000 5441.000 # NSBIII (sebastian)
621.600 5413.500 # Ems
723.000 5416.000 # DB (a bit NW, amadeus)
<end:waypoints>

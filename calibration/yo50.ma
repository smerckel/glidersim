behavior_name=yo

# lmm=lucas.merckelbach@gkss.de

# 29 Apr 2011:lmm: Initial setup. One dive to 40 m @ 25 degree full speed, 
#                  servo controlled, altimeter active.
# 8 jun 2011 lmm 20 half cycles =^ 1 hour. -> 3 hours subsurface, 60 half cycles
# 10 Jun 2011 lmm : amadeus reached waypoint last night, slow it down
# 11 Jun 2011 lmm : double yo's to stay underwater for 4 hours.
<start:b_arg>
    b_arg: start_when(enum)      2          # pitch idle (see doco below)
    b_arg: num_half_cycles_to_do(nodim) 4   # Number of dive/climbs to perform
                                            # <0 is infinite, i.e. never finishes
    b_arg: end_action(enum) 0               # 0-quit, 2 resume

# arguments for dive_to
    b_arg: d_target_depth(m)       50 # 
    b_arg: d_target_altitude(m)    5  #-1 disables

    b_arg: d_use_pitch(enum)        3      # 1 battpos, 2 pitch set once, 3 servo
                                           #    in           rad             rad    
    b_arg: d_pitch_value(X)        -0.430  #  
    b_arg: d_bpump_value(X)        -170.0  
    b_arg: d_stop_when_hover_for(sec)   60
    b_arg: d_stop_when_stalled_for(sec) 60

# arguments for climb_to
    b_arg: c_target_depth(m)      3
    b_arg: c_target_altitude(m)  -1
    b_arg: c_use_pitch(enum)      3      # 1 battpos, 2 pitch set once, 3 servo
                                         #    in           rad             rad    
    b_arg: c_pitch_value(X)       0.430  #   (0.384 0.454 0.489 0.524 rads = 22 26 28 30 degrees)  
    b_arg: c_bpump_value(X)      +170.0 
    b_arg: c_stop_when_hover_for(sec)   60
    b_arg: c_stop_when_stalled_for(sec) 60
<end:b_arg>


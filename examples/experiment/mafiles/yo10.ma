behavior_name=Yo

<start:b_arg>
	b_arg: start_when(enum) 2
	b_arg: num_half_cycles_to_do(nodim) 10
	b_arg: end_action(enum) 2
	b_arg: d_target_depth(m) 50
	b_arg: d_target_altitude(m) 2
	b_arg: d_use_pitch(enum) 3 # 1 position/3 servo
	b_arg: d_pitch_value(X) -0.43
	b_arg: d_bpump_value(X) -1000
	b_arg: d_stop_when_hover_for(sec) 120
	b_arg: d_stop_when_stalled_for(sec) 120
	b_arg: c_target_depth(m) 3
	b_arg: c_target_altitude(m) -1
	b_arg: c_use_pitch(enum) 3
	b_arg: c_pitch_value(X) 0.43
	b_arg: c_bpump_value(X) 1000
	b_arg: c_stop_when_hover_for(sec) 120
	b_arg: c_stop_when_stalled_for(sec) 120
<end:b_arg>

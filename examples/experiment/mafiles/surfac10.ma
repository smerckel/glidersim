# come up every 3 hours
behavior_name=Surface
<start:b_arg>
# Arguments for climb_to when going to surface
# 3 hr: 10800
# 6 hr: 21600
#10 hr: 36000
b_arg: when_secs(sec)    8640000 # How long between surfacings
b_arg: c_use_bpump(enum)      2
b_arg: c_bpump_value(X)  1000
b_arg: c_use_pitch(enum)      3  # servo on pitch
b_arg: c_pitch_value(X)  0.430
b_arg: end_action(enum)          1   # 0-quit, 1 wait for ^C quit/resume, 2 resume
b_arg: gps_wait_time(s)        300   # how long to wait for gps
b_arg: keystroke_wait_time(s)  300   # how long to wait for control-C
b_arg: strobe_on(bool)         1    # switch on the strobe light.
<end:b_arg>

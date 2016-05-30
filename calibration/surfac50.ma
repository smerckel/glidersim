behavior_name=surface

# lmm=lucas.merckelbach@gkss.de

# 14 Sep 2010:lmm: Initial setup. Surfacing at max speed and 25 degrees

<start:b_arg>
    # Arguments for climb_to when going to surface
    b_arg: c_use_bpump(enum)      2
    b_arg: c_bpump_value(X)  1000.0
    b_arg: c_use_pitch(enum)      3  # servo on pitch
    b_arg: c_pitch_value(X)  0.4363  # 25 degrees
    b_arg: end_action(enum)          1   # 0-quit, 1 wait for ^C quit/resume, 2 resume
    b_arg: gps_wait_time(s)        300   # how long to wait for gps
    b_arg: keystroke_wait_time(s)  300   # how long to wait for control-C
<end:b_arg>
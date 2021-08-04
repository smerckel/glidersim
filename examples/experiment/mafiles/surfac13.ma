# come up every 3 hours
behavior_name=Surface
<start:b_arg>
b_arg: c_use_bpump(enum)      2
b_arg: c_bpump_value(X)  1000
b_arg: c_use_pitch(enum)      3  # servo on pitch
b_arg: c_pitch_value(X)  0.430
b_arg: end_action(enum)          0   # 0-quit, 1 wait for ^C quit/resume, 2 resume
b_arg: gps_wait_time(s)        300   # how long to wait for gps
b_arg: keystroke_wait_time(s)  300   # how long to wait for control-C
b_arg: strobe_on(bool)         1    # switch on the strobe light.
b_arg: when_utc_min(min)        45
b_arg: when_utc_hour(hour)      12
b_arg: when_utc_day(day)        -1
b_arg: when_utc_month(month)    -1
<end:b_arg>

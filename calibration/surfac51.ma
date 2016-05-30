behavior_name=surface

# lmm=lucas.merckelbach@gkss.de

# 14 Sep 2010:lmm: Initial setup. Surfacing at max speed and 25 degrees. NoComms set at 10 minutes.
# 06 june 2011:lmm: timout to 3600 s
# 8 Jun 2011 lmm: time out to 12 hrs (43200 seconds)
<start:b_arg>
    b_arg: when_secs(sec)     43200   # How long between surfacing, only if start_when==6,9, or 12
    # Arguments for climb_to when going to surface
    b_arg: c_use_bpump(enum)      2
    b_arg: c_bpump_value(X)  1000.0
    b_arg: c_use_pitch(enum)      3  # servo on pitch
    b_arg: c_pitch_value(X)  0.4363  # 25 degrees
<end:b_arg>
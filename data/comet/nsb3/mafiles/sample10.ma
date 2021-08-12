behavior_name=sample
# lmm=lucas.merckelbach@gkss.de
# 27/04/11 lmm Initial. Settings for CTD

<start:b_arg>
    b_arg: sensor_type(enum)                 1  # ALL         0  C_SCIENCE_ALL_ON
         	                                # PROFILE     1  C_PROFILE_ON
						# FLNTU      19  C_FLNTU_ON
						# Mircorider/logger 39 C_LOGGER_ON			

                                                # 8 on_surface, 4 climbing, 2 hovering, 1 diving
    b_arg: state_to_sample(enum)             5  

    b_arg: sample_time_after_state_change(s) 0  # time after a positional stat

    b_arg: intersample_time(s)               0  # if < 0 then off, if = 0 then
                                                # as fast as possible, and if
                                                # > 0 then that many seconds
                                                # between measurements
<end:b_arg>
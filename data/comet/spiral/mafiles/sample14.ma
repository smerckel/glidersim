behavior_name=sample
# lmm=lucas.merckelbach@hzg.de
# 19 June 2016 lmm Initial. Settings dvl

<start:b_arg>
    b_arg: sensor_type(enum)                43  # ALL         0  C_SCIENCE_ALL_ON
         	                                # PROFILE     1  C_PROFILE_ON
						# FLNTU      19  C_FLNTU_ON
						# DVL        43  C_DVL_ON
						# Mircorider/logger 39 C_LOGGER_ON			

                                                # 8 on_surface, 4 climbing, 2 hovering, 1 diving
    b_arg: state_to_sample(enum)             1  

    b_arg: sample_time_after_state_change(s) 0  # time after a positional stat

    b_arg: intersample_time(s)               -1  # if < 0 then off, if = 0 then
                                                # as fast as possible, and if
                                                # > 0 then that many seconds
                                                # between measurements
    b_arg: min_depth(m)                      -5    #! min = -5; max = 1000.0
    	                                                           # minimum depth to collect data, default
                                                                   # is negative to leave on at surface in
                                                                   # spite of noise in depth reading
    b_arg: max_depth(m)                    2000    #! min = -5.0; max = 2000
                                                                      # maximum depth to collect data
<end:b_arg>


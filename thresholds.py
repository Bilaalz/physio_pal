

# Get thresholds for beginner mode
def get_thresholds_squats_beginner():

    _ANGLE_HIP_KNEE_VERT = {
                            'NORMAL' : (0,  32),
                            'TRANS'  : (35, 65),
                            'PASS'   : (70, 95)
                           }    

        
    thresholds = {
                    'HIP_KNEE_VERT': _ANGLE_HIP_KNEE_VERT,

                    'HIP_THRESH'   : [10, 50],
                    'ANKLE_THRESH' : 45,
                    'KNEE_THRESH'  : [50, 70, 95],

                    'OFFSET_THRESH'    : 35.0,
                    'INACTIVE_THRESH'  : 15.0,

                    'CNT_FRAME_THRESH' : 50
                            
                }

    return thresholds



# Get thresholds for beginner mode
def get_thresholds_squats_pro():

    _ANGLE_HIP_KNEE_VERT = {
                            'NORMAL' : (0,  32),
                            'TRANS'  : (35, 65),
                            'PASS'   : (80, 95)
                           }    

        
    thresholds = {
                    'HIP_KNEE_VERT': _ANGLE_HIP_KNEE_VERT,

                    'HIP_THRESH'   : [15, 50],
                    'ANKLE_THRESH' : 30,
                    'KNEE_THRESH'  : [50, 80, 95],

                    'OFFSET_THRESH'    : 35.0,
                    'INACTIVE_THRESH'  : 15.0,

                    'CNT_FRAME_THRESH' : 50
                            
                 }
                 
    return thresholds

def get_thresholds_leg_raises_beginner():
    _ANGLE_HIP_FLEX_VERT = {
        'NORMAL': (0, 15),
        'TRANS' : (16, 60),
        'PASS'  : (61, 95),
    }

    thresholds = {
        'HIP_KNEE_VERT': _ANGLE_HIP_FLEX_VERT,

        # More lenient form checks
        'KNEE_LOCK_MAX'   : 20,   # was 15 → allow up to ~20° knee bend before warning
        'TORSO_TILT_MAX'  : 25,   # was 20 → allow a bit more torso movement
        'REP_MIN_RANGE'   : 35,

        'HOLD_SEC'        : 1.0,

        'OFFSET_THRESH'   : 35.0,
        'INACTIVE_THRESH' : 15.0,

        'CNT_FRAME_THRESH': 50,
    }
    return thresholds


def get_thresholds_leg_raises_pro():
    _ANGLE_HIP_FLEX_VERT = {
        'NORMAL': (0, 20),
        'TRANS' : (21, 75),
        'PASS'  : (76, 95),
    }

    thresholds = {
        'HIP_KNEE_VERT': _ANGLE_HIP_FLEX_VERT,

        # More lenient form checks (still stricter than Beginner)
        'KNEE_LOCK_MAX'   : 15,   # was 10
        'TORSO_TILT_MAX'  : 20,   # was 15
        'REP_MIN_RANGE'   : 40,

        'HOLD_SEC'        : 1.5,

        'OFFSET_THRESH'   : 35.0,
        'INACTIVE_THRESH' : 15.0,

        'CNT_FRAME_THRESH': 50,
    }
    return thresholds

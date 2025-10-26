# process_frame_leg_raise.py
import time
import cv2
import numpy as np

from utils import find_angle, get_landmark_features, draw_text, draw_dotted_line


class ProcessFrame:
    """
    Per-frame controller for a straight-leg raise (supine).
    - Side-view recommended; uses the same "offset" check you had for squats.
    - States driven by HIP FLEXION vs torso (slightly more lenient): s1 (NORMAL/rest),
      s2 (TRANS/raising), s3 (PASS/top position).
    - Form checks:
        * Knee lock (keep knee nearly straight)
        * Torso/pelvic tilt (avoid arching/rocking)
        * Minimal rep range (reject micro-movements)
        * Hold time at the top before the rep counts (fixed 5 s timer)
    Returns: frame, play_sound (None | 'incorrect' | 'reset_counters' | '<int count>')
    """

    def __init__(self, thresholds, flip_frame=False):
        # Video mirroring flag
        self.flip_frame = flip_frame

        # Thresholds
        self.thresholds = thresholds

        # Text/lines
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.linetype = cv2.LINE_AA

        # Colors (BGR)
        self.COLORS = {
            'blue': (0, 127, 255),
            'red': (255, 50, 50),
            'green': (0, 255, 127),
            'light_green': (100, 233, 127),
            'yellow': (255, 255, 0),
            'magenta': (255, 0, 255),
            'white': (255, 255, 255),
            'cyan': (0, 255, 255),
            'light_blue': (102, 204, 255),
            'orange': (0, 165, 255),
        }

        # Landmark index maps (MediaPipe Pose)
        self.dict_features = {}
        self.left_features = {
            'shoulder': 11,
            'elbow': 13,
            'wrist': 15,
            'hip': 23,
            'knee': 25,
            'ankle': 27,
            'foot': 31,
        }
        self.right_features = {
            'shoulder': 12,
            'elbow': 14,
            'wrist': 16,
            'hip': 24,
            'knee': 26,
            'ankle': 28,
            'foot': 32,
        }
        self.dict_features['left'] = self.left_features
        self.dict_features['right'] = self.right_features
        self.dict_features['nose'] = 0

        # State + counters
        self.state_tracker = {
            # state machine / sequence
            'state_seq': [],         # expects ['s2', 's3', 's2'] between s1 rests
            'prev_state': None,
            'curr_state': None,

            # per-rep metrics
            's3_enter_time': None,
            's3_hold_ok': False,
            'rep_min_angle': None,   # min hip flex angle seen after entering s2
            'rep_max_angle': None,   # max hip flex angle seen after entering s2

            # inactivity timers (side + front checks)
            'start_inactive_time': time.perf_counter(),
            'INACTIVE_TIME': 0.0,
            'start_inactive_time_front': time.perf_counter(),
            'INACTIVE_TIME_FRONT': 0.0,

            # display/counters
            'DISPLAY_TEXT': np.full((4,), False),   # indexes into FEEDBACK_ID_MAP
            'COUNT_FRAMES': np.zeros((4,), dtype=np.int64),
            'INCORRECT_POSTURE': False,

            'CORRECT_COUNT': 0,
            'INCORRECT_COUNT': 0,
        }

        # Feedback labels
        # (label, y_position, box_color)
        self.FEEDBACK_ID_MAP = {
            0: ('LOCK YOUR KNEE',        215, (255, 80, 80)),   # KNEE_LOCK_MAX exceeded
            1: ("DON'T ARCH YOUR BACK",  170, (0, 153, 255)),   # TORSO_TILT_MAX exceeded
            2: ('RAISE HIGHER',          125, (255, 255, 0)),   # in s2 but not reaching PASS band
            3: ('CONTROL LOWERING',       90, (255, 80, 80)),   # dropped s3->s1 without s2
        }

    # ---------------------------- helpers ---------------------------- #

    def _get_state(self, hip_flex_vertical_angle):
        """
        Map hip-flexion angle (0..~95) to s1/s2/s3 using thresholds['HIP_KNEE_VERT'].
        """
        band = self.thresholds['HIP_KNEE_VERT']
        st = None
        if band['NORMAL'][0] <= hip_flex_vertical_angle <= band['NORMAL'][1]:
            st = 's1'
        elif band['TRANS'][0] <= hip_flex_vertical_angle <= band['TRANS'][1]:
            st = 's2'
        elif band['PASS'][0] <= hip_flex_vertical_angle <= band['PASS'][1]:
            st = 's3'
        return st

    def _update_state_sequence(self, state):
        """
        Enforce: enter s2 once, then s3 once, then s2 once (like in the squat code).
        """
        if state == 's2':
            if (('s3' not in self.state_tracker['state_seq']) and (self.state_tracker['state_seq'].count('s2') == 0)) or \
               (('s3' in self.state_tracker['state_seq']) and (self.state_tracker['state_seq'].count('s2') == 1)):
                self.state_tracker['state_seq'].append('s2')

        elif state == 's3':
            if ('s3' not in self.state_tracker['state_seq']) and ('s2' in self.state_tracker['state_seq']):
                self.state_tracker['state_seq'].append('s3')

    def _show_feedback(self, frame, c_frame, dict_maps):
        for idx in np.where(c_frame)[0]:
            draw_text(
                frame,
                dict_maps[idx][0],
                pos=(30, dict_maps[idx][1]),
                text_color=(255, 255, 230),
                font_scale=0.6,
                text_color_bg=dict_maps[idx][2],
            )
        return frame

    def _reset_live_flags(self):
        self.state_tracker['DISPLAY_TEXT'][:] = False
        self.state_tracker['COUNT_FRAMES'][:] = 0
        self.state_tracker['INCORRECT_POSTURE'] = False
        self.state_tracker['s3_enter_time'] = None
        self.state_tracker['s3_hold_ok'] = False
        self.state_tracker['rep_min_angle'] = None
        self.state_tracker['rep_max_angle'] = None

    def _hard_reset_all(self):
        # Counters preserved on inactivity reset? We follow your squat behavior: reset both.
        self.state_tracker['CORRECT_COUNT'] = 0
        self.state_tracker['INCORRECT_COUNT'] = 0

        self.state_tracker['state_seq'] = []
        self.state_tracker['prev_state'] = None
        self.state_tracker['curr_state'] = None

        self._reset_live_flags()

        self.state_tracker['INACTIVE_TIME'] = 0.0
        self.state_tracker['start_inactive_time'] = time.perf_counter()

        self.state_tracker['INACTIVE_TIME_FRONT'] = 0.0
        self.state_tracker['start_inactive_time_front'] = time.perf_counter()

    # -------------------------- main entry -------------------------- #

    def process(self, frame: np.array, pose):
        """
        Process a frame for the leg-raise. Returns (frame, play_sound)
        """
        play_sound = None
        frame_height, frame_width, _ = frame.shape

        # Pose estimation
        keypoints = pose.process(frame)

        # No landmarks → inactivity accumulation & minimal overlay
        if not keypoints.pose_landmarks:
            if self.flip_frame:
                frame = cv2.flip(frame, 1)

            # Inactivity accounting (side view)
            end_time = time.perf_counter()
            self.state_tracker['INACTIVE_TIME'] += end_time - self.state_tracker['start_inactive_time']
            self.state_tracker['start_inactive_time'] = end_time

            display_inactivity = self.state_tracker['INACTIVE_TIME'] >= self.thresholds['INACTIVE_THRESH']


            if display_inactivity:
                play_sound = 'reset_counters'
                self._hard_reset_all()

            return frame, play_sound

        # -------- Landmarks present -------- #
        ps_lm = keypoints.pose_landmarks

        # Get features for both sides + nose for offset
        nose_coord = get_landmark_features(ps_lm.landmark, self.dict_features, 'nose',
                                           frame_width, frame_height)
        l_sh, l_el, l_wr, l_hip, l_knee, l_ankle, l_foot = get_landmark_features(
            ps_lm.landmark, self.dict_features, 'left', frame_width, frame_height
        )
        r_sh, r_el, r_wr, r_hip, r_knee, r_ankle, r_foot = get_landmark_features(
            ps_lm.landmark, self.dict_features, 'right', frame_width, frame_height
        )

        # Camera alignment: nose + shoulders angle → if too "front", warn & pause logic
        offset_angle = find_angle(l_sh, r_sh, nose_coord)
        if offset_angle > self.thresholds['OFFSET_THRESH']:
            # Accumulate "front" inactivity
            end_time = time.perf_counter()
            self.state_tracker['INACTIVE_TIME_FRONT'] += end_time - self.state_tracker['start_inactive_time_front']
            self.state_tracker['start_inactive_time_front'] = end_time

            # Show alignment info + counters
            cv2.circle(frame, tuple(nose_coord), 7, self.COLORS['white'], -1)
            cv2.circle(frame, tuple(l_sh), 7, self.COLORS['yellow'], -1)
            cv2.circle(frame, tuple(r_sh), 7, self.COLORS['magenta'], -1)

            if self.flip_frame:
                frame = cv2.flip(frame, 1)


            draw_text(frame, 'CAMERA NOT ALIGNED PROPERLY!!!',
                      pos=(30, frame_height - 60), text_color=(255, 255, 230),
                      font_scale=0.65, text_color_bg=(255, 153, 0))
            draw_text(frame, f'OFFSET ANGLE: {int(offset_angle)}',
                      pos=(30, frame_height - 30), text_color=(255, 255, 230),
                      font_scale=0.65, text_color_bg=(255, 153, 0))

            # If front-inactive too long → hard reset
            if self.state_tracker['INACTIVE_TIME_FRONT'] >= self.thresholds['INACTIVE_THRESH']:
                play_sound = 'reset_counters'
                self._hard_reset_all()

            # Reset side-view inactivity accumulators
            self.state_tracker['INACTIVE_TIME'] = 0.0
            self.state_tracker['start_inactive_time'] = time.perf_counter()
            return frame, play_sound

        # Camera aligned → reset "front" timer
        self.state_tracker['INACTIVE_TIME_FRONT'] = 0.0
        self.state_tracker['start_inactive_time_front'] = time.perf_counter()

        # Choose the better-visible side (use shoulder-foot vertical span)
        dist_l = abs(l_foot[1] - l_sh[1])
        dist_r = abs(r_foot[1] - r_sh[1])

        if dist_l >= dist_r:
            sh, el, wr, hip, knee, ankle, foot = l_sh, l_el, l_wr, l_hip, l_knee, l_ankle, l_foot
            multiplier = -1
        else:
            sh, el, wr, hip, knee, ankle, foot = r_sh, r_el, r_wr, r_hip, r_knee, r_ankle, r_foot
            multiplier = 1

        # ------------------ Angles ------------------ #
        # Hip flexion (state driver) — more lenient reference:
        # use thigh vs torso: hip→knee against hip→shoulder, then invert to grow with flexion.
        hip_vertical = 180 - find_angle(knee, sh, hip)

        # Knee straightness: 180° is straight; compute flexion = 180 - angle at knee
        knee_internal = find_angle(hip, ankle, knee)     # 0..180
        knee_flexion = max(0, 180 - int(knee_internal))  # 0..180, small is straighter

        # Torso tilt vs vertical through hip (arch/rock control)
        torso_tilt = find_angle(sh, np.array([hip[0], 0]), hip)

        # ------------------ Drawing guides ------------------ #
        # Vertical dotted lines at hip/knee for visual reference
        draw_dotted_line(frame, hip, start=hip[1] - 80, end=hip[1] + 20, line_color=self.COLORS['blue'])
        draw_dotted_line(frame, knee, start=knee[1] - 50, end=knee[1] + 20, line_color=self.COLORS['blue'])

        # Skeleton lines (same style as squat)
        cv2.line(frame, tuple(sh), tuple(hip), self.COLORS['light_blue'], 4, lineType=self.linetype)
        cv2.line(frame, tuple(hip), tuple(knee), self.COLORS['light_blue'], 4, lineType=self.linetype)
        cv2.line(frame, tuple(knee), tuple(ankle), self.COLORS['light_blue'], 4, lineType=self.linetype)
        cv2.line(frame, tuple(ankle), tuple(foot), self.COLORS['light_blue'], 4, lineType=self.linetype)

        for p in (sh, hip, knee, ankle, foot):
            cv2.circle(frame, tuple(p), 7, self.COLORS['yellow'], -1, lineType=self.linetype)

        # State from hip flexion
        current_state = self._get_state(int(hip_vertical))
        self.state_tracker['curr_state'] = current_state
        self._update_state_sequence(current_state)

        # Track per-rep min/max hip angle once s2 has started
        if 's2' in self.state_tracker['state_seq']:
            ang = int(hip_vertical)
            if self.state_tracker['rep_min_angle'] is None:
                self.state_tracker['rep_min_angle'] = ang
                self.state_tracker['rep_max_angle'] = ang
            else:
                self.state_tracker['rep_min_angle'] = min(self.state_tracker['rep_min_angle'], ang)
                self.state_tracker['rep_max_angle'] = max(self.state_tracker['rep_max_angle'], ang)

        # ---------------- Hold timing at s3 (fixed 5-second timer) ----------------
        TARGET_HOLD = 5.0  # seconds
        if current_state == 's3':
            if self.state_tracker['s3_enter_time'] is None:
                self.state_tracker['s3_enter_time'] = time.perf_counter()
            else:
                if (time.perf_counter() - self.state_tracker['s3_enter_time']) >= TARGET_HOLD:
                    self.state_tracker['s3_hold_ok'] = True
        else:
            # If we left s3, keep the flag but clear entry time
            self.state_tracker['s3_enter_time'] = None

        # --------- SUPPRESS form cues while in s3 (timer running) ---------
        if current_state == 's3':
            # Turn off "LOCK YOUR KNEE" and "DON'T ARCH YOUR BACK" and reset their TTLs
            self.state_tracker['DISPLAY_TEXT'][0] = False
            self.state_tracker['COUNT_FRAMES'][0] = 0
            self.state_tracker['DISPLAY_TEXT'][1] = False
            self.state_tracker['COUNT_FRAMES'][1] = 0

        # ---------------------- Counting & Feedback ---------------------- #
        play_sound = None

        # When we return to s1, decide the outcome of the rep attempt
        if current_state == 's1':
            # Detect a "drop" from s3 straight to s1 (missed s2 on the way down)
            if self.state_tracker['prev_state'] == 's3':
                self.state_tracker['DISPLAY_TEXT'][3] = True
                self.state_tracker['INCORRECT_POSTURE'] = True

            seq = self.state_tracker['state_seq']
            have_full_seq = (len(seq) == 3 and seq == ['s2', 's3', 's2'])

            # Range requirement
            range_ok = False
            if self.state_tracker['rep_min_angle'] is not None and self.state_tracker['rep_max_angle'] is not None:
                if (self.state_tracker['rep_max_angle'] - self.state_tracker['rep_min_angle']) >= self.thresholds['REP_MIN_RANGE']:
                    range_ok = True

            if have_full_seq and not self.state_tracker['INCORRECT_POSTURE'] and \
               self.state_tracker['s3_hold_ok'] and range_ok:
                # CORRECT rep
                self.state_tracker['CORRECT_COUNT'] += 1
                play_sound = str(self.state_tracker['CORRECT_COUNT'])
            else:
                # INCORRECT (partial sequence, bad form, no hold, or too small range)
                # If we only saw s2 and never reached s3, show "RAISE HIGHER"
                if 's2' in seq and 's3' not in seq:
                    self.state_tracker['DISPLAY_TEXT'][2] = True
                self.state_tracker['INCORRECT_COUNT'] += 1
                play_sound = 'incorrect'

            # Reset per-rep state
            self.state_tracker['state_seq'] = []
            self._reset_live_flags()

        else:
            # Live feedback while moving / at top
            # Do NOT set knee/torso cues while in s3 (timer phase)
            if current_state != 's3' and knee_flexion > self.thresholds['KNEE_LOCK_MAX']:
                self.state_tracker['DISPLAY_TEXT'][0] = True
                self.state_tracker['INCORRECT_POSTURE'] = True

            if current_state != 's3' and torso_tilt > self.thresholds['TORSO_TILT_MAX']:
                self.state_tracker['DISPLAY_TEXT'][1] = True
                self.state_tracker['INCORRECT_POSTURE'] = True

            # If we're in s2 and clearly below PASS band, nudge "RAISE HIGHER"
            pass_lo = self.thresholds['HIP_KNEE_VERT']['PASS'][0]
            if current_state == 's2' and hip_vertical < pass_lo:
                self.state_tracker['DISPLAY_TEXT'][2] = True

        # ---------------------- Inactivity (side-view) ---------------------- #
        display_inactivity = False
        if self.state_tracker['curr_state'] == self.state_tracker['prev_state']:
            end_time = time.perf_counter()
            self.state_tracker['INACTIVE_TIME'] += end_time - self.state_tracker['start_inactive_time']
            self.state_tracker['start_inactive_time'] = end_time

            if self.state_tracker['INACTIVE_TIME'] >= self.thresholds['INACTIVE_THRESH']:
                play_sound = 'reset_counters'
                self._hard_reset_all()
                display_inactivity = True
        else:
            self.state_tracker['start_inactive_time'] = time.perf_counter()
            self.state_tracker['INACTIVE_TIME'] = 0.0

        # ---------------------- Overlay ---------------------- #
        # Flip if needed (do this before writing text coordinates)
        if self.flip_frame:
            frame = cv2.flip(frame, 1)

        # Numeric overlays
        # Hip flex (state driver)
        cv2.putText(frame, str(int(hip_vertical)), (int(hip[0] + 10 if not self.flip_frame else frame_width - hip[0] + 10), hip[1]),
                    self.font, 0.6, self.COLORS['light_green'], 2, lineType=self.linetype)

        # Knee flexion (as degrees of bend)
        cv2.putText(frame, str(int(knee_flexion)), (int(knee[0] + 15 if not self.flip_frame else frame_width - knee[0] + 15), knee[1] + 10),
                    self.font, 0.6, self.COLORS['light_green'], 2, lineType=self.linetype)

        # Show hold timer while in s3 (counts up to 5 s)
        if self.state_tracker['curr_state'] == 's3' and self.state_tracker['s3_enter_time'] is not None:
            held_for = time.perf_counter() - self.state_tracker['s3_enter_time']
            if held_for > 5.0:
                held_for = 5.0
            draw_text(
                frame,
                f"HOLD: {held_for:.1f}/5.0s",
                pos=(30, 40),
                text_color=(255, 255, 230),
                font_scale=0.7,
                text_color_bg=(18, 185, 0) if held_for >= 5.0 else (0, 102, 204),
            )



        # Feedback banners (with per-label lifetime)
        self.state_tracker['COUNT_FRAMES'][self.state_tracker['DISPLAY_TEXT']] += 1
        frame = self._show_feedback(frame, self.state_tracker['COUNT_FRAMES'], self.FEEDBACK_ID_MAP)

        # TTL for banners
        ttl = self.thresholds['CNT_FRAME_THRESH']
        mask = self.state_tracker['COUNT_FRAMES'] > ttl
        self.state_tracker['DISPLAY_TEXT'][mask] = False
        self.state_tracker['COUNT_FRAMES'][mask] = 0

        # Commit prev_state
        self.state_tracker['prev_state'] = current_state

        return frame, play_sound

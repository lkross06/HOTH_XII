from __future__ import division
import os
import cv2
import dlib
from .eye import Eye
from .calibration import Calibration

#horizontal ratio will be 0.0 < RIGHT_THRESHOLD < LEFT_THRESHOLD < 1.0
#(i.e. dividing the eye into three sections)
RIGHT_THRESHOLD = 0.30
LEFT_THRESHOLD = 0.65

#vertical ratio will be 0.0 < TOP_THRESHOLD < BOTTOM_THRESHOLD < 1.0
TOP_THRESHOLD = 0.45
BOTTOM_THRESHOLD = 0.687

#resting value of around 2.9-3.2, when blinking around 4.9-5.5
BLINKING_THRESHOLD = 4.68 #both eyes must be this closed
WINKING_RIGHT_THRESHOLD = 4.5
WINKING_LEFT_THRESHOLD = 4.2 #for some reason my eyes are really asymmetrical?? rip
#must be 8% difference in eye blinking amounts, since when you wink the muscles in your face
#make both eyes naturally close a bit
WINKING_EYE_DIFF = 0.08 

class GazeTracking(object):
    """
    This class tracks the user's gaze.
    It provides useful information like the position of the eyes
    and pupils and allows to know if the eyes are open or closed
    """

    def __init__(self):
        self.frame = None
        self.eye_left = None
        self.eye_right = None
        self.calibration = Calibration()

        # _face_detector is used to detect faces
        self._face_detector = dlib.get_frontal_face_detector()

        # _predictor is used to get facial landmarks of a given face
        cwd = os.path.abspath(os.path.dirname(__file__))
        model_path = os.path.abspath(os.path.join(cwd, "trained_models/shape_predictor_68_face_landmarks.dat"))
        self._predictor = dlib.shape_predictor(model_path)

    @property
    def pupils_located(self):
        """Check that the pupils have been located"""
        try:
            int(self.eye_left.pupil.x)
            int(self.eye_left.pupil.y)
            int(self.eye_right.pupil.x)
            int(self.eye_right.pupil.y)
            return True
        except Exception:
            return False

    def _analyze(self):
        """Detects the face and initialize Eye objects"""
        frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
        faces = self._face_detector(frame)

        try:
            landmarks = self._predictor(frame, faces[0])
            self.eye_left = Eye(frame, landmarks, 0, self.calibration)
            self.eye_right = Eye(frame, landmarks, 1, self.calibration)

        except IndexError:
            self.eye_left = None
            self.eye_right = None

    def refresh(self, frame):
        """Refreshes the frame and analyzes it.

        Arguments:
            frame (numpy.ndarray): The frame to analyze
        """
        self.frame = frame
        self._analyze()

    def pupil_left_coords(self):
        """Returns the coordinates of the left pupil"""
        if self.pupils_located:
            x = self.eye_left.origin[0] + self.eye_left.pupil.x
            y = self.eye_left.origin[1] + self.eye_left.pupil.y
            return (x, y)

    def pupil_right_coords(self):
        """Returns the coordinates of the right pupil"""
        if self.pupils_located:
            x = self.eye_right.origin[0] + self.eye_right.pupil.x
            y = self.eye_right.origin[1] + self.eye_right.pupil.y
            return (x, y)

    def horizontal_ratio(self):
        """Returns a number between 0.0 and 1.0 that indicates the
        horizontal direction of the gaze. The extreme right is 0.0,
        the center is 0.5 and the extreme left is 1.0
        """
        if self.pupils_located:
            pupil_left = self.eye_left.pupil.x / (self.eye_left.center[0] * 2 - 10)
            pupil_right = self.eye_right.pupil.x / (self.eye_right.center[0] * 2 - 10)
            return (pupil_left + pupil_right) / 2

    def vertical_ratio(self):
        """Returns a number between 0.0 and 1.0 that indicates the
        vertical direction of the gaze. The extreme top is 0.0,
        the center is 0.5 and the extreme bottom is 1.0
        """
        if self.pupils_located:
            pupil_left = self.eye_left.pupil.y / (self.eye_left.center[1] * 2 - 10)
            pupil_right = self.eye_right.pupil.y / (self.eye_right.center[1] * 2 - 10)
            return (pupil_left + pupil_right) / 2

    def annotated_frame(self):
        """Returns the main frame with pupils highlighted"""
        frame = self.frame.copy()

        if self.pupils_located:
            color = (0, 255, 0)
            x_left, y_left = self.pupil_left_coords()
            x_right, y_right = self.pupil_right_coords()
            cv2.line(frame, (x_left - 5, y_left), (x_left + 5, y_left), color)
            cv2.line(frame, (x_left, y_left - 5), (x_left, y_left + 5), color)
            cv2.line(frame, (x_right - 5, y_right), (x_right + 5, y_right), color)
            cv2.line(frame, (x_right, y_right - 5), (x_right, y_right + 5), color)

        return frame

    ########################################
    ###   MODIFIED FOR MY OWN PURPOSES  ####
    ########################################

    def get_bl(self):
        if self.pupils_located:
            return self.eye_right.blinking

    def get_br(self):
        if self.pupils_located:
            return self.eye_left.blinking
    
    def both_pupils_found(self):
        return self.pupils_located

    def is_right(self):
        """Returns true if the user is looking to the right"""
        if self.pupils_located:
            return self.horizontal_ratio() <= RIGHT_THRESHOLD

    def is_left(self):
        """Returns true if the user is looking to the left"""
        if self.pupils_located:
            return self.horizontal_ratio() >= LEFT_THRESHOLD

    def is_center(self):
        """Returns true if the user is looking to the center"""
        if self.pupils_located:
            return self.is_right() is not True and self.is_left() is not True

    def is_blinking(self):
        """Returns true if the user closes his eyes"""
        if self.pupils_located:
            return self.get_bl() > BLINKING_THRESHOLD and self.get_br() > BLINKING_THRESHOLD

    #***NOTE: the library considers "right" and "left" in terms of pixel position/coordinates
    #i consider them relative to myself, so i have to flip them
    def is_winking_right(self):
        if self.pupils_located:
            return self.get_br() > WINKING_RIGHT_THRESHOLD and self.get_br() - self.get_bl() >= WINKING_EYE_DIFF * WINKING_RIGHT_THRESHOLD
   
    def is_winking_left(self):
        if self.pupils_located:
            return self.get_bl() > WINKING_LEFT_THRESHOLD and self.get_bl() - self.get_br() >= WINKING_EYE_DIFF * WINKING_LEFT_THRESHOLD
    
    def is_up(self):
        if self.pupils_located:
            return self.vertical_ratio() <= TOP_THRESHOLD
    
    def is_bottom(self):
        if self.pupils_located:
            return self.vertical_ratio() >= BOTTOM_THRESHOLD

    def true_gaze_blinking(self):
        '''
        returns 0-3 corresponding to one of these blinking statuses:

        0 NOT BLINKING
        1 LEFT WINKING (left eye closed)
        2 RIGHT WINKING
        3 BLINKING

        or -1 if pupils not found
        '''
        if not self.pupils_located:
            return -1

        if self.is_blinking(): #greater threshold so we can check it first
            return 3
        if self.is_winking_right():
            return 2
        if self.is_winking_left():
            return 1
        return 0

    def true_gaze_direction(self):
        '''
        returns 0-8 corresponding to one of these direcitons:
        
        0 TOP-LEFT       1 TOP-MIDDLE     2 TOP-RIGHT
        3 CENTER-LEFT    4 TRUE CENTER    5 CENTER-RIGHT
        6 BOTTOM-LEFT    7 BOTTOM-MIDDLE  8 BOTTOM-RIGHT

        or -1 if pupils not found
        '''
        if not self.pupils_located:
            return -1

        if self.is_left():
            h_offset = 0
        elif self.is_right():
            h_offset = 2
        else:
            h_offset = 1

        if self.is_up():
            v_offset = 0
        elif self.is_bottom():
            v_offset = 6
        else:
            v_offset = 3
        
        return h_offset + v_offset

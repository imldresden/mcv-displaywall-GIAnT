# coding=utf-8
from collections import OrderedDict
from datetime import timedelta


# The time offset for the whole session. This is necessary if the videos would scroll in the negative time.
# It says how much later the video should be started to prevent this negativ time.
session_time_offset = 2.0
# The offset of the videos to show it in giant.
video_offsets = 0.0

# The timestamps of the start time of each video for this session.
video_timestamps = OrderedDict([
    ("kinect", 1510843432),
    ("camUser", 1510843435.1),
    ("camWall", 1510843430.1),
])

# Timestamps of each phase in this session
phase_timestamps = OrderedDict([
    ("Training Touch", ("15:44:20.518699", "15:56:21.690726")),
    ("Training Pointing", ("15:58:33.914189", "16:07:58.634671")),
    ("Guided Exploration", ("16:11:46.223985", "16:31:51.442140")),
    ("Free Exploration", ("16:32:17.216694", "16:41:05.160109"))
])

# The joint that will be used to calculate the distance between the body and the device or touch.
joint_type_body_to_device = "OKS_SPINE_MID"
joint_type_body_to_touch = "OKS_SPINE_SHOULDER"

# Values for the mapping of device ids to the skeleton ids:

# How many times should a device id be counted to assume that it can be coupled with a given skeleton id.
device_id_count_threshold = 5
# The time difference between the body and the device movement.
max_time_delta_body_to_device = timedelta(milliseconds=150)
# The maximal distance between a device and any body to be accounted for.
max_dist_delta_body_to_device = 0.55  # in m

# values for the mapping of touches to users (body and devices):

# The time difference between an touch on the wall and an injection.
max_time_delta_touch_to_inj = timedelta(milliseconds=150)
# The time delta between an injection of a touch to the wall and an interaction on the device itself.
max_time_delta_inj_to_de = timedelta(milliseconds=3)
# The time differencte between the body movement and the occurence of a touch on the wall.
max_time_delta_body_to_touch = timedelta(milliseconds=75)
# The minimal distance that is requiered between an touch and a body (only the z-position value).
min_body_dist_to_wall = 0.85  # in m
# The average arm span of the user in this study.
arm_span = 1.0  # in m

# Should touches with a -1 id be ignored. They will not be written to the giant_* output file.
ignore_not_found_touch_ids = False
# All skeleton ids that will be entered here will be removed from the giant_* output files.
ignore_skeleton_ids = [
    '72057594037927962',
    '72057594037929011',
    '72057594037928347'
]
# If the divico_to_giant is run once, it will create a file with the name session_*_skeleton_id_mapping.txt. The content
# of this file can be added here and can be modified.
user_ids = {
    '72057594037927961': 1,
    '72057594037927962': 3,
    '72057594037928024': 2,
    '72057594037928045': 2,
    '72057594037928062': 1,
    '72057594037928070': 1,
    '72057594037928070-2': 2,
    '72057594037928165': 2,
    '72057594037928198': 1,
    '72057594037928347': -1,
    '72057594037928354': 1,
    '72057594037928388': 2,
    '72057594037928411': 1,
    '72057594037928422': 1,
    '72057594037928553': 1,
    '72057594037928578': 1,
    '72057594037928607': 2,
    '72057594037928665': 2,
    '72057594037928707': 2,
    '72057594037928747': 1,
    '72057594037928777': 2,
    '72057594037928797': 1,
    '72057594037928993': 1,
    '72057594037929011': 9
}


# TODO: 72057594037928347 is the chair.

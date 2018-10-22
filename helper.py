# -*- coding: utf-8 -*-
# GIAnT Group Interaction Analysis Toolkit
# Copyright (C) 2017 Interactive Media Lab Dresden
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import time

import os

import imp
from math import sqrt


def unlink_node_list(node_list):
    for node in node_list:
        node.unlink(True)


def format_time(value, show_ms=True):
    ms = int((value - int(value)) * 1000 + 0.5)
    m, s = divmod(value, 60)
    time_str = "{:02d}:{:02d}".format(int(m), int(s))
    if show_ms and ms != 0:
        time_str += ".{:03d}".format(ms)
    return time_str

def map_value(value, from_min, from_max, to_min, to_max):
    old_range = from_max - from_min
    new_range = to_max - to_min
    value = (value - from_min) * new_range / old_range + to_min
    return value

def csvtime_to_float(date, csv_time):
    """
    Converts time from csv format to float seconds since 1970.

    :param date:
    :type date:
    :param csv_time:
    :type csv_time:
    :return: The time as unix timestamp.
    :rtype: float
    """
    time_str = date + " " + csv_time
    time_str, micorsec_str = time_str.split(".")
    # Fill the string with missing 0 at the end if the string is to short.
    micorsec_str = micorsec_str if len(micorsec_str) >= 6 else "{}{}".format(micorsec_str, "0" * (6 - len(micorsec_str)))

    time_struct = time.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    microsec = int(micorsec_str)
    return time.mktime(time_struct) + float(microsec) / 1000000


def mapping_kinect_to_giant_coordinates(pos_x, pos_y, pos_z):
    pos_x = map_value(pos_x, -1.709, 2.116, -4.295, -0.215)
    pos_y = map_value(pos_y, -0.694, 0.073, 1.01, 1.725)  # Close to the wall (in touch range)
    pos_z = map_value(pos_z, 1.805, 3.890, -3.025, -0.885)
    return pos_x, pos_y, pos_z


def map_kinect_to_device_coordinates(pos_x, pos_y, pos_z):
    # pos_x = map_value(pos_x, 2.5, -2.5, 0, 4.8)
    # pos_y = map_value(pos_y, -0.6, -0.05, 0.68, 1.37)
    # pos_z = map_value(pos_z, 4.5, 1.3, 0, 3.8)
    pos_x = map_value(pos_x, 2.116, -1.709, 0.215, 4.295)
    # pos_y = map_value(pos_y, -0.633, 0.152, 1.01, 1.715)
    pos_y = map_value(pos_y, -0.694, 0.073, 1.01, 1.725)  # Close to the wall (in touch range)
    pos_z = map_value(pos_z, 3.890, 1.805, 0.885, 3.025)
    return pos_x, pos_y, pos_z


def map_device_coordinates_to_wall_pixels(pos_x, pos_y):
    pos_x = map_value(pos_x, 0, 4.8, 0, 7680)
    # pos_y = map_value(pos_y, 0.68, 1.37, 2160, 1080)
    pos_y = map_value(pos_y, 1.08, 1.77, 2160, 1080)
    return pos_x, pos_y


def map_wall_pixels_to_device_coordinates(pos_x, pos_y):
    pos_x = map_value(pos_x, 0, 7680, 0, 4.8)
    pos_y = map_value(pos_y, 2160, 1080, 1.08, 1.77)
    return pos_x, pos_y, 0


_project_name = 'divico-GIAnT'
_input_folder_prefix = 'data_logs/session_'
_input_filename_prefix = 'session_'
def __get_config_filename(session_id):
    """
    Searches the absolute path to a config file for the given number.

    :param session_id: The id for the searched session config.
    :type session_id: str
    :return: The absolute path to the config file.
    :rtype: str
    """
    working_directory = os.getcwd()
    index = working_directory.find(_project_name)
    working_directory = working_directory[:index + len(_project_name)]

    cfg_file = _input_folder_prefix + session_id + '/'
    cfg_file += _input_filename_prefix + session_id + "_config.py"
    filename = os.path.join(working_directory, cfg_file)
    return filename


def get_config(session_id):
    """
    Loads a config with the given id.

    :param session_id: The id for the searched session config.
    :type session_id: str
    :return: The config for this session. If no config with this id was found, it will be None.
    """
    try:
        config = imp.load_source('', __get_config_filename(session_id))
        return config
    except IOError:
        print 'No config was found for this session: {}.'.format(session_id)
        return None


def calc_dist(p1, p2):
    return sqrt(sum([(p1[i] - p2[i]) ** 2 for i in range(len(p1))]))

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

import sqlite3
import math
from libavg import avg, player
import glob, os
import numpy as np

from helper import csvtime_to_float

player.loadPlugin("pyglm")
TIME_STEP = 1./30

wall_width = 4.90
wall_height = 2.06
# pos_range = [[-0.5,0,0.5], [5.5,2.5,2.5]]  # User head position minimum and maximum
pos_range = [[-0.5,0,0.5], [5.5,2.5,5]]  # User head position minimum and maximum
max_time = 0
time_offset = 0
touch_range = [4*1920, 3*1080]
x_wall_range = [0, wall_width]
y_wall_range = [0.4, 0.4+wall_height]


def execute_qry(qry, do_fetch=False):
    con = sqlite3.connect("db")
    cur = con.cursor()
    cur.execute(qry)
    if do_fetch:
        data = cur.fetchall()
    con.commit()
    con.close()
    if do_fetch:
        return data


def line_plane_intersect(line_pt, line_dir, plane_pt, plane_normal):
    line_pt = pyglm.vec3(line_pt)
    line_dir = pyglm.vec3(line_dir)
    plane_pt = pyglm.vec3(plane_pt)
    numerator = pyglm.vec3.dot(plane_pt - line_pt, plane_normal)
    denominator = pyglm.vec3.dot(line_dir, plane_normal)
    if math.fabs(denominator) > 0.000000001:
        length = numerator/denominator
        return pyglm.vec3(line_pt + pyglm.vec3(line_dir.getNormalized())*length)
    else:
        return None


class Session(object):
    def __init__(self, session_num, level_num, data_dir, optitrack_filename, touch_filename, device_touch_filename, device_filename, video_filenames,
                 date, video_start_times, video_time_offset, session_time_offset, num_users, user_pitch_offsets):
        self.session_num = session_num
        self.level_num = level_num
        self.data_dir = data_dir
        self.optitrack_filename = optitrack_filename
        self.touch_filename = touch_filename
        self.device_touch_filename = device_touch_filename
        self.device_filename = device_filename
        self.video_filenames = video_filenames
        self.date = date
        self.num_users = num_users
        self.__session_time_offset = session_time_offset
        # user_pitch_offsets: The recorded pitch data is incorrect by a constant if the subjects didn't wear the
        # helmet correctly.
        self.user_pitch_offsets = user_pitch_offsets

        self.video_start_times = []
        for video_start_time in video_start_times:
            self.video_start_times.append(csvtime_to_float(date, video_start_time) + video_time_offset)

    @property
    def time_offset(self):
        return self.__session_time_offset

    def load_from_db(self):
        self.start_time = execute_qry(
                "SELECT min(time) FROM head WHERE "+self.__get_level_select()+";", True)[0][0] + self.__session_time_offset
        self.duration = execute_qry(
                "SELECT max(time) FROM head WHERE "+self.__get_level_select()+";", True)[0][0] - self.start_time
        print "---- Load Session {} from DB ({} - {}) ----".format(self.session_num, self.start_time, self.start_time + self.duration)

        self.__users = []
        for userid in range(0, self.num_users):
            self.__users.append(self.__create_user(userid))

    def get_video_time_offset(self, video_num):
        if -1 < video_num < len(self.video_start_times):
            return self.start_time - self.video_start_times[video_num]
        return -1

    @property
    def users(self):
        return self.__users

    def __create_user(self, userid):
        user = plots.User(userid, self.duration)
        pitch_offset = self.user_pitch_offsets[userid]

        head_data_list = execute_qry("SELECT user, x, y, z, pitch, yaw, roll, time, x_sum, y_sum, z_sum "
                          "FROM head WHERE user = " + str(userid) + " AND " + self.__get_level_select() +
                          " GROUP BY time ORDER BY time;", True)

        if len(head_data_list) != 0:
            # ToDo !! fill user.HeadData with nonsense position for all times from start to end not in head_data_list (timestamp: head_list[7])
            user_start_time = head_data_list[0][7]
            user_end_time = head_data_list[-1][7]
            print "User   |", userid, "| time:", user_start_time, "-", user_end_time

            # add fake position data of user for time before he arrives
            for i in np.arange(self.start_time, user_start_time, step=TIME_STEP):
                first_head_data_prefix = head_data_list[0][7], head_data_list[0][8], head_data_list[0][9]
                fake_head_list = self.__create_fake_head_data_list(userid, i, [0.0, 0.0, 0.0])
                fake_head_data = self.__head_data_from_list(fake_head_list, pitch_offset)
                if fake_head_data is not None:
                    user.addHeadData(fake_head_data)

            # add actual position data of time user is actually there
            for head_list in head_data_list:
                head_data = self.__head_data_from_list(head_list, pitch_offset)
                if head_data is not None:
                    user.addHeadData(head_data)

            # add fake position data of user for time after he left
            for i in np.arange(user_end_time, self.start_time + self.duration, step=TIME_STEP):
                last_head_data_prefix = head_data_list[-1][7], head_data_list[-1][8], head_data_list[-1][9]
                fake_head_list = self.__create_fake_head_data_list(userid, i, [0, 0, 0])
                fake_head_data = self.__head_data_from_list(fake_head_list, pitch_offset)
                if fake_head_data is not None:
                    user.addHeadData(fake_head_data)

        touch_data_list = execute_qry("SELECT user, x, y, time, duration, injected, type "
                                      "FROM touch WHERE user = " + str(userid) + " AND " + self.__get_level_select() +
                                      " GROUP BY time ORDER BY time;", True)
        if len(touch_data_list) != 0:
            print "Touch  |", userid

        for touch_list in touch_data_list:
            touch = self.__touch_data_from_list(touch_list)
            if touch is not None:
                user.addTouch(touch)

        device_data_list = execute_qry("SELECT user, time, screen_x, screen_y, space_x, space_y, space_z, pitch, yaw, roll "
                                       "FROM device "
                                       "WHERE user = " + str(userid) + " AND " + self.__get_level_select() +
                                       " GROUP BY time ORDER BY time;", True)

        if len(device_data_list) != 0:
            device_start_time = device_data_list[0][1]
            device_end_time = device_data_list[-1][1]
            print "Device |", userid, "| time:", device_start_time, "-", device_end_time

            # Add fake position data of the device for time before it arrives.
            for i in np.arange(self.start_time, device_start_time, step=TIME_STEP):
                fake_device_entry_list = [userid, i, -1, -1, 2.0, 1.0, 2.0, 0, 0, 0]
                fake_device_entry = self.__device_entry_from_list(fake_device_entry_list, pitch_offset)
                if fake_device_entry is not None:
                    user.addDeviceEntry(fake_device_entry)

            # Add the normal and correct entries for the device.
            for device_list in device_data_list:
                device_entry = self.__device_entry_from_list(device_list, pitch_offset)
                if device_entry is not None:
                    user.addDeviceEntry(device_entry)

            # Add fake position data of the device for time after it left.
            for i in np.arange(device_end_time, self.start_time + self.duration, step=TIME_STEP):
                fake_device_entry_list = [userid, i, -1, -1, 2.0, 1.0, 2.0, 0, 0, 0]
                fake_device_entry = self.__device_entry_from_list(fake_device_entry_list, pitch_offset)
                if fake_device_entry is not None:
                    user.addDeviceEntry(fake_device_entry)

        de_t_data_list = execute_qry("SELECT user, x, y, time "
                                     "FROM device_touch WHERE user = " + str(userid) + " AND " + self.__get_level_select() +
                                     " GROUP BY time ORDER BY time;", True)
        if len(de_t_data_list) != 0:
            print "DTouch |", userid

        for device_touch_list in de_t_data_list:
            touch = self.__device_touch_data_from_list(device_touch_list)
            if touch is not None:
                user.addDeviceTouch(touch)

        return user

    def __create_fake_head_data_list(self, userid, timestamp, head_prefix_sum):
        fake_head_list = [userid, 2.0, 1.0, 2.0, 0, 0, 0, timestamp,
                          head_prefix_sum[0], head_prefix_sum[1], head_prefix_sum[2]]
        # head_data.posPrefixSum = head_list[8], head_list[9], head_list[10]
        return fake_head_list

    def __head_data_from_list(self, head_list, pitch_offset):

        def calc_wall_viewpoint(hd):
            yaw_quat = pyglm.quat.fromAxisAngle((0, 1, 0), hd.rot[0])
            pitch_quat = pyglm.quat.fromAxisAngle((1, 0, 0), hd.rot[1])
            roll_quat = pyglm.quat.fromAxisAngle((0, 0, 1), hd.rot[2])
            q = yaw_quat * pitch_quat * roll_quat
            head_dir = q * pyglm.vec3(0, 0, 1)

            viewpt3d = line_plane_intersect(hd.pos, head_dir, (0, 0, 0), (0, 0, 1))
            if viewpt3d is not None:
                hd.setWallViewpoint(avg.Point2D(viewpt3d.x, viewpt3d.y))
            else:
                hd.setWallViewpoint(avg.Point2D(0, 0))

        timestamp = head_list[7]
        if timestamp < self.start_time or self.start_time + self.duration < timestamp:
            return None

        userid = head_list[0]
        pos = head_list[1], head_list[2]-0.2, head_list[3]
        rot = head_list[4], head_list[5] + pitch_offset, head_list[6]
        head_data = plots.HeadData(userid, pos, rot, timestamp)
        head_data.posPrefixSum = head_list[8], head_list[9], head_list[10]
        calc_wall_viewpoint(head_data)
        return head_data

    def __touch_data_from_list(self, touch_list):
        timestamp = touch_list[3] - self.start_time
        if timestamp < 0 or timestamp > self.duration:
            return None

        userid = touch_list[0]
        pos = avg.Point2D(touch_list[1], touch_list[2])
        duration = touch_list[4]
        injected = touch_list[5]
        t_type = touch_list[6]
        return plots.Touch(userid, pos, timestamp, duration, bool(injected), str(t_type))

    def __device_touch_data_from_list(self, device_touch_list):
        timestamp = device_touch_list[3] - self.start_time
        if timestamp < 0 or timestamp > self.duration:
            return None

        userid = device_touch_list[0]
        pos = avg.Point2D(device_touch_list[1], device_touch_list[2])
        t_type = device_touch_list[3]
        return plots.Touch(userid, pos, timestamp, 0, True, str(t_type))

    def __device_entry_from_list(self, device_list, pitch_offset):

        def calc_wall_viewpoint(de):
            yaw_quat = pyglm.quat.fromAxisAngle((0, 1, 0), de.orientation[0])
            pitch_quat = pyglm.quat.fromAxisAngle((1, 0, 0), de.orientation[1])
            roll_quat = pyglm.quat.fromAxisAngle((0, 0, 1), de.orientation[2])
            q = yaw_quat * pitch_quat * roll_quat
            device_dir = q * pyglm.vec3(0, 0, 1)

            viewpt3d = line_plane_intersect(de.spacePos, device_dir, (0, 0, 0), (0, 0, 1))
            if viewpt3d is not None:
                de.setWallViewpoint(avg.Point2D(viewpt3d.x, viewpt3d.y))
            else:
                de.setWallViewpoint(avg.Point2D(0, 0))

        timestamp = device_list[1]
        if timestamp < self.start_time or self.start_time + self.duration < timestamp:
            return None

        user_id = device_list[0]
        screen_pos = avg.Point2D(device_list[2], device_list[3])
        space_pos = [device_list[4], device_list[5], device_list[6]]
        orientation = [device_list[7] + pitch_offset, device_list[8], device_list[9]]

        device_entry = plots.DeviceEntry(user_id, screen_pos, space_pos, orientation, timestamp)
        calc_wall_viewpoint(device_entry)
        return device_entry

    def __get_level_select(self):
        return "session=\"" + str(self.session_num) + "\" AND level=" + str(self.level_num)

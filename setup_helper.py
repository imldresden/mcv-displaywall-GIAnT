#!/usr/bin/env python
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

import csv
import sqlite3
import pat_model
import time

from libavg import player

from helper import csvtime_to_float
from one_euro_filter import OneEuroFilter

TIME_STEP = 1./30            # User position data stored with 30 FPS
# Its necessary to filter the coordinates of the user to reduce the jitter. The jitter can influence the calcuations
# for distances quite a bit (can double it).
use_filter_for_user_coordinates = True
use_filter_for_device_coordinates = True

player.loadPlugin("plots")


def create_table(table, columns):
    """
    :param table: name of the table (string)
    :param columns: columns separated by commas (string) i.e. "id INT, value1 FLOAT, value2 VARCHAR..."
    :return:
    """
    pat_model.execute_qry("DROP TABLE IF EXISTS " + table + ";")
    pat_model.execute_qry("CREATE TABLE " + table + " (" + columns + ");")


def import_optitrack(session):
    # Create filter.
    if use_filter_for_user_coordinates:
        x_filters = {uid: OneEuroFilter(freq=30, mincutoff=1, beta=1, dcutoff=1.0) for uid in range(session.num_users)}
        y_filters = {uid: OneEuroFilter(freq=30, mincutoff=1, beta=1, dcutoff=1.0) for uid in range(session.num_users)}
        z_filters = {uid: OneEuroFilter(freq=30, mincutoff=1, beta=1, dcutoff=1.0) for uid in range(session.num_users)}

    def head_data_from_csv(csv_record, date):
        timestamp = csvtime_to_float(date, csv_record[0])
        userid = eval(csv_record[1])
        pos = list(eval(csv_record[2]))
        # pos is in Meters, origin is lower left corner of the wall.
        # In the CSV file:
        #   If facing the wall, x points left, y up, z into the wall
        # In the DB:
        #   If facing the wall, x points right, y up, z away from the wall
        pos[0] = -pos[0]
        pos[2] = -pos[2]
        # Rotation is yaw, pitch, roll, origin is facing wall.
        rotation = eval(csv_record[3])
        head_data = plots.HeadData(userid, pos, rotation, timestamp)
        return head_data

    def create_interpolated_head_data(data1, data2, cur_time, prev_data):
        def interpolate(x1, x2, ratio):
            return x1 * ratio + x2 * (1 - ratio)

        if data1 is None:
            data = data2
        else:
            part = (cur_time - data1.time) / (data2.time - data1.time)
            assert(data1.userid == data2.userid)
            pos = [interpolate(data1.pos[0], data2.pos[0], part),
                    interpolate(data1.pos[1], data2.pos[1], part),
                    interpolate(data1.pos[2], data2.pos[2], part)]
            rot = [interpolate(data1.rot[0], data2.rot[0], part),
                    interpolate(data1.rot[1], data2.rot[1], part),
                    interpolate(data1.rot[2], data2.rot[2], part)]
            data = plots.HeadData(data1.userid, pos, rot, cur_time)
        if prev_data:
            prev_prefix_sum = prev_data.posPrefixSum
            data.posPrefixSum = (
                prev_prefix_sum[0] + data.pos[0],
                prev_prefix_sum[1] + data.pos[1],
                prev_prefix_sum[2] + data.pos[2])
        else:
            data.posPrefixSum = data.pos
        return data

    def head_data_to_list(head):
        # Its necessary to filter the coordinates of the user to reduce the jitter. The jitter can influence the calcuations
        # for distances quite a bit (can double it).
        pos = head.pos
        if use_filter_for_user_coordinates:
            pos = x_filters[head.userid](pos[0], head.time), y_filters[head.userid](pos[1], head.time), z_filters[head.userid](pos[2], head.time)
        return (session.session_num, session.level_num, head.userid,
                pos[0], pos[1], pos[2],
                head.rot[0], head.rot[1], head.rot[2],
                head.time,
                head.posPrefixSum[0], head.posPrefixSum[1], head.posPrefixSum[2])

    print "Importing optitrack data:"
    print "  Reading csv"
    with open(session.data_dir+"/"+session.optitrack_filename) as f:
        reader = csv.reader(f)
        csv_data = list(reader)
        csv_data.pop(0)
    print "  Processing"
    last_lines = [None] * session.num_users
    last_db_time = [None] * session.num_users
    last_interpol_data = [None] * session.num_users
    db_list = []
    for data_line in csv_data:
        head_data = head_data_from_csv(data_line, session.date)
        userid = head_data.userid
        if userid >= session.num_users:
            break

        last_data = last_lines[userid]
        if (last_data is not None) and (last_data.time == head_data.time):  # Discard equal lines
            continue
        while last_db_time[userid] < head_data.time:
            # The original (csv) data has irregular timestamps, the db should contain data every
            # TIME_STEP.
            interpol_data = create_interpolated_head_data(last_data, head_data, last_db_time[userid],
                                                          last_interpol_data[head_data.userid])
            db_list.append(head_data_to_list(interpol_data))
            if last_db_time[userid] is None:
                last_db_time[userid] = head_data.time
            else:
                last_db_time[userid] += TIME_STEP
            last_interpol_data[userid] = interpol_data
        last_lines[userid] = head_data
    print "  Writing database"
    con = sqlite3.connect("db")
    cur = con.cursor()
    cur.executemany(
        "INSERT INTO head (session, level, user, x, y, z, pitch, yaw, roll, time, x_sum, y_sum, z_sum) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?);",
        db_list)
    con.commit()
    con.close()


def import_touches(session):
    print "Importing touch data:"

    print "  Reading csv"
    with open(session.data_dir + "/" + session.touch_filename) as f:
        reader = csv.reader(f)
        csv_data = list(reader)
        csv_data.pop(0)
    print "  Processing"
    db_list = []
    last_time = 0
    for data in csv_data:
        timestamp = csvtime_to_float(session.date, data[0])
        pos = list(eval(data[1]))
        userid = int(data[2])
        injected = 1 if data[3] == 'True' else 0
        t_type = data[4]
        if userid is None:
            continue
        touch = [session.session_num, session.level_num, userid, pos[0], pos[1], timestamp, 0.03, injected, t_type]
        if timestamp > last_time + 0.1:
            # New touch
            db_list.append(touch)  # prepare for upload
        else:
            # Touch continuation
            touch[6] += timestamp - last_time
            db_list[-1] = touch
        last_time = touch[3]

    print "  Writing database"
    con = sqlite3.connect("db")
    cur = con.cursor()
    cur.executemany("INSERT INTO touch (session, level, user, x, y, time, duration, injected, type) VALUES (?,?,?,?,?,?,?,?,?);", db_list)
    con.commit()
    con.close()


def import_device(session):
    # Create filter.
    if use_filter_for_device_coordinates:
        x_filters = {uid: OneEuroFilter(freq=30, mincutoff=1, beta=1, dcutoff=1.0) for uid in range(session.num_users)}
        y_filters = {uid: OneEuroFilter(freq=30, mincutoff=1, beta=1, dcutoff=1.0) for uid in range(session.num_users)}
        z_filters = {uid: OneEuroFilter(freq=30, mincutoff=1, beta=1, dcutoff=1.0) for uid in range(session.num_users)}

    def device_entry_from_csv(csv_record, date):
        timestamp = csvtime_to_float(date, csv_record[0])
        uid = int(csv_record[1])
        pos_screen = list(eval(csv_record[2]))
        pos_space = list(eval(csv_record[3]))
        orientation = list(eval(csv_record[4]))
        device_entry = plots.DeviceEntry(uid, pos_screen, pos_space, orientation, timestamp)
        return device_entry

    def create_interpolated_device_entry(data1, data2, cur_time):

        def interpolate(x1, x2, ratio):
            return x1 * ratio + x2 * (1 - ratio)

        if data1 is None:
            data = data2
        else:
            part = (cur_time - data1.time) / (data2.time - data1.time)
            assert(data1.userid == data2.userid)
            pos_screen = [interpolate(data1.screenPos[0], data2.screenPos[0], part),
                          interpolate(data1.screenPos[1], data2.screenPos[1], part)]
            pos_space = [interpolate(data1.spacePos[0], data2.spacePos[0], part),
                         interpolate(data1.spacePos[1], data2.spacePos[1], part),
                         interpolate(data1.spacePos[2], data2.spacePos[2], part)]
            orientation = [interpolate(data1.orientation[0], data2.orientation[0], part),
                           interpolate(data1.orientation[1], data2.orientation[1], part),
                           interpolate(data1.orientation[2], data2.orientation[2], part)]
            data = plots.DeviceEntry(data1.userid, pos_screen, pos_space, orientation, cur_time)
        return data

    def device_entry_to_list(device_entry):
        # Its necessary to filter the coordinates of the user to reduce the jitter. The jitter can influence the calcuations
        # for distances quite a bit (can double it).
        pos = device_entry.spacePos
        if use_filter_for_device_coordinates:
            pos = (
                x_filters[device_entry.userid](pos[0], device_entry.time),
                y_filters[device_entry.userid](pos[1], device_entry.time),
                z_filters[device_entry.userid](pos[2], device_entry.time)
            )
        return [session.session_num, session.level_num, device_entry.userid,
                device_entry.screenPos[0], device_entry.screenPos[1],
                pos[0], pos[1], pos[2],
                device_entry.orientation[0], device_entry.orientation[1], device_entry.orientation[2],
                device_entry.time]

    print "Importing device data:"

    print "  Reading csv"
    with open(session.data_dir + "/" + session.device_filename) as f:
        reader = csv.reader(f)
        csv_data = list(reader)
        csv_data.pop(0)

    print "  Processing"
    last_lines = [None] * session.num_users
    last_db_time = [None] * session.num_users
    last_interpol_data = [None] * session.num_users
    db_list = []
    for data_line in csv_data:
        device_entry_v = device_entry_from_csv(data_line, session.date)
        userid = int(data_line[1])
        if userid >= session.num_users:
            break

        last_data = last_lines[userid]
        if (last_data is not None) and (last_data.time == device_entry_v.time):  # Discard equal lines
            continue

        while last_db_time[userid] < device_entry_v.time:
            # The original (csv) data has irregular timestamps, the db should contain data every
            # TIME_STEP.
            interpol_data = create_interpolated_device_entry(last_data, device_entry_v, last_db_time[userid])
            db_list.append(device_entry_to_list(interpol_data))
            if last_db_time[userid] is None:
                last_db_time[userid] = device_entry_v.time
            else:
                last_db_time[userid] += TIME_STEP
            last_interpol_data[userid] = interpol_data
        last_lines[userid] = device_entry_v

    print "  Writing database"
    con = sqlite3.connect("db")
    cur = con.cursor()
    cur.executemany("INSERT INTO device (session, level, user, screen_x, screen_y, space_x, space_y, space_z, pitch, yaw, roll, time) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?);", db_list)
    con.commit()
    con.close()


def import_device_touches(session):
    print "Importing device touch data:"

    print "  Reading csv"
    with open(session.data_dir + "/" + session.device_touch_filename) as f:
        reader = csv.reader(f)
        csv_data = list(reader)
        csv_data.pop(0)
    print "  Processing"
    db_list = []
    last_time = 0
    for data in csv_data:
        print data
        timestamp = csvtime_to_float(session.date, data[0])
        userid = int(data[1])
        pos = list(eval(data[2]))
        t_type = data[3]
        if userid is None:
            continue
        touch = [session.session_num, session.level_num, userid, pos[0], pos[1], timestamp, t_type]
        if timestamp > last_time + 0.1:
            # New touch
            db_list.append(touch)  # prepare for upload
        else:
            # Touch continuation
            touch[6] += timestamp - last_time
            db_list[-1] = touch
        last_time = touch[3]

    print "  Writing database"
    con = sqlite3.connect("db")
    cur = con.cursor()
    cur.executemany("INSERT INTO device_touch (session, level, user, x, y, time, type) VALUES (?,?,?,?,?,?,?);", db_list)
    con.commit()
    con.close()


def setup():
    create_table("head", "ID INTEGER PRIMARY KEY AUTOINCREMENT,"
                         "session VARCHAR(45) NOT NULL,"
                         "level TINYINT NOT NULL,"
                         "user TINYINT NOT NULL,"
                         "x FLOAT,"
                         "y FLOAT,"
                         "z FLOAT,"
                         "pitch FLOAT,"
                         "yaw FLOAT,"
                         "roll FLOAT,"
                         "time FLOAT NOT NULL,"
                         "x_sum FLOAT,"          # prefix sum for quick calculation of average positions.
                         "y_sum FLOAT,"
                         "z_sum FLOAT")
    create_table("touch", "ID INTEGER PRIMARY KEY AUTOINCREMENT,"
                          "session VARCHAR(45) NOT NULL,"
                          "level TINYINT NOT NULL,"
                          "user TINYINT NOT NULL,"
                          "x FLOAT,"
                          "y FLOAT,"
                          "time FLOAT NOT NULL,"
                          "duration FLOAT NOT NULL,"
                          "injected TINYINT NOT NULL,"
                          "type VARCHAR(45) NOT NULL")
    create_table("device_touch", "ID INTEGER PRIMARY KEY AUTOINCREMENT,"
                                 "session VARCHAR(45) NOT NULL,"
                                 "level TINYINT NOT NULL,"
                                 "user TINYINT NOT NULL,"
                                 "x FLOAT,"
                                 "y FLOAT,"
                                 "time FLOAT NOT NULL,"
                                 "type VARCHAR(45) NOT NULL")
    create_table("device", "ID INTEGER PRIMARY KEY AUTOINCREMENT,"
                           "session VARCHAR(45) NOT NULL,"
                           "level TINYINT NOT NULL,"
                           "user TINYINT NOT NULL,"
                           "screen_x FLOAT,"
                           "screen_y FLOAT,"
                           "space_x FLOAT,"
                           "space_y FLOAT,"
                           "space_z FLOAT,"
                           "pitch FLOAT,"
                           "yaw FLOAT,"
                           "roll FLOAT,"
                           "time FLOAT NOT NULL")

    # for data base generation
    # 1. create session object from data (filenames etc.)
            # session = Session (...)
    # 2. import optitrack data according to session data
            # import_optitrack(session)
    # 3. import touch data according to session data
            # import_touches(session)

if __name__ == '__main__':
    setup()
    print "Database setup complete."

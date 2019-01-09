# coding=utf-8
import os.path

import csv_data_reader
import os, glob, datetime
from helper import get_config
from setup_helper import create_table, import_optitrack, import_touches, import_device, import_device_touches
from pat_model import Session

# All sessions that should be created for the db and ther video offsets.
sessions = ['0', '1', '2', '3', '4', '5', '6', '13', '14', '16']
# sessions = ['16']
input_filename_prefix = "data_setup/giant_session_"
input_video_dir = "data_logs/session_"
input_video_prefix = "session_"

def get_number_of_users(tracking_filename, touch_filename):
    user_ids = []
    data = csv_data_reader.get_data(tracking_filename)
    if 'id' in data:
        for item in data['id']:
            if item not in user_ids:
                user_ids.append(item)
    data = csv_data_reader.get_data(touch_filename)
    if 'userid' in data:
        for item in data['userid']:
            if item not in user_ids:
                user_ids.append(item)

    return 2 if len(user_ids) == 0 else len(user_ids)

def create_session(session_number):
    config = get_config(session_number)
    video_timestamps = {} if config is None else config.video_timestamps

    tracking_filename = input_filename_prefix + str(session_number) + "_users.csv"
    touch_filename = input_filename_prefix + str(session_number) + "_touch.csv"
    device_touch_filename = input_filename_prefix + str(session_number) + "_device_touch.csv"
    device_filename = input_filename_prefix + str(session_number) + "_device.csv"

    number_of_users = get_number_of_users(tracking_filename, touch_filename)
    print "number of users in session: ", number_of_users
    user_pitch_offsets = [0] * number_of_users
    session_time_offset = 0.0 if config is None else config.session_time_offset
    video_time_offset = 0.0 if config is None else config.video_offsets

    current_dir = os.getcwd()
    os.chdir("{}{}".format(input_video_dir, session_number))
    filenames = glob.glob(input_video_prefix + str(session_number) + "_video*.mp4")

    if len(filenames) < 1 and len(video_timestamps) < 1:
        print "ERROR: cannot find video files or the config variables for the session " + str(session_number) + "."
        assert False
    if len(filenames) > 0:
        print "video file for session " + str(session_number) + ":", filenames[0]
    video_filenames = ["{}{}/{}".format(input_video_dir, session_number, fn) for fn in filenames]

    os.chdir(current_dir)

    video_start_times = []
    date = None

    video_filenames = video_filenames if len(video_filenames) > 0 else video_timestamps.keys()
    for video_filename in video_filenames:
        possible_timestamps = [ts for fn, ts in video_timestamps.iteritems() if fn in video_filename]
        if len(possible_timestamps) > 0:
            video_start_time_unix = possible_timestamps[0]
        else:
            video_start_time_unix = float(video_filename.split("_")[-1][:-4])

        print "video start time unix: {0: .6f}".format(video_start_time_unix)
        date_time = datetime.datetime.fromtimestamp(video_start_time_unix).strftime('%Y-%m-%d %H:%M:%S.%f')
        print "video start time:", date_time
        date_split = date_time.split(' ')
        if date is None:
            date = date_split[0]
        video_start_times.append(date_split[1])

    return Session(
        session_num=session_number,
        level_num=1,
        data_dir=current_dir,
        optitrack_filename=tracking_filename,
        touch_filename=touch_filename,
        device_touch_filename=device_touch_filename,
        device_filename=device_filename,
        video_filenames=video_filenames,
        date=date,
        video_start_times=video_start_times,
        video_time_offset=video_time_offset,
        session_time_offset=session_time_offset,
        num_users=number_of_users,
        user_pitch_offsets=user_pitch_offsets
    )


def setup_divico():
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
    for session_num in sessions:
        session = create_session(session_num)
        print "---- "+session.optitrack_filename+" ----"

        import_optitrack(session)
        import_device(session)
        import_touches(session)
        import_device_touches(session)

if __name__ == '__main__':
    os.chdir("../")
    setup_divico()
    print "Database setup complete."

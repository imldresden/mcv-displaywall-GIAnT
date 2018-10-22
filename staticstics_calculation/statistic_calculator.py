# coding=utf-8
from StringIO import StringIO

import itertools

import os
from collections import OrderedDict

import global_values
from data_setup.db_setup import create_session
from helper import get_config, csvtime_to_float, calc_dist, map_wall_pixels_to_device_coordinates

# Set the working directory to the parent folder.
os.chdir("../")

# session_ids = ['0', '1', '2', '3', '4', '5', '6', '13', '14', '16']
session_ids = ['16']
user_ids = [1, 2]
user_mapping = {1: "blue", 2: "yellow"}
phases = [
    "Training Touch",
    "Training Pointing",
    "Guided Exploration",
    "Free Exploration",
]

statistics_csv_path = "staticstics_calculation/statistics_for_{}.csv".format("-".join(session_ids))
durations_csv_path = "staticstics_calculation/durations_for_{}.csv".format("-".join(session_ids))
distance_csv_paths = ["staticstics_calculation/positions_of_users_({})_for_{}.csv".format(p, "-".join(session_ids)) for p in phases]

# Create the bins for the distance between user/user and user/wall
distance_bins_user_user = [
    (0.00, 0.46),
    (0.46, 0.76),
    (0.76, 1.20),
    (1.20, 3.70)
]

distance_bins_user_wall = [
    (0.00, 0.80),
    (0.80, 1.60),
    (1.60, 2.40),
    (2.40, 3.70)
]

# Set all column headers for the statistics file.
session_keys = [
    "Session ID",
    "Phase",
    "Color",
]
statistic_keys = [
    "# Touched",
    "# Injected",
    "# All Input",
    "# Touched (DOWN)",
    "# Injected (DOWN)",
    "# All Input (DOWN)",
    "m Walked User (in m)",
    "m Walked Device (in m)",
    "AVG d User/Wall (in m)",
    "U/W 0.00m-0.80m (in %)",
    "U/W 0.80m-1.60m (in %)",
    "U/W 1.60m-2.40m (in %)",
    "U/W 2.40m-3.70m (in %)",
    "AVG d User/User (in m)",
    "U/U 0.00m-0.46m (in %)",
    "U/U 0.46m-0.76m (in %)",
    "U/U 0.76m-1.20m (in %)",
    "U/U 1.20m-3.70m (in %)",
    "AVG d Device/Wall (in m)",
    "D/W 0.00m-0.80m (in %)",
    "D/W 0.80m-1.60m (in %)",
    "D/W 1.60m-2.40m (in %)",
    "D/W 2.40m-3.70m (in %)",
    "AVG d Device/Device (in m)",
    "AVG d Device/Cursor (in m)",
    "Cursor hit Wall (in %)",
]
# Open the content for the statistics.
statistics_content = StringIO()
statistics_content.write('"{}"\n'.format('";"'.join(session_keys + statistic_keys)))

# Set all column headers for the durations file.
duration_keys = [
    "Session ID",
    "Session Duration (in sec)",
    "{} Duration (in sec)".format(phases[0]),
    "{} Duration (in sec)".format(phases[1]),
    "{} Duration (in sec)".format(phases[2]),
    "{} Duration (in sec)".format(phases[3]),
]
# Open the content for the durations.
durations_content = StringIO()
durations_content.write('"{}"\n'.format('";"'.join(duration_keys)))

user_session_distances = [OrderedDict([(sid, None) for sid in session_ids]) for _ in phases]

# Open the content for the positions.
distance_contents = []
for _ in phases:
    content = StringIO()
    msg = ""
    for session_id in session_ids:
        for user_id in user_ids:
            msg += "{}-{};".format(session_id, user_mapping[user_id])
    content.write(msg[:-1] + "\n")
    distance_contents.append(content)

# Look at each session.
for session_id in session_ids:
    session = create_session(session_id)
    session.load_from_db()

    config = get_config(session_id)
    users = session.users

    phase_durations = OrderedDict()
    # Look at each phase.
    for c, (phase, phase_timestamp) in enumerate(config.phase_timestamps.iteritems()):
        # Calculate the duration and add it to the dict.
        start = csvtime_to_float(session.date, phase_timestamp[0]) - session.start_time
        end = csvtime_to_float(session.date, phase_timestamp[1]) - session.start_time
        phase_durations[phase] = end - start

        # Save the user distances for further use.
        user_session_distances[c][session_id] = OrderedDict([(uid, [pos[1] for pos in users[uid].getHeadXZPosns(start, end)])
                                                             for uid in user_ids])

        # Get all values to calculate the statistics.
        touches = {uid: users[uid].getTouches(start, end)
                   for uid in user_ids}
        user_positions = {uid: users[uid].getHeadXZPosns(start, end)
                          for uid in user_ids}
        device_posns, device_cursor_posns, device_view_pts = {}, {}, {}
        for uid in user_ids:
            device_posns[uid] = []
            device_cursor_posns[uid] = []
            device_view_pts[uid] = []
            for de in users[uid].getDeviceEntries(start, end):
                device_posns[uid].append(de.spacePos)
                device_cursor_posns[uid].append(map_wall_pixels_to_device_coordinates(de.screenPos[0], de.screenPos[1]))
                device_view_pts[uid].append(de.viewPoint)

        number_combinations = len(list(itertools.combinations(user_ids, 2)))

        # Create new variable for the new statistics.
        number_touches, number_injections, number_touches_down, number_inections_down = {}, {}, {}, {}
        # Calculate the number of inputs from the users.
        for uid in user_ids:
            number_touches[uid] = len([t for t in touches[uid] if not t.injected])
            number_injections[uid] = len([t for t in touches[uid] if t.injected])
            number_touches_down[uid] = len([t for t in touches[uid] if t.type == "DOWN" and not t.injected])
            number_inections_down[uid] = len([t for t in touches[uid] if t.type == "DOWN" and t.injected])

        # Create new variable for the new statistics.
        meter_walked_user = {uid: 0 for uid in user_ids}
        distance_user_wall = {uid: 0 for uid in user_ids}
        distance_user_wall_bins = {uid: [0, 0, 0, 0] for uid in user_ids}
        distance_user_user = 0
        distance_user_user_bins = [0, 0, 0, 0]
        last_pos = {uid: (user_positions[uid][0] if len(user_positions[uid]) > 0 else 0) for uid in user_ids}
        # Calculate the statistics for the user itself.
        u_positions_length = min([len(user_positions.values()[i]) for i in range(len(user_positions))])
        for i in range(1, u_positions_length):
            # Calculate the distance between the users.
            distance = 0
            for pair in itertools.combinations(user_ids, 2):
                distance += calc_dist(user_positions[pair[0]][i], user_positions[pair[1]][i])
            distance /= number_combinations
            distance_user_user += distance

            # Count how often the users stand apart from each other.
            for j, (min_v, max_v) in enumerate(distance_bins_user_user):
                if min_v < distance <= max_v:
                    distance_user_user_bins[j] += 1
                    break

            for uid in user_ids:
                # Calculate the meters walked from each user.
                meter_walked_user[uid] += calc_dist(last_pos[uid], user_positions[uid][i])
                last_pos[uid] = user_positions[uid][i]
                # Calculate the distance between any given user and the wall.
                distance_user_wall[uid] += user_positions[uid][i][1]
                # Count how often the user was in given distances in front of the wall.
                for j, (min_v, max_v) in enumerate(distance_bins_user_wall):
                    if min_v < user_positions[uid][i][1] <= max_v:
                        distance_user_wall_bins[uid][j] += 1
                        break

        distance_user_user /= u_positions_length - 1
        distance_user_wall = {uid: v / (u_positions_length - 1) for uid, v in distance_user_wall.iteritems()}
        distance_user_wall_bins = {uid: [float(v) * 100 / (u_positions_length - 1) for v in vs] for uid, vs in distance_user_wall_bins.iteritems()}
        distance_user_user_bins = [float(v) * 100 / (u_positions_length - 1) for v in distance_user_user_bins]

        # Create new variable for the new statistics.
        meter_walked_device =  {uid: 0 for uid in user_ids}
        distance_device_device = 0
        distance_device_wall = {uid: 0 for uid in user_ids}
        distance_device_wall_bins = {uid: [0, 0, 0, 0] for uid in user_ids}
        distance_device_cursor = {uid: 0 for uid in user_ids}
        device_pointed_to_wall = {uid: 0 for uid in user_ids}
        last_pos = {uid: (device_posns[uid][0] if len(device_posns[uid]) > 0 else 0) for uid in user_ids}
        # Calculate the statistics for the devices.
        device_posns_length = min([len(device_posns.values()[i]) for i in range(len(device_posns))])
        for i in range(1, device_posns_length):
            # Calculate the distance between the devices of users.
            distance = 0
            for pair in itertools.combinations(user_ids, 2):
                pos1, pos2 = device_posns[pair[0]][i], device_posns[pair[1]][i]
                distance += calc_dist(
                    p1=(pos1[0], pos1[2]),
                    p2=(pos2[0], pos2[2])
                )
            distance /= number_combinations
            distance_device_device += distance

            for uid in user_ids:
                meter_walked_device[uid] += calc_dist(
                    p1=(last_pos[uid][0], last_pos[uid][2]),
                    p2=(device_posns[uid][i][0], device_posns[uid][i][2])
                )
                last_pos[uid] = device_posns[uid][i]
                # Calculate the distance between any given device of an user and the wall.
                distance_device_wall[uid] += device_posns[uid][i][2]
                # Calculate the distance between any given device of an user and its cursor on the wall.
                distance_device_cursor[uid] += calc_dist(device_posns[uid][i], device_cursor_posns[uid][i])
                # Calculte if a cursor was pointed on the wall or not.
                if (0 <= device_view_pts[uid][i][0] <= global_values.WALL_SIZE_M[0] and
                    0 <= device_view_pts[uid][i][1] <= global_values.WALL_SIZE_M[1]):
                    device_pointed_to_wall[uid] += 1
                # Count how often the device was in given distances in front of the wall.
                for j, (min_v, max_v) in enumerate(distance_bins_user_wall):
                    if min_v < device_posns[uid][i][2] <= max_v:
                        distance_device_wall_bins[uid][j] += 1
                        break

        distance_device_device /= device_posns_length - 1
        distance_device_wall = {uid: v / (device_posns_length - 1) for uid, v in distance_device_wall.iteritems()}
        distance_device_wall_bins = {uid: [float(v) * 100 / (device_posns_length - 1) for v in vs] for uid, vs in distance_device_wall_bins.iteritems()}
        distance_device_cursor = {uid: v / (device_posns_length - 1) for uid, v in distance_device_cursor.iteritems()}
        device_pointed_to_wall = {uid: float(v) * 100 / (device_posns_length - 1) for uid, v in device_pointed_to_wall.iteritems()}

        # Add for each user an own line in the csv.
        for user_id in user_ids:
            # Create the new line for the user in the csv.
            dur_line = "{session};{phase};{color};" \
                   "{touched};{injected};{input};" \
                   "{touched_down};{injected_down};{input_down};" \
                   "{walked_u:0.1f};{walked_d:0.1f};" \
                   "{u_w:0.3f};{u_w_0:04.1f};{u_w_1:04.1f};{u_w_2:04.1f};{u_w_3:04.1f};" \
                   "{u_u:0.3f};{u_u_0:04.1f};{u_u_1:04.1f};{u_u_2:04.1f};{u_u_3:04.1f};" \
                   "{d_w:0.3f};{d_w_0:04.1f};{d_w_1:04.1f};{d_w_2:04.1f};{d_w_3:04.1f};" \
                   "{d_d:0.3f};{d_c:0.3f};{c_hit:04.1f}\n".format(
                session=session_id,
                phase=phase,
                color=user_mapping[user_id],
                touched=number_touches[user_id],
                injected=number_injections[user_id],
                input=number_touches[user_id] + number_injections[user_id],
                touched_down=number_touches_down[user_id],
                injected_down=number_inections_down[user_id],
                input_down=number_touches_down[user_id] + number_inections_down[user_id],
                walked_u=meter_walked_user[user_id],
                walked_d=meter_walked_device[user_id],
                u_w=distance_user_wall[user_id],
                u_w_0=distance_user_wall_bins[user_id][0],
                u_w_1=distance_user_wall_bins[user_id][1],
                u_w_2=distance_user_wall_bins[user_id][2],
                u_w_3=distance_user_wall_bins[user_id][3],
                u_u=distance_user_user,
                u_u_0=distance_user_user_bins[0],
                u_u_1=distance_user_user_bins[1],
                u_u_2=distance_user_user_bins[2],
                u_u_3=distance_user_user_bins[3],
                d_w=distance_device_wall[user_id],
                d_w_0=distance_device_wall_bins[user_id][0],
                d_w_1=distance_device_wall_bins[user_id][1],
                d_w_2=distance_device_wall_bins[user_id][2],
                d_w_3=distance_device_wall_bins[user_id][3],
                d_d=distance_device_device,
                d_c=distance_device_cursor[user_id],
                c_hit=device_pointed_to_wall[user_id]
            ).replace('.', ',')
            statistics_content.write(dur_line)

    # Create the new line for the session in the csv.
    dur_line = "{session};{duration};{t_t_dur};{t_p_dur};{g_e_dur};{f_e_dur}\n".format(
        session=session_id,
        duration=session.duration,
        t_t_dur=phase_durations["Training Touch"],
        t_p_dur=phase_durations["Training Pointing"],
        g_e_dur=phase_durations["Guided Exploration"],
        f_e_dur=phase_durations["Free Exploration"],
    ).replace('.', ',')
    durations_content.write(dur_line)

# Look at each phase individually.
for c, session_distances in enumerate(user_session_distances):
    most_dist = float("-inf")
    # Calculate the longest number of positiions of an user in a phase.
    for user_distances in session_distances.itervalues():
        m_dist = max([len(l) for l in user_distances.itervalues()])
        most_dist = max([m_dist, most_dist])

    all_distances = [[] for _ in range(most_dist)]
    # Go through all positions of the user in a session in this current phase.
    for user_distances in session_distances.itervalues():
        # Go through all possible positions.
        for pos_i in range(most_dist):
            for uid in user_ids:
                all_distances[pos_i].append(user_distances[uid][pos_i] if pos_i < len(user_distances[uid]) else "")

    for distances in all_distances:
        distance_contents[c].write(";".join(["{}".format(d) for d in distances]) + "\n")

# Create a new file for the statistics and save all the content.
csv_file = open(statistics_csv_path, 'w')
csv_file.write(statistics_content.getvalue())
csv_file.close()

# Create a new file for the durations and save all the content.
csv_file = open(durations_csv_path, 'w')
csv_file.write(durations_content.getvalue())
csv_file.close()

# Create a new file for the positions and save all the content.
for c, content in enumerate(distance_contents):
    csv_file = open(distance_csv_paths[c], 'w')
    csv_file.write(content.getvalue())
    csv_file.close()
import pprint
import math
from datetime import datetime, timedelta

from csv_data_reader import get_data
from cStringIO import StringIO
from helper import map_kinect_to_device_coordinates, map_device_coordinates_to_wall_pixels, \
    mapping_kinect_to_giant_coordinates, map_wall_pixels_to_device_coordinates, get_config

input_folder_prefix = '../data_logs/session_'
input_filename_prefix = 'session_'
output_filename_prefix = 'giant_session_'
# session_ids = ['0', '1', '2', '3', '4', '5', '6', '13', '14', '16']
session_ids = ['6']

for session_id in session_ids:
    config = get_config(session_id)

    joint_type_body_to_device = "OKS_SPINE_MID" if config is None else config.joint_type_body_to_device
    joint_type_body_to_touch = "OKS_SPINE_SHOULDER" if config is None else config.joint_type_body_to_touch
    device_id_count_threshold = 5 if config is None else config.device_id_count_threshold
    max_time_delta_body_to_device = timedelta(milliseconds=150) if config is None else config.max_time_delta_body_to_device
    max_dist_delta_body_to_device = 0.6 if config is None else config.max_dist_delta_body_to_device
    max_time_delta_touch_to_inj = timedelta(milliseconds=150) if config is None else config.max_time_delta_touch_to_inj
    max_time_delta_inj_to_de = timedelta(milliseconds=2) if config is None else config.max_time_delta_inj_to_de
    max_time_delta_body_to_touch = timedelta(milliseconds=75) if config is None else config.max_time_delta_body_to_touch
    min_body_dist_to_wall = 0.7 if config is None else config.min_body_dist_to_wall
    arm_span = 0.8 if config is None else config.arm_span
    touch_user_dist_border = 1.5

    ignore_skeleton_ids = [] if config is None else config.ignore_skeleton_ids
    ignore_not_found_touch_ids = False if config is None else config.ignore_not_found_touch_ids

    # makes long kinect user id to short int.
    user_ids = {} if config is None else config.user_ids
    fake_ids = []
    def user_id_to_short(tracking_id):
        if tracking_id not in user_ids:
            device1 = device_ids_count['1']
            device2 = device_ids_count['3'] if '3' in device_ids_count else device_ids_count['2']

            tracked_device1, tracked_device2 = False, False
            # Look up which device is the tracking id corresponding with.
            if tracking_id in device1:
                # Only use the given device if the number of the count is greater than the threshold.
                if device1[tracking_id] >= device_id_count_threshold:
                    tracked_device1 = True
            if tracking_id in device2:
                # Only use the given device if the number of the count is greater than the threshold.
                if device2[tracking_id] >= device_id_count_threshold:
                    tracked_device2 = True

            # Have both devices a connection to this tracking id.
            if tracked_device1 and tracked_device2:
                if device1[tracking_id] > device2[tracking_id]:
                    user_ids[tracking_id] = 1
                else:
                    user_ids[tracking_id] = 2
            # Has none of the devices a connection to this tracking id.
            elif not tracked_device1 and not tracked_device2:
                fake_ids.append(tracking_id)
                user_ids[tracking_id] = 2 + len(fake_ids)
            else:
                if tracked_device1:
                    user_ids[tracking_id] = 1
                elif tracked_device2:
                    user_ids[tracking_id] = 2

        return user_ids[tracking_id]

    # -------------- USERS MOVEMENT DATA ----------------

    # header keys for data items
    key_time = 'time'
    key_day = 'day'
    key_user = 'skeleton_id'
    b_key_x = joint_type_body_to_device + '_x'
    b_key_y = joint_type_body_to_device + '_y'
    b_key_z = joint_type_body_to_device + '_z'
    key_tracking_state = joint_type_body_to_device + '_tracking-state'
    key_roll = "roll_in_rad"
    key_pitch = "pitch_in_rad"
    key_yaw = "yaw_in_rad"

    key_device_id = "device_id"
    d_key_x = 'space_pos_x_in_m'
    d_key_y = 'space_pos_y_in_m'
    d_key_z = 'space_pos_z_in_m'

    # Body Tracking Data
    body_filename = "{0}{1}/{2}{1}_body_tracking.csv".format(input_folder_prefix, session_id, input_filename_prefix)
    body_data = get_data(body_filename)

    # clean up data, 1) if tracking state not 2 (tracked) or 2) when body data within wall :|
    i = 0
    while i < len(body_data[key_tracking_state]):
        # if body_csv_data[key_tracking_state][i] != " 2" or \
    #                     float(body_csv_data[key_z][i]) > -1.7:
        if body_data[key_tracking_state][i] == " 0":
            body_data[key_time].pop(i)
            body_data[key_user].pop(i)
            body_data[b_key_x].pop(i)
            body_data[b_key_z].pop(i)
            body_data[key_tracking_state].pop(i)
        else:
            i += 1

    body_positions = [map_kinect_to_device_coordinates(float(body_data[b_key_x][i]), float(body_data[b_key_y][i]), float(body_data[b_key_z][i])) for i in range(len(body_data[b_key_x]))]
    body_times = [datetime.strptime("{} {}".format(d, t), '%Y-%m-%d %H:%M:%S.%f') for d, t in zip(body_data[key_day], body_data[key_time])]

    # Device Position Data for orientation of user
    device_position_filename = "{0}{1}/{2}{1}_device_position.csv".format(input_folder_prefix, session_id, input_filename_prefix)
    device_pos_data = get_data(device_position_filename)
    device_pos_times = [datetime.strptime("{} {}".format(d, t), '%Y-%m-%d %H:%M:%S.%f') for d, t in zip(device_pos_data[key_day], device_pos_data[key_time])]

    device_ids_count = {d.strip(): {} for d in device_pos_data[key_device_id]}
    # Map the user ids to the device ids.
    device_line_index = 0
    for i, b_time in enumerate(body_times):
        b_pos = [body_positions[i][0]] + [body_positions[i][2]]
        dli = None
        for j in range(device_line_index, len(device_pos_times)):
            # If the difference between the body time and the device time is to great (body time is greater) use the
            # next device time.
            if b_time - device_pos_times[j] > max_time_delta_body_to_device:
                continue
            # If the difference between the body time and the device time is to great (device time is greater) than use
            # the next body time.
            if b_time - device_pos_times[j] < -max_time_delta_body_to_device:
                break
            # Save the first device time in range to start at this point in the next loop.
            if dli is None:
                dli = j

            d_pos = [float(device_pos_data[v][j]) for v in [d_key_x, d_key_z]]
            # Check if the distance of the device and the body are in range.
            distance = sum((u - d) ** 2 for u, d in zip(b_pos, d_pos))
            if distance > max_dist_delta_body_to_device ** 2:
                continue

            u_id = body_data[key_user][i].strip()
            d_id = device_pos_data[key_device_id][j].strip()

            if u_id not in device_ids_count[d_id]:
                device_ids_count[d_id][u_id] = 0
            device_ids_count[d_id][u_id] += 1

        # If a new start index was found, save it for the next loop.
        if dli is not None:
            device_line_index = dli

    from collections import Counter
    pprint.pprint(Counter(device_pos_data["device_id"]))
    pprint.pprint({k: sum(v.values()) for k, v in device_ids_count.iteritems()})
    pprint.pprint(device_ids_count)

    # write to file
    new_filename = output_filename_prefix + str(session_id) + '_users.csv'
    try:
        f = open(new_filename, 'w')
        content = StringIO()
        # write header
        content.write('"timestamp","id","pos","rot"\n')
        # write content
        for i in range(len(body_data[key_time])):
            # If a skeleton id is the given list, ignore it.
            if body_data[key_user][i].strip() in ignore_skeleton_ids:
                continue

            orientation_at_current_time = ("0.0", "0.0", "0.0")
            # if body_csv_data[key_time][i] in exact_times_orientation:
            #     orientation_at_current_time = exact_times_orientation[body_csv_data[key_time][i]]
            x, y, z = mapping_kinect_to_giant_coordinates(
                float(body_data[b_key_x][i]),
                float(body_data[b_key_y][i]),
                float(body_data[b_key_z][i])
            )
            msg_str = '"%s","%s","(%f, %f, %f)","(%s, %s, %s)"\n' % \
                (body_data[key_time][i].strip(),
                 user_id_to_short(body_data[key_user][i].strip()),
                 # tracking is logged in kinect coordinates - here we convert to meters
                 # giant currently uses lower left as origin, x points left, y up, z into the wall
                 x, y, z,
                 orientation_at_current_time[0].strip(),
                 orientation_at_current_time[1].strip(),
                 orientation_at_current_time[2].strip())
            content.write(msg_str)
        f.write(content.getvalue())
        f.close()
    except IOError:
        print 'Error while writing users file.'


    with open('../data_logs/session_{}/session_{}_skeleton_id_mapping.txt'.format(session_id, session_id), 'w') as f:
        pprint.pprint(user_ids, f)

    # -------------- WALL TOUCH DATA ----------------
    del body_data, body_positions, body_times, f, content
    b_key_x = joint_type_body_to_touch + '_x'
    b_key_y = joint_type_body_to_touch + '_y'
    b_key_z = joint_type_body_to_touch + '_z'
    key_tracking_state = joint_type_body_to_touch + '_tracking-state'

    # Body Tracking Data
    body_data = get_data(body_filename)

    # clean up data, 1) if tracking state not 2 (tracked) or 2) when body data within wall :|
    i = 0
    while i < len(body_data[key_tracking_state]):
        # if body_csv_data[key_tracking_state][i] != " 2" or \
    #                     float(body_csv_data[key_z][i]) > -1.7:
        if body_data[key_tracking_state][i] == " 0":
            body_data[key_time].pop(i)
            body_data[key_user].pop(i)
            body_data[b_key_x].pop(i)
            body_data[b_key_z].pop(i)
            body_data[key_tracking_state].pop(i)
        else:
            i += 1

    key_time = 'time'
    touch_user = 'user_id_str'
    t_key_x = 'pos_x_in_px'
    t_key_y = 'pos_y_in_px'
    t_key_event_type = 'event_type_str'

    inj_key_x = 'pos_x_in_px'
    inj_key_y = 'pos_y_in_px'
    de_key_id = 'device_id'
    d_key_x_px = 'screen_pos_x_in_px'
    d_key_y_px = 'screen_pos_y_in_px'

    body_positions = [map_kinect_to_device_coordinates(float(body_data[b_key_x][i]), float(body_data[b_key_y][i]), float(body_data[b_key_z][i])) for i in range(len(body_data[b_key_x]))]
    body_positions_px = [list(map_device_coordinates_to_wall_pixels(p[0], p[1])) for p in body_positions]
    body_times = [datetime.strptime("{} {}".format(d, t), '%Y-%m-%d %H:%M:%S.%f') for d, t in zip(body_data[key_day], body_data[key_time])]

    touch_filename = "{0}{1}/{2}{1}_touch.csv".format(input_folder_prefix, session_id, input_filename_prefix)
    touch_data = get_data(touch_filename)
    touch_data[t_key_event_type] = [e.split('_')[1] for e in touch_data[t_key_event_type]]
    touch_times = [datetime.strptime("{} {}".format(d, t), '%Y-%m-%d %H:%M:%S.%f')for d, t in zip(touch_data[key_day], touch_data[key_time])]
    touch_injected = [False for _ in range(len(touch_times))]
    touch_positions_m = [map_wall_pixels_to_device_coordinates(float(touch_data[t_key_x][i]), float(touch_data[t_key_y][i])) for i in range(len(touch_data[t_key_x]))]

    device_injection_filename = "{0}{1}/{2}{1}_touch_injection.csv".format(input_folder_prefix, session_id, input_filename_prefix)
    injection_data = get_data(device_injection_filename)
    injection_times = [datetime.strptime("{} {}".format(d, t), '%Y-%m-%d %H:%M:%S.%f')for d, t in zip(injection_data[key_day], injection_data[key_time])]

    device_events_filename = "{0}{1}/{2}{1}_device_event.csv".format(input_folder_prefix, session_id, input_filename_prefix)
    device_events_data = get_data(device_events_filename)
    device_events_times = [datetime.strptime("{} {}".format(d, t), '%Y-%m-%d %H:%M:%S.%f') for d, t in zip(device_events_data[key_day], device_events_data[key_time])]

    zones_margin = 10
    horizontal_zones_to_ignore = [0, 1080, 2160, 3240]
    vertical_zones_to_ignore = [0, 1960, 3840, 5760, 7680]
    areas_not_to_ignore = [(3840 + zones_margin, 2160 - zones_margin, 5760 - zones_margin, 2160 + zones_margin)]

    for i, t_time in enumerate(touch_times):
        t_pos = [int(touch_data[v][i]) for v in [t_key_x, t_key_y]]

        # Check if the given position lies on the display boarders. If its the case, skip this value.
        skip = False
        for v_zones in vertical_zones_to_ignore:
            skip = skip or v_zones - zones_margin <= t_pos[0] <= v_zones + zones_margin
        for h_zones in horizontal_zones_to_ignore:
            skip = skip or h_zones - zones_margin <= t_pos[1] <= h_zones + zones_margin
        # Check if a area of the border should be ignored. If its the case don't skip this value.
        for i_area in areas_not_to_ignore:
            old_skip = skip
            skip = False if i_area[0] < t_pos[0] < i_area[2] and i_area[1] < t_pos[1] < i_area[3] else skip
            if old_skip and not skip:
                print "Ignored skip:", t_pos

        if skip:
            print "Skiped      :", t_pos
            touch_data[touch_user][i] = 'ignore'
            continue

    touch_mapping_count = 0
    # Mapping of some of the touch ids to the touch injection.
    inj_line_index, device_event_line_index, device_pos_line_index = 0, 0, 0
    for i, t_time in enumerate(touch_times):
        if touch_data[touch_user][i] == 'ignore':
            continue

        # If the touch was a MOTION, it's necessary to use the movement of the device itself.
        if touch_data[t_key_event_type][i].strip() == 'MOTION':
            device_id = None
            dpli = None
            for j in range(device_pos_line_index, len(device_pos_times)):
                # If the time difference is to great, look at the next injection time.
                if t_time > device_pos_times[j]:
                    continue
                # if the time difference is less than the given delta check the next touch event.
                if t_time - device_pos_times[j] < -max_time_delta_touch_to_inj:
                    break
                # Save the first injection index to be found.
                if dpli is None:
                    dpli = j

                # Check if both positions are the same.
                if not (int(touch_data[t_key_x][i]) == int(float(device_pos_data[d_key_x_px][j])) and
                        int(touch_data[t_key_y][i]) == int(float(device_pos_data[d_key_y_px][j]))):
                    continue

                device_id = str(int(device_pos_data[key_device_id][j]))
                break

            # Save the new starting point if one is available.
            if dpli is not None:
                device_pos_line_index = dpli

            # If a device id could be found save it.
            if device_id is not None:
                touch_data[touch_user][i] = device_id if device_id.strip() != '3' else '2'
                touch_injected[i] = True
                touch_mapping_count += 1
        # If any other touch was injection, this injection was directly created through an interaction on the device.
        else:
            ili = None
            for j in range(inj_line_index, len(injection_times)):
                # If the time difference is to great, look at the next injection time.
                if t_time - injection_times[j] > max_time_delta_touch_to_inj:
                    continue
                # Only look in the retrospective of the current time.
                if t_time - injection_times[j] < timedelta():
                    break
                # Save the first injection index to be found.
                if ili is None:
                    ili = j

                # Check if both positions of the touch and the injection events are equal.
                if not (touch_data[t_key_x][i] == injection_data[inj_key_x][j] and
                        touch_data[t_key_y][i] == injection_data[inj_key_y][j]):
                    continue

                device_id = None
                # Get the device id for this injection.
                deli = None
                for k in range(device_event_line_index, len(device_events_times)):
                    if injection_times[j] - device_events_times[k] > max_time_delta_inj_to_de:
                        continue
                    if injection_times[j] - device_events_times[k] < -max_time_delta_inj_to_de:
                        break
                    if deli is None:
                        deli = k

                    device_id = device_events_data[de_key_id][k]
                    break
                # Save the new starting point if one is available.
                if deli is not None:
                    device_event_line_index = deli

                # If none device id could be found check the next injection time.
                if device_id is None:
                    continue

                # Save the new touch device id.
                touch_data[touch_user][i] = device_id if device_id.strip() != '3' else '2'
                touch_injected[i] = True
                touch_mapping_count += 1
                break

            # Save the new starting point if one is available.
            if ili is not None:
                inj_line_index = ili

    # Mapping of all touch ids that are currently -1 to the possible kinect body that were in front of the touch.
    # Use a ball around the neck of the person to look if a touch lies inside this volume.
    body_line_index = 0
    for i, t_time in enumerate(touch_times):
        # Only check those touches that don't have an id yet.
        if touch_data[touch_user][i].strip() != '-1':
            continue

        t_pos = [int(touch_data[v][i]) for v in [t_key_x, t_key_y]] + [0]
        closest_id = ['', float('inf')]

        bli = None
        for j in range(body_line_index, len(body_times)):
            # If the time difference between the touch and the body time is greater than the given delta use the next body time.
            if t_time - body_times[j] > max_time_delta_body_to_touch:
                continue
            # If the time difference between the touch and the body time is lass than the given delta check the next touch event..
            if t_time - body_times[j] < -max_time_delta_body_to_touch:
                break
            # Save the first body index to be found.
            if bli is None:
                bli = j

            # Check if the z position of the body is in a given range.
            if body_positions[j][2] > min_body_dist_to_wall or body_positions[j][2] > arm_span:
                continue

            # Calculate the radius of the sectional plane of a sphere and the wall.
            radius = math.sqrt(arm_span ** 2 - body_positions[j][2] ** 2)
            radius = map_device_coordinates_to_wall_pixels(radius, radius)
            # Subtract the maximal height (in px) of the display wall.
            radius = radius[0], 3240 - radius[1]
            pos = body_positions_px[j]
            # Check if the touch was inside a rectangle given through the distance of the section plane from the center to the edges.
            if not (pos[0] - radius[0] < int(touch_data[t_key_x][i]) < pos[0] + radius[0] and
                    pos[1] - radius[1] < int(touch_data[t_key_y][i]) < pos[1] + radius[1]):
                continue

            b_pos = body_positions_px[j] + [body_positions[j][2] * 100]
            # Get the distance between the body and the touch and use it only if its the smaller one.
            distance = sum([(b - t) ** 2 for b, t in zip(b_pos, t_pos)])
            if distance < closest_id[1]:
                closest_id[0] = body_data[key_user][j].strip()
                closest_id[1] = distance

        # Save the new starting point if one is available.
        if bli is not None:
            body_line_index = bli

        # Save the found id if one was found at all and save it.
        if len(closest_id[0]) != 0:
            touch_mapping_count += 1
            touch_data[touch_user][i] = str(user_id_to_short(closest_id[0]))

    # Mapping of all touch ids that are currently -1 to the possible kinect body that were in front of the touch.
    # Calculate the distance between the touch and the persons. If a person is significat nearer use him.
    body_line_index = 0
    for i, t_time in enumerate(touch_times):
        # Only check those touches that don't have an id yet.
        if touch_data[touch_user][i].strip() != '-1':
            continue
        if touch_data[touch_user][i].strip() == 'ignore':
            continue

        t_pos = [int(touch_data[v][i]) for v in [t_key_x, t_key_y]] + [0]
        user_info = {}

        bli = None
        for j in range(body_line_index, len(body_times)):
            # If the time difference between the touch and the body time is greater than the given delta use the next body time.
            if t_time - body_times[j] > max_time_delta_body_to_touch:
                continue
            # If the time difference between the touch and the body time is lass than the given delta check the next touch event..
            if t_time - body_times[j] < -max_time_delta_body_to_touch:
                break
            # Save the first body index to be found.
            if bli is None:
                bli = j

            b_pos, t_pos_m = body_positions[j], touch_positions_m[i]
            distance = sum([(b - t) ** 2 for b, t in zip(b_pos, t_pos_m)])

            user_id = body_data[key_user][j].strip()
            if user_id not in user_info or user_info[user_id] > distance:
                user_info[user_id] = distance

        # Save the new starting point if one is available.
        if bli is not None:
            body_line_index = bli

        # Save the found id if one was found at all and save it.
        map_user_id = None
        if len(user_info) > 0:
            could_map = True
            # If only one user was found use him.
            if len(user_info) == 1:
                uid = str(user_id_to_short(user_info.keys()[0]))
                if user_info.values()[0] > touch_user_dist_border:
                    # TODO: only works for the two users 1 and 2 in DiViCo
                    map_user_id = "1" if uid == '2' else "2"
                else:
                    map_user_id = uid
            # If several users were found, check if the user were in the given distances from the touch.
            else:
                closest_id = None
                other_ids = {}
                for uid in sorted(user_info, key=lambda u: user_info[u]):
                    d = math.sqrt(user_info[uid])
                    if closest_id is None:
                        closest_id = [uid, d]
                    else:
                        other_ids[uid] = d

                if closest_id[1] < touch_user_dist_border and len([d for d in other_ids.values() if d < touch_user_dist_border]) == 0:
                    map_user_id = str(user_id_to_short(closest_id[0]))
                else:
                    could_map = False

            if could_map:
                touch_data[touch_user][i] = map_user_id
                touch_mapping_count += 1

    print "Could map {} from a total of {} touch inputs.".format(touch_mapping_count, len(touch_times))

    new_filename = output_filename_prefix + str(session_id) + '_touch.csv'
    try:
        f = open(new_filename, 'w')
        content = StringIO()
        # write header
        content.write('"timestamp","pos","userid","injected","type"\n')
        # write content
        for i in range(len(touch_data['time'])):
            if touch_data[touch_user][i].strip() == 'ignore':
                continue

            # If a skeleton id is the given list, ignore it.
            if touch_data[touch_user][i].strip() != '-1':
                if user_ids.keys()[user_ids.values().index(int(touch_data[touch_user][i].strip()))] in ignore_skeleton_ids:
                    continue
            # If the touch id is -1 and it should be ignored, continue the loop.
            elif ignore_not_found_touch_ids:
                continue

            user = touch_data[touch_user][i].strip()
            user = user if user != "-1" else "0"
            msg_str = '"%s","(%s, %s)","%s","%s","%s"\n' % \
                (touch_data[key_time][i].strip(), touch_data[t_key_x][i].strip(),
                 touch_data[t_key_y][i].strip(), user,
                 str(touch_injected[i]), touch_data[t_key_event_type][i].strip())
            content.write(msg_str)
        f.write(content.getvalue())
        f.close()
    except IOError:
        print 'Error while writing touch file.'

    del body_data, body_positions, body_times, touch_data, touch_times, touch_injected
    del device_events_data, device_events_times, f, content

    # -------------- USERS DEVICE DATA ----------------
    d_key_pitch = "pitch_in_rad"
    d_key_yaw = "yaw_in_rad"
    d_key_roll = "roll_in_rad"

    new_filename = output_filename_prefix + str(session_id) + '_device.csv'
    try:
        f = open(new_filename, 'w')
        content = StringIO()
        # write header
        content.write('"timestamp","userid","screenPos","spacePos","orientation"\n')
        # write content
        for i in range(len(device_pos_times)):
            user = device_pos_data[key_device_id][i].strip()
            user = user if user != "3" else "2"
            msg_str = '"%s","%s","(%s, %s)","(%s, %s, %s)","(%s, %s, %s)"\n' % (
                device_pos_data[key_time][i].strip(),
                user,
                device_pos_data[d_key_x_px][i].strip(), device_pos_data[d_key_y_px][i].strip(),
                device_pos_data[d_key_x][i].strip(), device_pos_data[d_key_y][i].strip(), device_pos_data[d_key_z][i].strip(),
                device_pos_data[d_key_pitch][i].strip(), device_pos_data[d_key_yaw][i].strip(), device_pos_data[d_key_roll][i].strip(),
            )
            content.write(msg_str)

        f.write(content.getvalue())
        f.close()
    except IOError:
        print 'Error while writing device file.'

    # -------------- DEVICE TOUCH DATA ----------------
    de_t_user = 'device_id'
    de_t_key_x = 'canvas_pos_x_in_px'
    de_t_key_y = 'canvas_pos_y_in_px'
    de_t_event_type = 'event_type'

    de_touch_filename = "{0}{1}/{2}{1}_device_event.csv".format(input_folder_prefix, session_id, input_filename_prefix)
    de_touch_data = get_data(de_touch_filename)
    de_touch_events = [list(reversed(e.split(' ')))[0] for e in de_touch_data[de_t_event_type]]

    new_filename = output_filename_prefix + str(session_id) + '_device_touch.csv'
    try:
        f = open(new_filename, 'w')
        content = StringIO()
        # write header
        content.write('"timestamp","userid","screenPos","type"\n')
        # write content
        for i in range(len(de_touch_data[key_time])):
            if de_touch_data[de_t_event_type][i].strip() not in ["CURSOR DOWN", "CURSOR MOTION", "CURSOR UP"]:
                continue

            user = de_touch_data[de_t_user][i].strip()
            user = user if user != "3" else "2"

            msg_str = '"%s","%s","(%s, %s)","%s"\n' % (
                de_touch_data[key_time][i].strip(),
                user,
                de_touch_data[de_t_key_x][i].strip(), de_touch_data[de_t_key_y][i].strip(),
                de_touch_events[i].strip()
            )
            content.write(msg_str)

        f.write(content.getvalue())
        f.close()
    except IOError:
        print 'Error while writing device touch file.'



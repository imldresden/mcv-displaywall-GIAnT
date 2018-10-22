# coding=utf-8
from enum import Enum
from math import sqrt

import itertools
from libavg import avg, gesture

import global_values
from helper import map_wall_pixels_to_device_coordinates, calc_dist
from panels import vis_panel


class Statistics(Enum):
    NumberTouched = 0
    NumberInjected = 1
    NumberInput = 2
    MeterWalkedUser = 3
    DistanceUserWall = 4
    DistanceUserUser = 5
    DistanceDeviceWall = 6
    DistanceDeviceDevice = 7
    ProcentualDistanceWall = 8
    DistanceDeviceCursor = 9
    ProcentualDevicePointedToWall = 10
    ProcentualDistanceUserUser = 11
    MeterWalkedDevice = 12

    @staticmethod
    def string_mapping(enum_value):
        return {
            Statistics.NumberTouched: "# Touched",
            Statistics.NumberInjected: "# Injected",
            Statistics.NumberInput: "# Input",
            Statistics.MeterWalkedUser: "m Walked User",
            Statistics.DistanceUserWall: "AVG d User/Wall",
            Statistics.DistanceUserUser: "AVG d User/User",
            Statistics.DistanceDeviceWall: "AVG d Device/Wall",
            Statistics.DistanceDeviceDevice: "AVG d Device/Device",
            Statistics.ProcentualDistanceWall: "0.00m-0.46m|0.46m-0.76m\n0.76m-1.20m|1.20m-3.70m",
            Statistics.DistanceDeviceCursor: "AVG d Device/Cursor",
            Statistics.ProcentualDevicePointedToWall: "% Cursor hit wall",
            Statistics.ProcentualDistanceUserUser: "0.00m-0.46m|0.46m-0.76m\n0.76m-1.20m|1.20m-3.70m",
            Statistics.MeterWalkedDevice: "m Walked Device",
        }[enum_value]


class StatisticsPanel(vis_panel.VisPanel):
    __PADDING = (3, 7)
    __STATISTICS = [
        Statistics.NumberTouched,
        Statistics.NumberInjected,
        Statistics.NumberInput,
        Statistics.MeterWalkedUser,
        Statistics.MeterWalkedDevice,
        Statistics.DistanceUserWall,
        Statistics.ProcentualDistanceWall,
        Statistics.DistanceUserUser,
        Statistics.ProcentualDistanceUserUser,
        Statistics.DistanceDeviceWall,
        Statistics.DistanceDeviceDevice,
        Statistics.DistanceDeviceCursor,
        Statistics.ProcentualDevicePointedToWall
    ]
    __USER_USER_BINS = [
        (0.00, 0.46),
        (0.46, 0.76),
        (0.76, 1.20),
        (1.20, 3.70)
    ]
    __USER_WALL_BINS = __USER_USER_BINS

    def __init__(self, session, vis_params, parent, statistics=None, user_ids=None, max_users=2, use_reload_overlay=False, **kwargs):
        """
        :param session: The session this panel should show.
        :type session: Session
        :param vis_params: The state/parameter for this whole application.
        :type vis_params: VisParams
        :param max_users: The number of user that should be maximal shown in this view.
        :type max_users: int
        :param statistics: Decides which statics should be shown in this view.
        :type statistics: list[Statistics]
        :param user_ids: The user ids that should be shown. If this is used, the max_users parameter is ignored.
        :type user_ids: list[int]
        :param use_reload_overlay: Should this statistics panel use a reload overlay to prevent that it will be reloaded each time
                                   the _update_time methods is called?
        :type use_reload_overlay: bool
        :param parent: The parent for this panel.
        :type parent: avg.DivNode
        :param kwargs: Other parameters that are used for the VisPanel.
        """
        super(StatisticsPanel, self).__init__("Statistics", vis_params, (0, 0), True, parent=parent, **kwargs)

        self.__duration = session.duration
        self.__use_reload_overlay = use_reload_overlay

        self.__users = session.users
        self.__user_ids = user_ids
        self.__max_users = max_users if self.__user_ids is None else len(self.__user_ids)
        self.__user_count = len(self.__users) if len(self.__users) < self.__max_users else self.__max_users
        self.__user_ids = self.__user_ids if self.__user_ids is not None else range(self.__user_count)

        self.__time_interval = [None, None]

        self._create_data_div()

        self.__column_count = self.__user_count + 2

        column_width = (self._data_div.width - (self.__column_count - 1) * self.__PADDING[0]) / self.__column_count
        self.__first_column_width = column_width * 1.5
        self.__column_width = ((self._data_div.width - self.__first_column_width) - (self.__column_count - 2) * self.__PADDING[0]) / (self.__column_count - 1.)
        # self.__column_width = (self._data_div.width - self.__PADDING[0] * (self.__column_count + 1)) / (self.__column_count + 1)

        self.__statistis = statistics if statistics is not None else self.__STATISTICS
        self.__header_words_nodes = None
        self.__statistics_words_nodes = None
        self.__words_nodes = None
        self.__create_word_nodes(vis_params)

        self.__reload = False
        self.__reload_overlay = None
        self.__reload_tap_recognizer = None
        self.__create_reload_overlay()

    def __create_word_nodes(self, vis_params):
        self.__header_words_nodes = []
        header, header_color = [], []
        for uid in self.__user_ids:
            header.append(global_values.USER_TO_COLOR[uid] if uid in global_values.USER_TO_COLOR else "U{}".format(uid))
            header_color.append(str(vis_params.get_user_color(uid)))
        header.append("Sum")
        header_color.append(global_values.COLOR_FOREGROUND)

        for i, text in enumerate(header):
            words_node = avg.WordsNode(
                parent=self._data_div,
                text=text,
                rawtextmode=True,
                fontsize=global_values.FONT_SIZE,
                color=header_color[i],
                alignment="left",
                size=(self.__column_width, global_values.FONT_SIZE),
                pos=(self.__first_column_width + self.__PADDING[0] + (self.__column_width + self.__PADDING[0]) * i,
                     self.__PADDING[1])
            )
            self.__header_words_nodes.append(words_node)

        self.__statistics_words_nodes = []
        self.__words_nodes = []
        for i, statistic in enumerate(self.__statistis):
            pos_y = self.__PADDING[1] * 3 + global_values.FONT_SIZE + (global_values.FONT_SIZE_SMALLER * 2 + 2 + self.__PADDING[1]) * i

            words_node = avg.WordsNode(
                parent=self._data_div,
                text=Statistics.string_mapping(statistic),
                rawtextmode=True,
                fontsize=global_values.FONT_SIZE_SMALLER,
                color=global_values.COLOR_FOREGROUND,
                alignment="left",
                linespacing=0,
                size=(self.__first_column_width, global_values.FONT_SIZE_SMALLER * 2 + 2),
                pos=(self.__PADDING[0], pos_y)
            )
            self.__statistics_words_nodes.append(words_node)

            self.__words_nodes.append([])
            for j in range(1, self.__column_count):
                words_node = avg.WordsNode(
                    parent=self._data_div,
                    rawtextmode=True,
                    fontsize=global_values.FONT_SIZE_SMALLER,
                    color=global_values.COLOR_FOREGROUND,
                    alignment="left",
                    linespacing=0,
                    size=(self.__column_width, global_values.FONT_SIZE_SMALLER * 2 + 2),
                    pos=(self.__first_column_width + self.__PADDING[0] + (self.__PADDING[0] + self.__column_width) * (j - 1),
                         pos_y)
                )
                self.__words_nodes[i].append(words_node)

    def __create_reload_overlay(self):
        if not self.__use_reload_overlay:
            return

        self.__reload_overlay = avg.DivNode(
            parent=self._data_div,
            size=self._data_div.size,
            active=False
        )
        avg.RectNode(
            parent=self.__reload_overlay,
            size=self._data_div.size,
            strokewidth=0,
            fillopacity=0.75,
            fillcolor=global_values.COLOR_DARK_GREY
        )
        text = avg.WordsNode(
            parent=self.__reload_overlay,
            text="Click to\nreload",
            fontsize=global_values.FONT_SIZE * 2,
            color=global_values.COLOR_FOREGROUND,
            alignment="center",
            rawtextmode=True,
            pos=(self._data_div.size[0] / 2, self._data_div.size[1] / 2)
        )
        text.pos = text.pos[0], text.pos[1] - 2 * global_values.FONT_SIZE + text.linespacing
        self.__reload_tap_recognizer = gesture.TapRecognizer(
            node=self.__reload_overlay,
            detectedHandler=self.__on_reload_overlay_tapped,
            maxDist=5,
            maxTime=500
        )

    def _update_time(self, vis_params=None):
        """
        Called when the visparam has changed.

        :type vis_params: VisParams
        """
        if vis_params is not None:
            # Check if something has changed.
            if self.__time_interval == vis_params.get_time_interval():
                return

            # Set the new interval.
            self.__time_interval = vis_params.get_time_interval()[:]

        # Check if the reload overlay should be displayed.
        if self.__reload_overlay is not None and not self.__reload:
            self.__reload_overlay.active = True
            return
        else:
            self.__reload_overlay.active = False
            self.__reload = False

        if self.__words_nodes is None:
            return

        # Get all values to calculate the statistics.
        touches = {uid: self.__users[uid].getTouches(self.__time_interval[0], self.__time_interval[1])
                   for uid in self.__user_ids}
        positions = {uid: self.__users[uid].getHeadXZPosns(self.__time_interval[0], self.__time_interval[1])
                     for uid in self.__user_ids}
        device_posns, device_cursor_posns, device_view_pts = {}, {}, {}
        for uid in self.__user_ids:
            device_posns[uid] = []
            device_cursor_posns[uid] = []
            device_view_pts[uid] = []
            for de in self.__users[uid].getDeviceEntries(self.__time_interval[0], self.__time_interval[1]):
                device_posns[uid].append(de.spacePos)
                device_cursor_posns[uid].append(map_wall_pixels_to_device_coordinates(de.screenPos[0], de.screenPos[1]))
                device_view_pts[uid].append(de.viewPoint)

        number_combinations = len(list(itertools.combinations(self.__user_ids, 2)))

        # Create new variable for the new statistics.
        number_touches, number_injections = {}, {}
        # Calculate the number of inputs from the users.
        for uid in self.__user_ids:
            number_touches[uid] = len([t for t in touches[uid] if not t.injected])
            number_injections[uid] = len([t for t in touches[uid] if t.injected])

        # Create new variable for the new statistics.
        meter_walked_user = {uid: 0 for uid in self.__user_ids}
        distance_user_wall = {uid: 0 for uid in self.__user_ids}
        distance_user_wall_bins = {uid: [0, 0, 0, 0] for uid in self.__user_ids}
        distance_user_user = 0
        distance_user_user_bins = [0, 0, 0, 0]
        last_pos = {uid: (positions[uid][0] if len(positions[uid]) > 0 else 0) for uid in self.__user_ids}
        # Calculate the statistics for the user itself.
        positions_length = min([len(positions.values()[i]) for i in range(len(positions))])
        for i in range(1, positions_length):
            # Calculate the distance between the users.
            distance = 0
            for pair in itertools.combinations(self.__user_ids, 2):
                distance += calc_dist(positions[pair[0]][i], positions[pair[1]][i])
            distance /= number_combinations
            distance_user_user += distance

            # Count how often the users stand apart from each other.
            for j, (min_v, max_v) in enumerate(self.__USER_USER_BINS):
                if min_v < distance <= max_v:
                    distance_user_user_bins[j] += 1
                    break

            for uid in self.__user_ids:
                # Calculate the meters walked from each user.
                meter_walked_user[uid] += calc_dist(last_pos[uid], positions[uid][i])
                last_pos[uid] = positions[uid][i]
                # Calculate the distance between any given user and the wall.
                distance_user_wall[uid] += positions[uid][i][1]
                # Count how often the user was in given distances in front of the wall.
                for j, (min_v, max_v) in enumerate(self.__USER_WALL_BINS):
                    if min_v < positions[uid][i][1] <= max_v:
                        distance_user_wall_bins[uid][j] += 1
                        break

        distance_user_user /= positions_length - 1
        distance_user_wall = {uid: v / (positions_length - 1) for uid, v in distance_user_wall.iteritems()}
        distance_user_wall_bins = {uid: [float(v) * 100 / (positions_length - 1) for v in vs] for uid, vs in distance_user_wall_bins.iteritems()}
        distance_user_user_bins = [float(v) * 100 / (positions_length - 1) for v in distance_user_user_bins]

        # Create new variable for the new statistics.
        meter_walked_device =  {uid: 0 for uid in self.__user_ids}
        distance_device_device = 0
        distance_device_wall = {uid: 0 for uid in self.__user_ids}
        distance_device_cursor = {uid: 0 for uid in self.__user_ids}
        device_pointed_to_wall = {uid: 0 for uid in self.__user_ids}
        last_pos = {uid: (device_posns[uid][0] if len(device_posns[uid]) > 0 else 0) for uid in self.__user_ids}
        # Calculate the statistics for the devices.
        device_posns_length = min([len(device_posns.values()[i]) for i in range(len(device_posns))])
        for i in range(1, device_posns_length):
            # Calculate the distance between the devices of users.
            distance = 0
            for pair in itertools.combinations(self.__user_ids, 2):
                pos1, pos2 = device_posns[pair[0]][i], device_posns[pair[1]][i]
                distance += calc_dist(
                    p1=(pos1[0], pos1[2]),
                    p2=(pos2[0], pos2[2])
                )
            distance /= number_combinations
            distance_device_device += distance

            for uid in self.__user_ids:
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

        distance_device_device /= device_posns_length - 1
        distance_device_wall = {uid: v / (device_posns_length - 1) for uid, v in distance_device_wall.iteritems()}
        distance_device_cursor = {uid: v / (device_posns_length - 1) for uid, v in distance_device_cursor.iteritems()}
        device_pointed_to_wall = {uid: float(v) * 100 / (device_posns_length - 1) for uid, v in device_pointed_to_wall.iteritems()}

        # Set all words nodes to the correct value.
        for i, key in enumerate(self.__statistis):
            if Statistics.NumberTouched is key:
                for j, uid in enumerate(self.__user_ids):
                    self.__words_nodes[i][j].text = "{0}".format(number_touches[uid])
                self.__words_nodes[i][-1].text = "{0}".format(sum(number_touches.values()))
            elif Statistics.NumberInjected is key:
                for j, uid in enumerate(self.__user_ids):
                    self.__words_nodes[i][j].text = "{0}".format(number_injections[uid])
                self.__words_nodes[i][-1].text = "{0}".format(sum(number_injections.values()))
            elif Statistics.NumberInput is key:
                for j, uid in enumerate(self.__user_ids):
                    self.__words_nodes[i][j].text = "{0}".format(number_touches[uid] + number_injections[uid])
                self.__words_nodes[i][-1].text = "{0}".format(sum(number_injections.values()) + sum(number_touches.values()))
            elif Statistics.MeterWalkedUser is key:
                for j, uid in enumerate(self.__user_ids):
                    self.__words_nodes[i][j].text = "{0:0.1f}m".format(meter_walked_user[uid])
                self.__words_nodes[i][-1].text = "{0:0.1f}m".format(sum(meter_walked_user.values()))
            elif Statistics.DistanceUserWall is key:
                for j, uid in enumerate(self.__user_ids):
                    self.__words_nodes[i][j].text = "{0:0.3f}m".format(distance_user_wall[uid])
                self.__words_nodes[i][-1].text = "{0:0.3f}m".format(sum(distance_user_wall.values()) / self.__user_count)
            elif Statistics.DistanceUserUser is key:
                self.__words_nodes[i][-1].text = "{0:0.3f}m".format(distance_user_user)
            elif Statistics.DistanceDeviceWall is key:
                for j, uid in enumerate(self.__user_ids):
                    self.__words_nodes[i][j].text = "{0:0.3f}m".format(distance_device_wall[uid])
                self.__words_nodes[i][-1].text = "{0:0.3f}m".format(sum(distance_device_wall.values()) / self.__user_count)
            elif Statistics.DistanceDeviceDevice is key:
                self.__words_nodes[i][-1].text = "{0:0.3f}m".format(distance_device_device)
            elif Statistics.ProcentualDistanceWall is key:
                for j, uid in enumerate(self.__user_ids):
                    self.__words_nodes[i][j].text = "{0:04.1f}%|{1:04.1f}%\n{2:04.1f}%|{3:04.1f}%".format(
                        distance_user_wall_bins[uid][0], distance_user_wall_bins[uid][1], distance_user_wall_bins[uid][2], distance_user_wall_bins[uid][3]
                    )
                s_d_from_wall = [sum([distance_user_wall_bins[uid][k] for uid in self.__user_ids]) / self.__user_count for k in range(4)]
                self.__words_nodes[i][-1].text = "{0:04.1f}%|{1:04.1f}%\n{2:04.1f}%|{3:04.1f}%".format(
                    s_d_from_wall[0], s_d_from_wall[1], s_d_from_wall[2], s_d_from_wall[3]
                )
            elif Statistics.DistanceDeviceCursor is key:
                for j, uid in enumerate(self.__user_ids):
                    self.__words_nodes[i][j].text = "{0:0.3f}m".format(distance_device_cursor[uid])
                self.__words_nodes[i][-1].text = "{0:0.3f}m".format(sum(distance_device_cursor.values()) / self.__user_count)
            elif Statistics.ProcentualDevicePointedToWall is key:
                for j, uid in enumerate(self.__user_ids):
                    self.__words_nodes[i][j].text = "{0:04.1f}%".format(device_pointed_to_wall[uid])
                self.__words_nodes[i][-1].text = "{0:04.1f}%".format(sum(device_pointed_to_wall.values()) / self.__user_count)
            elif Statistics.ProcentualDistanceUserUser is key:
                self.__words_nodes[i][-1].text = "{0:04.1f}%|{1:04.1f}%\n{2:04.1f}%|{3:04.1f}%".format(
                    distance_user_user_bins[0], distance_user_user_bins[1], distance_user_user_bins[2], distance_user_user_bins[3]
                )
            elif Statistics.MeterWalkedDevice is key:
                for j, uid in enumerate(self.__user_ids):
                    self.__words_nodes[i][j].text = "{0:0.1f}m".format(meter_walked_device[uid])
                self.__words_nodes[i][-1].text = "{0:0.1f}m".format(sum(meter_walked_device.values()))

    def __on_reload_overlay_tapped(self):
        """
        Called if the reload overlay was tapped.
        """
        self.__reload = True
        self._update_time()

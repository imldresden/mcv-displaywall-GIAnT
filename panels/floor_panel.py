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

import math

import datetime

import helper
import pat_model
import global_values
import vis_panel
import vis_params
from libavg import avg

from helper import map_value


class FloorPanel(vis_panel.VisPanel):
    __VERTICAL_POS_RANGE = (-0.5, 3.5)
    __HORIZONTAL_POS_RANGE = pat_model.pos_range[0][0], pat_model.pos_range[1][0]

    __FROM_RANGE_MIN = __HORIZONTAL_POS_RANGE[0], __VERTICAL_POS_RANGE[0]
    __FROM_RANGE_MAX = __HORIZONTAL_POS_RANGE[1], __VERTICAL_POS_RANGE[1]

    def __init__(self, session, vis_params, parent, mode="user", use_heatmap=True, label=None,
                 **kwargs):
        """
        :param session: The session this panel is based on.
        :type session: Session
        :param vis_params:
        :type vis_params:
        :param mode: The mode that will be used for this panel. Either "user" for user data or "device" for device data.
        :type mode: str
        :param label: This can be set if a custom label for this view should be given.
        :type label: str
        :param parent: The parent of this Panel.
        :type parent: avg.DivNode
        :param kwargs: Other parameters for a VisPanel object.
        """
        pos_range = pat_model.pos_range
        view_extent = avg.Point2D(pos_range[1][0] - pos_range[0][0], 3.0)
        aspect = view_extent.y/view_extent.x

        label = label or "Floor {}".format(mode)
        super(FloorPanel, self).__init__(label, vis_params, (60, 25), True, aspect, parent=parent, **kwargs)

        self.__session_start_time = session.start_time
        self.__session_time_offset = session.time_offset
        self.__users = session.users
        self.__mode = mode
        self.__use_heatmap = use_heatmap

        self._create_x_axis(
            data_range=(pos_range[0][0], pos_range[1][0]),
            unit="m",
            top_axis=True
        )
        self._create_y_axis(
            data_range=self.__VERTICAL_POS_RANGE,
            tick_positions=[0,1,2,3],
            unit="m",
            hide_rims=True
        )
        self.__create_wall_rect()

        self._create_data_div()
        self.__user_nodes = []

        self.__user_visibility = [True for _ in range(len(self.__users))]
        self.__heatmap_nodes = []
        self.__line_movement_nodes = []
        for user in self.__users:
            color = str(vis_params.get_user_color(user.getUserID()))
            node = heatmap.HeatMapNode(
                size=self._data_div.size,
                viewportrangemin=(pos_range[0][0], self.__VERTICAL_POS_RANGE[0]),
                viewportrangemax=(pos_range[1][0], self.__VERTICAL_POS_RANGE[1]),
                mapsize=(50,25),
                valuerangemin=0,
                valuerangemax=6,
                colormap=(color, color),
                opacitymap=(0,1),
                blendmode=global_values.BLEND_MODE,
                parent=self._data_div
            )
            node.setEffect(avg.BlurFXNode(radius=1.2))
            self.__heatmap_nodes.append(node)
            # Create an empty poly line node.
            line_node = avg.PolyLineNode(
                parent=self._data_div,
                color=color,
                strokewidth=2,
                opacity=0.45
            )
            self.__line_movement_nodes.append(line_node)

        self.__time_interval = [None, None]
        self.__timestamp_words_node = avg.WordsNode(
            parent=self._data_div,
            color=global_values.COLOR_FOREGROUND,
            rawtextmode=True,
            alignment="right",
            fontsize=global_values.FONT_SIZE / 2,
            pos=(self._data_div.width - 3, 3)
        )

    @property
    def use_heatmap(self):
        return self.__use_heatmap

    @use_heatmap.setter
    def use_heatmap(self, value):
        self.__use_heatmap = value

        for heatmap in self.__heatmap_nodes:
            heatmap.active = self.__use_heatmap
            if self.__use_heatmap:
                self.__show_user_heatmap(self.__time_interval)

    def _update_time(self, vis_params):
        self.__show_users(vis_params.highlight_time)

        user_visibility = [vis_params.get_user_visible(i) for i in range(len(self.__users))]
        # Check if something has changed.
        if self.__time_interval == vis_params.get_time_interval() and self.__user_visibility == user_visibility:
            return

        # Set the new interval.
        self.__time_interval = vis_params.get_time_interval()[:]
        # Set the new visibility of the user.
        self.__user_visibility = user_visibility

        self.__show_user_heatmap(vis_params.get_time_interval())
        self.__show_user_movement_lines(vis_params.get_time_interval())

    def __show_users(self, time):
        set_timestamp = True

        helper.unlink_node_list(self.__user_nodes)
        self.__user_nodes = []

        for i, user in enumerate(self.__users):
            if not self._vis_params.get_user_visible(i):
                continue
            if self.__mode == "user" and user.headInfoCount == 0 or self.__mode == "device" and user.deviceEntryInfoCount == 0:
                continue

            if self.__mode == "user":
                pos = user.getHeadPos(time)
                viewpt = (self._x_axis.value_to_pixel(user.getWallViewpoint(time).x),
                          self._y_axis.value_to_pixel(0))
                if set_timestamp:
                    head_data = user.getHeadData(time)
                    self.__timestamp_words_node.text = "{}\n{}".format(
                        datetime.datetime.fromtimestamp(head_data.time).strftime("%H:%M:%S.%f"),
                        helper.format_time(head_data.time - self.__session_start_time)
                    )
                    set_timestamp = False
            elif self.__mode == "device":
                pos = user.getDeviceEntry(time).spacePos
                viewpt = (self._x_axis.value_to_pixel(user.getDeviceWallViewpoint(time).x),
                          self._y_axis.value_to_pixel(0))
                if set_timestamp:
                    device_entry = user.getDeviceEntry(time)
                    self.__timestamp_words_node.text = "{}\n{}".format(
                        datetime.datetime.fromtimestamp(device_entry.time).strftime("%H:%M:%S.%f"),
                        helper.format_time(device_entry.time - self.__session_start_time)
                    )
                    set_timestamp = False
            else:
                return

            pixel_pos = avg.Point2D(self._x_axis.value_to_pixel(pos[0]), self._y_axis.value_to_pixel(pos[2]))
            node = UserNode(user.getUserID(), pos=pixel_pos, viewpt=viewpt, parent=self._data_div)
            self.__user_nodes.append(node)

    def __show_user_heatmap(self, time_interval):
        if self.__mode != "user" and self.__mode != "device":
            return

        val_max = 6 * ((time_interval[1] - time_interval[0]) / 60.)
        for i, user in enumerate(self.__users):
            if not self.__use_heatmap:
                self.__heatmap_nodes[i].active = False
                continue

            self.__heatmap_nodes[i].valuerangemax = val_max
            if self._vis_params.get_user_visible(i):
                if self.__mode == "user":
                    pos_data = user.getHeadXZPosns(time_interval[0], time_interval[1])
                elif self.__mode == "device":
                    pos_data = user.getDeviceXZSpacePosns(time_interval[0], time_interval[1])
                else:
                    continue

                head_posns = pos_data
                self.__heatmap_nodes[i].setPosns(head_posns)
            else:
                self.__heatmap_nodes[i].setPosns([])

    def __show_user_movement_lines(self, time_interval):
        """
        Updates the poly line nodes associated to any given user.

        :param time_interval: The time interval the poly line node should show.
        :type time_interval: tuple
        """
        if self.__mode != "user" and self.__mode != "device":
            return

        for i, user in enumerate(self.__users):
            # Set the new values for the polyline node, if the user should be shown.
            if self._vis_params.get_user_visible(i):
                if self.__mode == "user":
                    pos_data = user.getHeadXZPosnsMapped(time_interval[0], time_interval[1], self.__FROM_RANGE_MIN, self.__FROM_RANGE_MAX, (0, 0), self._data_div.size)
                elif self.__mode == "device":
                    pos_data = user.getDeviceXZSpacePosnsMapped(time_interval[0], time_interval[1], self.__FROM_RANGE_MIN, self.__FROM_RANGE_MAX, (0, 0), self._data_div.size)
                else:
                    continue

                self.__line_movement_nodes[i].pos = pos_data
            else:
                self.__line_movement_nodes[i].pos = []

    def __create_wall_rect(self):
        x_min = self._x_axis.value_to_pixel(0)
        x_max = self._x_axis.value_to_pixel(pat_model.wall_width)
        y_max = self._y_axis.value_to_pixel(0)

        avg.RectNode(pos=(x_min, y_max-16), size=(x_max - x_min, 16), fillcolor=global_values.COLOR_DARK_GREY,
                fillopacity=1, parent=self._data_div)
        label_pos = (x_min + (x_max-x_min)/2, y_max-18)
        avg.WordsNode(pos=label_pos, text="WALL", fontsize=14, alignment="center",
                parent=self._data_div)


class UserNode(avg.DivNode):

    def __init__(self, userid, pos, viewpt, parent, **kwargs):
        super(UserNode, self).__init__(**kwargs)
        self.registerInstance(self, parent)

        color = vis_params.VisParams.get_user_color(userid)

        end_pos = avg.Point2D(viewpt)
        if (end_pos-pos).getNorm() > 200:
            dir = (end_pos-pos).getNormalized()
            end_pos = pos + dir*200
        avg.LineNode(
            pos1=pos,
            pos2=end_pos,
            color=color,
            parent=self,
            strokewidth=2
        )
        avg.CircleNode(
            pos=pos,
            r=6,
            fillopacity=1,
            color=color,
            fillcolor="000000",
            parent=self
        )
        avg.WordsNode(
            parent=self,
            pos=(pos[0], pos[1] + 6 + 2),
            fontsize=11,
            color=color,
            rawtextmode=True,
            text=str(userid),
            alignment='center'
        )

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
import copy

import datetime


import helper
import pat_model
import global_values
import vis_panel
from libavg import avg, player, gesture

player.loadPlugin("plots")


class MovementPanel(vis_panel.VisPanel):

    PIXELS_PER_SAMPLE = 4
    MAX_SMOOTHNESS = 500

    def __init__(self, session, vis_params, is_dist_view, parent, show_timestamp_lines=False, label=None, **kwargs):
        label = label or "Movement Timeline"
        super(MovementPanel, self).__init__(label, vis_params, (60, 25), True, parent=parent, **kwargs)

        self.__duration = session.duration
        self.__session_start_time = session.start_time
        self.__users = session.users
        self.__is_dist_view = is_dist_view
        self.__show_timestamp_lines = show_timestamp_lines
        self.__time_interval = [None, None]

        self.__user_lines = []
        
        max_width = 1 if self.__is_dist_view else (min(self.width, self.height) / 12)
        for userid in range(session.num_users):
            color = vis_params.get_user_color(userid)
            self.__user_lines.append(plots.VWLineNode(
                color=color,
                maxwidth=max_width,
                useopacity=not(is_dist_view),
                blendmode=global_values.BLEND_MODE,
                parent=self._data_div
            )
            )
            self.__user_lines[-1].setHighlightColor(avg.Color(global_values.VM_LINE_HIGHLIGHT_COLOR))

        if self.__is_dist_view:
            self._create_y_axis(
                data_range=[0, 3.5],
                tick_positions=[i for i in range(1, 4)],
                unit="m",
                hide_rims=True,
                label_offset=-2,
                inverted=True
            )
        else:
            self._create_y_axis(
                data_range=(pat_model.pos_range[0][0], pat_model.pos_range[1][0]),
                unit="m",
                hide_rims=True,
                label_offset=15,
                inverted=True
            )
            
        self._create_x_axis(
            data_range=[0, session.duration],
            unit="s"
        )
        self.__create_wall_rect()
        self._create_data_div()

        self.__phase_lines = {}
        self.__create_phase_lines(session)

        self.__time_factor = self._data_div.width / vis_params.get_time_duration()

        self.__highlight_line = avg.LineNode(
            color=global_values.COLOR_SECONDARY,
            pos1=(0, 0),
            pos2=(0, self._data_div.height),
            active=False,
            parent=self._data_div
        )
        self.__highlight_words_node = avg.WordsNode(
            parent=self._data_div,
            color=global_values.COLOR_FOREGROUND,
            rawtextmode=True,
            alignment="left",
            fontsize=global_values.FONT_SIZE / 2,
            active=False
        )
        self.__hover_id = self._data_div.subscribe(avg.Node.CURSOR_MOTION, self.__on_hover)

        self.__enable_time = True
        vis_params.subscribe(vis_params.IS_PLAYING, self.__on_play_pause)

        self._data_div.subscribe(avg.Node.MOUSE_WHEEL, self.__on_mouse_wheel)
        self.__drag_recognizer = gesture.DragRecognizer(
                eventNode=self,
                detectedHandler=self.__on_drag_start,
                moveHandler=self.__on_drag,
                upHandler=self.__on_drag
                )

    def __create_phase_lines(self, session):
        """
        Create lines for the different phases in the session. Green ones for the start of a phase and red ones for the
        end.

        :param session: The session this phase lines should represent.
        :type session: Session
        """
        if not self.__show_timestamp_lines:
            return

        config = helper.get_config(session.session_num)
        if config is None:
            return

        # Get all the times of all phases and creates a line for each one.
        for start, end in config.phase_timestamps.itervalues():
            start = helper.csvtime_to_float(session.date, start) - session.start_time
            end = helper.csvtime_to_float(session.date, end) - session.start_time

            for time, color in [(start, global_values.COLOR_PHASE_GREEN), (end, global_values.COLOR_PHASE_RED)]:
                line_node = avg.LineNode(
                    color=color,
                    pos1=(0, 2),
                    pos2=(0, self._data_div.height - 2),
                    strokewidth=2,
                    opacity=0.8,
                    active=False,
                    parent=self._data_div
                )
                self.__phase_lines[time] = line_node

    def _update_time(self, vis_params):
        # update position of pinned highlight line and highlight line marker
        highlight_xpos = self.__time_to_xpos(self._vis_params.highlight_time)
        if highlight_xpos > self.width or highlight_xpos < 0:
            self.__highlight_line.active = False
            self.__highlight_words_node.active = False
        else:
            self.__highlight_line.active = True
            self.__highlight_line.pos1 = (highlight_xpos, self.__highlight_line.pos1[1])
            self.__highlight_line.pos2 = (highlight_xpos, self.__highlight_line.pos2[1])
            self.__highlight_words_node.active = True
            self.__highlight_words_node.text = "{}\n{}".format(
                datetime.datetime.fromtimestamp(self.__session_start_time + self._vis_params.highlight_time).strftime("%H:%M:%S.%f"),
                helper.format_time(self._vis_params.highlight_time)
            )
            self.__highlight_words_node.pos = highlight_xpos + 3, self.__highlight_line.pos1[1] + 3

        for i, user_line in enumerate(self.__user_lines):
            user_line.active = vis_params.get_user_visible(i)

        # Check if something has changed.
        if self.__time_interval == vis_params.get_time_interval():
            return

        # Set the new interval.
        self.__time_interval = vis_params.get_time_interval()[:]

        self.__time_min = self.__time_interval[0]
        self.__time_factor = self._data_div.width / vis_params.get_time_duration()
        self.__create_lines(vis_params)

        self._x_axis.hide_rims = not(math.fabs(vis_params.get_time_duration() - self.__duration) < 0.0001)
        self._x_axis.update(self.__time_interval[0], self.__time_interval[1])
        self._update_grid()

        # Update the phase lines.
        for time, line in self.__phase_lines.iteritems():
            if not self.__time_interval[0] < time < self.__time_interval[1]:
                line.active = False
                continue

            pos_x = self.__time_to_xpos(time)
            line.active = True
            line.pos1 = (pos_x, line.pos1[1])
            line.pos2 = (pos_x, line.pos2[1])

    def __on_play_pause(self, playing):
        self.__enable_time = not playing

    def __on_mouse_wheel(self, event):
        if self.__enable_time:
            rel_pos = self._data_div.getRelPos(event.pos)
            pos_fraction = rel_pos[0]/self._data_div.width
            if event.motion.y > 0:
                self._vis_params.zoom_in_at(pos_fraction)
            else:
                self._vis_params.zoom_out_at(pos_fraction)

    def __create_lines(self, vis_params):
        time_start = self.__xpos_to_time(0)
        time_end = self.__xpos_to_time(self._data_div.width)
        smoothness = self.__calc_smoothness(vis_params.get_smoothness_factor(), time_end-time_start)

        pos_range = list(copy.deepcopy(pat_model.pos_range))
        if self.__is_dist_view:
            pos_range[0][2] = 0 if self._y_axis.inverted else 3.5
            pos_range[1][2] = 3.5 if self._y_axis.inverted else 0
        x_extent = float(pos_range[1][0] - pos_range[0][0])
        y_extent = float(pos_range[1][2] - pos_range[0][2])
        vis_height = self._data_div.height
        for i, user in enumerate(self.__users):
            if user.headInfoCount == 0:
                continue

            if vis_params.get_user_visible(i):
                points = []
                dists = []
                for cur_sample_x in range(0, int(self._data_div.width), self.PIXELS_PER_SAMPLE):
                    cur_time = self.__xpos_to_time(cur_sample_x)

                    head_position_averaged = user.getHeadPosAvg(cur_time, smoothness)

                    norm_x = (head_position_averaged[0] - pos_range[0][0]) / x_extent
                    norm_z = (head_position_averaged[2] - pos_range[0][2]) / y_extent

                    if self.__is_dist_view:
                        vis_y = (1 - norm_z) * vis_height
                        dists.append(2)
                    else:
                        vis_y = (1 - norm_x) * vis_height
                        dists.append(norm_z)
                    points.append((cur_sample_x, vis_y))
                userline = self.__user_lines[i]
                userline.setValues(points, dists)
                touches = user.getTouches(time_start, time_end)
                touches_x = [self.__time_to_xpos(touch.time) for touch in touches]
                touches_width = [touch.duration*self.__time_factor  for touch in touches]
                userline.setHighlights(touches_x, touches_width)

    def __create_wall_rect(self):
        if self.__is_dist_view:
            pos = avg.Point2D(0.5, self._data_div.height-16.5)
            size = avg.Point2D(50, 16)
            avg.RectNode(pos=pos, size=size, fillcolor=global_values.COLOR_DARK_GREY, fillopacity=1, parent=self)
            avg.WordsNode(pos=pos+(25,0), text="WALL", fontsize=12, alignment="center", parent=self)
        else:
            y_min = self._y_axis.value_to_pixel(pat_model.wall_width)
            y_max = self._y_axis.value_to_pixel(0)
            pos = avg.Point2D(40.5, y_min+0.5)
            size = avg.Point2D(16, y_max-y_min)
            avg.RectNode(pos=pos, size=size, fillcolor=global_values.COLOR_DARK_GREY, fillopacity=1, parent=self)
            avg.WordsNode(pos=(31,(y_max-y_min)/2+15), angle=-math.pi/2, text="WALL", fontsize=12, alignment="center",
                    parent=self)

    def __on_hover(self, event=None):
        """
        Moves the highlight line along the vertical mouse position.
        """
        if self.__enable_time:
            rel_pos = self._data_div.getRelPos(event.pos)
            self._vis_params.highlight_time = self.__xpos_to_time(rel_pos.x)
            self._vis_params.notify()

    def __on_drag_start(self):
        self.__drag_start_interval = self._vis_params.get_time_interval()

    def __on_drag(self, offset):
        time_change = offset.x/self.__time_factor
        start = self.__drag_start_interval[0]
        end = self.__drag_start_interval[1]
        if start - time_change < 0:
            time_change = start
        if end - time_change > self.__duration:
            time_change = end - self.__duration
        self._vis_params.set_time_interval((start-time_change, end-time_change))

    def __xpos_to_time(self, x):
        return x / self.__time_factor + self._vis_params.get_time_interval()[0]

    def __time_to_xpos(self, t):
        return (float(t)-self._vis_params.get_time_interval()[0]) * self.__time_factor

    def __calc_smoothness(self, smoothness_factor, time_range):
        smoothness = int((time_range / self._vis_params.get_time_interval()[1]) * self.MAX_SMOOTHNESS * smoothness_factor)
        if smoothness < 1:
            smoothness = 1
        return smoothness


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
from libavg import widget, avg
import custom_slider
import helper
import global_values


class OptionsPanel(avg.DivNode):
    def __init__(self, vis_params, session, parent, **kwargs):
        super(OptionsPanel, self).__init__(**kwargs)
        self.registerInstance(self, parent)

        self.__vis_params = vis_params
        self.parent_div = parent        # parent node
        self.__duration = session.duration
        self.__time_interval = [None, None]

        # rect for coloured border and background
        self.background_rect = avg.RectNode(
            pos=(0, 0),
            size=self.size,
            parent=self,
            strokewidth=1,
            fillopacity=1,
            color=global_values.COLOR_BACKGROUND,
            fillcolor=global_values.COLOR_BACKGROUND
        )

        """play/pause button"""
        icon_size = (15, 15)
        button_size = (30, 30)
        # rect for play button border
        self.play_rect = avg.RectNode(
            pos=(6, 22),
            size=button_size,
            parent=self,
            strokewidth=1,
            fillopacity=0,
            color=global_values.COLOR_FOREGROUND,
            sensitive=False
        )
        # play button
        icon_h_size = (icon_size[0]/2, icon_size[1]/2)
        self.play_button = widget.ToggleButton(
            uncheckedUpNode=avg.ImageNode(href="images/play.png", pos=icon_h_size, size=icon_size),
            uncheckedDownNode=avg.ImageNode(href="images/play.png", pos=icon_h_size, size=icon_size),
            checkedUpNode=avg.ImageNode(href="images/pause.png", pos=icon_h_size, size=icon_size),
            checkedDownNode=avg.ImageNode(href="images/pause.png", pos=icon_h_size, size=icon_size),
            pos=self.play_rect.pos,
            size=button_size,
            parent=self
        )
        self.play_button.subscribe(widget.CheckBox.TOGGLED, lambda checked: self.__play_pause(checked))

        self.__init_time_bar(self.__duration, vis_params.get_time_interval())
        self.__phase_lines = {}
        self.__create_phase_lines(session)
#        self.__init_smoothness_slider()

        self.__vis_params.subscribe(self.__vis_params.CHANGED, self.__update_time)
        self.__vis_params.subscribe(self.__vis_params.IS_PLAYING, self.__on_play_pause)

    def __init_time_bar(self, duration, interval):
        pos = avg.Point2D(58, 0)
        size = avg.Point2D(self.width - pos.x - 10, 60)
        self.__time_bar = avg.DivNode(pos=pos, size=size,  parent=self)

        avg.WordsNode(
            pos=(0,0),
            color=global_values.COLOR_FOREGROUND,
            fontsize=global_values.FONT_SIZE,
            text="Time range",
            parent=self.__time_bar
        )

        self.__time_slider = custom_slider.IntervalScrollBar(
            pos=(0,27),
            width=size.x,
            range=(0, duration),
            thumbExtent=duration,
            parent=self.__time_bar
        )
        self.__time_slider.subscribe(custom_slider.IntervalScrollBar.THUMB_POS_CHANGED, self.__on_scroll)

        self.__start_label = avg.WordsNode(
            pos=(0,48),
            color=global_values.COLOR_FOREGROUND,
            text="0:00 ({})".format(helper.format_time(interval[0], False)),
            fontsize=global_values.FONT_SIZE,
            parent=self.__time_bar
        )
        self.__end_label = avg.WordsNode(
            pos=(size.x,48),
            color=global_values.COLOR_FOREGROUND,
            text="({}) {}".format(helper.format_time(interval[1], False), helper.format_time(self.__duration, False)),
            alignment="right",
            fontsize=global_values.FONT_SIZE,
            parent=self.__time_bar
        )
        self.__cur_time_line = avg.LineNode(
            color=global_values.COLOR_WHITE,
            sensitive=False,
            parent=self.__time_bar
        )
        self.__duration_time_label = avg.WordsNode(
            pos=(size.x,0),
            color=global_values.COLOR_FOREGROUND,
            alignment="right",
            fontsize = global_values.FONT_SIZE,
            parent=self.__time_bar
        )

    def __create_phase_lines(self, session):
        """
        Create lines for the different phases in the session. Green ones for the start of a phase and red ones for the
        end.

        :param session: The session this phase lines should represent.
        :type session: Session
        """
        config = helper.get_config(session.session_num)
        if config is None:
            return

        # Get all the times of all phases and creates a line for each one.
        for start, end in config.phase_timestamps.itervalues():
            start = helper.csvtime_to_float(session.date, start) - session.start_time
            end = helper.csvtime_to_float(session.date, end) - session.start_time

            for time, color in [(start, global_values.COLOR_PHASE_GREEN), (end, global_values.COLOR_PHASE_RED)]:
                pos_x = (time / self.__duration) * self.__time_slider.width
                line_node = avg.LineNode(
                    color=color,
                    pos1=(pos_x, 25),
                    pos2=(pos_x, 48),
                    strokewidth=2,
                    opacity=0.8,
                    active=True,
                    parent=self.__time_bar
                )
                self.__phase_lines[time] = line_node

    def __init_smoothness_slider(self):
        pos = avg.Point2D(self.width - 180, 0)

        avg.WordsNode(pos=pos+(4,0), color=global_values.COLOR_FOREGROUND, fontsize=global_values.FONT_SIZE,
                text="Smoothness", parent=self)

        smoothness_range = self.__vis_params.MIN_SMOOTHNESS_FACTOR, self.__vis_params.MAX_SMOOTHNESS_FACTOR
        self.smoothness_slider = widget.Slider(pos=pos+(0,33), width=180, range=smoothness_range, parent=self)
        self.smoothness_slider.thumbPos = self.__vis_params.get_smoothness_factor()
        self.smoothness_slider.subscribe(widget.Slider.THUMB_POS_CHANGED, self.__on_smoothness_change)

    def __on_smoothness_change(self, pos):
        self.__vis_params.set_smoothness_factor(pos)
        self.__vis_params.notify()

    def __on_scroll(self, pos):
        # update global time interval
        delta = pos - self.__vis_params.get_time_interval()[0]

        new_highlight_time = self.__vis_params.highlight_time + delta
        if new_highlight_time < 0:
            new_highlight_time = 0
        elif self.__duration < new_highlight_time:
            new_highlight_time = self.__duration
        self.__vis_params.highlight_time = new_highlight_time

        interval = pos, pos + self.__time_slider.thumbExtent
        self.__vis_params.set_time_interval(interval)

    def __play_pause(self, checked):
        self.__vis_params.is_playing = not self.__vis_params.is_playing

    def __update_time(self, vis_params):
        cur_time = vis_params.highlight_time
        line_x = (cur_time/self.__duration)*self.__time_slider.width
        self.__cur_time_line.pos1 = (line_x, 23)
        self.__cur_time_line.pos2 = (line_x, 50)

        # Check if something has changed.
        if self.__time_interval == vis_params.get_time_interval():
            return

        # Set the new interval.
        self.__time_interval = vis_params.get_time_interval()[:]

        self.__time_slider.setThumbExtent(self.__time_interval[1] - self.__time_interval[0])
        self.__time_slider.setThumbPos(self.__time_interval[0])

        self.__start_label.text = "0:00 ({})".format(helper.format_time(self.__time_interval[0], False))
        self.__end_label.text = "({}) {}".format(helper.format_time(self.__time_interval[1], False), helper.format_time(self.__duration, False))
        self.__duration_time_label.text = "Interval duration: " + helper.format_time(self.__time_interval[1] - self.__time_interval[0], False)

    def __on_play_pause(self, playing):
        self.__time_slider.sensitive = not playing
        self.play_button.checked = self.__vis_params.is_playing


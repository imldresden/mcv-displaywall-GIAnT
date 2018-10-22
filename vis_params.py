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

from libavg import avg, player
import random


class VisParams(avg.Publisher):
    CHANGED = avg.Publisher.genMessageID()
    IS_PLAYING = avg.Publisher.genMessageID()

    MIN_SMOOTHNESS_FACTOR = 0.01
    MAX_SMOOTHNESS_FACTOR = 1.

    __highlight_time = 0
    __zoom_strength = 0.15

    user_hues = [280, 90, 40, 130, 200, 310]

    def __init__(self, session):
        super(VisParams, self).__init__()
        self.__is_playing = False
        self.__time_interval = [0, session.duration]
        self.publish(VisParams.CHANGED)
        self.publish(VisParams.IS_PLAYING)

        self.__smoothness_factor = self.MAX_SMOOTHNESS_FACTOR/2.
        self.__users_visible = [True]*session.num_users
        self.__duration = session.duration

        for i in range(0, 100):
            VisParams.user_hues.append(random.randint(0, 310))

        self.__timer_replacement = False
        self.__last_frame_time = 0

    def get_time_interval(self):
        return self.__time_interval

    def get_time_duration(self):
        return self.__time_interval[1] - self.__time_interval[0]

    def zoom_in_at(self, fraction_in_timeframe, zoom_strength=None):
        zoom_strength = zoom_strength or self.__zoom_strength
        point = self.__time_interval[0] + fraction_in_timeframe * (self.__time_interval[1] - self.__time_interval[0])
        self.__time_interval[0] = point - (point - self.__time_interval[0]) * (1 - zoom_strength)
        self.__time_interval[1] = point + (self.__time_interval[1] - point) * (1 - zoom_strength)
        self.notify()

    def zoom_out_at(self, fraction_in_timeframe, zoom_strength=None):
        zoom_strength = zoom_strength or self.__zoom_strength
        time_range = [0, self.__duration]
        if self.__time_interval == time_range:
            return
        point = self.__time_interval[0] + fraction_in_timeframe * (self.__time_interval[1] - self.__time_interval[0])
        self.__time_interval[0] -= (point - self.__time_interval[0]) / ((1 / zoom_strength) - 1)
        self.__time_interval[1] += (self.__time_interval[1] - point) / ((1 / zoom_strength) - 1)

        if self.__time_interval[0] < time_range[0]:
            self.__time_interval[0] = time_range[0]

        if self.__time_interval[1] > time_range[1]:
            self.__time_interval[1] = time_range[1]
        self.notify()

    def shift_time(self, forwards, amount=-1, shift_interval=True):
        """
        Shifts the time of the whole session.

        :param forwards: Should the shift be happen forwards?
        :type forwards: bool
        :param amount: The amount of shift that should take place. If -1 it will be calculated automatically.
        :type amount: float
        :param shift_interval: Should the interval be shifted as well, if the highlight time (current time) is over those
                               boundaries?
        :type shift_interval: bool
        """
        if amount == -1:
            amount = (self.__time_interval[1] - self.__time_interval[0]) * self.__zoom_strength / 2
        forwards = 1 if forwards else -1
        shift_amount = forwards * amount

        self.__highlight_time += shift_amount

        # Move the highlight time if it would lie outside the given time range.
        if self.__highlight_time < 0:
            self.__highlight_time = 0
        elif self.__highlight_time > self.__duration:
            self.__highlight_time = self.__duration

        # Move the time interval if the highlight time reaches the end or the beginning of it.
        if shift_interval:
            if self.__highlight_time < self.__time_interval[0]:
                time_diff = self.__time_interval[0] - self.__highlight_time
                self.__time_interval[0] -= time_diff
                self.__time_interval[1] -= time_diff
            if self.__highlight_time > self.__time_interval[1]:
                time_diff = self.__highlight_time - self.__time_interval[1]
                self.__time_interval[0] += time_diff
                self.__time_interval[1] += time_diff

        self.notify()

    def set_time_interval(self, interval):
        self.__time_interval = list(interval)
        self.notify()

    def notify(self):
        self.notifySubscribers(VisParams.CHANGED, [self])

    def get_user_visible(self, i):
        return self.__users_visible[i]

    def set_user_visible(self, i, visible):
        self.__users_visible[i] = visible
        self.notify()

    def set_smoothness_factor(self, value):
        self.__smoothness_factor = value

    def get_smoothness_factor(self):
        return self.__smoothness_factor

    @classmethod
    def get_user_color(cls, userid, offset_hue = 0):
        # User colors are specified in CIE Lch color space.
        # This allows us to easily pick four colors that have the same perceptual brightness and saturation,
        # but differing hue.
        user_grey = (60, 0, 0)
        # user_hues = (40, 130, 220, 310)
        # user_hues = user_hues
        if userid <= 0:
            l, c, h = user_grey
        else:
            l = 60
            c = 90
            h = VisParams.user_hues[userid - 1] + offset_hue
        return avg.Color.fromLch(l, c, h)

    def __set_highlight_time(self, time):
        self.__highlight_time = time

    def __get_highlight_time(self):
        return self.__highlight_time
    highlight_time = property(__get_highlight_time, __set_highlight_time)

    def __set_is_playing(self, is_playing):
        self.__is_playing = is_playing
        self.notifySubscribers(VisParams.IS_PLAYING, [self.__is_playing])

        if self.__is_playing and self.__timer_replacement:
            self.__last_frame_time = player.getFrameTime() / 1000.0

    def __get_is_playing(self):
        return self.__is_playing
    is_playing = property(__get_is_playing, __set_is_playing)

    def set_video_timer(self):
        """
        Sets the vis params objects as its own video timer. This will be used if the current session has no video
        that can be used as a timer.
        """
        self.__timer_replacement = True
        player.subscribe(player.ON_FRAME, self.__on_frame)

    def __on_frame(self):
        """
        Called every frame. This will replace the frame method of the videos.
        """
        if not self.__timer_replacement:
            return
        if not self.__is_playing:
            return

        curr_time = player.getFrameTime() / 1000.0
        time_change = curr_time - self.__last_frame_time
        self.shift_time(True, time_change)
        self.__last_frame_time = curr_time

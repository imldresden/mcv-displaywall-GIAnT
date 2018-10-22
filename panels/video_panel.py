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

import libavg
from libavg import avg, player
import global_values


class VideoPanel(avg.DivNode):
    def __init__(self, filename, vis_params, time_offset, mirror=False,
                 parent=None, **kwargs):
        super(VideoPanel, self).__init__(**kwargs)
        self.registerInstance(self, parent)

        self.__path = filename
        size = self.size - (global_values.VIDEO_LEFT_MARGIN,0)
        if size[0] / size[1] > 16.0 / 9.0:
            vid_size = (size[1] * 16.0 / 9.0, size[1])
        else:
            vid_size = (size[0], size[0] * 9.0 / 16.0)
        vid_pos = (global_values.VIDEO_LEFT_MARGIN,0) # (size - vid_size)/2
        self.__time_offset = time_offset

        self.__vis_params = vis_params
        self.is_playing = False
        self.__videoNode = avg.VideoNode(
            href=self.__path,
            pos=vid_pos,
            size=vid_size,
            mipmap=True,
            threaded=False,
            enablesound=False,
            parent=self
        )
        if mirror:
            player.setTimeout(0, lambda: self.__videoNode.setMirror(self.__videoNode.HORIZONTAL))

        # rectangle for border
        libavg.RectNode(
            parent=self,
            pos=vid_pos,
            size=vid_size,
            strokewidth=1,
            color=global_values.COLOR_FOREGROUND
        )

        self.__videoNode.volume = 0

        self.__videoNode.play()
        self.__videoNode.pause()

        vis_params.subscribe(vis_params.CHANGED, self.update_time)
        vis_params.subscribe(vis_params.IS_PLAYING, self.__play_pause)

    def update_time(self, vis_params):
        if not self.is_playing:
            self.__videoNode.seekToTime(int((vis_params.highlight_time + self.__time_offset) * 1000))

    def __play_pause(self, play=True):
        self.is_playing = play
        if play:
            self.__videoNode.play()
        else:
            self.__videoNode.pause()


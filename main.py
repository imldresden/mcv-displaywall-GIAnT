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
import os

import libavg
from panels import movement_panel
from panels import options_panel
from panels import video_panel
from panels import wall_panel
from libavg import app, avg, player

import global_values
import vis_params
from panels import floor_panel
from data_setup.db_setup import create_session
from panels.device_panel import DevicePanel
from panels.satistics_panel import StatisticsPanel
from panels.task_time_panel import TaskTimePanel
from panels.time_jump_panel import TimeJumpPanel
from panels.touch_time_panel import TouchTimePanel

SESSION_ID = '16'

class MainDiv(app.MainDiv):
    last_time = 0
    viewport_change_duration = 0.3

    def onInit(self):
        self.session = create_session(SESSION_ID)
        self.session.load_from_db()
        self.__vis_params = vis_params.VisParams(self.session)
        # self.elementoutlinecolor="FF0000"

        b_padding = global_values.BIG_PADDING  # and padding inbetween elements of visualization
        s_padding = global_values.SMALL_PADDING  # and padding inbetween elements of visualization
        menu_height = 60

        margin = global_values.APP_MARGIN    # distance to all sides of application window
        self.pos = margin
        self.size -= 2 * avg.Point2D(margin)

        # rectangle to color background
        libavg.RectNode(
            parent=self,
            pos=(-1000, -1000),
            size=(10000, 10000),
            strokewidth=0,
            fillcolor=global_values.COLOR_BACKGROUND,
            fillopacity=1
        )

        # Visualization panels
        vis_area_size = avg.Point2D(self.width, self.height - menu_height - b_padding)
        panel_size = avg.Point2D((vis_area_size.x - 5 * b_padding) / 6., (vis_area_size.y - b_padding) / 2.)
        # panel_size = avg.Point2D(vis_area_size.x / 3., vis_area_size.y / 2.) - (b_padding * 2, b_padding)
        video_panel_height = (vis_area_size.y + 2 * s_padding) / 3.

        # First column
        pos_x = 0
        time_jump_buttons_pos = avg.Point2D(pos_x, 0)
        time_jump_buttons_size = avg.Point2D(150, 125)
        statistics_panel_pos = avg.Point2D(pos_x, 125 + s_padding)
        device1_panel_pos = avg.Point2D(pos_x, 125 + panel_size.y + 2 * s_padding)
        device2_panel_pos = avg.Point2D(pos_x + (panel_size.x - s_padding) / 2. + s_padding, 125 + panel_size.y + 2 * s_padding)
        devive_panel_size = avg.Point2D((panel_size.x - s_padding) / 2., 16./9. * ((panel_size.x - s_padding) / 2.))
        if devive_panel_size.y > vis_area_size.y - (time_jump_buttons_size.y + panel_size.y + 2 * s_padding):
            devive_panel_size.y = vis_area_size.y - (time_jump_buttons_size.y + panel_size.y + 2 * s_padding)
            devive_panel_size.x = 9./16. * devive_panel_size.y
        # Second+Third column
        pos_x = panel_size.x + b_padding
        task_time_panel_pos = avg.Point2D(pos_x, 0)
        time_panel_pos = avg.Point2D(pos_x, panel_size.y / 4. + s_padding)
        touch_time_panel_pos = avg.Point2D(pos_x, time_panel_pos.y + panel_size.y + s_padding)
        time_panel_alt_pos = avg.Point2D(pos_x, touch_time_panel_pos.y + panel_size.y / 4. + s_padding)
        # Fourth column
        pos_x = (panel_size.x + b_padding) * 3
        video_panel_first_pos = avg.Point2D(pos_x, 0)
        video_panel_second_pos = avg.Point2D(pos_x, video_panel_height + s_padding)
        video_panel_third_pos = avg.Point2D(pos_x, (video_panel_height + s_padding) * 2)
        # Fifth+Sixth column
        pos_x = (panel_size.x + b_padding) * 4
        wall_touch_panel_pos = avg.Point2D(pos_x, 0)
        floor_panel_pos = avg.Point2D(pos_x, panel_size.y + s_padding)

        self.time_jump_buttons = TimeJumpPanel(
            parent=self,
            pos=time_jump_buttons_pos,
            size=time_jump_buttons_size,
            session=self.session,
            vis_params=self.__vis_params
        )
        self.statistics_panel = StatisticsPanel(
            parent=self,
            pos=statistics_panel_pos,
            size=panel_size,
            session=self.session,
            vis_params=self.__vis_params,
            user_ids=[1, 2],
            use_reload_overlay=True
        )
        self.device1_panel = DevicePanel(
            parent=self,
            pos=device1_panel_pos,
            size=devive_panel_size,
            session=self.session,
            vis_params=self.__vis_params,
            label="Device Touch {}".format(global_values.USER_TO_COLOR[1]),
            user=1
        )
        self.device2_panel = DevicePanel(
            parent=self,
            pos=device2_panel_pos,
            size=devive_panel_size,
            session=self.session,
            vis_params=self.__vis_params,
            label="Device Touch {}".format(global_values.USER_TO_COLOR[2]),
            user=2
        )

        self.task_time_panel = TaskTimePanel(
            parent=self,
            pos=task_time_panel_pos,
            size=(panel_size.x * 2 + b_padding, panel_size.y / 4),
            session=self.session,
            vis_params=self.__vis_params,
            csv_path="data_logs/session_{0}/session_{0}_task.csv".format(self.session.session_num)
        )
        self.timeline_panel = movement_panel.MovementPanel(
            pos=time_panel_pos,
            size=(panel_size.x * 2 + b_padding, panel_size.y),
            session=self.session,
            vis_params=self.__vis_params,
            is_dist_view=False,
            show_timestamp_lines=True,
            label="Movement Timeline",
            parent=self
        )
        self.__show_dist_view = False
        self.touch_time_panel = TouchTimePanel(
            parent=self,
            pos=touch_time_panel_pos,
            size=(panel_size.x * 2 + b_padding, panel_size.y / 4),
            session=self.session,
            vis_params=self.__vis_params,
            max_users=3
        )
        self.timeline_dist_panel = movement_panel.MovementPanel(
            pos=time_panel_alt_pos,
            size=(panel_size.x * 2 + b_padding, panel_size.y / 2),
            session=self.session,
            vis_params=self.__vis_params,
            is_dist_view=True,
            show_timestamp_lines=True,
            label="Distance Timeline",
            parent=self
        )

        if len(self.session.video_filenames) > 0 and os.path.isfile(self.session.video_filenames[0]):
            self.video_first_panel = video_panel.VideoPanel(
                pos=video_panel_first_pos,
                size=(panel_size.x, video_panel_height),
                filename=self.session.data_dir + "/" + self.session.video_filenames[0],
                time_offset=self.session.get_video_time_offset(0),
                vis_params=self.__vis_params,
                parent=self
            )
        if len(self.session.video_filenames) > 1 and os.path.isfile(self.session.video_filenames[1]):
            self.video_second_panel = video_panel.VideoPanel(
                pos=video_panel_second_pos,
                size=(panel_size.x, video_panel_height),
                filename=self.session.data_dir + "/" + self.session.video_filenames[1],
                time_offset=self.session.get_video_time_offset(1),
                vis_params=self.__vis_params,
                parent=self
            )
        if len(self.session.video_filenames) > 2 and os.path.isfile(self.session.video_filenames[2]):
            self.video_third_panel = video_panel.VideoPanel(
                pos=video_panel_third_pos,
                size=(panel_size.x, video_panel_height),
                filename=self.session.data_dir + "/" + self.session.video_filenames[2],
                time_offset=self.session.get_video_time_offset(2),
                vis_params=self.__vis_params,
                parent=self
            )
        # No video was created.
        self.__vis_params.set_video_timer()

        self.wall_touch_panel = wall_panel.WallPanel(
            pos=wall_touch_panel_pos,
            size=(panel_size.x * 2 + b_padding, panel_size.y),
            session=self.session,
            vis_params=self.__vis_params,
            label="Wall Touches",
            parent=self
        )
        self.user_floor_panel = floor_panel.FloorPanel(
            pos=floor_panel_pos,
            size=(panel_size.x * 2 + b_padding, panel_size.y),
            session=self.session,
            vis_params=self.__vis_params,
            label="Movement (Kinect)",
            use_heatmap=False,
            active=False,
            parent=self
        )
        self.device_floor_panel = floor_panel.FloorPanel(
            pos=floor_panel_pos,
            size=(panel_size.x * 2 + b_padding, panel_size.y),
            session=self.session,
            vis_params=self.__vis_params,
            mode="device",
            label="Movement (OptiTrack)",
            use_heatmap=False,
            active=True,
            parent=self
        )

        options_pos = (0, self.height-menu_height)
        options_size = (self.width, menu_height)
        self.options = options_panel.OptionsPanel(
            pos=options_pos,
            size=options_size,
            vis_params=self.__vis_params,
            session=self.session,
            parent=self
        )

        app.keyboardmanager.bindKeyDown(keyname='Right', handler=self.shift_forward, help="Step forward")
        app.keyboardmanager.bindKeyDown(keyname='Left', handler=self.shift_back, help="Step back")
        app.keyboardmanager.bindKeyDown(keyname='Up', handler=self.zoom_in, help="Zoom in")
        app.keyboardmanager.bindKeyDown(keyname='Down', handler=self.zoom_out, help="Zoom out")
        app.keyboardmanager.bindKeyDown(keyname='Space', handler=self.play_pause, help="Play/pause")
        app.keyboardmanager.bindKeyDown(keyname='F', handler=self.toggle_floor_view, help="Changes the floor view")
        app.keyboardmanager.bindKeyDown(keyname='H', handler=self.toggle_heat_maps, help="Toggle heatmaps on the Floor views")
        for i in range(0,4):
            app.keyboardmanager.bindKeyDown(keyname=str(i+1),
                    handler=lambda userid=i: self.toggle_user_visible(userid),
                    help = "Toggle user "+str(i+1))

        self.__vis_params.set_time_interval((0, self.session.duration))

    def zoom_in(self):
        self.__vis_params.zoom_in_at(0.5, 0.6)

    def zoom_out(self):
        self.__vis_params.zoom_out_at(0.5)

    def shift_back(self):
        self.__vis_params.shift_time(False)

    def shift_forward(self):
        self.__vis_params.shift_time(True)

    def play_pause(self):
        self.__vis_params.is_playing = not self.__vis_params.is_playing

    def toggle_floor_view(self):
        self.user_floor_panel.active = not self.user_floor_panel.active
        self.device_floor_panel.active = not self.device_floor_panel.active

    def toggle_user_visible(self, userid):
        is_visible = self.__vis_params.get_user_visible(userid)
        self.__vis_params.set_user_visible(userid, not is_visible)

    def toggle_heat_maps(self):
        self.user_floor_panel.use_heatmap = not self.user_floor_panel.use_heatmap
        self.device_floor_panel.use_heatmap = not self.device_floor_panel.use_heatmap


def value_to_pixel(value, max_px, interval):
    a = (interval[1] - interval[0]) / max_px
    return (value - interval[0]) / a


player.setWindowTitle("GIAnT - Session {}".format(SESSION_ID))
app.App().run(
    MainDiv(),
    app_resolution="2880x1000",
    app_window_size="1920x666"
)

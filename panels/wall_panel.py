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

import pat_model
import global_values
import vis_panel
from libavg import avg, player

player.loadPlugin("heatmap")

class WallPanel(vis_panel.VisPanel):

    def __init__(self, session, vis_params, parent, mode="user", use_heatmap=False, label=None,
                 **kwargs):
        """
        :param session: The session this panel is based on.
        :type session: Session
        :param vis_params:
        :type vis_params:
        :param mode: The mode that will be used for this panel. Either "user" for user data or "device" for device data.
        :type mode: str
        :param use_heatmap: Should the heat map for this view be used?
        :type use_heatmap: bool
        :param label: This can be set if a custom label for this view should be given.
        :type label: str
        :param parent: The parent of this Panel.
        :type parent: avg.DivNode
        :param kwargs: Other parameters for a VisPanel object.
        """
        pos_range = pat_model.pos_range
        view_extent = avg.Point2D(pos_range[1][0] - pos_range[0][0], pos_range[1][1] - pos_range[0][1])
        aspect = view_extent.y/view_extent.x

        label = label or "Wall {}".format(mode)
        super(WallPanel, self).__init__(label, vis_params, (60, 25), False, aspect, parent, **kwargs)

        self.__users = session.users
        self.__mode = mode
        self.__use_heatmap = use_heatmap

        self._create_x_axis(
            data_range=(pos_range[0][0], pos_range[1][0]),
            hide_rims=True,
            unit="m"
        )
        self._create_y_axis(
            data_range=(pos_range[0][1], pos_range[1][1]),
            unit="m",
            tick_positions=[0,1,2],
            hide_rims=True,
            inverted=True
        )

        # Calculate size of wall in pixels.
        normalized_wall_pos = avg.Point2D((pat_model.x_wall_range[0] - pos_range[0][0]) / view_extent.x,
                (pat_model.y_wall_range[1] - pos_range[0][1]) / view_extent.y)
        wall_pos = avg.Point2D(self._data_div.size.x * normalized_wall_pos.x,
                self._data_div.size.y * (1-normalized_wall_pos.y))
        wall_size = avg.Point2D(self._data_div.size.x * pat_model.x_wall_range[1] / view_extent.x,
                self._data_div.size.y * (1-pat_model.y_wall_range[0] / view_extent.y))
        avg.RectNode(pos=wall_pos, size=wall_size, color=global_values.COLOR_SECONDARY,
                parent=self._data_div)

        self.__plot_div = avg.DivNode(pos=wall_pos, size=wall_size, parent=self._data_div)
        self._create_data_div()
        self.__create_display_borders()

        self.__touch_plots_norm = []
        self.__touch_plots_inj = []
        self.__heatmap_nodes = []
        for user in self.__users:
            color_norm = str(vis_params.get_user_color(user.getUserID()))
            color_inj = str(vis_params.get_user_color(user.getUserID(), offset_hue=20))

            node = heatmap.HeatMapNode(
                size=self.__plot_div.size,
                viewportrangemin=(pat_model.x_wall_range[0], pat_model.y_wall_range[0]),
                viewportrangemax=(pat_model.x_wall_range[1], pat_model.y_wall_range[1]),
                mapsize=(50,25),
                valuerangemin=0,
                valuerangemax=8,
                colormap=(color_norm, color_norm),
                opacitymap=(0,1),
                blendmode=global_values.BLEND_MODE,
                parent=self.__plot_div
            )
            node.setEffect(avg.BlurFXNode(radius=1))
            self.__heatmap_nodes.append(node)

            node = plots.ScatterPlotNode(
                size=self.__plot_div.size,
                viewportrangemax=pat_model.touch_range,
                color=color_norm,
                parent=self.__plot_div
            )
            self.__touch_plots_norm.append(node)
            node = plots.ScatterPlotNode(
                size=self.__plot_div.size,
                viewportrangemax=pat_model.touch_range,
                color=color_inj,
                parent=self.__plot_div
            )
            self.__touch_plots_inj.append(node)

        self.__time_interval = [None, None]
        self.__user_visibility = [True for _ in range(len(self.__users))]

    @property
    def use_heatmap(self):
        return self.__use_heatmap

    @use_heatmap.setter
    def use_heatmap(self, value):
        self.__use_heatmap = value

        for heatmap in self.__heatmap_nodes:
            heatmap.active = self.__use_heatmap
            if self.__use_heatmap:
                self.__show_viewpoints(self.__time_interval)

    def _update_time(self, vis_params):
        user_visibility = [vis_params.get_user_visible(i) for i in range(len(self.__users))]
        # Check if something has changed.
        if self.__time_interval == vis_params.get_time_interval() and self.__user_visibility == user_visibility:
            return

        # Set the new interval.
        self.__time_interval = vis_params.get_time_interval()[:]
        # Set the new visibility of the user.
        self.__user_visibility = user_visibility

        self.__show_touches(self.__time_interval)
        self.__show_viewpoints(self.__time_interval)

    def __create_display_borders(self):
        parent = self.__plot_div
        for i in range(1,3):
            y = i/3. * parent.height
            avg.LineNode(pos1=(0, y), pos2=(parent.width, y), color=global_values.COLOR_BACKGROUND,
                    parent=parent)

        for i in range(1, 4):
            x = i / 4. * parent.width
            avg.LineNode(pos1=(x, 0), pos2=(x, parent.height), color=global_values.COLOR_BACKGROUND,
                parent=parent)

    def __show_touches(self, time_interval):
        for i, user in enumerate(self.__users):
            if self.__mode == "user":
                if self._vis_params.get_user_visible(i):
                    touches_norm = []
                    touches_inj = []
                    for t in user.getTouches(time_interval[0], time_interval[1]):
                        if t.injected:
                            touches_inj.append(t.pos)
                        else:
                            touches_norm.append(t.pos)

                    self.__touch_plots_norm[i].setPosns(touches_norm)
                    self.__touch_plots_inj[i].setPosns(touches_inj)
                else:
                    self.__touch_plots_norm[i].setPosns([])
                    self.__touch_plots_inj[i].setPosns([])
            elif self.__mode == "device":
                if self._vis_params.get_user_visible(i):
                    # device_posns = [de.screenPos for de in user.getDeviceEntries(time_interval[0], time_interval[1])]
                    device_posns = []
                    for de in user.getDeviceEntries(time_interval[0], time_interval[1]):
                        pos = de.screenPos
                        # TODO: The scatterplot can only handle points that lie in the given touch range.
                        if 0 <= pos[0] <= pat_model.touch_range[0] and 0 <= pos[1] <= pat_model.touch_range[1]:
                            device_posns.append(pos)
                    self.__touch_plots_norm[i].setPosns(device_posns)
                else:
                    self.__touch_plots_norm[i].setPosns([])


    def __show_viewpoints(self, time_interval):
        if self.__mode != "user":
            return

        val_max = 8 * ((time_interval[1] - time_interval[0])/60.)
        for i, user in enumerate(self.__users):
            if user.headInfoCount == 0:
                continue

            if not self.__use_heatmap:
                self.__heatmap_nodes[i].active = False
                continue

            self.__heatmap_nodes[i].valuerangemax = val_max
            if self._vis_params.get_user_visible(i):
                viewpoints = user.getHeadViewpoints(time_interval[0], time_interval[1])
                self.__heatmap_nodes[i].setPosns(viewpoints)
            else:
                self.__heatmap_nodes[i].setPosns([])

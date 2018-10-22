# coding=utf-8
import math
from libavg import avg

import global_values
import helper
from panels import vis_panel


class TouchTimePanel(vis_panel.VisPanel):
    __RECT_SIZE = (2, 20)

    def __init__(self, session, vis_params, max_users, parent, **kwargs):
        """
        :param session: The session this panel should show.
        :type session: Session
        :param vis_params: The state/parameter for this whole application.
        :type vis_params: VisParams
        :param max_users: The number of user that should be maximal shown in this view.
        :type max_users: int
        :param parent: The parent for this panel.
        :type parent: avg.DivNode
        :param kwargs: Other parameters that are used for the VisPanel.
        """
        super(TouchTimePanel, self).__init__("Touches", vis_params, (60, 25), True, parent=parent, **kwargs)

        self.__duration = session.duration
        self.__users = session.users
        self.__max_users = max_users
        self.__user_count = len(self.__users) if len(self.__users) < self.__max_users else self.__max_users
        self.__time_interval = [None, None]
        self.__user_visibility = [True for _ in range(len(self.__users))]
        self.__user_rect_nodes = None

        self._create_x_axis(
            data_range=[0, session.duration],
            unit="s"
        )
        self._create_y_axis(
            data_range=[-0.5, self.__user_count - 0.5],
            unit="own",
            tick_positions=[i for i in range(self.__user_count)],
            tick_labels=["" for _ in range(self.__user_count)],
            hide_rims=True
        )
        self._create_data_div()

        self._create_all_rect_nodes(vis_params)

        # Create the highlight line
        self.__highlight_line = avg.LineNode(
            color=global_values.COLOR_SECONDARY,
            pos1=(0, 0),
            pos2=(0, self._data_div.height),
            active=False,
            parent=self._data_div
        )


    def _create_all_rect_nodes(self, vis_params):
        """
        Creates all rect nodes necessary for this visualisization.

        :param vis_params: The parameter that are needed to create this view.
        """
        time_interval = vis_params.get_time_interval()[:]

        self.__user_rect_nodes = [{} for _ in range(self.__user_count)]
        for i in range(self.__user_count):
            color_norm = str(vis_params.get_user_color(self.__users[i].getUserID()))
            color_inj = str(vis_params.get_user_color(self.__users[i].getUserID(), offset_hue=20))
            touches = self.__users[i].getTouches(time_interval[0], time_interval[1])

            for t in touches:
                rect_node = avg.RectNode(
                    parent=self._data_div,
                    strokewidth=0,
                    fillopacity=0.35,
                    fillcolor=color_inj if t.injected else color_norm,
                    size=self.__RECT_SIZE,
                    active=False
                )
                self.__user_rect_nodes[i][t.time] = rect_node

    def _update_time(self, vis_params):
        """
        Called when the visparam has changed.

        :type vis_params: VisParams
        """
        # Calculate the new position of the highlight line.
        time_factor = self._data_div.width / vis_params.get_time_duration()
        highlight_xpos = (float(self._vis_params.highlight_time) - vis_params.get_time_interval()[0]) * time_factor
        if highlight_xpos > self.width or highlight_xpos < 0:
            self.__highlight_line.active = False
        else:
            self.__highlight_line.active = True
            self.__highlight_line.pos1 = (highlight_xpos, self.__highlight_line.pos1[1])
            self.__highlight_line.pos2 = (highlight_xpos, self.__highlight_line.pos2[1])

        user_visibility = [vis_params.get_user_visible(i) for i in range(len(self.__users))]
        # Check if something has changed.
        if self.__time_interval == vis_params.get_time_interval() and self.__user_visibility == user_visibility:
            return

        # Set the new interval.
        self.__time_interval = vis_params.get_time_interval()[:]
        # Set the new visibility of the user.
        self.__user_visibility = user_visibility

        # Change the axis of the view.
        self._x_axis.hide_rims = not(math.fabs(vis_params.get_time_duration() - self.__duration) < 0.0001)
        self._x_axis.update(self.__time_interval[0], self.__time_interval[1])
        self._update_grid()

        # Checks if the rect node were created yet.
        if self.__user_rect_nodes is None:
            return

        user_touches_count = {}
        # Draw the new rect nodes for the touches of each user.
        for i in range(self.__user_count):
            if not vis_params.get_user_visible(i):
                for rect_node in self.__user_rect_nodes[i].itervalues():
                    rect_node.active = False
                continue

            user_touches_count[i] = 0

            pos_y = self._y_axis.value_to_pixel(i) - self.__RECT_SIZE[1] / 2
            for time, rect_node in self.__user_rect_nodes[i].iteritems():
                if self.__time_interval[0] < time < self.__time_interval[1]:
                    pos_x = self._x_axis.value_to_pixel(time) - self.__RECT_SIZE[0] / 2
                    rect_node.pos = pos_x, pos_y
                    rect_node.active = True
                    user_touches_count[i] += 1
                else:
                    rect_node.active = False

        touch_sum = sum(user_touches_count.values())

        # Update the axis labels for the user.
        axis_labels = []
        for i in range(self.__user_count):
            if vis_params.get_user_visible(i):
                axis_labels.append("{0: 3.1f}".format((float(user_touches_count[i]) * 100 / touch_sum) if touch_sum > 0 else 0))
            else:
                axis_labels.append("")
        self._y_axis.tick_labels = axis_labels


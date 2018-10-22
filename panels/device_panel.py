from libavg import player, avg

import global_values
from panels import vis_panel

player.loadPlugin("heatmap")


class DevicePanel(vis_panel.VisPanel):
    def __init__(self, session, vis_params, parent, user, label=None, **kwargs):
        """
        :param session: The session this panel is based on.
        :type session: Session
        :param vis_params:
        :type vis_params:
        :param user: Which user should be used.
        :type user: int
        :param label: This can be set if a custom label for this view should be given.
        :type label: str
        :param parent: The parent of this Panel.
        :type parent: avg.DivNode
        :param kwargs: Other parameters for a VisPanel object.
        """
        label = label or "Device Touch U{}".format(user)
        super(DevicePanel, self).__init__(label, vis_params, (0, 0), True, parent=parent, **kwargs)

        self.__user = session.users[user]
        self.__time_interval = [None, None]

        self._create_data_div()

        color = str(vis_params.get_user_color(self.__user.getUserID()))
        self.__heatmap = heatmap.HeatMapNode(
            size=self._data_div.size,
            viewportrangemin=(0, 0),
            viewportrangemax=(1080, 1920),
            mapsize=(18, 32),
            valuerangemin=0,
            valuerangemax=8,
            colormap=(color, color),
            opacitymap=(0, 1),
            blendmode=global_values.BLEND_MODE,
            parent=self._data_div
        )
        self.__heatmap.setEffect(avg.BlurFXNode(radius=1))

    def _update_time(self, vis_params):
        # Check if something has changed.
        if self.__time_interval == vis_params.get_time_interval():
            return

        # Set the new interval.
        self.__time_interval = vis_params.get_time_interval()[:]

        touches = self.__user.getDeviceTouches(self.__time_interval[0], self.__time_interval[1])
        self.__heatmap.setPosns([t.pos for t in touches])

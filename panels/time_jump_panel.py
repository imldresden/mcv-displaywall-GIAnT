# coding=utf-8
from collections import OrderedDict

from libavg import avg, gesture

import global_values
from helper import csvtime_to_float, get_config


class TimeJumpPanel(avg.DivNode):
    __PADDING = 5
    __STROKE_WIDTH = 2

    def __init__(self, session, vis_params, parent, **kwargs):
        super(TimeJumpPanel, self).__init__(**kwargs)
        self.registerInstance(self, parent)

        self.__vis_params = vis_params

        config = get_config(session.session_num)
        self.__jump_times = OrderedDict([("Entire Session", (0.0, session.duration))])
        if config is not None:
            for name, (start, end) in config.phase_timestamps.iteritems():
                start = csvtime_to_float(session.date, start) - session.start_time
                end = csvtime_to_float(session.date, end) - session.start_time

                self.__jump_times[name] = (start, end)

        self.__button_divs = []
        self.__tap_recognizers = []
        self.__create_buttons()

    def __create_buttons(self):
        if len(self.__jump_times) == 0:
            return

        button_height = (self.height - (len(self.__jump_times) - 1) * self.__PADDING) / len(self.__jump_times)

        for i, name in enumerate(self.__jump_times.keys()):
            div_node = avg.DivNode(
                parent=self,
                pos=(0, (button_height + self.__PADDING) * i),
                size=(self.width, button_height),
                crop=True
            )
            rect_node = avg.RectNode(
                parent=div_node,
                pos=(self.__STROKE_WIDTH, self.__STROKE_WIDTH),
                size=(self.width - 2 * self.__STROKE_WIDTH, button_height - 2 * self.__STROKE_WIDTH),
                color=global_values.COLOR_DARK_GREY,
                fillcolor=global_values.VIS_PANEL_BACKGROUND,
                strokewidth=self.__STROKE_WIDTH,
                fillopacity=1
            )
            avg.WordsNode(
                parent=div_node,
                rawtextmode=True,
                alignment="center",
                size=rect_node.size,
                pos=(rect_node.pos[0] + rect_node.size[0] / 2, rect_node.pos[1]),
                fontsize=global_values.FONT_SIZE_SMALL,
                color=global_values.COLOR_FOREGROUND,
                text=name
            )

            recognizer = gesture.TapRecognizer(
                node=div_node,
                detectedHandler=(lambda btn_name=name: self.__on_tap(btn_name))
            )
            self.__button_divs.append(div_node)
            self.__tap_recognizers.append(recognizer)

    def __on_tap(self, btn_name):
        if btn_name not in self.__jump_times:
            return

        self.__vis_params.highlight_time = self.__jump_times[btn_name][0]
        self.__vis_params.set_time_interval(self.__jump_times[btn_name])

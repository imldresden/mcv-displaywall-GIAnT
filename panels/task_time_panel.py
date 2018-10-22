# coding=utf-8
import math
from enum import Enum

from libavg import avg

import global_values
from helper import csvtime_to_float
from panels import vis_panel


class TaskTypes(Enum):
    AidLineCreated = 0  # y-axis: 3
    AidLineDeleted = 1  # y-axis: 3
    LensCreated = 2  # y-axis: 4
    LensDeleted = 3  # y-axis: 4
    FilterActivated = 4  # y-axis: 5
    FilterDeactivated = 5  # y-axis: 5
    BlockStarted = 6  # y-axis: 0
    TaskChecked = 7  # y-axis: 1
    PhaseChanged = 8  # y-axis: 0
    TipGranted = 9  # y-axis: 2
    Reseted = 10  # y-axis: 2


class TaskTimePanel(vis_panel.VisPanel):
    # First is color, second is axis to show this rect.
    __task_types_mapping = {
        TaskTypes.AidLineCreated: ["1d1", 3],
        TaskTypes.AidLineDeleted: ["d11", 3],
        TaskTypes.LensCreated: ["1d1", 4],
        TaskTypes.LensDeleted: ["d11", 4],
        TaskTypes.FilterActivated: ["1d1", 5],
        TaskTypes.FilterDeactivated: ["d11", 5],
        TaskTypes.BlockStarted: ["d11", 0],
        TaskTypes.TaskChecked: ["1d1", 1],
        TaskTypes.PhaseChanged: ["1d1", 0],
        TaskTypes.TipGranted: ["1d1", 2],
        TaskTypes.Reseted: ["d11", 2]
    }
    __axis_names = [
        "Phase/Block",
        "Task Check",
        "Tip/Reset",
        "AidLines",
        "Lenses",
        "Filter"
    ]

    __RECT_WIDTH = 4

    def __init__(self, session, vis_params, csv_path, parent, **kwargs):
        super(TaskTimePanel, self).__init__("App Events", vis_params, (60, 25), True, parent=parent, **kwargs)
        self.crop = False

        self.__task_data = {}
        self._read_csv_file(csv_path)
        self.__session_start_time = session.start_time
        self.__duration = session.duration
        self.__time_interval = [None, None]
        self.__rect_nodes = None

        self._create_x_axis(
            data_range=[0, session.duration],
            unit="s",
            hide_rims=True
        )
        self._create_y_axis(
            data_range=[-0.5, len(self.__axis_names) - 0.5],
            tick_positions=[i for i in range(len(self.__axis_names))],
            tick_labels=self.__axis_names,
            unit="own",
            hide_rims=True,
            label_fontsize=global_values.FONT_SIZE_SMALLER
        )
        self._create_data_div()

        self._create_all_rect_nodes()

        # Create the highlight line
        self.__highlight_line = avg.LineNode(
            color=global_values.COLOR_SECONDARY,
            pos1=(0, 0),
            pos2=(0, self._data_div.height),
            active=False,
            parent=self._data_div
        )

    def _read_csv_file(self, csv_path):
        """
        Reads the csv file and saves it in an extra dict with enums.

        :param csv_path: The path to the csv file for the tasks.
        :type csv_path: str
        """
        with open(csv_path, 'r') as f:
            next(f)
            for line in f:
                # Split the string in its different columns.
                line = line.split(", ")
                # Add the last column back together because it could contain ,
                line[2] = ", ".join(line[2:])
                timestamp = csvtime_to_float(line[0], line[1])

                if "aid line" in line[2]:
                    created = "created" in line[2]
                    self.__task_data[timestamp] = TaskTypes.AidLineCreated if created else TaskTypes.AidLineDeleted
                elif "lens" in line[2] and "Filter" not in line[2]:
                    created = "created" in line[2]
                    self.__task_data[timestamp] = TaskTypes.LensCreated if created else TaskTypes.LensDeleted
                elif "Filter" in line[2]:
                    deactivated = "deactivated" in line[2]
                    self.__task_data[timestamp] = TaskTypes.FilterDeactivated if deactivated else TaskTypes.FilterActivated
                elif "phase" in line[2]:
                    self.__task_data[timestamp] = TaskTypes.PhaseChanged
                elif "block" in line[2] and "Started" in line[2]:
                    self.__task_data[timestamp] = TaskTypes.BlockStarted
                elif "Checked/Unchecked" in line[2]:
                    self.__task_data[timestamp] = TaskTypes.TaskChecked
                elif "tip was granted" in line[2]:
                    self.__task_data[timestamp] = TaskTypes.TipGranted
                elif "reset" in line[2]:
                    self.__task_data[timestamp] = TaskTypes.Reseted


    def _create_all_rect_nodes(self):
        """
        Creates all rect nodes necessary for this visualisization.
        """
        rect_height = self.height / (len(self.__axis_names) * 2)

        self.__rect_nodes = {}
        for time, task_type in self.__task_data.iteritems():
            rect_node = avg.RectNode(
                parent=self._data_div,
                strokewidth=0,
                fillopacity=0.675,
                fillcolor=self.__task_types_mapping[task_type][0],
                pos=(0, self._y_axis.value_to_pixel(self.__task_types_mapping[task_type][1]) - rect_height / 2),
                size=(self.__RECT_WIDTH, rect_height),
                active=False
            )
            self.__rect_nodes[time - self.__session_start_time] = rect_node

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

        # Check if something has changed.
        if self.__time_interval == vis_params.get_time_interval():
            return

        # Set the new interval.
        self.__time_interval = vis_params.get_time_interval()[:]

        # Change the axis of the view.
        self._x_axis.hide_rims = not(math.fabs(vis_params.get_time_duration() - self.__duration) < 0.0001)
        self._x_axis.update(self.__time_interval[0], self.__time_interval[1])
        self._update_grid()

        # Checks if the rect nodes were created yet.
        if self.__rect_nodes is None:
            return

        # Draw the new rect nodes for the tasks.
        times = {t for t in self.__rect_nodes.iterkeys() if self.__time_interval[0] < t < self.__time_interval[1]}

        for time, node in self.__rect_nodes.iteritems():
            if time not in times:
                node.active = False
            else:
                node.pos = self._x_axis.value_to_pixel(time) - self.__RECT_WIDTH / 2, node.pos[1]
                node.active = True

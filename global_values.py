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

THEME = "dark"

COLOR_BLACK = "010101"  # for black background
COLOR_WHITE = "FFFFFF"  # for bright highlights
COLOR_DARK_GREY = "636363"  # used for cosmetics

if THEME == "dark":
    BLEND_MODE = "add"

    COLOR_FOREGROUND = "EEEEEE"                         # foreground color used for axis and text
    COLOR_SECONDARY = "888888"                          # second more faint foreground color
    COLOR_BACKGROUND = "222222"                         # background color
    COLOR_HIGHLIGHT = "FF0000"                          # distinctive highlight color

    COLOR_PHASE_GREEN = "069913"
    COLOR_PHASE_RED = "99071c"

    VIS_PANEL_BACKGROUND = "010101"
    VM_LINE_HIGHLIGHT_COLOR = "ffffff"
elif THEME == "light":
    BLEND_MODE = "blend"

    COLOR_FOREGROUND = "222222"                         # foreground color used for axis and text
    COLOR_SECONDARY = "555555"                          # second more faint foreground color
    COLOR_BACKGROUND = "DCDCDC"                         # background color
    COLOR_HIGHLIGHT = "FF0000"                          # distinctive highlight color

    COLOR_PHASE_GREEN = "069913"
    COLOR_PHASE_RED = "99071c"

    VIS_PANEL_BACKGROUND = "EDEDED"
    VM_LINE_HIGHLIGHT_COLOR = "000000"

"""display values"""
APP_MARGIN = (15, 15)                                  # space of content to application window in px
BIG_PADDING = 20                                    # space between content of application in px
SMALL_PADDING = 5
VIDEO_LEFT_MARGIN = 0

FONT_SIZE = 18
FONT_SIZE_SMALL = 14
FONT_SIZE_SMALLER = 11

WALL_SIZE_M = (4.9, 2.06)


USER_TO_COLOR = {
    1: "Blue",
    2: "Yellow"
}

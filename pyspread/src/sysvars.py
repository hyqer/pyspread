#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""

sysvars
=======

System environment access

"""

import os

import wx


# Paths


def get_program_path():
    """Returns the path in which pyspread is installed"""

    return os.path.dirname(__file__) + '/../'


def get_help_path():
    """Returns the pyspread help path"""

    return get_program_path() + "doc/help/"


def get_python_tutorial_path():
    """Returns the Python tutorial path"""

    # If the OS has the Python tutorial installed locally, use it.
    # the current path is for Debian

    if os.path.isfile("/usr/share/doc/python-doc/html/tutorial/index.html"):
        return "/usr/share/doc/python-doc/html/tutorial/index.html"

    else:
        return "http://docs.python.org/2/tutorial/"

# System settings


def get_dpi():
    """Returns screen dpi resolution"""

    pxmm_2_dpi = lambda (pixels, length_mm): pixels * 25.6 / length_mm
    return map(pxmm_2_dpi, zip(wx.GetDisplaySize(), wx.GetDisplaySizeMM()))


def get_color(name):
    """Returns string representation of named system color"""

    return wx.SystemSettings.GetColour(name).Get()


def get_default_font():
    """Returns default font"""

    return wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)


def get_font_string(name):
    """Returns string representation of named system font"""

    return wx.SystemSettings.GetFont(name).GetFaceName()

# Fonts


def get_font_list():
    """Returns a sorted list of all system font names"""

    font_enum = wx.FontEnumerator()
    font_enum.EnumerateFacenames(wx.FONTENCODING_SYSTEM)
    font_list = font_enum.GetFacenames()
    font_list.sort()

    return font_list

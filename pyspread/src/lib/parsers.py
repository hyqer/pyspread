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

parsers
=======

Provides
--------

 * get_font_from_data
 * get_pen_from_data
 * color2code
 * code2color
 * parse_dict_strings

"""

import ast

import wx

from src.sysvars import get_default_font


def get_font_from_data(fontdata):
    """Returns wx.Font from fontdata string"""

    textfont = get_default_font()

    if fontdata != "":
        nativefontinfo = wx.NativeFontInfo()
        nativefontinfo.FromString(fontdata)
        textfont.SetNativeFontInfo(nativefontinfo)

    return textfont


def get_pen_from_data(pendata):
    """Returns wx.Pen from pendata attribute list"""

    pen_color = wx.Colour()
    pen_color.SetRGB(pendata[0])
    pen = wx.Pen(pen_color, *pendata[1:])
    pen.SetJoin(wx.JOIN_MITER)

    return pen


def code2color(color_string):
    """Returns wx.Colour from 3-tuple of floats in [0.0, 1.0]"""

    color_tuple = ast.literal_eval(color_string)
    color_tuple_int = map(lambda x: int(x * 255.0), color_tuple)

    return wx.Colour(*color_tuple_int)


def color2code(color):
    """Returns repr of 3-tuple of floats in [0.0, 1.0] from wx.Colour"""

    return unicode(tuple(i / 255.0 for i in color.Get()))


def parse_dict_strings(code):
    """Generator of elements of a dict that is given in the code string

    Parsing is shallow, i.e. all content is yielded as strings

    Parameters
    ----------
    code: String
    \tString that contains a dict

    """

    i = 0
    level = 0
    chunk_start = 0
    curr_paren = None

    for i, char in enumerate(code):
        if char in ["(", "[", "{"] and curr_paren is None:
            level += 1
        elif char in [")", "]", "}"] and curr_paren is None:
            level -= 1
        elif char in ['"', "'"]:
            if curr_paren == char:
                curr_paren = None
            elif curr_paren is None:
                curr_paren = char

        if level == 0 and char in [':', ','] and curr_paren is None:
            yield code[chunk_start: i].strip()
            chunk_start = i + 1

    yield code[chunk_start:i + 1].strip()
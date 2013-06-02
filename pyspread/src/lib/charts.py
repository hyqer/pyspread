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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread. If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
charts
======

Provides matplotlib figure that are chart templates

Provides
--------

* object2code: Returns code for widget from dict object
* fig2bmp: Returns wx.Bitmap from matplotlib chart
* ChartFigure: Main chart class

"""

from copy import copy
from cStringIO import StringIO
import datetime
import i18n

import wx

from matplotlib.figure import Figure
from matplotlib import dates
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


def object2code(key, code):
    """Returns code for widget from dict object"""

    if key in ["xscale", "yscale"]:
        if code == "log":
            code = True
        else:
            code = False

    elif key in ["xlabel", "ylabel", "label"]:
        code = repr(code)

    else:
        code = str(code)

    return code


def fig2bmp(figure, width, height, dpi, zoom):
    """Returns wx.Bitmap from matplotlib chart

    Parameters
    ----------
    fig: Object
    \tMatplotlib figure
    width: Integer
    \tImage width in pixels
    height: Integer
    \tImage height in pixels
    dpi = Float
    \tDC resolution

    """

    dpi *= float(zoom)

    figure.set_figwidth(width / dpi)
    figure.set_figheight(height / dpi)
    figure.subplots_adjust()

    figure.set_canvas(FigureCanvas(figure))
    png_stream = StringIO()

    figure.savefig(png_stream, format='png', dpi=(dpi))

    png_stream.seek(0)
    img = wx.ImageFromStream(png_stream, type=wx.BITMAP_TYPE_PNG)

    return wx.BitmapFromImage(img)


def fig2x(figure, format):
    """Returns svg from matplotlib chart"""

    # Save svg to file like object svg_io
    io = StringIO()
    figure.savefig(io, format=format)

    # Rewind the file like object
    io.seek(0)

    data = io.getvalue()
    io.close()

    return data


class ChartFigure(Figure):
    """Chart figure class with drawing method"""

    plot_type_fixed_attrs = {
        "plot": ["ydata"],
        "bar": ["left", "height"],
        "boxplot": ["x"],
        "hist": ["x"],
        "pie": ["x"],
    }

    plot_type_xy_mapping = {
        "plot": ["xdata", "ydata"],
        "bar": ["left", "height"],
        "boxplot": ["x", "x"],
        "hist": ["label", "x"],
        "pie": ["labels", "x"],
        "annotate": ["xy", "xy"],
    }

    def __init__(self, *attributes):

        Figure.__init__(self, (5.0, 4.0), facecolor="white")

        self.attributes = attributes

        self.__axes = self.add_subplot(111)

        # Insert empty attributes with a dict for figure attributes
        if not self.attributes:
            self.attributes = [{}]

        self.draw_chart()

    def _xdate_setter(self, xdate_format='%Y-%m-%d'):
        """Makes x axis a date axis with auto format

        Parameters
        ----------

        xdate_format: String
        \tSets date formatting

        """

        if xdate_format:
            # We have to validate xdate_format. If wrong then bail out.
            try:
                datetime.date(2000, 1, 1).strftime(xdate_format)

            except ValueError:
                return

            self.__axes.xaxis_date()
            formatter = dates.DateFormatter(xdate_format)
            self.__axes.xaxis.set_major_formatter(formatter)
            self.autofmt_xdate()

    def _setup_axes(self, axes_data):
        """Sets up axes for drawing chart"""

        self.__axes.clear()

        key2setter = {
            "title": self.__axes.set_title,
            "xlabel": self.__axes.set_xlabel,
            "ylabel": self.__axes.set_ylabel,
            "xscale": self.__axes.set_xscale,
            "yscale": self.__axes.set_yscale,
            "xlim": self.__axes.set_xlim,
            "ylim": self.__axes.set_ylim,
            "grid": self.__axes.grid,
            "xdate_format": self._xdate_setter,
        }

        for key in key2setter:
            if key in axes_data and axes_data[key]:
                key2setter[key](axes_data[key])

    def _setup_legend(self, axes_data):
        """Sets up legend for drawing chart"""

        if "legend" in axes_data and axes_data["legend"]:
            self.__axes.legend()

    def draw_chart(self):
        """Plots chart from self.attributes"""

        if not hasattr(self, "attributes"):
            return

        # The first element is always axes data
        self._setup_axes(self.attributes[0])

        for attribute in self.attributes[1:]:

            series = copy(attribute)
            # Extract chart type
            chart_type_string = series.pop("type")

            x_str, y_str = self.plot_type_xy_mapping[chart_type_string]
            # Check xdata length
            if x_str in series and \
               len(series[x_str]) != len(series[y_str]):
                # Wrong length --> ignore xdata
                series.pop(x_str)
            else:
                series[x_str] = tuple(series[x_str])

            fixed_attrs = []
            if chart_type_string in self.plot_type_fixed_attrs:
                for attr in self.plot_type_fixed_attrs[chart_type_string]:
                    # Remove attr if it is a fixed (non-kwd) attr
                    # If a fixed attr is missing, insert a dummy
                    try:
                        fixed_attrs.append(tuple(series.pop(attr)))
                    except KeyError:
                        fixed_attrs.append(())

            if not fixed_attrs or all(fixed_attrs):

                # Draw series to axes

                chart_method = getattr(self.__axes, chart_type_string)
                chart_method(*fixed_attrs, **series)

        # The legend has to be set up after all series are drawn
        self._setup_legend(self.attributes[0])
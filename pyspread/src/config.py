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
pyspread config file
====================

"""

from ast import literal_eval

import wx

from sysvars import get_color, get_font_string

VERSION = "0.2.4"


class DefaultConfig(object):
    """Contains default config for starting pyspread without resource file"""

    def __init__(self):
        # Config file version
        # -------------------

        self.config_version = VERSION

        # User defined paths
        # ------------------

        standardpaths = wx.StandardPaths.Get()
        self.work_path = standardpaths.GetDocumentsDir()

        # Window configuration
        # --------------------

        self.window_position = "(10, 10)"
        self.window_size = repr((wx.GetDisplaySize()[0] * 9 / 10,
                                 wx.GetDisplaySize()[1] * 9 / 10))
        self.window_layout = "''"
        self.icon_theme = "'Tango'"

        self.help_window_position = repr((wx.GetDisplaySize()[0] * 7 / 10, 15))
        self.help_window_size = repr((wx.GetDisplaySize()[0] * 3 / 10,
                                      wx.GetDisplaySize()[1] * 7 / 10))

        # Grid configuration
        # ------------------

        ##self.grid_shape = "(1000, 100, 3)"

        self.grid_rows = "1000"
        self.grid_columns = "100"
        self.grid_tables = "3"

        self.max_unredo = "5000"

        # Maximum result length in a cell in characters
        self.max_result_length = "1000"

        # Colors
        self.grid_color = repr(get_color(wx.SYS_COLOUR_3DSHADOW))
        self.selection_color = repr(get_color(wx.SYS_COLOUR_HIGHLIGHT))
        self.background_color = repr(get_color(wx.SYS_COLOUR_WINDOW))
        self.text_color = repr(get_color(wx.SYS_COLOUR_WINDOWTEXT))

        # Fonts

        self.font = repr(get_font_string(wx.SYS_DEFAULT_GUI_FONT))

        # Default cell font size

        self.font_default_sizes = "[6, 8, 10, 12, 14, 16, 18, 20, 24, 28, 32]"

        # Zoom

        self.minimum_zoom = "0.25"
        self.maximum_zoom = "8.0"

        # Increase and decrease factor on zoom in and zoom out
        self.zoom_factor = "0.05"

        # GPG parameters
        # --------------

        self.gpg_key_uid = repr('')

        # CSV parameters for import and export
        # ------------------------------------

        # Number of bytes for the sniffer (should be larger than 1st+2nd line)
        self.sniff_size = "65536"

        # Maximum number of characters in wx.TextCtrl
        self.max_textctrl_length = "65534"


class Config(object):
    """Configuration class for the application pyspread"""

    # Only keys in default_config are config keys

    def __init__(self, defaults=None):
        self.config_filename = "pyspreadrc"

        # The current version of pyspread
        self.version = VERSION

        if defaults is None:
            self.defaults = DefaultConfig()

        else:
            self.defaults = defaults()

        self.data = DefaultConfig()

        self.cfg_file = wx.Config(self.config_filename)

        # Config keys to be resetted to default value on version upgrades
        self.reset_on_version_change = ["window_layout"]

        self.load()

    def __getitem__(self, key):
        """Main config element read access"""

        if key == "version":
            return self.version

        return literal_eval(getattr(self.data, key))

    def __setitem__(self, key, value):
        """Main config element write access"""

        setattr(self.data, key, value)

    def load(self):
        """Loads configuration file"""

        # Config files prior to 0.2.4 dor not have config version keys
        old_config = not self.cfg_file.Exists("config_version")

        # Reset data
        self.data.__dict__.update(self.defaults.__dict__)

        for key in self.defaults.__dict__:
            if self.cfg_file.Exists(key):
                setattr(self.data, key, self.cfg_file.Read(key))

        # Reset keys that should be reset on version upgrades
        if old_config or self.version != self.data.config_version:
            for key in self.reset_on_version_change:
                setattr(self.data, key, getattr(DefaultConfig(), key))
            self.data.config_version = self.version

        # Reset GPG key if version prior 0.2.4
        # because of pyme -> gnupg migration

        if old_config:
            key = "gpg_key_uid"
            setattr(self.data, key, getattr(DefaultConfig(), key))

    def save(self):
        """Saves configuration file"""

        ## TODO: Set permissions here, SetUmask

        for key in self.defaults.__dict__:
            data = getattr(self.data, key)

            self.cfg_file.Write(key, data)

config = Config()
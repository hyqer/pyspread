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
i18n
====

This module handles internationalization

"""

import os
import gettext
import sys

import wx

#  Translation files are located in
#  @LOCALE_DIR@/@LANGUAGE@/LC_MESSAGES/@APP_NAME@.mo
APP_NAME = "pyspread"

APP_DIR = os.path.abspath(os.path.dirname(sys.argv[0]))

# .mo files  are located in APP_Dir/locale/LANGUAGECODE/LC_MESSAGES/
LOCALE_DIR = os.path.join(APP_DIR, 'locale')

# Choose the language
# -------------------
# A list is provided,gettext uses the first translation available in the list
DEFAULT_LANGUAGES = ['en_US']

langid = wx.LANGUAGE_DEFAULT
wxlocale = wx.Locale(langid)
languages = [wxlocale.GetCanonicalName()]

# Languages and locations of translations are in env + default locale

#languages += DEFAULT_LANGUAGES

mo_location = LOCALE_DIR

# gettext initialization
# ----------------------

language = gettext.translation(APP_NAME, mo_location, languages=languages,
                               fallback=True)
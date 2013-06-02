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
test_selection
==============

Unit tests for selection.py

"""

import os
import sys

import wx
app = wx.App()

TESTPATH = "/".join(os.path.realpath(__file__).split("/")[:-1]) + "/"
sys.path.insert(0, TESTPATH)
sys.path.insert(0, TESTPATH + "/../../..")
sys.path.insert(0, TESTPATH + "/../..")

from src.lib.testlib import params, pytest_generate_tests

from src.lib.selection import Selection


class TestSelection(object):
    """Unit tests for Selection"""

    param_test_nonzero = [
        {'sel': Selection([], [], [], [], [(32), (34)])},
        {'sel': Selection([], [], [], [], [(32, 53), (34, 56)])},
        {'sel': Selection([], [], [], [3], [])},
        {'sel': Selection([], [], [2], [], [])},
        {'sel': Selection([(1, 43)], [(2, 354)], [], [], [])},
    ]

    @params(param_test_nonzero)
    def test_nonzero(self, sel):
        """Unit test for __nonzero__"""

        assert sel

    def test_repr(self):
        """Unit test for __repr__"""

        selection = Selection([], [], [], [], [(32, 53), (34, 56)])
        assert str(selection) == \
            "Selection([], [], [], [], [(32, 53), (34, 56)])"

    param_test_eq = [
        {'sel1': Selection([], [], [], [], [(32, 53), (34, 56)]),
         'sel2': Selection([], [], [], [], [(32, 53), (34, 56)]),
         'res': True},
        {'sel1': Selection([], [], [], [], [(32, 53)]),
         'sel2': Selection([], [], [], [], [(32, 53), (34, 56)]),
         'res': False},
        {'sel1': Selection([], [], [], [], [(34, 56), (32, 53)]),
         'sel2': Selection([], [], [], [], [(32, 53), (34, 56)]),
         'res': False},
        {'sel1': Selection([], [], [3, 5], [1, 4], [(32, 53)]),
         'sel2': Selection([], [], [5, 3], [1, 4], [(32, 53)]),
         'res': False},
        {'sel1': Selection([], [], [3, 5], [1, 4], [(32, 2343)]),
         'sel2': Selection([], [], [5, 3], [1, 4], [(32, 53)]),
         'res': False},
        {'sel1': Selection([(2, 3), (9, 10)], [(5, 9), (100, 34)], [], [], []),
         'sel2': Selection([(2, 3), (9, 10)], [(5, 9), (100, 34)], [], [], []),
         'res': True},
        {'sel1': Selection([(9, 10), (2, 3)], [(100, 34), (5, 9)], [], [], []),
         'sel2': Selection([(2, 3), (9, 10)], [(5, 9), (100, 34)], [], [], []),
         'res': False},
    ]

    @params(param_test_eq)
    def test_eq(self, sel1, sel2, res):
        """Unit test for __eq__"""

        assert (sel1 == sel2) == res
        assert (sel2 == sel1) == res

    param_test_contains = [
        # Cell selections
        {'sel': Selection([], [], [], [], [(32, 53), (34, 56)]),
         'key': (32, 53), 'res': True},
        {'sel': Selection([], [], [], [], [(32, 53), (34, 56)]),
         'key': (23, 34534534), 'res': False},
        # Block selections
        {'sel': Selection([(4, 5)], [(100, 200)], [], [], []),
         'key': (4, 5), 'res': True},
        {'sel': Selection([(4, 5)], [(100, 200)], [], [], []),
         'key': (99, 199), 'res': True},
        {'sel': Selection([(4, 5)], [(100, 200)], [], [], []),
         'key': (100, 200), 'res': True},
        {'sel': Selection([(4, 5)], [(100, 200)], [], [], []),
         'key': (0, 0), 'res': False},
        {'sel': Selection([(4, 5)], [(100, 200)], [], [], []),
         'key': (0, 1), 'res': False},
        {'sel': Selection([(4, 5)], [(100, 200)], [], [], []),
         'key': (1, 0), 'res': False},
        {'sel': Selection([(4, 5)], [(100, 200)], [], [], []),
         'key': (4, 4), 'res': False},
        {'sel': Selection([(4, 5)], [(100, 200)], [], [], []),
         'key': (3, 5), 'res': False},
        {'sel': Selection([(4, 5)], [(100, 200)], [], [], []),
         'key': (100, 201), 'res': False},
        {'sel': Selection([(4, 5)], [(100, 200)], [], [], []),
         'key': (10**10, 10**10), 'res': False},
        # Row selection
        {'sel': Selection([], [], [3], [], []),
         'key': (0, 0), 'res': False},
        {'sel': Selection([], [], [3], [], []),
         'key': (3, 0), 'res': True},
        {'sel': Selection([], [], [3, 5], [], []),
         'key': (3, 0), 'res': True},
        {'sel': Selection([], [], [3, 5], [], []),
         'key': (5, 0), 'res': True},
        {'sel': Selection([], [], [3, 5], [], []),
         'key': (4, 0), 'res': False},
        # Column selection
        {'sel': Selection([], [], [], [2, 234, 434], []),
         'key': (234, 234), 'res': True},
        {'sel': Selection([], [], [], [2, 234, 434], []),
         'key': (234, 0), 'res': False},
        # Combinations
        {'sel': Selection([(0, 0)], [(90, 23)], [0], [0, 34], [((0, 0))]),
         'key': (0, 0), 'res': True},
    ]

    @params(param_test_contains)
    def test_contains(self, sel, key, res):
        """Unit test for __contains__

        Used in: ele in selection

        """

        assert (key in sel) == res

    param_test_add = [
        {'sel': Selection([], [], [], [], [(0, 0), (34, 56)]),
         'add': (4, 5),
         'res': Selection([], [], [], [], [(4, 5), (38, 61)])},
        {'sel': Selection([], [], [], [], [(0, 0), (34, 56)]),
         'add': (0, 0),
         'res': Selection([], [], [], [], [(0, 0), (34, 56)])},
        {'sel': Selection([], [], [], [], [(0, 0), (34, 56)]),
         'add': (-3, -24),
         'res': Selection([], [], [], [], [(-3, -24), (31, 32)])},
        {'sel': Selection([(2, 5)], [(4, 6)], [1], [0], [(0, 0), (34, 56)]),
         'add': (1, 0),
         'res': Selection([(3, 5)], [(5, 6)], [2], [0], [(1, 0), (35, 56)])},
    ]

    @params(param_test_add)
    def test_add(self, sel, add, res):
        """Unit test for __add__"""

        val = sel + add
        assert val == res

    param_test_insert = [
        {'sel': Selection([], [], [2], [], []),
         'point': 1, 'number': 10, 'axis': 0,
         'res': Selection([], [], [12], [], [])},
        {'sel': Selection([], [], [], [], [(234, 23)]),
         'point': 20, 'number': 4, 'axis': 1,
         'res': Selection([], [], [], [], [(234, 27)])},
        {'sel': Selection([], [], [21], [33, 44], [(234, 23)]),
         'point': 40, 'number': 4, 'axis': 1,
         'res': Selection([], [], [21], [33, 48], [(234, 23)])},
    ]

    @params(param_test_insert)
    def test_insert(self, sel, point, number, axis, res):
        """Unit test for insert"""

        sel.insert(point, number, axis)
        assert sel == res

    param_test_get_bbox = [
        {'sel': Selection([], [], [], [], [(32, 53), (34, 56)]),
         'res': ((32, 53), (34, 56))},
        {'sel': Selection([(4, 5)], [(100, 200)], [], [], []),
         'res': ((4, 5), (100, 200))},
    ]

    @params(param_test_get_bbox)
    def test_get_bbox(self, sel, res):
        """Unit test for get_bbox"""

        assert sel.get_bbox() == res

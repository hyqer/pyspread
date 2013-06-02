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
testlib.py
==========

Helper functions for unit tests

"""

# Standard grid values for initial filling

grid_values = { \
    (0, 0, 0): "'Test'",
    (999, 0, 0): "1",
    (999, 99, 0): "$^%&$^",
    (0, 1, 0): "1",
    (0, 2, 0): "2",
    (1, 1, 0): "3",
    (1, 2, 0): "4",
    (1, 2, 2): "78",
}

# Helper methods for efficient testing


def _fill_grid(grid, values):
    """Fills grid with values (use e. g. grid_values)"""

    for key in values:
        grid.code_array[key] = values[key]


def restore_basic_grid(grid):
    """Restores basic, filled grid"""

    default_test_shape = (1000, 100, 3)

    grid.actions.clear(default_test_shape)
    _fill_grid(grid, grid_values)


def basic_setup_test(grid, func, test_key, test_val, *args, **kwargs):
    """Sets up basic test env, runs func and tests test_key in grid"""

    restore_basic_grid(grid)

    func(*args, **kwargs)

    assert grid.code_array(test_key) == test_val


def params(funcarglist):
    """Test function parameter decorator

    Provides arguments based on the dict funcarglist.

    """

    def wrapper(function):
        function.funcarglist = funcarglist
        return function
    return wrapper


def pytest_generate_tests(metafunc):
    """Enables params to work in py.test environment"""

    for funcargs in getattr(metafunc.function, 'funcarglist', ()):
        metafunc.addcall(funcargs=funcargs)
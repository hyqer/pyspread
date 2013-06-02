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
test_gpg
========

Unit tests for gpg.py

"""

import os
import sys

import wx
app = wx.App()

TESTPATH = "/".join(os.path.realpath(__file__).split("/")[:-1]) + "/"
sys.path.insert(0, TESTPATH)
sys.path.insert(0, TESTPATH + "/../../..")
sys.path.insert(0, TESTPATH + "/../..")

import src.lib.gpg as gpg
from src.lib.testlib import params, pytest_generate_tests


def _set_sig(filename, sigfilename):
    """Creates a signature sigfilename for file filename"""

    signature = gpg.sign(filename).data

    sigfile = open(sigfilename, "w")
    sigfile.write(signature)
    sigfile.close()


def test_sign():
    """Unit test for sign"""

    filename = TESTPATH + "test1.pys"
    sigfilename = filename + ".sig"

    _set_sig(filename, sigfilename)

    valid = gpg.verify(sigfilename, filename)

    assert valid

param_verify = [
    {'filename': TESTPATH + "test1.pys",
     'sigfilename': TESTPATH + "test1.pys.sig", 'valid': 1},
    {'filename': TESTPATH + "test1.pys",
     'sigfilename': TESTPATH + "test1.pys.empty", 'valid': 0},
    {'filename': TESTPATH + "test1.pys",
     'sigfilename': TESTPATH + "test1.pys.nonsense", 'valid': 0},
]


@params(param_verify)
def test_sign_verify(filename, sigfilename, valid):
    """Unit test for verify"""

    if valid:
        assert gpg.verify(sigfilename, filename)
    else:
        assert not gpg.verify(sigfilename, filename)

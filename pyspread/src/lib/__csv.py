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
csvlib
======

Provides
--------

 * sniff: Sniffs CSV dialect and header info
 * get_first_line
 * csv_digest_gen
 * cell_key_val_gen
 * Digest: Converts any object to target type as good as possible
 * CsvInterface
 * TxtGenerator

"""

import csv
import datetime
import os
import types

from src.config import config

from src.gui._events import post_command_event, StatusBarEventMixin

import src.lib.i18n as i18n

#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


def sniff(filepath):
    """
    Sniffs CSV dialect and header info from csvfilepath

    Returns a tuple of dialect and has_header

    """

    try:
        csvfile = open(filepath, "rb")
        sample = csvfile.read(config["sniff_size"])
    finally:
        csvfile.close()

    sniffer = csv.Sniffer()
    dialect = sniffer.sniff(sample)()
    has_header = sniffer.has_header(sample)

    return dialect, has_header


def get_first_line(filepath, dialect):
    """Returns List of first line items of file filepath"""

    try:
        csvfile = open(filepath, "rb")
        csvreader = csv.reader(csvfile, dialect=dialect)

        for first_line in csvreader:
            break

    finally:
        csvfile.close()

    return first_line


def digested_line(line, digest_types):
    """Returns list of digested values in line"""

    digested_line = []
    for i, ele in enumerate(line):
        try:
            digest_key = digest_types[i]

        except IndexError:
            digest_key = digest_types[0]

        digest = Digest(acceptable_types=[digest_key])

        try:
            digested_line.append(repr(digest(ele)))

        except Exception, err:
            digested_line.append(str(err))

    return digested_line


def csv_digest_gen(filepath, dialect, has_header, digest_types):
    """Generator of digested values from csv file in filepath

    Parameters
    ----------
    filepath:String
    \tFile path of csv file to read
    dialect: Object
    \tCsv dialect
    digest_types: tuple of types
    \tTypes of data for each col

    """

    try:
        csvfile = open(filepath, "rb")
        csvreader = csv.reader(csvfile, dialect=dialect)

        if has_header:
            # Ignore first line
            for line in csvreader:
                break

        for line in csvreader:
            yield digested_line(line, digest_types)

    finally:
        csvfile.close()


def cell_key_val_gen(iterable, shape, topleft=(0, 0)):
    """Generator of row, col, value tuple from iterable of iterables

    it: Iterable of iterables
    \tMatrix that shall be mapped on target grid
    shape: Tuple of Integer
    \tShape of target grid
    topleft: 2-tuple of Integer
    \tTop left cell for insertion of it

    """

    top, left = topleft

    for __row, line in enumerate(iterable):
        row = top + __row
        if row >= shape[0]:
            break

        for __col, value in enumerate(line):
            col = left + __col
            if col >= shape[1]:
                break

            yield row, col, value


class Digest(object):
    """
    Maps types to types that are acceptable for target class

    The Digest class handles data of unknown type. Its objects are
    callable. They return an acceptable data type, which may be the fallback
    data type if everything else fails.

    The Digest class is intended to be subclassed by the target class.

    Parameters:
    -----------

    acceptable_types: list of types, defaults to None
    \tTypes that are acceptable for the target_class.
    \tThey are ordered highest preference first
    \tIf None, the string representation of the object is returned

    fallback_type: type, defaults to types.UnicodeType
    \t

    """

    def __init__(self, acceptable_types=None, fallback_type=None):

        if acceptable_types is None:
            acceptable_types = [None]

        self.acceptable_types = acceptable_types
        self.fallback_type = fallback_type

        # Type conversion functions

        def make_string(obj):
            """Makes a string object from any object"""

            if type(obj) is types.StringType:
                return obj

            if obj is None:
                return ""
            try:
                return str(obj)
            except Exception:
                return repr(obj)

        def make_unicode(obj):
            """Makes a unicode object from any object"""

            if type(obj) is types.UnicodeType:
                return obj

            if obj is None:
                return u""

            return unicode(obj)

        def make_slice(obj):
            """Makes a slice object from slice or int"""

            if isinstance(obj, slice):
                return obj

            return slice(obj, obj + 1, None)

        def make_date(obj):
            """Makes a date from comparable types"""

            from dateutil.parser import parse
            return parse(obj).date()

        def make_datetime(obj):
            """Makes a datetime from comparable types"""

            from dateutil.parser import parse
            return parse(obj)

        def make_time(obj):
            """Makes a time from comparable types"""

            from dateutil.parser import parse
            return parse(obj).time()

        def make_object(obj):
            """Returns the object"""

            return obj

        self.typehandlers = {
            None: repr,
            types.StringType: make_string,
            types.UnicodeType: make_unicode,
            types.SliceType: make_slice,
            types.BooleanType: bool,
            types.ObjectType: make_object,
            types.IntType: int,
            types.FloatType: float,
            types.CodeType: make_object,
            datetime.date: make_date,
            datetime.datetime: make_datetime,
            datetime.time: make_time,
        }

        if self.fallback_type is not None and \
           self.fallback_type not in self.typehandlers:

            err_msg = _("Fallback type {type} unknown.").\
                format(type=str(self.fallback_type))

            raise NotImplementedError(err_msg)

    def __call__(self, orig_obj):
        """Returns acceptable object"""

        errormessage = ""

        type_found = False

        for target_type in self.acceptable_types:
            if target_type in self.typehandlers:
                type_found = True
                break
        if not type_found:
            target_type = self.fallback_type

        try:
            acceptable_obj = self.typehandlers[target_type](orig_obj)
            return acceptable_obj
        except TypeError, err:
            errormessage += str(err)

        try:
            acceptable_obj = self.typehandlers[self.fallback_type](orig_obj)
            return acceptable_obj
        except TypeError, err:
            errormessage += str(err)

        return errormessage

# end of class Digest


class CsvInterface(StatusBarEventMixin):
    """CSV interface class

    Provides
    --------
     * __iter__: CSV reader - generator of generators of csv data cell content
     * write: CSV writer

    """

    def __init__(self, main_window, path, dialect, digest_types, has_header):
        self.main_window = main_window
        self.path = path
        self.csvfilename = os.path.split(path)[1]

        self.dialect = dialect
        self.digest_types = digest_types
        self.has_header = has_header

        self.first_line = False

    def __iter__(self):
        """Generator of generators that yield csv data"""

        try:
            csv_file = open(self.path, "r")
            csv_reader = csv.reader(csv_file, self.dialect)

        except IOError, err:
            statustext = "Error opening file " + self.path + "."
            post_command_event(self.main_window, self.StatusBarMsg,
                               text=statustext)

            csv_file = []

        self.first_line = self.has_header

        try:
            for line in csv_reader:
                yield self._get_csv_cells_gen(line)
                self.first_line = False

        except Exception, err:
            msg = 'The file "' + self.csvfilename + '" only partly loaded.' + \
                  '\n \nError message:\n' + str(err)
            short_msg = 'Error reading CSV file'
            self.main_window.interfaces.display_warning(msg, short_msg)

        finally:
            statustext = "File " + self.csvfilename + " imported successfully."
            post_command_event(self.main_window, self.StatusBarMsg,
                               text=statustext)

        csv_file.close()

    def _get_csv_cells_gen(self, line):
        """Generator of values in a csv line"""

        digest_types = self.digest_types

        for j, value in enumerate(line):
            if self.first_line:
                digest_key = None
                digest = lambda x: x
            else:
                try:
                    digest_key = digest_types[j]
                except IndexError:
                    digest_key = digest_types[0]

                digest = Digest(acceptable_types=[digest_key])

            try:
                digest_res = digest(value)

                if digest_key is not None and digest_res != "\b" and \
                   digest_key is not types.CodeType:
                    digest_res = repr(digest_res)
                elif digest_res == "\b":
                    digest_res = None

            except Exception, err:
                digest_res = str(err)

            yield digest_res

    def write(self, iterable):
        """Writes values from iterable into CSV file"""

        io_error_text = _("Error writing to file {filepath}.")
        io_error_text = io_error_text.format(filepath=self.path)

        try:
            csvfile = open(self.path, "wb")

        except IOError:
            txt = \
                _("Error opening file {filepath}.").format(filepath=self.path)
            try:
                post_command_event(self.main_window, self.StatusBarMsg,
                                   text=txt)
            except TypeError:
                # The main window does not exist any more
                pass
            return False

        csv_writer = csv.writer(csvfile, self.dialect)

        for line in iterable:
            csv_writer.writerow(line)

        csvfile.close()


class TxtGenerator(StatusBarEventMixin):
    """Generator of generators of Whitespace separated txt file cell content"""

    def __init__(self, main_window, path):
        self.main_window = main_window
        try:
            self.infile = open(path)

        except IOError:
            statustext = "Error opening file " + path + "."
            post_command_event(self.main_window, self.StatusBarMsg,
                               text=statustext)
            self.infile = None

    def __iter__(self):

        # If self.infile is None then stopiteration is reached immediately
        if self.infile is None:
            return

        for line in self.infile:
            yield (col for col in line.split())

        self.infile.close()

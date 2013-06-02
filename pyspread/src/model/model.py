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

Model
=====

The model contains the core data structures of pyspread.
It is divided into layers.

Layer 3: CodeArray
Layer 2: DataArray
Layer 1: DictGrid
Layer 0: KeyValueStore

"""

import ast
import base64
import bz2
from copy import copy
import cStringIO
import datetime
from itertools import imap, ifilter, product
import re
import sys
from types import SliceType, IntType

import numpy

import wx

from src.config import config

from src.lib.typechecks import is_slice_like, is_string_like, is_generator_like
from src.lib.selection import Selection

import src.lib.charts as charts

from unredo import UnRedo


class KeyValueStore(dict):
    """Key-Value store in memory. Currently a dict with default value None.

    This class represents layer 0 of the model.

    """

    def __missing__(self, value):
        """Returns the default value None"""

        return

# End of class KeyValueStore

# -----------------------------------------------------------------------------


class CellAttributes(list):
    """Stores cell formatting attributes in a list of 3 - tuples

    The first element of each tuple is a Selection.
    The second element is the table
    The third element is a dict of attributes that are altered.

    The class provides attribute read access to single cells via __getitem__
    Otherwise it behaves similar to a list.

    Note that for the method undoable_append to work, unredo has to be
    defined as class attribute.

    """

    default_cell_attributes = {
        "borderwidth_bottom": 1,
        "borderwidth_right": 1,
        "bordercolor_bottom": wx.Colour(*config["grid_color"]).GetRGB(),
        "bordercolor_right": wx.Colour(*config["grid_color"]).GetRGB(),
        "bgcolor": wx.Colour(*config["background_color"]).GetRGB(),
        "textfont": config["font"],
        "pointsize": 10,
        "fontweight": wx.NORMAL,
        "fontstyle": wx.NORMAL,
        "textcolor": wx.Colour(*config["text_color"]).GetRGB(),
        "underline": False,
        "strikethrough": False,
        "angle": 0.0,
        "column-width": 150,
        "row-height": 26,
        "vertical_align": "top",
        "justification": "left",
        "frozen": False,
        "merge_area": None,
    }

    # Cache for __getattr__ maps key to tuple of len and attr_dict

    _attr_cache = {}

    def undoable_append(self, value):
        """Appends item to list and provides undo and redo functionality"""

        undo_operation = (self.pop, [])
        redo_operation = (self.undoable_append, [value])

        self.unredo.append(undo_operation, redo_operation)

        self.unredo.mark()

        self.append(value)
        self._attr_cache.clear()

    def __getitem__(self, key):
        """Returns attribute dict for a single key"""

        assert not any(type(key_ele) is SliceType for key_ele in key)

        if key in self._attr_cache:
            cache_len, cache_dict = self._attr_cache[key]

            # Use cache result only if no new attrs have been defined
            if cache_len == len(self):
                return cache_dict

        row, col, tab = key

        result_dict = copy(self.default_cell_attributes)

        for selection, table, attr_dict in self:
            if tab == table and (row, col) in selection:
                result_dict.update(attr_dict)

        # Upddate cache with current length and dict
        self._attr_cache[key] = (len(self), result_dict)

        return result_dict

    def get_merging_cell(self, key):
        """Returns key of cell that merges the cell key

        or None if cell key not merged

        Parameters
        ----------
        key: 3-tuple of Integer
        \tThe key of the cell that is merged

        """

        row, col, tab = key

        merging_cell = None

        def is_in_merge_area(row, col, merge_area):
            top, left, bottom, right = merge_area
            return top <= row <= bottom and left <= col <= right

        for selection, table, attr_dict in self:
            try:
                merge_area = attr_dict["merge_area"]
                if table == tab and merge_area is not None:
                    # We have a merge area in the cell's table
                    if is_in_merge_area(row, col, merge_area):
                        merging_cell = merge_area[0], merge_area[1], tab
            except KeyError:
                pass

        return merging_cell

# End of class CellAttributes


class ParserMixin(object):
    """Provides parser methods for DictGrid"""

    def _split_tidy(self, string, maxsplit=None):
        """Rstrips string for \n and splits string for \t"""

        if maxsplit is None:
            return string.rstrip("\n").split("\t")
        else:
            return string.rstrip("\n").split("\t", maxsplit)

    def _get_key(self, *keystrings):
        """Returns int key tuple from key string list"""

        return tuple(imap(int, keystrings))

    def parse_to_shape(self, line):
        """Parses line and adjusts grid shape"""

        self.shape = self._get_key(*self._split_tidy(line))

    def parse_to_grid(self, line):
        """Parses line and inserts grid data"""

        row, col, tab, code = self._split_tidy(line, maxsplit=3)
        key = self._get_key(row, col, tab)

        self[key] = unicode(code, encoding='utf-8')

    def parse_to_attribute(self, line):
        """Parses line and appends cell attribute"""

        splitline = self._split_tidy(line)

        selection_data = map(ast.literal_eval, splitline[:5])
        selection = Selection(*selection_data)

        tab = int(splitline[5])

        attrs = {}
        for col, ele in enumerate(splitline[6:]):
            if not (col % 2):
                # Odd entries are keys
                key = ast.literal_eval(ele)

            else:
                # Even cols are values
                attrs[key] = ast.literal_eval(ele)

        self.cell_attributes.append((selection, tab, attrs))

    def parse_to_height(self, line):
        """Parses line and inserts row hight"""

        # Split with maxsplit 3
        row, tab, height = self._split_tidy(line)
        key = self._get_key(row, tab)

        try:
            self.row_heights[key] = float(height)

        except ValueError:
            pass

    def parse_to_width(self, line):
        """Parses line and inserts column width"""

        # Split with maxsplit 3
        col, tab, width = self._split_tidy(line)
        key = self._get_key(col, tab)

        try:
            self.col_widths[key] = float(width)

        except ValueError:
            pass

    def parse_to_macro(self, line):
        """Appends line to macro"""

        self.macros += line

# End of class ParserMixin


class StringGeneratorMixin(object):
    """String generation methods for DictGrid"""

    def grid_to_strings(self):
        """Yields a string that represents the grid content for saving

        Format
        ------
        [shape]
        rows\tcols\ttabs\n
        [grid]
        row\tcol\ttab\tcode\n
        row\tcol\ttab\tcode\n
        ...

        """

        yield u"[shape]\n"
        yield u"\t".join(map(unicode, self.shape)) + u"\n"

        yield u"[grid]\n"

        for key in self:
            key_str = u"\t".join(repr(ele) for ele in key)
            code_str = unicode(self[key])

            yield key_str + u"\t" + code_str + u"\n"

    def attributes_to_strings(self):
        """Yields a string that represents the cell attributes for saving

        Format
        ------

        [attributes]
        selection[0]\t...\tselection[5]\ttab\tkey\tvalue\t...\tkey\tvalue\n
        ...

        """

        yield u"[attributes]\n"

        for selection, tab, attr_dict in self.cell_attributes:
            sel_list = [selection.block_tl, selection.block_br,
                        selection.rows, selection.cols, selection.cells]

            tab_list = [tab]

            attr_dict_list = []
            for key in attr_dict:
                attr_dict_list.append(key)
                attr_dict_list.append(attr_dict[key])

            line_list = map(repr, sel_list + tab_list + attr_dict_list)

            yield u"\t".join(line_list) + u"\n"

    def heights_to_strings(self):
        """Yields a string that represents the row heights for saving

        Format
        ------

        [row_heights]
        row\ttab\tvalue\n
        ...

        """

        yield u"[row_heights]\n"

        for row, tab in self.row_heights:
            height = self.row_heights[(row, tab)]
            height_strings = map(repr, [row, tab, height])
            yield u"\t".join(height_strings) + u"\n"

    def widths_to_strings(self):
        """Yields a string that represents the column widths for saving

        Format
        ------

        [col_widths]
        col\ttab\tvalue\n
        ...

        """

        yield u"[col_widths]\n"

        for col, tab in self.col_widths:
            width = self.col_widths[(col, tab)]
            width_strings = map(repr, [col, tab, width])
            yield u"\t".join(width_strings) + u"\n"

    def macros_to_strings(self):
        """Yields a string that represents the content for saving

        Format
        ------

        [macros]
        Macro code

        """

        yield u"[macros]\n"

        for line in self.macros.split("\n"):
            yield line + u"\n"

# End of class StringGeneratorMixin


class DictGrid(KeyValueStore, ParserMixin, StringGeneratorMixin):
    """The core data class with all information that is stored in a pys file.

    Besides grid code access via standard dict operations, it provides
    the following attributes:

    * cell_attributes: Stores cell formatting attributes
    * macros:          String of all macros

    This class represents layer 1 of the model.

    Parameters
    ----------
    shape: n-tuple of integer
    \tShape of the grid

    """

    def __init__(self, shape):
        KeyValueStore.__init__(self)

        self.shape = shape

        self.cell_attributes = CellAttributes()

        self.macros = u""

        self.row_heights = {}  # Keys have the format (row, table)
        self.col_widths = {}  # Keys have the format (col, table)

    def __getitem__(self, key):

        shape = self.shape

        for axis, key_ele in enumerate(key):
            if shape[axis] <= key_ele or key_ele < -shape[axis]:
                msg = "Grid index {key} outside grid shape {shape}."
                msg = msg.format(key=key, shape=shape)
                raise IndexError(msg)

        return KeyValueStore.__getitem__(self, key)

# End of class DictGrid

# -----------------------------------------------------------------------------


class DataArray(object):
    """DataArray provides enhanced grid read/write access.

    Enhancements comprise:
     * Slicing
     * Multi-dimensional operations such as insertion and deletion along 1 axis
     * Undo/redo operations

    This class represents layer 2 of the model.

    Parameters
    ----------
    shape: n-tuple of integer
    \tShape of the grid

    """

    def __init__(self, shape):
        self.dict_grid = DictGrid(shape)

        # Undo and redo management
        self.unredo = UnRedo()
        self.dict_grid.cell_attributes.unredo = self.unredo

        # Safe mode
        self.safe_mode = False

    # Row and column attributes mask
    # Keys have the format (row, table)

    @property
    def row_heights(self):
        """Returns row_heights dict"""

        return self.dict_grid.row_heights

    @property
    def col_widths(self):
        """Returns col_widths dict"""

        return self.dict_grid.col_widths

    # Cell attributes mask
    @property
    def cell_attributes(self):
        """Returns cell_attributes list"""

        return self.dict_grid.cell_attributes

    def __iter__(self):
        """Returns iterator over self.dict_grid"""

        return iter(self.dict_grid)

    def _get_macros(self):
        """Returns macros string"""

        return self.dict_grid.macros

    def _set_macros(self, macros):
        """Sets  macros string"""

        self.dict_grid.macros = macros

    macros = property(_get_macros, _set_macros)

    def keys(self):
        """Returns keys in self.dict_grid"""

        return self.dict_grid.keys()

    def pop(self, key, mark_unredo=True):
        """Pops dict_grid with undo and redo support

        Parameters
        ----------
        key: 3-tuple of Integer
        \tCell key that shall be popped
        mark_unredo: Boolean, defaults to True
        \tIf True then an unredo marker is set after the operation

        """

        # UnRedo support

        try:
            undo_operation = (self.__setitem__, [key, self.dict_grid[key],
                                                 mark_unredo])
            redo_operation = (self.pop, [key, mark_unredo])

            self.unredo.append(undo_operation, redo_operation)

            if mark_unredo:
                self.unredo.mark()

        except KeyError:
            # If key not present then unredo is not necessary
            pass

        # End UnRedo support

        return self.dict_grid.pop(key)

    # Shape mask

    def _get_shape(self):
        """Returns dict_grid shape"""

        return self.dict_grid.shape

    def _set_shape(self, shape, mark_unredo=True):
        """Deletes all cells beyond new shape and sets dict_grid shape

        Parameters
        ----------
        shape: 3-tuple of Integer
        \tTarget shape for grid
        mark_unredo: Boolean, defaults to True
        \tIf True then an unredo marker is set after the operation

        """

        # Delete each cell that is beyond new borders

        old_shape = self.shape

        if any(new_axis < old_axis
               for new_axis, old_axis in zip(shape, old_shape)):
            for key in self.dict_grid.keys():
                if any(key_ele >= new_axis
                       for key_ele, new_axis in zip(key, shape)):
                    self.pop(key)

        # Set dict_grid shape attribute

        self.dict_grid.shape = shape

        # UnRedo support

        undo_operation = (self._set_shape, [old_shape, mark_unredo])
        redo_operation = (self._set_shape, [shape, mark_unredo])

        self.unredo.append(undo_operation, redo_operation)

        if mark_unredo:
            self.unredo.mark()

        # End UnRedo support

    shape = property(_get_shape, _set_shape)

    # Pickle support

    def __getstate__(self):
        """Returns dict_grid for pickling

        Note that all persistent data is contained in the DictGrid class

        """

        return {"dict_grid": self.dict_grid}

    def __str__(self):
        return self.dict_grid.__str__()

    # Slice support

    def __getitem__(self, key):
        """Adds slicing access to cell code retrieval

        The cells are returned as a generator of generators, of ... of unicode.

        Parameters
        ----------
        key: n-tuple of integer or slice
        \tKeys of the cell code that is returned

        Note
        ----
        Classical Excel type addressing (A$1, ...) may be added here

        """

        for key_ele in key:
            if is_slice_like(key_ele):
                # We have something slice-like here

                return self.cell_array_generator(key)

            elif is_string_like(key_ele):
                # We have something string-like here
                msg = "Cell string based access not implemented"
                raise NotImplementedError(msg)

        # key_ele should be a single cell

        return self.dict_grid[key]

    def __setitem__(self, key, value, mark_unredo=True):
        """Accepts index and slice keys

        Parameters
        ----------
        key: 3-tuple of Integer or Slice object
        \tCell key(s) that shall be set
        value: Object (should be Unicode or similar)
        \tCode for cell(s) to be set
        mark_unredo: Boolean, defaults to True
        \tIf True then an unredo marker is set after the operation

        """

        single_keys_per_dim = []

        for axis, key_ele in enumerate(key):
            if is_slice_like(key_ele):
                # We have something slice-like here

                length = key[axis]
                slice_range = xrange(*key_ele.indices(length))
                single_keys_per_dim.append(slice_range)

            elif is_string_like(key_ele):
                # We have something string-like here

                raise NotImplementedError

            else:
                # key_ele is a single cell

                single_keys_per_dim.append((key_ele, ))

        single_keys = product(*single_keys_per_dim)

        unredo_mark = False

        for single_key in single_keys:
            if value:
                # UnRedo support

                old_value = self(key)

                try:
                    old_value = unicode(old_value, encoding="utf-8")
                except TypeError:
                    pass

                # We seem to have double calls on __setitem__
                # This hack catches them

                if old_value != value:

                    unredo_mark = True

                    undo_operation = (self.__setitem__,
                                      [key, old_value, mark_unredo])
                    redo_operation = (self.__setitem__,
                                      [key, value, mark_unredo])

                    self.unredo.append(undo_operation, redo_operation)

                    # End UnRedo support

                self.dict_grid[single_key] = value
            else:
                # Value is empty --> delete cell
                try:
                    self.dict_grid.pop(key)

                except (KeyError, TypeError):
                    pass

        if mark_unredo and unredo_mark:
            self.unredo.mark()

    def cell_array_generator(self, key):
        """Generator traversing cells specified in key

        Parameters
        ----------
        key: Iterable of Integer or slice
        \tThe key specifies the cell keys of the generator

        """

        for i, key_ele in enumerate(key):

            # Get first element of key that is a slice
            if type(key_ele) is SliceType:
                slc_keys = xrange(*key_ele.indices(self.dict_grid.shape[i]))
                key_list = list(key)

                key_list[i] = None

                has_subslice = any(type(ele) is SliceType for ele in key_list)

                for slc_key in slc_keys:
                    key_list[i] = slc_key

                    if has_subslice:
                        # If there is a slice left yield generator
                        yield self.cell_array_generator(key_list)

                    else:
                        # No slices? Yield value
                        yield self[tuple(key_list)]

                break

    def _adjust_shape(self, amount, axis, mark_unredo=True):
        """Changes shape along axis by amount"""

        new_shape = list(self.shape)
        new_shape[axis] += amount

        self._set_shape(tuple(new_shape), mark_unredo=mark_unredo)

    def _set_cell_attributes(self, value):
        """Setter for cell_atributes"""

        # Empty cell_attributes first
        self.cell_attributes[:] = []
        self.cell_attributes.extend(value)

    def _adjust_cell_attributes(self, insertion_point, no_to_insert, axis):
        """Adjusts cell attributes on insertion/deletion"""

        assert axis in [0, 1, 2]

        if axis < 2:
            # Adjust selections
            for selection, _, _ in self.cell_attributes:
                selection.insert(insertion_point, no_to_insert, axis)

            self.cell_attributes._attr_cache.clear()

            # Adjust row heights and col widths
            cell_sizes = self.col_widths if axis else self.row_heights

            new_sizes = {}

            for pos, tab in cell_sizes:
                if pos > insertion_point:
                    new_sizes[(pos + no_to_insert, tab)] = \
                        cell_sizes[(pos, tab)]
                    cell_sizes[(pos, tab)] = None
                else:
                    new_sizes[(pos, tab)] = cell_sizes[(pos, tab)]

            cell_sizes.update(new_sizes)

        elif axis == 2:
            # Adjust tabs
            new_tabs = []
            for _, old_tab, _ in self.cell_attributes:
                new_tabs.append(old_tab + no_to_insert
                                if old_tab > insertion_point else old_tab)

            for i, new_tab in new_tabs:
                self.cell_attributes[i][1] = new_tab

            self.cell_attributes._attr_cache.clear()

        else:
            raise ValueError("Axis must be in [0, 1, 2]")

        # Make undoable

        undo_operation = (self._adjust_cell_attributes,
                          [insertion_point, -no_to_insert, axis])
        redo_operation = (self._adjust_cell_attributes,
                          [insertion_point, no_to_insert, axis])

        self.unredo.append(undo_operation, redo_operation)

    def insert(self, insertion_point, no_to_insert, axis):
        """Inserts no_to_insert rows/cols/tabs/... before insertion_point

        Parameters
        ----------

        insertion_point: Integer
        \tPont on axis, before which insertion takes place
        no_to_insert: Integer >= 0
        \tNumber of rows/cols/tabs that shall be inserted
        axis: Integer
        \tSpecifies number of dimension, i.e. 0 == row, 1 == col, ...

        """

        if not 0 <= axis <= len(self.shape):
            raise ValueError("Axis not in grid dimensions")

        if insertion_point > self.shape[axis] or \
           insertion_point <= -self.shape[axis]:
            raise IndexError("Insertion point not in grid")

        new_keys = {}

        for key in self.dict_grid.keys():
            if key[axis] >= insertion_point:
                new_key = list(key)
                new_key[axis] += no_to_insert

                new_keys[tuple(new_key)] = self.pop(key, mark_unredo=False)

        self._adjust_shape(no_to_insert, axis, mark_unredo=False)

        for key in new_keys:
            self.__setitem__(key, new_keys[key], mark_unredo=False)

        self._adjust_cell_attributes(insertion_point, no_to_insert, axis)

        self.unredo.mark()

    def delete(self, deletion_point, no_to_delete, axis):
        """Deletes no_to_delete rows/cols/... starting with deletion_point

        Axis specifies number of dimension, i.e. 0 == row, 1 == col, ...

        """

        if not 0 <= axis < len(self.shape):
            raise ValueError("Axis not in grid dimensions")

        if no_to_delete < 0:
            raise ValueError("Cannot delete negative number of rows/cols/...")

        elif no_to_delete >= self.shape[axis]:
            raise ValueError("Last row/column/table must not be deleted")

        if deletion_point > self.shape[axis] or \
           deletion_point <= -self.shape[axis]:
            raise IndexError("Deletion point not in grid")

        # Store all keys that are moved here because dict iteration is unsorted
        new_key_values = {}

        # Note that the loop goes over a list that copies all dict keys
        for key in self.dict_grid.keys():
            if deletion_point <= key[axis] < deletion_point + no_to_delete:
                self.pop(key, mark_unredo=False)

            elif key[axis] >= deletion_point + no_to_delete:
                new_key = list(key)
                new_key[axis] -= no_to_delete

                new_key_values[tuple(new_key)] = \
                    self.pop(key, mark_unredo=False)

        self._adjust_cell_attributes(deletion_point, -no_to_delete, axis)

        self._adjust_shape(-no_to_delete, axis, mark_unredo=False)

        # Now re-insert moved keys

        for key in new_key_values:
            self.__setitem__(key, new_key_values[key], mark_unredo=False)

        self.unredo.mark()

    def set_row_height(self, row, tab, height):
        """Sets row height"""

        try:
            old_height = self.row_heights[(row, tab)]

        except KeyError:
            old_height = None

        if height is None:
            self.row_heights.pop((row, tab))

        else:
            self.row_heights[(row, tab)] = height

        # Make undoable

        undo_operation = (self.set_row_height, [row, tab, old_height])
        redo_operation = (self.set_row_height, [row, tab, height])

        self.unredo.append(undo_operation, redo_operation)

    def set_col_width(self, col, tab, width):
        """Sets column width"""

        try:
            old_width = self.col_widths[(col, tab)]

        except KeyError:
            old_width = None

        if width is None:
            self.col_widths.pop((col, tab))

        else:
            self.col_widths[(col, tab)] = width

        # Make undoable

        undo_operation = (self.set_col_width, [col, tab, old_width])
        redo_operation = (self.set_col_width, [col, tab, width])

        self.unredo.append(undo_operation, redo_operation)

    # Element access via call

    __call__ = __getitem__

# End of class DataArray

# -----------------------------------------------------------------------------


class CodeArray(DataArray):
    """CodeArray provides objects when accessing cells via __getitem__

    Cell code can be accessed via function call

    This class represents layer 3 of the model.

    """

    operators = (
        "+", "-", "*", "**", "/", "//", "%", "<<", ">>", "&", "|", "^", "~",
        "<", ">", "<=", ">=", "==", "!=", "<>",
    )

    # Cache for results from __getitem__ calls
    result_cache = {}

    # Cache for frozen objects
    frozen_cache = {}

    def __setitem__(self, key, value, mark_unredo=True):
        """Sets cell code and resets result cache"""

        # Prevent unchanged cells from being recalculated on cursor movement

        repr_key = repr(key)

        unchanged = (repr_key in self.result_cache and
                     value == self(key)) or \
                    ((value is None or value == "") and
                     repr_key not in self.result_cache)

        DataArray.__setitem__(self, key, value, mark_unredo=mark_unredo)

        if not unchanged:
            # Reset result cache
            self.result_cache = {}

    def __getitem__(self, key):
        """Returns _eval_cell"""

        # Frozen cell handling
        if all(type(k) is not SliceType for k in key):
            frozen_res = self.cell_attributes[key]["frozen"]
            if frozen_res:
                if repr(key) in self.frozen_cache:
                    return self.frozen_cache[repr(key)]
                else:
                    # Frozen cache is empty.
                    # Maybe we have a reload without the frozen cache
                    result = self._eval_cell(key, self(key))
                    self.frozen_cache[repr(key)] = result
                    return result

        # Normal cell handling

        if repr(key) in self.result_cache:
            return self.result_cache[repr(key)]

        elif self(key) is not None:
            result = self._eval_cell(key, self(key))
            self.result_cache[repr(key)] = result

            return result

    def _make_nested_list(self, gen):
        """Makes nested list from generator for creating numpy.array"""

        res = []

        for ele in gen:
            if ele is None:
                res.append(None)

            elif not is_string_like(ele) and is_generator_like(ele):
                # Nested generator
                res.append(self._make_nested_list(ele))

            else:
                res.append(ele)

        return res

    def _get_assignment_target_end(self, ast_module):
        """Returns position of 1st char after assignment traget.

        If there is no assignment, -1 is returned

        If there are more than one of any ( expressions or assigments)
        then a ValueError is raised.

        """

        if len(ast_module.body) > 1:
            raise ValueError("More than one expression or assignment.")

        elif len(ast_module.body) > 0 and \
                type(ast_module.body[0]) is ast.Assign:
            if len(ast_module.body[0].targets) != 1:
                raise ValueError("More than one assignment target.")
            else:
                return len(ast_module.body[0].targets[0].id)

        return -1

    def _get_updated_environment(self, env_dict=None):
        """Returns globals environment with 'magic' variable

        Parameters
        ----------
        env_dict: Dict, defaults to {'S': self}
        \tDict that maps global variable name to value

        """

        if env_dict is None:
            env_dict = {'S': self}

        env = globals().copy()
        env.update(env_dict)

        return env

    def _eval_cell(self, key, code):
        """Evaluates one cell and returns its result"""

        # Set up environment for evaluation

        env_dict = {'X': key[0], 'Y': key[1], 'Z': key[2], 'bz2': bz2,
                    'base64': base64, 'charts': charts,
                    'R': key[0], 'C': key[1], 'T': key[2], 'S': self}
        env = self._get_updated_environment(env_dict=env_dict)

        _old_code = self(key)

        # Return cell value if in safe mode

        if self.safe_mode:
            return code

        # If cell is not present return None

        if code is None:
            return

        elif is_generator_like(code):
            # We have a generator object

            return numpy.array(self._make_nested_list(code), dtype="O")

        # If only 1 term in front of the "=" --> global

        try:
            assignment_target_error = None
            module = ast.parse(code)
            assignment_target_end = self._get_assignment_target_end(module)

        except ValueError, err:
            assignment_target_error = ValueError(err)

        except AttributeError, err:
            # Attribute Error includes RunTimeError
            assignment_target_error = AttributeError(err)

        except Exception, err:
            assignment_target_error = Exception(err)

        if assignment_target_error is None and assignment_target_end != -1:
            glob_var = code[:assignment_target_end]
            expression = code.split("=", 1)[1]
            expression = expression.strip()

            # Delete result cache because assignment changes results
            self.result_cache.clear()

        else:
            glob_var = None
            expression = code

        if assignment_target_error is not None:
            result = assignment_target_error

        else:
            try:
                result = eval(expression, env, {})

            except AttributeError, err:
                # Attribute Error includes RunTimeError
                result = AttributeError(err)

            except Exception, err:
                result = Exception(err)

        # Change back cell value for evaluation from other cells
        self.dict_grid[key] = _old_code

        if glob_var is not None:
            globals().update({glob_var: result})

        return result

    def reload_modules(self):
        """Reloads modules that are available in cells"""

        import src.lib.charts as charts
        modules = [charts, bz2, base64, re, ast, sys, wx, numpy, datetime]

        for module in modules:
            reload(module)

    def clear_globals(self):
        """Clears all newly assigned globals"""

        base_keys = ['cStringIO', 'IntType', 'KeyValueStore', 'UnRedo',
                     'is_generator_like', 'StringGeneratorMixin',
                     'is_string_like', 'ParserMixin', 'bz2', 'base64',
                     '__package__', 're', 'config', '__doc__', 'SliceType',
                     'CellAttributes', 'product', 'ast', '__builtins__',
                     '__file__', 'charts', 'sys', 'is_slice_like', '__name__',
                     'copy', 'imap', 'wx', 'ifilter', 'Selection', 'DictGrid',
                     'numpy', 'CodeArray', 'DataArray', 'datetime']

        for key in globals().keys():
            if key not in base_keys:
                globals().pop(key)

    def execute_macros(self):
        """Executes all macros and returns result string

        Executes macros only when not in safe_mode

        """

        if self.safe_mode:
            return "Safe mode activated. Code not executed."

        # Windows exec does not like Windows newline
        self.macros = self.macros.replace('\r\n', '\n')

        # Set up environment for evaluation
        globals().update(self._get_updated_environment())

        # Create file-like string to capture output
        code_out = cStringIO.StringIO()
        code_err = cStringIO.StringIO()

        # Capture output and errors
        sys.stdout = code_out
        sys.stderr = code_err

        try:
            exec(self.macros, globals())

        except Exception, err:
            print err

        # Restore stdout and stderr
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

        outstring = code_out.getvalue() + code_err.getvalue()

        code_out.close()
        code_err.close()

        # Reset result cache
        self.result_cache.clear()

        # Reset frozen cache
        self.frozen_cache.clear()

        return outstring

    def _sorted_keys(self, keys, startkey, reverse=False):
        """Generator that yields sorted keys starting with startkey

        Parameters
        ----------

        keys: Iterable of tuple/list
        \tKey sequence that is sorted
        startkey: Tuple/list
        \tFirst key to be yielded
        reverse: Bool
        \tSort direction reversed if True

        """

        tuple_key = lambda t: t[::-1]
        if reverse:
            tuple_cmp = lambda t: t[::-1] > startkey[::-1]
        else:
            tuple_cmp = lambda t: t[::-1] < startkey[::-1]

        searchkeys = sorted(keys, key=tuple_key, reverse=reverse)
        searchpos = sum(1 for _ in ifilter(tuple_cmp, searchkeys))

        searchkeys = searchkeys[searchpos:] + searchkeys[:searchpos]

        for key in searchkeys:
            yield key

    def _string_match(self, datastring, findstring, flags=None):
        """
        Returns position of findstring in datastring or None if not found.
        Flags is a list of strings. Supported strings are:
         * "MATCH_CASE": The case has to match for valid find
         * "WHOLE_WORD": The word has to be surrounded by whitespace characters
                         if in the middle of the string
         * "REG_EXP":    A regular expression is evaluated.

        """

        if type(datastring) is IntType:  # Empty cell
            return None

        if flags is None:
            flags = []

        if "REG_EXP" in flags:
            match = re.search(findstring, datastring)
            if match is None:
                pos = -1
            else:
                pos = match.start()
        else:
            if "MATCH_CASE" not in flags:
                datastring = datastring.lower()
                findstring = findstring.lower()

            if "WHOLE_WORD" in flags:
                pos = -1
                matchstring = r'\b' + findstring + r'+\b'
                for match in re.finditer(matchstring, datastring):
                    pos = match.start()
                    break  # find 1st occurrance
            else:
                pos = datastring.find(findstring)

        if pos == -1:
            return None
        else:
            return pos

    def findnextmatch(self, startkey, find_string, flags):
        """ Returns a tuple with the position of the next match of find_string

        Returns None if string not found.

        Parameters:
        -----------
        startkey:   Start position of search
        find_string:String to be searched for
        flags:      List of strings, out of
                    ["UP" xor "DOWN", "WHOLE_WORD", "MATCH_CASE", "REG_EXP"]

        """

        assert "UP" in flags or "DOWN" in flags
        assert not ("UP" in flags and "DOWN" in flags)

        # List of keys in sgrid in search order

        reverse = "UP" in flags

        for key in self._sorted_keys(self.keys(), startkey, reverse=reverse):
            code = self(key)
            res_str = unicode(self[key])

            if self._string_match(code, find_string, flags) is not None or \
               self._string_match(res_str, find_string, flags) is not None:
                return key

# End of class CodeArray

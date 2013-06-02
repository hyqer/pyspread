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
_grid_actions.py
=======================

Module for main main grid level actions.
All non-trivial functionality that results from grid actions
and belongs to the grid only goes here.

Provides:
---------
  1. FileActions: Actions which affect the open grid
  2. TableRowActionsMixin: Mixin for TableActions
  3. TableColumnActionsMixin: Mixin for TableActions
  4. TableTabActionsMixin: Mixin for TableActions
  5. TableActions: Actions which affect table
  6. MacroActions: Actions on macros
  7. UnRedoActions: Actions on the undo redo system
  8. GridActions: Actions on the grid as a whole
  9. SelectionActions: Actions on the grid selection
  10. FindActions: Actions for finding and replacing
  11. AllGridActions: All grid actions as a bundle


"""

import bz2
import itertools
import src.lib.i18n as i18n
import os

import wx

from src.config import config
from src.sysvars import get_default_font

from src.gui._grid_table import GridTable

try:
    from src.lib.gpg import sign, verify
    GPG_PRESENT = True

except ImportError:
    GPG_PRESENT = False

from src.lib.selection import Selection

from src.actions._main_window_actions import Actions
from src.actions._grid_cell_actions import CellActions

from src.gui._events import post_command_event

#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


class FileActions(Actions):
    """File actions on the grid"""

    def __init__(self, grid):
        Actions.__init__(self, grid)

        self.saving = False

        self.main_window.Bind(self.EVT_CMD_GRID_ACTION_OPEN, self.open)
        self.main_window.Bind(self.EVT_CMD_GRID_ACTION_SAVE, self.save)

    def _is_aborted(self, cycle, statustext, total_elements=None, freq=100):
        """Displays progress and returns True if abort

        Parameters
        ----------

        cycle: Integer
        \tThe current operation cycle
        statustext: String
        \tLeft text in statusbar to be displayed
        total_elements: Integer:
        \tThe number of elements that have to be processed
        freq: Integer, defaults to 1000
        \tNo. operations between two abort possibilities

        """

        if total_elements is None:
            statustext += _("{nele} elements processed. Press <Esc> to abort.")
        else:
            statustext += _("{nele} of {totalele} elements processed. "
                            "Press <Esc> to abort.")

        # Show progress in statusbar each freq (1000) cells
        if cycle % freq == 0:
            text = statustext.format(nele=cycle, totalele=total_elements)
            try:
                post_command_event(self.main_window, self.StatusBarMsg,
                                   text=text)
            except TypeError:
                # The main window does not exist any more
                pass

            # Now wait for the statusbar update to be written on screen
            wx.Yield()

            # Abort if we have to
            if self.need_abort:
                # We have to abort`
                return True

        # Continue
        return False

    def validate_signature(self, filename):
        """Returns True if a valid signature is present for filename"""

        if not GPG_PRESENT:
            return False

        sigfilename = filename + '.sig'

        try:
            dummy = open(sigfilename)
            dummy.close()
        except IOError:
            # Signature file does not exist
            return False

        # Check if the sig is valid for the sigfile
        return verify(sigfilename, filename)

    def enter_safe_mode(self):
        """Enters safe mode"""

        self.code_array.safe_mode = True

    def leave_safe_mode(self):
        """Leaves safe mode"""

        self.code_array.safe_mode = False

        # Clear result cache
        self.code_array.result_cache.clear()

        # Execute macros
        self.main_window.actions.execute_macros()

        post_command_event(self.main_window, self.SafeModeExitMsg)

    def approve(self, filepath):
        """Sets safe mode if signature missing of invalid"""

        if self.validate_signature(filepath):
            self.leave_safe_mode()
            post_command_event(self.main_window, self.SafeModeExitMsg)

            statustext = _("Valid signature found. File is trusted.")
            post_command_event(self.main_window, self.StatusBarMsg,
                               text=statustext)

        else:
            self.enter_safe_mode()
            post_command_event(self.main_window, self.SafeModeEntryMsg)

            statustext = \
                _("File is not properly signed. Safe mode "
                  "activated. Select File -> Approve to leave safe mode.")
            post_command_event(self.main_window, self.StatusBarMsg,
                               text=statustext)

    def clear_globals_reload_modules(self):
        """Clears globals and reloads modules"""

        self.code_array.clear_globals()
        self.code_array.reload_modules()

        # Clear result cache
        self.code_array.result_cache.clear()

    def _get_file_version(self, infile):
        """Returns infile version string."""

        # Determine file version
        for line1 in infile:
            if line1.strip() != "[Pyspread save file version]":
                raise ValueError(_("File format unsupported."))
            break

        for line2 in infile:
            return line2.strip()

    def _abort_open(self, filepath, infile):
        """Aborts file open"""

        statustext = _("File loading aborted.")
        post_command_event(self.main_window, self.StatusBarMsg,
                           text=statustext)

        infile.close()

        self.opening = False
        self.need_abort = False

    def clear(self, shape=None):
        """Empties grid and sets shape to shape

        Clears all attributes, row heights, column withs and frozen states.
        Empties undo/redo list and caches. Empties globals.

        Properties
        ----------

        shape: 3-tuple of Integer, defaults to None
        \tTarget shape of grid after clearing all content.
        \tShape unchanged if None

        """

        # Clear cells
        self.code_array.dict_grid.clear()

        # Clear attributes
        del self.code_array.dict_grid.cell_attributes[:]

        if shape is not None:
            # Set shape
            self.code_array.shape = shape

        # Clear row heights and column widths
        self.code_array.row_heights.clear()
        self.code_array.col_widths.clear()

        # Clear caches
        self.code_array.unredo.reset()
        self.code_array.result_cache.clear()

        # Clear globals
        self.code_array.clear_globals()
        self.code_array.reload_modules()

    def open(self, event):
        """Opens a file that is specified in event.attr

        Parameters
        ----------
        event.attr: Dict
        \tkey filepath contains file path of file to be loaded

        """

        filepath = event.attr["filepath"]

        # Set states for file open

        self.opening = True
        self.need_abort = False

        try:
            infile = bz2.BZ2File(filepath, "r")

        except IOError:
            txt = _("Error opening file {filepath}.").format(filepath=filepath)
            post_command_event(self.main_window, self.StatusBarMsg, text=txt)

            return False

        # Make loading safe
        self.approve(filepath)

        # Abort if file version not supported
        try:
            version = self._get_file_version(infile)
            if version != "0.1":
                text = _("File version {version} unsupported (not 0.1).")
                text = text.format(version=version)
                post_command_event(self.main_window, self.StatusBarMsg,
                                   text=text)

                return False

        except (IOError, ValueError), errortext:
            post_command_event(self.main_window, self.StatusBarMsg,
                               text=errortext)

        # Parse content

        def parser(*args):
            """Dummy parser. Raises ValueError"""

            raise ValueError(_("No section parser present."))

        section_readers = {
            "[shape]": self.code_array.dict_grid.parse_to_shape,
            "[grid]": self.code_array.dict_grid.parse_to_grid,
            "[attributes]": self.code_array.dict_grid.parse_to_attribute,
            "[row_heights]": self.code_array.dict_grid.parse_to_height,
            "[col_widths]": self.code_array.dict_grid.parse_to_width,
            "[macros]": self.code_array.dict_grid.parse_to_macro,
        }

        # Disable undo
        self.grid.code_array.unredo.active = True

        try:
            for cycle, line in enumerate(infile):
                stripped_line = line.decode("utf-8").strip()
                if stripped_line:
                    # There is content in this line
                    if stripped_line in section_readers:
                        # Switch parser
                        parser = section_readers[stripped_line]
                    else:
                        # Parse line
                        parser(line)
                        if parser == self.code_array.dict_grid.parse_to_shape:
                            # Empty grid
                            self.clear(self.code_array.shape)

                            self.grid.GetTable().ResetView()
                else:
                    pass

                # Enable abort during long saves
                if self._is_aborted(cycle, "Loading file... "):
                    self._abort_open(filepath, infile)
                    return False

        except IOError:
            txt = _("Error opening file {filepath}.").format(filepath=filepath)
            post_command_event(self.main_window, self.StatusBarMsg, text=txt)

            return False

        except EOFError:
            # Normally on empty grids
            pass

        infile.close()
        self.opening = False

        # Execute macros
        self.main_window.actions.execute_macros()

        # Enable undo again
        self.grid.code_array.unredo.active = False

        self.grid.GetTable().ResetView()
        self.grid.ForceRefresh()

        # File sucessfully opened. Approve again to show status.
        self.approve(filepath)

    def sign_file(self, filepath):
        """Signs file if possible"""

        if not GPG_PRESENT:
            return

        signed_data = sign(filepath)
        signature = signed_data.data

        if signature is None or not signature:
            statustext = _('Error signing file. ') + signed_data.stderr
            try:
                post_command_event(self.main_window, self.StatusBarMsg,
                                   text=statustext)
            except TypeError:
                # The main window does not exist any more
                pass

            return

        signfile = open(filepath + '.sig', 'wb')
        signfile.write(signature)
        signfile.close()

        # Statustext differs if a save has occurred

        if self.code_array.safe_mode:
            statustext = _('File saved and signed')
        else:
            statustext = _('File signed')

        try:
            post_command_event(self.main_window, self.StatusBarMsg,
                               text=statustext)
        except TypeError:
            # The main window does not exist any more
            pass

    def _abort_save(self, filepath, outfile):
        """Aborts file save"""

        statustext = _("Save aborted.")

        try:
            post_command_event(self.main_window, self.StatusBarMsg,
                               text=statustext)
        except TypeError:
            # The main window does not exist any more
            pass

        outfile.close()
        os.remove(filepath)

        self.saving = False
        self.need_abort = False

    def save(self, event):
        """Saves a file that is specified in event.attr

        Parameters
        ----------
        event.attr: Dict
        \tkey filepath contains file path of file to be saved

        """

        filepath = event.attr["filepath"]

        dict_grid = self.code_array.dict_grid

        self.saving = True
        self.need_abort = False

        io_error_text = _("Error writing to file {filepath}.")
        io_error_text = io_error_text.format(filepath=filepath)

        # Save file is compressed
        try:
            outfile = bz2.BZ2File(filepath, "wb")

        except IOError:
            txt = _("Error opening file {filepath}.").format(filepath=filepath)
            try:
                post_command_event(self.main_window, self.StatusBarMsg,
                                   text=txt)
            except TypeError:
                # The main window does not exist any more
                pass
            return False

        # Header
        try:
            outfile.write("[Pyspread save file version]\n")
            outfile.write("0.1\n")

        except IOError:
            try:
                post_command_event(self.main_window, self.StatusBarMsg,
                                   text=io_error_text)
            except TypeError:
                # The main window does not exist any more
                pass

            return False

        # The output generators yield the lines for the outfile
        output_generators = [
            # Grid content
            dict_grid.grid_to_strings(),
            # Cell attributes
            dict_grid.attributes_to_strings(),
            # Row heights
            dict_grid.heights_to_strings(),
            # Column widths
            dict_grid.widths_to_strings(),
            # Macros
            dict_grid.macros_to_strings(),
        ]

        # Options for self._is_aborted
        abort_options_list = [
            ["Saving grid... ", len(dict_grid), 100000],
            ["Saving cell attributes... ", len(dict_grid.cell_attributes)],
            ["Saving row heights... ", len(dict_grid.row_heights)],
            ["Saving column widths... ", len(dict_grid.col_widths)],
            ["Saving macros... ", dict_grid.macros.count("\n")],
        ]

        # Save cycle

        for generator, options in zip(output_generators, abort_options_list):
            for cycle, line in enumerate(generator):
                try:
                    outfile.write(line.encode("utf-8"))

                except IOError:
                    try:
                        post_command_event(self.main_window, self.StatusBarMsg,
                                           text=io_error_text)
                    except TypeError:
                        # The main window does not exist any more
                        pass
                    return False

                # Enable abort during long saves
                if self._is_aborted(cycle, *options):
                    self._abort_save(filepath, outfile)
                    return False

        # Save is done

        outfile.close()

        self.saving = False

        # Mark content as unchanged
        try:
            post_command_event(self.main_window, self.ContentChangedMsg,
                               changed=False)
        except TypeError:
            # The main window does not exist any more
            pass

        # Sign so that the new file may be retrieved without safe mode
        if self.code_array.safe_mode:
            msg = _("File saved but not signed because it is unapproved.")
            try:
                post_command_event(self.main_window, self.StatusBarMsg,
                                   text=msg)
            except TypeError:
                # The main window does not exist any more
                pass

        else:
            self.sign_file(filepath)


class TableRowActionsMixin(Actions):
    """Table row controller actions"""

    def set_row_height(self, row, height):
        """Sets row height and marks grid as changed"""

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        tab = self.grid.current_table

        self.code_array.set_row_height(row, tab, height)
        self.grid.SetRowSize(row, height)

    def insert_rows(self, row, no_rows=1):
        """Adds no_rows rows before row, appends if row > maxrows

        and marks grid as changed

        """

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        self.code_array.insert(row, no_rows, axis=0)

    def delete_rows(self, row, no_rows=1):
        """Deletes no_rows rows and marks grid as changed"""

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        try:
            self.code_array.delete(row, no_rows, axis=0)

        except ValueError, err:
            post_command_event(self.main_window, self.StatusBarMsg,
                               text=err.message)


class TableColumnActionsMixin(Actions):
    """Table column controller actions"""

    def set_col_width(self, col, width):
        """Sets column width and marks grid as changed"""

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        tab = self.grid.current_table

        self.code_array.set_col_width(col, tab, width)
        self.grid.SetColSize(col, width)

    def insert_cols(self, col, no_cols=1):
        """Adds no_cols columns before col, appends if col > maxcols

        and marks grid as changed

        """

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        self.code_array.insert(col, no_cols, axis=1)

    def delete_cols(self, col, no_cols=1):
        """Deletes no_cols column and marks grid as changed"""

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        try:
            self.code_array.delete(col, no_cols, axis=1)

        except ValueError, err:
            post_command_event(self.main_window, self.StatusBarMsg,
                               text=err.message)


class TableTabActionsMixin(Actions):
    """Table tab controller actions"""

    def insert_tabs(self, tab, no_tabs=1):
        """Adds no_tabs tabs before table, appends if tab > maxtabs

        and marks grid as changed

        """

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        self.code_array.insert(tab, no_tabs, axis=2)

        # Update TableChoiceIntCtrl
        shape = self.grid.code_array.shape
        post_command_event(self.main_window, self.ResizeGridMsg, shape=shape)

    def delete_tabs(self, tab, no_tabs=1):
        """Deletes no_tabs tabs and marks grid as changed"""

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        try:
            self.code_array.delete(tab, no_tabs, axis=2)

            # Update TableChoiceIntCtrl
            shape = self.grid.code_array.shape
            post_command_event(self.main_window, self.ResizeGridMsg,
                               shape=shape)

        except ValueError, err:
            post_command_event(self.main_window, self.StatusBarMsg,
                               text=err.message)


class TableActions(TableRowActionsMixin, TableColumnActionsMixin,
                   TableTabActionsMixin):
    """Table controller actions"""

    def __init__(self, grid):
        TableRowActionsMixin.__init__(self, grid)
        TableColumnActionsMixin.__init__(self, grid)
        TableTabActionsMixin.__init__(self, grid)

        # Action states

        self.pasting = False

        # Bindings

        self.main_window.Bind(wx.EVT_KEY_DOWN, self.on_key)

    def on_key(self, event):
        """Sets abort if pasting and if escape is pressed"""

        # If paste is running and Esc is pressed then we need to abort

        if event.GetKeyCode() == wx.WXK_ESCAPE and \
           self.pasting or self.grid.actions.saving:
            self.need_abort = True

        event.Skip()

    def _get_full_key(self, key):
        """Returns full key even if table is omitted"""

        length = len(key)

        if length == 3:
            return key

        elif length == 2:
            row, col = key
            tab = self.grid.current_table
            return row, col, tab

        else:
            msg = _("Key length {length}  not in (2, 3)").format(length=length)
            raise ValueError(msg)

    def _abort_paste(self):
        """Aborts import"""

        statustext = _("Paste aborted.")
        post_command_event(self.main_window, self.StatusBarMsg,
                           text=statustext)

        self.pasting = False
        self.need_abort = False

    def _show_final_overflow_message(self, row_overflow, col_overflow):
        """Displays overflow message after import in statusbar"""

        if row_overflow and col_overflow:
            overflow_cause = _("rows and columns")
        elif row_overflow:
            overflow_cause = _("rows")
        elif col_overflow:
            overflow_cause = _("columns")
        else:
            raise AssertionError(_("Import cell overflow missing"))

        statustext = \
            _("The imported data did not fit into the grid {cause}. "
              "It has been truncated. Use a larger grid for full import.").\
            format(cause=overflow_cause)
        post_command_event(self.main_window, self.StatusBarMsg,
                           text=statustext)

    def _show_final_paste_message(self, tl_key, no_pasted_cells):
        """Show actually pasted number of cells"""

        plural = "" if no_pasted_cells == 1 else _("s")

        statustext = _("{ncells} cell{plural} pasted at cell {topleft}").\
            format(ncells=no_pasted_cells, plural=plural, topleft=tl_key)

        post_command_event(self.main_window, self.StatusBarMsg,
                           text=statustext)

    def paste_to_current_cell(self, tl_key, data):
        """Pastes data into grid from top left cell tl_key

        Parameters
        ----------

        ul_key: Tuple
        \key of top left cell of paste area
        data: iterable of iterables where inner iterable returns string
        \tThe outer iterable represents rows

        """

        self.pasting = True

        grid_rows, grid_cols, __ = self.grid.code_array.shape

        self.need_abort = False

        tl_row, tl_col, tl_tab = self._get_full_key(tl_key)

        row_overflow = False
        col_overflow = False

        no_pasted_cells = 0

        for src_row, row_data in enumerate(data):
            target_row = tl_row + src_row

            if self.grid.actions._is_aborted(src_row, _("Pasting cells... ")):
                self._abort_paste()
                return False

            # Check if rows fit into grid
            if target_row >= grid_rows:
                row_overflow = True
                break

            for src_col, cell_data in enumerate(row_data):
                target_col = tl_col + src_col

                if target_col >= grid_cols:
                    col_overflow = True
                    break

                if cell_data is not None:
                    # Is only None if pasting into selection
                    key = target_row, target_col, tl_tab

                    try:
                        # Set cell but do not mark unredo
                        # before pasting is finished

                        self.grid.code_array.__setitem__(key, cell_data,
                                                         mark_unredo=False)
                        no_pasted_cells += 1
                    except KeyError:
                        pass

        if row_overflow or col_overflow:
            self._show_final_overflow_message(row_overflow, col_overflow)

        else:
            self._show_final_paste_message(tl_key, no_pasted_cells)

        if no_pasted_cells:
            # If cells have been pasted mark unredo operation
            self.grid.code_array.unredo.mark()

        self.pasting = False

    def selection_paste_data_gen(self, selection, data):
        """Generator that yields data for selection paste"""

        (bb_top, bb_left), (bb_bottom, bb_right) = \
            selection.get_grid_bbox(self.grid.code_array.shape)
        bbox_height = bb_bottom - bb_top + 1
        bbox_width = bb_right - bb_left + 1

        for row, row_data in enumerate(itertools.cycle(data)):
            # Break if row is not in selection bbox
            if row >= bbox_height:
                break

            # Duplicate row data if selection is wider than row data
            duplicated_row_data = row_data * (bbox_width // len(row_data) + 1)
            duplicated_row_data = duplicated_row_data[:bbox_width]

            for col in xrange(len(duplicated_row_data)):
                if (bb_top, bb_left + col) not in selection:
                    duplicated_row_data[col] = None

            yield duplicated_row_data

    def paste_to_selection(self, selection, data):
        """Pastes data into grid selection"""

        (bb_top, bb_left), (bb_bottom, bb_right) = \
            selection.get_grid_bbox(self.grid.code_array.shape)
        adjusted_data = self.selection_paste_data_gen(selection, data)
        self.paste_to_current_cell((bb_top, bb_left), adjusted_data)

    def paste(self, tl_key, data):
        """Pastes data into grid, marks grid changed

        If no selection is present, data is pasted starting with current cell
        If a selection is present, data is pasted fully if the selection is
        smaller. If the selection is larger then data is duplicated.

        Parameters
        ----------

        ul_key: Tuple
        \key of top left cell of paste area
        data: iterable of iterables where inner iterable returns string
        \tThe outer iterable represents rows

        """

        # Get selection bounding box

        selection = self.get_selection()

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        if selection:
            # There is a selection.  Paste into it
            self.paste_to_selection(selection, data)
        else:
            # There is no selection.  Paste from top left cell.
            self.paste_to_current_cell(tl_key, data)

    def change_grid_shape(self, shape):
        """Grid shape change event handler, marks content as changed"""

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        self.grid.code_array.shape = shape

        # Update TableChoiceIntCtrl
        post_command_event(self.main_window, self.ResizeGridMsg, shape=shape)

        # Clear caches
        self.code_array.unredo.reset()
        self.code_array.result_cache.clear()


class UnRedoActions(Actions):
    """Undo and redo operations"""

    def undo(self):
        """Calls undo in model.code_array.unredo, marks content as changed"""

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        self.grid.code_array.unredo.undo()

    def redo(self):
        """Calls redo in model.code_array.unredo, marks content as changed"""

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        self.grid.code_array.unredo.redo()


class GridActions(Actions):
    """Grid level grid actions"""

    def __init__(self, grid):
        Actions.__init__(self, grid)

        self.code_array = grid.code_array

        self.prev_rowcol = []  # Last mouse over cell

        self.main_window.Bind(self.EVT_CMD_GRID_ACTION_NEW, self.new)
        self.main_window.Bind(self.EVT_CMD_GRID_ACTION_TABLE_SWITCH,
                              self.switch_to_table)

    def new(self, event):
        """Creates a new spreadsheet. Expects code_array in event."""

        # Grid table handles interaction to code_array

        self.grid.actions.clear(event.shape)

        _grid_table = GridTable(self.grid, self.grid.code_array)
        self.grid.SetTable(_grid_table, True)

        # Update toolbars
        self.grid.update_entry_line()
        self.grid.update_attribute_toolbar()

    # Zoom actions

    def _zoom_rows(self, zoom):
        """Zooms grid rows"""

        self.grid.SetDefaultRowSize(self.grid.std_row_size * zoom,
                                    resizeExistingRows=True)
        self.grid.SetRowLabelSize(self.grid.row_label_size * zoom)

        for row, tab in self.code_array.row_heights:
            if tab == self.grid.current_table:
                zoomed_row_size = \
                    self.code_array.row_heights[(row, tab)] * zoom
                self.grid.SetRowSize(row, zoomed_row_size)

    def _zoom_cols(self, zoom):
        """Zooms grid columns"""

        self.grid.SetDefaultColSize(self.grid.std_col_size * zoom,
                                    resizeExistingCols=True)
        self.grid.SetColLabelSize(self.grid.col_label_size * zoom)

        for col, tab in self.code_array.col_widths:
            if tab == self.grid.current_table:
                zoomed_col_size = self.code_array.col_widths[(col, tab)] * zoom
                self.grid.SetColSize(col, zoomed_col_size)

    def _zoom_labels(self, zoom):
        """Adjust grid label font to zoom factor"""

        labelfont = self.grid.GetLabelFont()
        default_fontsize = get_default_font().GetPointSize()
        labelfont.SetPointSize(max(1, int(round(default_fontsize * zoom))))
        self.grid.SetLabelFont(labelfont)

    def zoom(self, zoom=None):
        """Zooms to zoom factor"""

        status = True

        if zoom is None:
            zoom = self.grid.grid_renderer.zoom
            status = False

        # Zoom factor for grid content
        self.grid.grid_renderer.zoom = zoom

        # Zoom grid labels
        self._zoom_labels(zoom)

        # Zoom rows and columns
        self._zoom_rows(zoom)
        self._zoom_cols(zoom)

        self.grid.ForceRefresh()

        if status:
            statustext = _(u"Zoomed to {0:.2f}.").format(zoom)

            post_command_event(self.main_window, self.StatusBarMsg,
                               text=statustext)

    def zoom_in(self):
        """Zooms in by zoom factor"""

        zoom = self.grid.grid_renderer.zoom

        target_zoom = zoom * (1 + config["zoom_factor"])

        if target_zoom < config["maximum_zoom"]:
            self.zoom(target_zoom)

    def zoom_out(self):
        """Zooms out by zoom factor"""

        zoom = self.grid.grid_renderer.zoom

        target_zoom = zoom * (1 - config["zoom_factor"])

        if target_zoom > config["minimum_zoom"]:
            self.zoom(target_zoom)

    def on_mouse_over(self, key):
        """Displays cell code of cell key in status bar"""

        row, col, tab = key

        if (row, col) != self.prev_rowcol and row >= 0 and col >= 0:
            self.prev_rowcol[:] = [row, col]

            max_result_length = int(config["max_result_length"])
            table = self.grid.GetTable()
            hinttext = table.GetSource(row, col, tab)[:max_result_length]

            if hinttext is None:
                hinttext = ''

            post_command_event(self.main_window, self.StatusBarMsg,
                               text=hinttext)

    def get_visible_area(self):
        """Returns visible area

        Format is a tuple of the top left tuple and the lower right tuple

        """

        grid = self.grid

        top = grid.YToRow(grid.GetViewStart()[1] * grid.ScrollLineX)
        left = grid.XToCol(grid.GetViewStart()[0] * grid.ScrollLineY)

        # Now start at top left for determining the bottom right visible cell

        bottom, right = top, left

        while grid.IsVisible(bottom, left, wholeCellVisible=False):
            bottom += 1

        while grid.IsVisible(top, right, wholeCellVisible=False):
            right += 1

        # The derived lower right cell is *NOT* visible

        bottom -= 1
        right -= 1

        return (top, left), (bottom, right)

    def switch_to_table(self, event):
        """Switches grid to table

        Parameters
        ----------

        event.newtable: Integer
        \tTable that the grid is switched to

        """

        newtable = event.newtable

        no_tabs = self.grid.code_array.shape[2] - 1

        if 0 <= newtable <= no_tabs:
            self.grid.current_table = newtable

            # Change value of entry_line and table choice
            post_command_event(self.main_window, self.TableChangedMsg,
                               table=newtable)

            # Reset row heights and column widths by zooming

            self.zoom()

            statustext = _("Switched to table {table}.").format(table=newtable)

            post_command_event(self.main_window, self.StatusBarMsg,
                               text=statustext)

    def get_cursor(self):
        """Returns current grid cursor cell (row, col, tab)"""

        return self.grid.GetGridCursorRow(), self.grid.GetGridCursorCol(), \
            self.grid.current_table

    def set_cursor(self, value):
        """Changes the grid cursor cell.

        Parameters
        ----------

        value: 2-tuple or 3-tuple of String
        \trow, col, tab or row, col for target cursor position

        """

        if len(value) == 3:
            row, col, tab = value

            if tab != self.cursor[2]:
                post_command_event(self.main_window,
                                   self.GridActionTableSwitchMsg, newtable=tab)
        else:
            row, col = value

        if not (row is None and col is None):
            self.grid.MakeCellVisible(row, col)
            self.grid.SetGridCursor(row, col)

    cursor = property(get_cursor, set_cursor)


class SelectionActions(Actions):
    """Actions that affect the grid selection"""

    def get_selection(self):
        """Returns selected cells in grid as Selection object"""

        # GetSelectedCells: individual cells selected by ctrl-clicking
        # GetSelectedRows: rows selected by clicking on the labels
        # GetSelectedCols: cols selected by clicking on the labels
        # GetSelectionBlockTopLeft
        # GetSelectionBlockBottomRight: For blocks selected by dragging
        # across the grid cells.

        block_top_left = self.grid.GetSelectionBlockTopLeft()
        block_bottom_right = self.grid.GetSelectionBlockBottomRight()
        rows = self.grid.GetSelectedRows()
        cols = self.grid.GetSelectedCols()
        cells = self.grid.GetSelectedCells()

        return Selection(block_top_left, block_bottom_right, rows, cols, cells)

    def select_cell(self, row, col, add_to_selected=False):
        """Selects a single cell"""

        self.grid.SelectBlock(row, col, row, col,
                              addToSelected=add_to_selected)

    def select_slice(self, row_slc, col_slc, add_to_selected=False):
        """Selects a slice of cells

        Parameters
        ----------
         * row_slc: Integer or Slice
        \tRows to be selected
         * col_slc: Integer or Slice
        \tColumns to be selected
         * add_to_selected: Bool, defaults to False
        \tOld selections are cleared if False

        """

        if not add_to_selected:
            self.grid.ClearSelection()

        if row_slc == row_slc == slice(None, None, None):
            # The whole grid is selected
            self.grid.SelectAll()

        elif row_slc.stop is None and col_slc.stop is None:
            # A block is selected:
            self.grid.SelectBlock(row_slc.start, col_slc.start,
                                  row_slc.stop - 1, col_slc.stop - 1)
        else:
            for row in xrange(row_slc.start, row_slc.stop, row_slc.step):
                for col in xrange(col_slc.start, col_slc.stop, col_slc.step):
                    self.select_cell(row, col, add_to_selected=True)

    def delete_selection(self):
        """Deletes selected cells, marks content as changed"""

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        selection = self.get_selection()

        del_keys = \
            [key for key in self.grid.code_array if key[:2] in selection]

        for key in del_keys:
            self.grid.actions.delete_cell(key)

        self.grid.code_array.result_cache.clear()


class FindActions(Actions):
    """Actions for finding inside the grid"""

    def find(self, gridpos, find_string, flags):
        """Return next position of event_find_string in MainGrid

        Parameters:
        -----------
        gridpos: 3-tuple of Integer
        \tPosition at which the search starts
        find_string: String
        \tString to find in grid
        flags: List of strings
        \t Search flag out of
        \t ["UP" xor "DOWN", "WHOLE_WORD", "MATCH_CASE", "REG_EXP"]

        """

        findfunc = self.grid.code_array.findnextmatch

        if "DOWN" in flags:
            if gridpos[0] < self.grid.code_array.shape[0]:
                gridpos[0] += 1
            elif gridpos[1] < self.grid.code_array.shape[1]:
                gridpos[1] += 1
            elif gridpos[2] < self.grid.code_array.shape[2]:
                gridpos[2] += 1
            else:
                gridpos = (0, 0, 0)
        elif "UP" in flags:
            if gridpos[0] > 0:
                gridpos[0] -= 1
            elif gridpos[1] > 0:
                gridpos[1] -= 1
            elif gridpos[2] > 0:
                gridpos[2] -= 1
            else:
                gridpos = [dim - 1 for dim in self.grid.code_array.shape]

        return findfunc(tuple(gridpos), find_string, flags)

    def replace(self, findpos, find_string, replace_string):
        """Replaces occurrences of find_string with replace_string at findpos

        and marks content as changed

        Parameters
        ----------

        findpos: 3-Tuple of Integer
        \tPosition in grid that shall be replaced
        find_string: String
        \tString to be overwritten in the cell
        replace_string: String
        \tString to be used for replacement

        """

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        old_code = self.grid.code_array(findpos)
        new_code = old_code.replace(find_string, replace_string)

        self.grid.code_array[findpos] = new_code
        self.grid.actions.cursor = findpos

        statustext = _("Replaced {old} with {new} in cell {key}.")
        statustext = statustext.format(old=old_code, new=new_code, key=findpos)

        post_command_event(self.main_window, self.StatusBarMsg,
                           text=statustext)


class AllGridActions(FileActions, TableActions, UnRedoActions,
                     GridActions, SelectionActions, FindActions, CellActions):
    """All grid actions as a bundle"""

    def __init__(self, grid):
        FileActions.__init__(self, grid)
        TableActions.__init__(self, grid)
        UnRedoActions.__init__(self, grid)
        GridActions.__init__(self, grid)
        SelectionActions.__init__(self, grid)
        FindActions.__init__(self, grid)
        CellActions.__init__(self, grid)

    def _replace_bbox_none(self, bbox):
        """Returns bbox, in which None is replaced by grid boundaries"""

        (bb_top, bb_left), (bb_bottom, bb_right) = bbox

        if bb_top is None:
            bb_top = 0

        if bb_left is None:
            bb_left = 0

        if bb_bottom is None:
            bb_bottom = self.code_array.shape[0] - 1

        if bb_right is None:
            bb_right = self.code_array.shape[1] - 1

        return (bb_top, bb_left), (bb_bottom, bb_right)
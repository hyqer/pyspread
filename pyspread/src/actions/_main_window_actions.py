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
_main_window_actions.py
=======================

Module for main window level actions.
All non-trivial functionality that results from main window actions
and belongs to the application as whole (in contrast to the grid only)
goes here.

Provides:
---------
  1. ExchangeActions: Actions for foreign format import and export
  2. PrintActions: Actions for printing
  3. ClipboardActions: Actions which affect the clipboard
  4. MacroActions: Actions which affect macros
  5. HelpActions: Actions for getting help
  6. AllMainWindowActions: All main window actions as a bundle

"""

import ast
import base64
import bz2
import os

import wx
import wx.html

from matplotlib.figure import Figure

import lib.i18n as i18n
from src.sysvars import get_help_path

from src.config import config
from src.lib.__csv import CsvInterface, TxtGenerator
from src.lib.charts import fig2bmp, fig2x
from src.gui._printout import PrintCanvas, Printout
from src.gui._events import post_command_event, EventMixin

#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


class Actions(EventMixin):
    """Actions base class"""

    def __init__(self, grid):
        self.main_window = grid.main_window
        self.grid = grid
        self.code_array = grid.code_array


class ExchangeActions(Actions):
    """Actions for foreign format import and export"""

    def _import_csv(self, path):
        """CSV import workflow"""

        # If path is not set, do nothing
        if not path:
            return

        # Get csv info

        try:
            dialect, has_header, digest_types = \
                self.main_window.interfaces.get_csv_import_info(path)

        except IOError:
            msg = _("Error opening file {filepath}.").format(filepath=path)
            post_command_event(self.main_window, self.StatusBarMsg, text=msg)
            return

        return CsvInterface(self.main_window,
                            path, dialect, digest_types, has_header)

    def _import_txt(self, path):
        """Whitespace-delimited txt import workflow. This should be fast."""

        return TxtGenerator(self.main_window, path)

    def import_file(self, filepath, filterindex):
        """Imports external file

        Parameters
        ----------

        filepath: String
        \tPath of import file
        filterindex: Integer
        \tIndex for type of file, 0: csv, 1: tab-delimited text file

        """

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        if filterindex == 0:
            # CSV import option choice
            return self._import_csv(filepath)
        elif filterindex == 1:
            # TXT import option choice
            return self._import_txt(filepath)
        else:
            msg = _("Unknown import choice {choice}.")
            msg = msg.format(choice=filterindex)
            short_msg = _('Error reading CSV file')

            self.main_window.interfaces.display_warning(msg, short_msg)

    def _export_csv(self, filepath, data):
        """CSV export of code_array results

        Parameters
        ----------
        filepath: String
        \tPath of export file
        data: Object
        \tCode array result object slice, i. e. one object or iterable of
        \tsuch objects

        """

        # Get csv info

        csv_info = self.main_window.interfaces.get_csv_export_info(data)

        if csv_info is None:
            return

        try:
            dialect, digest_types, has_header = csv_info
        except TypeError:
            return

        # Export CSV file

        csv_interface = CsvInterface(filepath, dialect, digest_types,
                                     has_header)

        try:
            csv_interface.write(data)

        except IOError, err:
            msg = _("The file {filepath} could not be fully written\n \n"
                    "Error message:\n{msg}")
            msg = msg.format(filepath=filepath, msg=err)
            short_msg = _('Error writing CSV file')
            self.main_window.interfaces.display_warning(msg, short_msg)

    def _export_figure(self, filepath, data, format):
        """Export of single cell that contains a matplotlib figure

        Parameters
        ----------
        filepath: String
        \tPath of export file
        data: Matplotlib Figure
        \tMatplotlib figure that is eported
        format: String in ["png", "pdf", "ps", "eps", "svg"]

        """

        formats = ["svg", "eps", "ps", "pdf", "png"]
        assert format in formats

        data = fig2x(data, format)

        try:
            outfile = open(filepath, "wb")
            outfile.write(data)

        except IOError, err:
            msg = _("The file {filepath} could not be fully written\n \n"
                    "Error message:\n{msg}")
            msg = msg.format(filepath=filepath, msg=err)
            short_msg = _('Error writing SVG file')
            self.main_window.interfaces.display_warning(msg, short_msg)

        finally:
            outfile.close()

    def export_file(self, filepath, filterindex, data):
        """Export data for other applications

        Parameters
        ----------
        filepath: String
        \tPath of export file
        filterindex: Integer
        \tIndex of the import filter
        data: Object
        \tCode array result object slice, i. e. one object or iterable of
        \tsuch objects

        """

        formats = ["csv", "svg", "eps", "ps", "pdf", "png"]

        if filterindex == 0:
            self._export_csv(filepath, data)

        elif filterindex >= 1:
            self._export_figure(filepath, data, formats[filterindex])


class PrintActions(Actions):
    """Actions for printing"""

    def print_preview(self, print_area, print_data):
        """Launch print preview"""

        # Create the print canvas
        canvas = PrintCanvas(self.main_window, self.grid, print_area)

        printout = Printout(canvas)
        printout2 = Printout(canvas)

        preview = wx.PrintPreview(printout, printout2, print_data)

        if not preview.Ok():
            print "Printout preview failed.\n"
            return

        pfrm = wx.PreviewFrame(preview, self.main_window, _("Print preview"))

        pfrm.Initialize()
        pfrm.SetPosition(self.main_window.GetPosition())
        pfrm.SetSize(self.main_window.GetSize())
        pfrm.Show(True)

    def printout(self, print_area, print_data):
        """Print out print area

        See:
        http://aspn.activestate.com/ASPN/Mail/Message/wxpython-users/3471083

        """

        pdd = wx.PrintDialogData(print_data)
        printer = wx.Printer(pdd)

        # Create the print canvas
        canvas = PrintCanvas(self.main_window, self.grid, print_area)

        printout = Printout(canvas)

        if printer.Print(self.main_window, printout, True):
            self.print_data = \
                wx.PrintData(printer.GetPrintDialogData().GetPrintData())

        printout.Destroy()
        canvas.Destroy()


class ClipboardActions(Actions):
    """Actions which affect the clipboard"""

    def cut(self, selection):
        """Cuts selected cells and returns data in a tab separated string

        Parameters
        ----------

        selection: Selection object
        \tSelection of cells in current table that shall be copied

        """

        # Call copy with delete flag

        return self.copy(selection, delete=True)

    def _get_code(self, key):
        """Returns code for given key (one cell)

        Parameters
        ----------

        key: 3-Tuple of Integer
        \t Cell key

        """

        data = self.grid.code_array(key)
        self.grid.code_array.result_cache.clear()

        return data

    def copy(self, selection, getter=None, delete=False):
        """Returns code from selection in a tab separated string

        Cells that are not in selection are included as empty.

        Parameters
        ----------

        selection: Selection object
        \tSelection of cells in current table that shall be copied
        getter: Function, defaults to _get_code
        \tGetter function for copy content
        delete: Bool
        \tDeletes all cells inside selection

        """

        if getter is None:
            getter = self._get_code

        tab = self.grid.current_table

        selection_bbox = selection.get_bbox()

        if not selection_bbox:
            # There is no selection
            bb_top, bb_left = self.grid.actions.cursor[:2]
            bb_bottom, bb_right = bb_top, bb_left
        else:
            replace_none = self.main_window.grid.actions._replace_bbox_none
            (bb_top, bb_left), (bb_bottom, bb_right) = \
                replace_none(selection.get_bbox())

        data = []

        for __row in xrange(bb_top, bb_bottom + 1):
            data.append([])

            for __col in xrange(bb_left, bb_right + 1):
                # Only copy content if cell is in selection or
                # if there is no selection

                if (__row, __col) in selection or not selection_bbox:
                    content = getter((__row, __col, tab))

                    # Delete cell if delete flag is set

                    if delete:
                        try:
                            self.grid.code_array.pop((__row, __col, tab))

                        except KeyError:
                            pass

                    # Store data

                    if content is None:
                        data[-1].append(u"")

                    else:
                        data[-1].append(content)

                else:
                    data[-1].append(u"")

        return "\n".join("\t".join(line) for line in data)

    def _get_result_string(self, key):
        """Returns unicode string of result for given key (one cell)

        Parameters
        ----------

        key: 3-Tuple of Integer
        \t Cell key

        """

        row, col, tab = key

        result_obj = self.grid.code_array[row, col, tab]

        try:
            # Numpy object arrays are converted because of numpy repr bug
            result_obj = result_obj.tolist()

        except AttributeError:
            pass

        return unicode(result_obj)

    def copy_result(self, selection):
        """Returns result

        If selection consists of one cell only and result is a bitmap then
        the bitmap is returned.
        Otherwise the method returns string representations of the result
        for the given selection in a tab separated string.

        """

        bbox = selection.get_bbox()

        if not bbox:
            # There is no selection
            bb_top, bb_left = self.grid.actions.cursor[:2]
            bb_bottom, bb_right = bb_top, bb_left
        else:
            # Thereis a selection
            (bb_top, bb_left), (bb_bottom, bb_right) = bbox

        if bb_top == bb_bottom and bb_left == bb_right:
            # We have  a single selection

            tab = self.grid.current_table
            result = self.grid.code_array[bb_top, bb_left, tab]

            if isinstance(result, wx._gdi.Bitmap):
                # The result is a wx.Bitmap. Return it.
                return result

            elif isinstance(result, Figure):
                # The result is a matplotlib figure
                # Therefore, a wx.Bitmap is returned
                key = bb_top, bb_left, tab
                rect = self.grid.CellToRect(bb_top, bb_left)
                merged_rect = self.grid.grid_renderer.get_merged_rect(
                    self.grid, key, rect)
                dpi = float(wx.ScreenDC().GetPPI()[0])
                zoom = self.grid.grid_renderer.zoom

                return fig2bmp(result, merged_rect.width, merged_rect.height,
                               dpi, zoom)

        # So we have result strings to be returned
        getter = self._get_result_string

        return self.copy(selection, getter=getter)

    def bmp2code(self, key, bmp):
        """Pastes bitmap into single cell"""

        assert type(bmp) is wx._gdi.Bitmap

        code_template = \
            "wx.BitmapFromImage(wx.ImageFromData(" + \
            "{width}, {height}, bz2.decompress(base64.b64decode('{data}'))))"

        img = bmp.ConvertToImage()

        data = base64.b64encode(bz2.compress(img.GetData(), 9))

        code_str = code_template.format(width=img.GetWidth(),
                                        height=img.GetHeight(), data=data)

        return code_str

    def _get_paste_data_gen(self, key, data):
        """Generator for paste data

        Can be used in grid.actions.paste

        """

        if type(data) is wx._gdi.Bitmap:
            code_str = self.bmp2code(key, data)
            return [[code_str]]
        else:
            return (line.split("\t") for line in data.split("\n"))

    def paste(self, key, data):
        """Pastes data into grid

        Parameters
        ----------

        key: 2-Tuple of Integer
        \tTop left cell
        data: String or wx.Bitmap
        \tTab separated string of paste data
        \tor paste data image
        """

        data_gen = self._get_paste_data_gen(key, data)

        self.grid.actions.paste(key[:2], data_gen)

        self.main_window.grid.ForceRefresh()

    def _get_pasteas_data(self, dim, obj):
        """Returns list of lists of obj than has dimensionality dim

        Parameters
        ----------
        dim: Integer
        \tDimensionality of obj
        obj: Object
        \tIterable object of dimensionality dim

        """

        if dim == 0:
            return [[repr(obj)]]
        elif dim == 1:
            return [[repr(o)] for o in obj]
        elif dim == 2:
            return [map(repr, o) for o in obj]

    def paste_as(self, key, data):
        """Paste and transform data

        Data may be given as a Python code as well as a tab separated
        multi-line strings similar to paste.

        """

        def error_msg(err):
            msg = _("Error evaluating data: ") + str(err)
            post_command_event(self.main_window, self.StatusBarMsg, text=msg)

        interfaces = self.main_window.interfaces
        key = self.main_window.grid.actions.cursor

        try:
            obj = ast.literal_eval(data)

        except (SyntaxError, AttributeError):
            # This is no Python code so te try to interpret it as paste data
            try:
                obj = [map(ast.literal_eval, line.split("\t"))
                        for line in data.split("\n")]

            except Exception, err:
                error_msg(err)
                return

        except ValueError, err:
            error_msg(err)
            return

        parameters = interfaces.get_pasteas_parameters_from_user(obj)

        paste_data = self._get_pasteas_data(parameters["dim"], obj)

        if parameters["transpose"]:
            paste_data = zip(*paste_data)

        self.main_window.grid.actions.paste(key, paste_data)


class MacroActions(Actions):
    """Actions which affect macros"""

    def replace_macros(self, macros):
        """Replaces macros"""

        self.grid.code_array.macros = macros

    def execute_macros(self):
        """Executes macros and marks grid as changed"""

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        self.grid.code_array.execute_macros()

    def open_macros(self, filepath):
        """Loads macros from file and marks grid as changed

        Parameters
        ----------
        filepath: String
        \tPath to macro file

        """

        try:
            macro_infile = open(filepath, "r")

        except IOError:
            msg = _("Error opening file {filepath}.").format(filepath=filepath)
            post_command_event(self.main_window, self.StatusBarMsg, text=msg)

            return False

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        macrocode = macro_infile.read()
        macro_infile.close()

        self.grid.code_array.macros += "\n" + macrocode.strip("\n")

        self.main_window.grid.actions.enter_safe_mode()
        post_command_event(self.main_window, self.SafeModeEntryMsg)

    def save_macros(self, filepath, macros):
        """Saves macros to file

        Parameters
        ----------
        filepath: String
        \tPath to macro file
        macros: String
        \tMacro code

        """

        io_error_text = _("Error writing to file {filepath}.")
        io_error_text = io_error_text.format(filepath=filepath)

        try:
            macro_outfile = open(filepath, "w")

        except IOError:
            txt = _("Error opening file {filepath}.").format(filepath=filepath)
            try:
                post_command_event(self.main_window, self.StatusBarMsg,
                                   text=txt)
            except TypeError:
                # The main window does not exist any more
                pass

            return False

        macro_outfile.write(macros)
        macro_outfile.close()


class HelpActions(Actions):
    """Actions for getting help"""

    def launch_help(self, helpname, filename):
        """Generic help launcher

        Launches HTMLWindow that shows content of filename
        or the Internet page with the filename url

        Parameters
        ----------

        filename: String
        \thtml file or url

        """

        # Set up window

        position = config["help_window_position"]
        size = config["help_window_size"]

        self.help_window = wx.Frame(self.main_window, -1,
                                    helpname, position, size)
        self.help_htmlwindow = wx.html.HtmlWindow(self.help_window, -1,
                                                  (0, 0), size)

        self.help_window.Bind(wx.EVT_MOVE, self.OnHelpMove)
        self.help_window.Bind(wx.EVT_SIZE, self.OnHelpSize)
        self.help_htmlwindow.Bind(wx.EVT_RIGHT_DOWN, self.OnHelpBack)

        # Get help data
        current_path = os.getcwd()
        os.chdir(get_help_path())

        try:
            if os.path.isfile(filename):
                self.help_htmlwindow.LoadFile(filename)

            else:
                self.help_htmlwindow.LoadPage(filename)

        except IOError:
            self.help_htmlwindow.LoadPage(filename)

        # Show tutorial window

        self.help_window.Show()

        os.chdir(current_path)

    def OnHelpBack(self, event):
        """Goes back apage if possible"""

        if self.help_htmlwindow.HistoryCanBack():
            self.help_htmlwindow.HistoryBack()

    def OnHelpMove(self, event):
        """Help window move event handler stores position in config"""

        position = event.GetPosition()
        config["help_window_position"] = repr((position.x, position.y))

        event.Skip()

    def OnHelpSize(self, event):
        """Help window size event handler stores size in config"""

        size = event.GetSize()
        config["help_window_size"] = repr((size.width, size.height))

        event.Skip()


class AllMainWindowActions(ExchangeActions, PrintActions,
                           ClipboardActions, MacroActions, HelpActions):
    """All main window actions as a bundle"""

    pass

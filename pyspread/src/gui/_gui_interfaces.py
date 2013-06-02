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
_gui_interfaces
===============

Provides:
---------
  1) GuiInterfaces: Main window interfaces to GUI elements

"""

import csv
import os
import sys
import types

import wx
import wx.lib.agw.genericmessagedialog as GMD

import src.lib.i18n as i18n

from _dialogs import MacroDialog, DimensionsEntryDialog, AboutDialog
from _dialogs import CsvImportDialog, CellEntryDialog, CsvExportDialog
from _dialogs import PreferencesDialog, GPGParamsDialog, PasteAsDialog

#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


class ModalDialogInterfaceMixin(object):
    """Main window interfaces to modal dialogs"""

    def get_dimensions_from_user(self, no_dim):
        """Queries grid dimensions in a model dialog and returns n-tuple

        Parameters
        ----------
        no_dim: Integer
        \t Number of grid dimensions, currently must be 3

        """

        # Grid dimension dialog

        if no_dim != 3:
            raise NotImplementedError(
                _("Currently, only 3D grids are supported."))

        dim_dialog = DimensionsEntryDialog(self.main_window)

        if dim_dialog.ShowModal() != wx.ID_OK:
            dim_dialog.Destroy()
            return

        dim = tuple(dim_dialog.dimensions)
        dim_dialog.Destroy()

        return dim

    def get_preferences_from_user(self):
        """Launches preferences dialog and returns dict with preferences"""

        dlg = PreferencesDialog(self.main_window)

        change_choice = dlg.ShowModal()

        preferences = {}

        if change_choice == wx.ID_OK:
            for (parameter, _), ctrl in zip(dlg.parameters, dlg.textctrls):
                preferences[parameter] = repr(ctrl.Value)

        dlg.Destroy()

        return preferences

    def get_save_request_from_user(self):
        """Queries user if grid should be saved"""

        msg = _("There are unsaved changes.\nDo you want to save?")

        dlg = GMD.GenericMessageDialog(
            self.main_window, msg,
            _("Unsaved changes"), wx.YES_NO | wx.ICON_QUESTION | wx.CANCEL)

        save_choice = dlg.ShowModal()

        dlg.Destroy()

        if save_choice == wx.ID_YES:
            return True

        elif save_choice == wx.ID_NO:
            return False

    def get_filepath_findex_from_user(self, wildcard, message, style):
        """Opens a file dialog and returns filepath and filterindex

        Parameters
        ----------
        wildcard: String
        \tWildcard string for file dialog
        message: String
        \tMessage in the file dialog
        style: Integer
        \tDialog style, e. g. wx.OPEN | wx.CHANGE_DIR

        """

        dlg = wx.FileDialog(self.main_window, wildcard=wildcard,
                            message=message, style=style)

        filepath = None
        filter_index = None

        if dlg.ShowModal() == wx.ID_OK:
            filepath = dlg.GetPath()
            filter_index = dlg.GetFilterIndex()

        return filepath, filter_index

    def display_warning(self, message, short_message,
                        style=wx.OK | wx.ICON_WARNING):
        """Displays a warning message"""

        dlg = GMD.GenericMessageDialog(self.main_window, message,
                                       short_message, style)
        dlg.ShowModal()
        dlg.Destroy()

    def get_warning_choice(self, message, short_message,
                           style=wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING):
        """Launches proceeding dialog and returns True if ok to proceed"""

        dlg = GMD.GenericMessageDialog(self.main_window, message,
                                       short_message, style)

        choice = dlg.ShowModal()

        dlg.Destroy()

        return choice == wx.ID_YES

    def get_print_setup(self, print_data):
        """Opens print setup dialog and returns print_data"""

        psd = wx.PageSetupDialogData(print_data)
        ##psd.EnablePrinter(False)
        psd.CalculatePaperSizeFromId()
        dlg = wx.PageSetupDialog(self.main_window, psd)
        dlg.ShowModal()

        # this makes a copy of the wx.PrintData instead of just saving
        # a reference to the one inside the PrintDialogData that will
        # be destroyed when the dialog is destroyed
        new_print_data = wx.PrintData(dlg.GetPageSetupData().GetPrintData())

        dlg.Destroy()

        return new_print_data

    def get_csv_import_info(self, path):
        """Launches the csv dialog and returns csv_info

        csv_info is a tuple of dialect, has_header, digest_types

        Parameters
        ----------

        path: String
        \tFile path of csv file

        """

        csvfilename = os.path.split(path)[1]

        try:
            filterdlg = CsvImportDialog(self.main_window, csvfilepath=path)

        except csv.Error, err:
            # Display modal warning dialog

            msg = _("'{filepath}' does not seem to be a valid CSV file.\n \n"
                    "Opening it yielded the error:\n{error}")
            msg = msg.format(filepath=csvfilename, error=err)
            short_msg = _('Error reading CSV file')

            self.display_warning(msg, short_msg)

            return

        if filterdlg.ShowModal() == wx.ID_OK:
            dialect, has_header = filterdlg.csvwidgets.get_dialect()
            digest_types = filterdlg.grid.dtypes

        else:
            filterdlg.Destroy()

            return

        filterdlg.Destroy()

        return dialect, has_header, digest_types

    def get_csv_export_info(self, data):
        """Shows csv export preview dialog and returns csv_info

        csv_info is a tuple of dialect, has_header, digest_types

        Parameters
        ----------
        data: Iterable of iterables
        \tContains csv export data row-wise

        """

        preview_rows = 100
        preview_cols = 100

        export_preview = data[:preview_rows, :preview_cols]

        filterdlg = CsvExportDialog(self.main_window, data=export_preview)

        if filterdlg.ShowModal() == wx.ID_OK:
            dialect, has_header = filterdlg.csvwidgets.get_dialect()
            digest_types = [types.StringType]
        else:
            filterdlg.Destroy()
            return

        filterdlg.Destroy()

        return dialect, has_header, digest_types

    def get_int_from_user(self, title="Enter integer value",
                          cond_func=lambda i: i is not None):
        """Opens an integer entry dialog and returns integer

        Parameters
        ----------
        title: String
        \tDialog title
        cond_func: Function
        \tIf cond_func of int(<entry_value> then result is returned.
        \tOtherwise the dialog pops up again.

        """

        is_integer = False

        while not is_integer:
            dlg = wx.TextEntryDialog(None, title, title)

            if dlg.ShowModal() == wx.ID_OK:
                result = dlg.GetValue()
            else:
                return None

            dlg.Destroy()

            try:
                integer = int(result)

                if cond_func(integer):
                    is_integer = True

            except ValueError:
                pass

        return integer

    def get_pasteas_parameters_from_user(self, obj):
        """Opens a PasteAsDialog and returns parameters dict"""

        dlg = PasteAsDialog(None, -1, obj)
        dlg_choice = dlg.ShowModal()

        if dlg_choice != wx.ID_OK:
            dlg.Destroy()
            return None

        parameters = {}
        parameters.update(dlg.parameters)
        dlg.Destroy()

        return parameters


class DialogInterfaceMixin(object):
    """Main window interfaces to dialogs that are not modal"""

    def display_gotocell(self):
        """Displays goto cell dialog"""

        dlg = CellEntryDialog(self.main_window)

        dlg.Show()

    def display_macros(self):
        """Displays macro dialog"""

        macros = self.main_window.grid.code_array.macros

        dlg = MacroDialog(self.main_window, macros, -1)

        dlg.Show()

    def display_about(self, parent):
        """Displays About dialog"""

        AboutDialog(parent)


class GuiInterfaces(DialogInterfaceMixin, ModalDialogInterfaceMixin):
    """Main window interfaces to GUI elements"""

    def __init__(self, main_window):
        self.main_window = main_window


def get_key_params_from_user():
    """Displays parameter entry dialog and returns parameter dict"""

    gpg_key_parameters = [
        ('key_type', 'DSA'),
        ('key_length', '2048'),
        ('subkey_type', 'ELG-E'),
        ('subkey_length', '2048'),
        ('expire_date', '0'),
    ]

    params = [
        [_('Real name'), 'name_real'],
    ]

    vals = [""] * len(params)

    while "" in vals:
        dlg = GPGParamsDialog(None, -1, "Enter GPG key parameters", params)
        dlg.CenterOnScreen()

        for val, textctrl in zip(vals, dlg.textctrls):
            textctrl.SetValue(val)

        if dlg.ShowModal() != wx.ID_OK:
            sys.exit()

        vals = [textctrl.Value for textctrl in dlg.textctrls]

        dlg.Destroy()

        if "" in vals:
            msg = _("Please enter a value in each field.")

            dlg = GMD.GenericMessageDialog(None, msg, _("Missing value"),
                                           wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()

    for (__, key), val in zip(params, vals):
        gpg_key_parameters.insert(-2, (key, val))

    return dict(gpg_key_parameters)
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread. If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
_events
=======

Event handler module

Provides
--------

* post_command_event: Posts a command event

"""

import wx
import wx.lib
import wx.lib.newevent


def post_command_event(target, msg_cls, **kwargs):
    """Posts command event to main window

    Command events propagate.

    Parameters
    ----------
     * msg_cls: class
    \tMessage class from new_command_event()
     * kwargs: dict
    \tMessage arguments

    """

    msg = msg_cls(id=-1, **kwargs)
    wx.PostEvent(target, msg)


new_command_event = wx.lib.newevent.NewCommandEvent


class MainWindowEventMixin(object):
    """Mixin class for mainwindow events"""

    TitleMsg, EVT_CMD_TITLE = new_command_event()

    SafeModeEntryMsg, EVT_CMD_SAFE_MODE_ENTRY = new_command_event()
    SafeModeExitMsg, EVT_CMD_SAFE_MODE_EXIT = new_command_event()

    PreferencesMsg, EVT_CMD_PREFERENCES = new_command_event()

    CloseMsg, EVT_CMD_CLOSE = new_command_event()

    FontDialogMsg, EVT_CMD_FONTDIALOG = new_command_event()
    TextColorDialogMsg, EVT_CMD_TEXTCOLORDIALOG = new_command_event()
    BgColorDialogMsg, EVT_CMD_BGCOLORDIALOG = new_command_event()

    ManualMsg, EVT_CMD_MANUAL = new_command_event()
    TutorialMsg, EVT_CMD_TUTORIAL = new_command_event()
    FaqMsg, EVT_CMD_FAQ = new_command_event()
    PythonTutorialMsg, EVT_CMD_PYTHON_TURORIAL = new_command_event()
    AboutMsg, EVT_CMD_ABOUT = new_command_event()

    MacroListMsg, EVT_CMD_MACROLIST = new_command_event()
    MacroReplaceMsg, EVT_CMD_MACROREPLACE = new_command_event()
    MacroExecuteMsg, EVT_CMD_MACROEXECUTE = new_command_event()
    MacroLoadMsg, EVT_CMD_MACROLOAD = new_command_event()
    MacroSaveMsg, EVT_CMD_MACROSAVE = new_command_event()

    MainToolbarToggleMsg, EVT_CMD_MAINTOOLBAR_TOGGLE = new_command_event()
    MacroToolbarToggleMsg, EVT_CMD_MACROTOOLBAR_TOGGLE = new_command_event()
    AttributesToolbarToggleMsg, EVT_CMD_ATTRIBUTESTOOLBAR_TOGGLE = \
                                            new_command_event()
    FindToolbarToggleMsg, EVT_CMD_FIND_TOOLBAR_TOGGLE = new_command_event()
    EntryLineToggleMsg, EVT_CMD_ENTRYLINE_TOGGLE = new_command_event()
    TableChoiceToggleMsg, EVT_CMD_TABLECHOICE_TOGGLE = new_command_event()

    ToolbarUpdateMsg, EVT_CMD_TOOLBAR_UPDATE = new_command_event()

    ContentChangedMsg, EVT_CONTENT_CHANGED = new_command_event()


class GridCellEventMixin(object):
    """Mixin class for grid cell events"""

    # Cell code entry events

    CodeEntryMsg, EVT_CMD_CODE_ENTRY = new_command_event()

    # Cell attribute events

    FontMsg, EVT_CMD_FONT = new_command_event()
    FontSizeMsg, EVT_CMD_FONTSIZE = new_command_event()
    FontBoldMsg, EVT_CMD_FONTBOLD = new_command_event()
    FontItalicsMsg, EVT_CMD_FONTITALICS = new_command_event()
    FontUnderlineMsg, EVT_CMD_FONTUNDERLINE = new_command_event()
    FontStrikethroughMsg, EVT_CMD_FONTSTRIKETHROUGH = new_command_event()
    FrozenMsg, EVT_CMD_FROZEN = new_command_event()
    MergeMsg, EVT_CMD_MERGE = new_command_event()
    JustificationMsg, EVT_CMD_JUSTIFICATION = new_command_event()
    AlignmentMsg, EVT_CMD_ALIGNMENT = new_command_event()
    BorderChoiceMsg, EVT_CMD_BORDERCHOICE = new_command_event()
    BorderWidthMsg, EVT_CMD_BORDERWIDTH = new_command_event()
    BorderColorMsg, EVT_CMD_BORDERCOLOR = new_command_event()
    BackgroundColorMsg, EVT_CMD_BACKGROUNDCOLOR = new_command_event()
    TextColorMsg, EVT_CMD_TEXTCOLOR = new_command_event()
    RotationDialogMsg,  EVT_CMD_ROTATIONDIALOG = new_command_event()
    TextRotationMsg, EVT_CMD_TEXTROTATATION = new_command_event()

    # Cell edit events

    EditorShownMsg, EVT_CMD_EDITORSHOWN = new_command_event()
    EditorHiddenMsg, EVT_CMD_EDITORHIDDEN = new_command_event()

    # Cell selection events

    CellSelectedMsg, EVT_CMD_CELLSELECTED = new_command_event()


class GridEventMixin(object):
    """Mixin class for grid events"""

    # File events

    NewMsg, EVT_CMD_NEW = new_command_event()
    OpenMsg, EVT_CMD_OPEN = new_command_event()
    SaveMsg, EVT_CMD_SAVE = new_command_event()
    SaveAsMsg, EVT_CMD_SAVEAS = new_command_event()
    ImportMsg, EVT_CMD_IMPORT = new_command_event()
    ExportMsg, EVT_CMD_EXPORT = new_command_event()
    ApproveMsg, EVT_CMD_APPROVE = new_command_event()
    ClearGobalsMsg, EVT_CMD_CLEAR_GLOBALS = new_command_event()

    # Print events

    PageSetupMsg, EVT_CMD_PAGE_SETUP = new_command_event()
    PrintPreviewMsg, EVT_CMD_PRINT_PREVIEW = new_command_event()
    PrintMsg, EVT_CMD_PRINT = new_command_event()

    # Clipboard events

    CutMsg, EVT_CMD_CUT = new_command_event()
    CopyMsg, EVT_CMD_COPY = new_command_event()
    CopyResultMsg, EVT_CMD_COPY_RESULT = new_command_event()
    PasteMsg, EVT_CMD_PASTE = new_command_event()
    PasteAsMsg, EVT_CMD_PASTE_AS = new_command_event()

    # Grid edit mode events

    EnterSelectionModeMsg, EVT_CMD_ENTER_SELECTION_MODE = new_command_event()
    ExitSelectionModeMsg, EVT_CMD_EXIT_SELECTION_MODE = new_command_event()
    SelectionMsg, EVT_CMD_SELECTION = new_command_event()

    # Grid view events

    RefreshSelectionMsg, EVT_CMD_REFRESH_SELECTION = new_command_event()
    DisplayGotoCellDialogMsg, EVT_CMD_DISPLAY_GOTO_CELL_DIALOG = \
                                                        new_command_event()
    GotoCellMsg, EVT_CMD_GOTO_CELL = new_command_event()
    ZoomInMsg, EVT_CMD_ZOOM_IN = new_command_event()
    ZoomOutMsg, EVT_CMD_ZOOM_OUT = new_command_event()
    ZoomStandardMsg, EVT_CMD_ZOOM_STANDARD = new_command_event()

    # Find events

    FindMsg, EVT_CMD_FIND = new_command_event()
    FindFocusMsg, EVT_CMD_FOCUSFIND = new_command_event()
    ReplaceMsg, EVT_CMD_REPLACE = new_command_event()

    # Grid change events

    InsertRowsMsg, EVT_CMD_INSERT_ROWS = new_command_event()
    InsertColsMsg, EVT_CMD_INSERT_COLS = new_command_event()
    InsertTabsMsg, EVT_CMD_INSERT_TABS = new_command_event()
    DeleteRowsMsg, EVT_CMD_DELETE_ROWS = new_command_event()
    DeleteColsMsg, EVT_CMD_DELETE_COLS = new_command_event()
    DeleteTabsMsg, EVT_CMD_DELETE_TABS = new_command_event()

    ShowResizeGridDialogMsg, EVT_CMD_SHOW_RESIZE_GRID_DIALOG = \
                                                    new_command_event()

    TableChangedMsg, EVT_CMD_TABLE_CHANGED = new_command_event()

    InsertBitmapMsg, EVT_CMD_INSERT_BMP = new_command_event()
    LinkBitmapMsg, EVT_CMD_LINK_BMP = new_command_event()
    InsertChartMsg, EVT_CMD_INSERT_CHART = new_command_event()
    ResizeGridMsg, EVT_CMD_RESIZE_GRID = new_command_event()

    # Grid attribute events

    # Undo/Redo events

    UndoMsg, EVT_CMD_UNDO = new_command_event()
    RedoMsg, EVT_CMD_REDO = new_command_event()


class GridActionEventMixin(object):
    """Mixin class for grid action events"""

    # Tuple dim
    GridActionNewMsg, EVT_CMD_GRID_ACTION_NEW = new_command_event()

    # Attr dict: keys: filepath: string, interface: object
    GridActionOpenMsg, EVT_CMD_GRID_ACTION_OPEN = new_command_event()
    GridActionSaveMsg, EVT_CMD_GRID_ACTION_SAVE = new_command_event()

    # For calling the grid
    GridActionTableSwitchMsg, EVT_CMD_GRID_ACTION_TABLE_SWITCH = \
                                                      new_command_event()


class EntryLineEventMixin(object):
    """Mixin class for entry line events"""

    EntryLineMsg, EVT_ENTRYLINE_MSG = new_command_event()
    ##EntryLineSelectionMsg, EVT_ENTRYLINE_SELECTION_MSG = new_command_event()


class StatusBarEventMixin(object):
    """Mixin class for statusbar events"""

    StatusBarMsg, EVT_STATUSBAR_MSG = wx.lib.newevent.NewEvent()


class EventMixin(MainWindowEventMixin, GridCellEventMixin, StatusBarEventMixin,
                 GridActionEventMixin, EntryLineEventMixin, GridEventMixin):
    """Event collector class"""

    pass


class ChartDialogEventMixin(object):
    """Mixin class for chart dialog events.

    Class remains independent from EventMixin container class

    """

    DrawChartMsg, EVT_CMD_DRAW_CHART = new_command_event()
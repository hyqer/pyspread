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
_toolbars
===========

Provides toolbars

Provides:
---------
  1. MainToolbar: Main toolbar of pyspread
  2. FindToolbar: Toolbar for Find operation
  3. AttributesToolbar: Toolbar for editing cell attributes

"""

import wx
import wx.lib.colourselect as csel
import wx.lib.agw.aui as aui

from _events import post_command_event, EventMixin

import src.lib.i18n as i18n

from src.config import config
from src.sysvars import get_default_font, get_font_list
from icons import icons

import _widgets

#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


class ToolbarBase(aui.AuiToolBar, EventMixin):
    """Base class for toolbars, requires self.toolbardata set in init

    Toolbardata has the following structure:
    [["tool type", "method name", "label", "tool tip"], ... ]

    Tool types are:

    "T": Simple tool
    "S": Separator
    "C": Control
    "O": Check tool / option button

    """

    def __init__(self, parent, *args, **kwargs):

        # Toolbars should be able to overflow
        kwargs["agwStyle"] = aui.AUI_TB_OVERFLOW

        aui.AuiToolBar.__init__(self, parent, *args, **kwargs)

        self.SetToolBitmapSize(icons.icon_size)

        self.ids_msgs = {}
        self.label2id = {}

        self.parent = parent

    def add_tools(self):
        """Adds tools from self.toolbardata to self"""

        for data in self.toolbardata:
            # tool type is in data[0]

            if data[0] == "T":
                # Simple tool

                _, msg_type, label, tool_tip = data
                icon = icons[label]

                self.label2id[label] = tool_id = wx.NewId()

                self.AddSimpleTool(tool_id, label, icon,
                                   short_help_string=tool_tip)

                self.ids_msgs[tool_id] = msg_type

                self.parent.Bind(wx.EVT_TOOL, self.OnTool, id=tool_id)

            elif data[0] == "S":
                # Separator

                self.AddSeparator()

            elif data[0] == "C":
                # Control

                _, control, tool_tip = data

                self.AddControl(control, label=tool_tip)

            elif data[0] == "O":
                # Check tool / option button

                _, label, tool_tip = data
                icon = icons[label]

                self.label2id[label] = tool_id = wx.NewId()

                self.AddCheckTool(tool_id, label, icon, icon, tool_tip)

            else:
                raise ValueError("Unknown tooltype " + str(data[0]))

        self.SetCustomOverflowItems([], [])
        self.Realize()

        # Adjust Toolbar size
        self.SetSize(self.DoGetBestSize())

    def OnTool(self, event):
        """Toolbar event handler"""

        msgtype = self.ids_msgs[event.GetId()]
        post_command_event(self, msgtype)


class MainToolbar(ToolbarBase):
    """Main application toolbar, built from attribute toolbardata"""

    def __init__(self, parent, *args, **kwargs):

        ToolbarBase.__init__(self, parent, *args, **kwargs)

        self.toolbardata = [
            ["T", self.NewMsg, "FileNew", _("New")],
            ["T", self.OpenMsg, "FileOpen", _("Open")],
            ["T", self.SaveMsg, "FileSave", _("Save")],
            ["S"],
            ["T", self.UndoMsg, "Undo", _("Undo")],
            ["T", self.RedoMsg, "Redo", _("Redo")],
            ["S"],
            ["T", self.FindFocusMsg, "Find", _("Find")],
            ["T", self.ReplaceMsg, "FindReplace", _("Replace")],
            ["S"],
            ["T", self.CutMsg, "EditCut", _("Cut")],
            ["T", self.CopyMsg, "EditCopy", _("Copy")],
            ["T", self.CopyResultMsg, "EditCopyRes", _("Copy Results")],
            ["T", self.PasteMsg, "EditPaste", _("Paste")],
            ["S"],
            ["T", self.PrintMsg, "FilePrint", _("Print")],
        ]

        self.add_tools()

# end of class MainToolbar


class MacroToolbar(ToolbarBase):
    """Macro toolbar, built from attribute toolbardata"""

    def __init__(self, parent, *args, **kwargs):

        ToolbarBase.__init__(self, parent, *args, **kwargs)

        self.toolbardata = [
            ["T", self.InsertBitmapMsg, "InsertBitmap", _("Insert bitmap")],
            ["T", self.LinkBitmapMsg, "LinkBitmap", _("Link bitmap")],
            ["T", self.InsertChartMsg, "InsertChart", _("Insert chart")],
        ]

        self.add_tools()

# end of class MainToolbar


class FindToolbar(ToolbarBase):
    """Toolbar for find operations (replaces wxFindReplaceDialog)"""

    def __init__(self, parent, *args, **kwargs):

        ToolbarBase.__init__(self, parent, *args, **kwargs)

        self.search_history = []
        self.search_options = ["DOWN"]
        self.search_options_buttons = ["MATCH_CASE", "REG_EXP", "WHOLE_WORD"]

        # Controls
        # --------

        # Search entry control
        search_tooltip = _("Find in code and results")
        self.search = wx.SearchCtrl(self, size=(140, -1),
                                    style=wx.TE_PROCESS_ENTER | wx.NO_BORDER)
        self.search.SetToolTip(wx.ToolTip(search_tooltip))
        self.menu = self.make_menu()
        self.search.SetMenu(self.menu)

        # Search direction togglebutton
        direction_tooltip = _("Search direction")
        iconnames = ["GoDown", "GoUp"]
        bmplist = [icons[iconname] for iconname in iconnames]
        self.search_direction_tb = _widgets.BitmapToggleButton(self, bmplist)
        self.search_direction_tb.SetToolTip(wx.ToolTip(direction_tooltip))

        # Toolbar data
        # ------------

        self.toolbardata = [
            ["C", self.search, search_tooltip],
            ["C", self.search_direction_tb, direction_tooltip],
            ["O", "MATCH_CASE", _("Case sensitive")],
            ["O", "REG_EXP", _("Regular expression")],
            ["O", "WHOLE_WORD", _("Surrounded by whitespace")],
        ]

        self.add_tools()

        # Bindings and polish
        # -------------------

        self._bindings()

    def _bindings(self):
        self.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, self.OnSearch, self.search)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnSearch, self.search)
        self.Bind(wx.EVT_MENU_RANGE, self.OnSearchFlag)
        self.Bind(wx.EVT_BUTTON, self.OnSearchDirectionButton,
                  self.search_direction_tb)
        self.Bind(wx.EVT_MENU, self.OnMenu)

    def make_menu(self):
        """Creates the search menu"""

        menu = wx.Menu()
        item = menu.Append(-1, "Recent Searches")
        item.Enable(False)

        for __id, txt in enumerate(self.search_history):
            menu.Append(__id, txt)
        return menu

    def OnMenu(self, event):
        """Search history has been selected"""

        __id = event.GetId()
        try:
            menuitem = event.GetEventObject().FindItemById(__id)
            selected_text = menuitem.GetItemLabel()
            self.search.SetValue(selected_text)
        except AttributeError:
            # Not called by menu
            event.Skip()

    def OnSearch(self, event):
        """Event handler for starting the search"""

        search_string = self.search.GetValue()

        if search_string not in self.search_history:
            self.search_history.append(search_string)
        if len(self.search_history) > 10:
            self.search_history.pop(0)

        self.menu = self.make_menu()
        self.search.SetMenu(self.menu)

        search_flags = self.search_options + ["FIND_NEXT"]

        post_command_event(self, self.FindMsg, text=search_string,
                           flags=search_flags)

        self.search.SetFocus()

    def OnSearchDirectionButton(self, event):
        """Event handler for search direction toggle button"""

        if "DOWN" in self.search_options:
            flag_index = self.search_options.index("DOWN")
            self.search_options[flag_index] = "UP"
        elif "UP" in self.search_options:
            flag_index = self.search_options.index("UP")
            self.search_options[flag_index] = "DOWN"
        else:
            raise AttributeError(_("Neither UP nor DOWN in search_flags"))

        event.Skip()

    def OnSearchFlag(self, event):
        """Event handler for search flag toggle buttons"""

        for label in self.search_options_buttons:
            button_id = self.label2id[label]
            if button_id == event.GetId():
                if event.IsChecked():
                    self.search_options.append(label)
                else:
                    flag_index = self.search_options.index(label)
                    self.search_options.pop(flag_index)

        event.Skip()

# end of class FindToolbar


class AttributesToolbar(aui.AuiToolBar, EventMixin):
    """Toolbar for editing cell attributes

    Class attributes
    ----------------

    border_toggles: Toggles for border changes, points to
                    (top, bottom, left, right, inner, outer)
    bordermap: Meaning of each border_toggle item

    """

    border_toggles = [
        ("AllBorders",       (1, 1, 1, 1, 1, 1)),
        ("LeftBorders",      (0, 0, 1, 0, 1, 1)),
        ("RightBorders",     (0, 0, 0, 1, 1, 1)),
        ("TopBorders",       (1, 0, 0, 0, 1, 1)),
        ("BottomBorders",    (0, 1, 0, 0, 1, 1)),
        ##("InsideBorders",    (1, 1, 1, 1, 1, 0)),
        ("OutsideBorders",   (1, 1, 1, 1, 0, 1)),
        ("TopBottomBorders", (1, 1, 0, 0, 0, 1)),
    ]

    bordermap = {
        "AllBorders":       ("top", "bottom", "left", "right", "inner"),
        "LeftBorders":      ("left"),
        "RightBorders":     ("right"),
        "TopBorders":       ("top"),
        "BottomBorders":    ("bottom"),
        ##"InsideBorders":    ("inner"),
        "OutsideBorders":   ("top", "bottom", "left", "right"),
        "TopBottomBorders": ("top", "bottom"),
    }

    def __init__(self, parent, *args, **kwargs):
        kwargs["style"] = aui.AUI_TB_OVERFLOW
        aui.AuiToolBar.__init__(self, parent, *args, **kwargs)

        self.parent = parent

        self.SetToolBitmapSize(icons.icon_size)

        self._create_font_choice_combo()
        self._create_font_size_combo()
        self._create_font_face_buttons()
        self._create_justification_button()
        self._create_alignment_button()
        self._create_borderchoice_combo()
        self._create_penwidth_combo()
        self._create_color_buttons()
        self._create_merge_button()
        self._create_textrotation_spinctrl()

        self.Realize()

        # Adjust Toolbar size
        self.SetSize(self.DoGetBestSize())

    # Create toolbar widgets
    # ----------------------

    def _create_font_choice_combo(self):
        """Creates font choice combo box"""

        self.fonts = get_font_list()
        self.font_choice_combo = \
            _widgets.FontChoiceCombobox(self, choices=self.fonts,
                                        style=wx.CB_READONLY, size=(125, -1))
        self.AddControl(self.font_choice_combo)

        self.Bind(wx.EVT_COMBOBOX, self.OnTextFont, self.font_choice_combo)
        self.parent.Bind(self.EVT_CMD_TOOLBAR_UPDATE, self.OnUpdate)

    def _create_font_size_combo(self):
        """Creates font size combo box"""

        self.std_font_sizes = config["font_default_sizes"]
        font_size = str(get_default_font().GetPointSize())
        self.font_size_combo = \
            wx.ComboBox(self, -1, value=font_size, size=(60, -1),
                        choices=map(unicode, self.std_font_sizes),
                        style=wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER)
        self.AddControl(self.font_size_combo)
        self.Bind(wx.EVT_COMBOBOX, self.OnTextSize, self.font_size_combo)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnTextSize, self.font_size_combo)

    def _create_font_face_buttons(self):
        """Creates font face buttons"""

        font_face_buttons = [
            (wx.FONTFLAG_BOLD, "OnBold", "FormatTextBold", _("Bold")),
            (wx.FONTFLAG_ITALIC, "OnItalics", "FormatTextItalic",
             _("Italics")),
            (wx.FONTFLAG_UNDERLINED, "OnUnderline", "FormatTextUnderline",
                _("Underline")),
            (wx.FONTFLAG_STRIKETHROUGH, "OnStrikethrough",
                "FormatTextStrikethrough", _("Strikethrough")),
            (wx.FONTFLAG_MASK, "OnFreeze", "Freeze", _("Freeze")),
        ]

        for __id, method, iconname, helpstring in font_face_buttons:
            bmp = icons[iconname]
            self.AddCheckTool(__id, iconname, bmp, bmp,
                              short_help_string=helpstring)
            self.Bind(wx.EVT_TOOL, getattr(self, method), id=__id)

    def _create_justification_button(self):
        """Creates horizontal justification button"""

        iconnames = ["JustifyLeft", "JustifyCenter", "JustifyRight"]
        bmplist = [icons[iconname] for iconname in iconnames]
        self.justify_tb = _widgets.BitmapToggleButton(self, bmplist)
        self.Bind(wx.EVT_BUTTON, self.OnJustification, self.justify_tb)
        self.AddControl(self.justify_tb)

    def _create_alignment_button(self):
        """Creates vertical alignment button"""

        iconnames = ["AlignTop", "AlignCenter", "AlignBottom"]
        bmplist = [icons[iconname] for iconname in iconnames]

        self.alignment_tb = _widgets.BitmapToggleButton(self, bmplist)
        self.Bind(wx.EVT_BUTTON, self.OnAlignment, self.alignment_tb)
        self.AddControl(self.alignment_tb)

    def _create_borderchoice_combo(self):
        """Create border choice combo box"""

        choices = [c[0] for c in self.border_toggles]
        self.borderchoice_combo = \
            _widgets.BorderEditChoice(self, choices=choices,
                                      style=wx.CB_READONLY, size=(50, -1))

        self.borderstate = self.border_toggles[0][0]

        self.AddControl(self.borderchoice_combo)

        self.Bind(wx.EVT_COMBOBOX, self.OnBorderChoice,
                  self.borderchoice_combo)

        self.borderchoice_combo.SetValue("AllBorders")

    def _create_penwidth_combo(self):
        """Create pen width combo box"""

        choices = map(unicode, xrange(12))
        self.pen_width_combo = \
            _widgets.PenWidthComboBox(self, choices=choices,
                                      style=wx.CB_READONLY, size=(50, -1))

        self.AddControl(self.pen_width_combo)
        self.Bind(wx.EVT_COMBOBOX, self.OnLineWidth, self.pen_width_combo)

    def _create_color_buttons(self):
        """Create color choice buttons"""

        button_size = (30, 30)
        button_style = wx.NO_BORDER

        try:
            self.linecolor_choice = \
                csel.ColourSelect(self, -1, unichr(0x2500), (0, 0, 0),
                                  size=button_size, style=button_style)
        except UnicodeEncodeError:
            # ANSI wxPython installed
            self.linecolor_choice = \
                csel.ColourSelect(self, -1, "-", (0, 0, 0),
                                  size=button_size, style=button_style)

        self.bgcolor_choice = \
            csel.ColourSelect(self, -1, "", (255, 255, 255),
                              size=button_size, style=button_style)
        self.textcolor_choice = \
            csel.ColourSelect(self, -1, "A", (0, 0, 0),
                              size=button_size, style=button_style)

        self.AddControl(self.linecolor_choice)
        self.AddControl(self.bgcolor_choice)
        self.AddControl(self.textcolor_choice)

        self.linecolor_choice.Bind(csel.EVT_COLOURSELECT, self.OnLineColor)
        self.bgcolor_choice.Bind(csel.EVT_COLOURSELECT, self.OnBGColor)
        self.textcolor_choice.Bind(csel.EVT_COLOURSELECT, self.OnTextColor)

    def _create_merge_button(self):
        """Create merge button"""

        bmp = icons["Merge"]
        self.mergetool_id = wx.NewId()
        self.AddCheckTool(self.mergetool_id, "Merge", bmp, bmp,
                          short_help_string=_("Merge cells"))
        self.Bind(wx.EVT_TOOL, self.OnMerge, id=self.mergetool_id)

    def _create_textrotation_spinctrl(self):
        """Create text rotation spin control"""

        self.rotation_spinctrl = wx.SpinCtrl(self, -1, "", size=(50, -1))
        self.rotation_spinctrl.SetRange(-179, 180)
        self.rotation_spinctrl.SetValue(0)

        # For compatibility with toggle buttons
        self.rotation_spinctrl.GetToolState = lambda x: None

        self.AddControl(self.rotation_spinctrl)

        self.Bind(wx.EVT_SPINCTRL, self.OnRotate, self.rotation_spinctrl)

    # Update widget state methods
    # ---------------------------

    def _update_font(self, textfont):
        """Updates text font widget

        Parameters
        ----------

        textfont: String
        \tFont name

        """

        try:
            fontface_id = self.fonts.index(textfont)
        except ValueError:
            fontface_id = 0

        self.font_choice_combo.Select(fontface_id)

    def _update_pointsize(self, pointsize):
        """Updates text size widget

        Parameters
        ----------

        pointsize: Integer
        \tFont point size

        """

        self.font_size_combo.SetValue(str(pointsize))

    def _update_font_weight(self, font_weight):
        """Updates font weight widget

        Parameters
        ----------

        font_weight: Integer
        \tButton down iif font_weight == wx.FONTWEIGHT_BOLD

        """

        toggle_state = font_weight & wx.FONTWEIGHT_BOLD == wx.FONTWEIGHT_BOLD

        self.ToggleTool(wx.FONTFLAG_BOLD, toggle_state)

    def _update_font_style(self, font_style):
        """Updates font style widget

        Parameters
        ----------

        font_style: Integer
        \tButton down iif font_style == wx.FONTSTYLE_ITALIC

        """

        toggle_state = font_style & wx.FONTSTYLE_ITALIC == wx.FONTSTYLE_ITALIC

        self.ToggleTool(wx.FONTFLAG_ITALIC, toggle_state)

    def _update_frozencell(self, frozen):
        """Updates frozen cell widget

        Parameters
        ----------

        frozen: Bool or string
        \tUntoggled iif False

        """

        toggle_state = not frozen is False

        self.ToggleTool(wx.FONTFLAG_MASK, toggle_state)

    def _update_underline(self, underlined):
        """Updates underline widget

        Parameters
        ----------

        underlined: Bool
        \tToggle state

        """

        self.ToggleTool(wx.FONTFLAG_UNDERLINED, underlined)

    def _update_strikethrough(self, strikethrough):
        """Updates text strikethrough widget

        Parameters
        ----------

        strikethrough: Bool
        \tToggle state

        """

        self.ToggleTool(wx.FONTFLAG_STRIKETHROUGH, strikethrough)

    def _update_justification(self, justification):
        """Updates horizontal text justification button

        Parameters
        ----------

        justification: String in ["left", "center", "right"]
        \tSwitches button to untoggled if False and toggled if True

        """

        states = {"left": 2, "center": 0, "right": 1}

        self.justify_tb.state = states[justification]

        self.justify_tb.toggle(None)
        self.justify_tb.Refresh()

    def _update_alignment(self, alignment):
        """Updates vertical text alignment button

        Parameters
        ----------

        alignment: String in ["top", "middle", "right"]
        \tSwitches button to untoggled if False and toggled if True

        """

        states = {"top": 2, "middle": 0, "bottom": 1}

        self.alignment_tb.state = states[alignment]

        self.alignment_tb.toggle(None)
        self.alignment_tb.Refresh()

    def _update_fontcolor(self, fontcolor):
        """Updates text font color button

        Parameters
        ----------

        fontcolor: Integer
        \tText color in integer RGB format

        """

        textcolor = wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOWTEXT)
        textcolor.SetRGB(fontcolor)

        self.textcolor_choice.SetColour(textcolor)

    def _update_merge(self, merged):
        """Updates cell merge toggle control"""

        self.ToggleTool(self.mergetool_id, merged)

    def _update_textrotation(self, angle):
        """Updates text rotation spin control"""

        self.rotation_spinctrl.SetValue(angle)

    def _update_bgbrush(self, bgcolor):
        """Updates background color"""

        brush_color = wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW)
        brush_color.SetRGB(bgcolor)

        self.bgcolor_choice.SetColour(brush_color)

    def _update_bordercolor(self, bordercolor):
        """Updates background color"""

        border_color = wx.SystemSettings_GetColour(wx.SYS_COLOUR_ACTIVEBORDER)
        border_color.SetRGB(bordercolor)

        self.linecolor_choice.SetColour(border_color)

    def _update_borderwidth(self, borderwidth):
        """Updates background color"""

        self.pen_width_combo.SetSelection(borderwidth)

    # Attributes toolbar event handlers
    # ---------------------------------

    def OnUpdate(self, event):
        """Updates the toolbar states"""

        wx.Yield()

        attributes = event.attr

        self._update_font(attributes["textfont"])
        self._update_pointsize(attributes["pointsize"])
        self._update_font_weight(attributes["fontweight"])
        self._update_font_style(attributes["fontstyle"])
        self._update_frozencell(attributes["frozen"])
        self._update_underline(attributes["underline"])
        self._update_strikethrough(attributes["strikethrough"])
        self._update_justification(attributes["justification"])
        self._update_alignment(attributes["vertical_align"])
        self._update_fontcolor(attributes["textcolor"])
        self._update_merge(attributes["merge_area"] is not None)
        self._update_textrotation(attributes["angle"])
        self._update_bgbrush(attributes["bgcolor"])
        self._update_bordercolor(attributes["bordercolor_bottom"])
        self._update_borderwidth(attributes["borderwidth_bottom"])

        self.Refresh()

    def OnBorderChoice(self, event):
        """Change the borders that are affected by color and width changes"""

        choicelist = event.GetEventObject().GetItems()
        self.borderstate = choicelist[event.GetInt()]

    def OnLineColor(self, event):
        """Line color choice event handler"""

        color = event.GetValue().GetRGB()
        borders = self.bordermap[self.borderstate]

        post_command_event(self, self.BorderColorMsg, color=color,
                           borders=borders)

    def OnLineWidth(self, event):
        """Line width choice event handler"""

        linewidth_combobox = event.GetEventObject()
        idx = event.GetInt()
        width = int(linewidth_combobox.GetString(idx))
        borders = self.bordermap[self.borderstate]

        post_command_event(self, self.BorderWidthMsg, width=width,
                           borders=borders)

    def OnBGColor(self, event):
        """Background color choice event handler"""

        color = event.GetValue().GetRGB()

        post_command_event(self, self.BackgroundColorMsg, color=color)

    def OnTextColor(self, event):
        """Text color choice event handler"""

        color = event.GetValue().GetRGB()

        post_command_event(self, self.TextColorMsg, color=color)

    def OnTextFont(self, event):
        """Text font choice event handler"""

        fontchoice_combobox = event.GetEventObject()
        idx = event.GetInt()

        try:
            font_string = fontchoice_combobox.GetString(idx)
        except AttributeError:
            font_string = event.GetString()

        post_command_event(self, self.FontMsg, font=font_string)

    def OnTextSize(self, event):
        """Text size combo text event handler"""

        try:
            size = int(event.GetString())

        except Exception:
            size = get_default_font().GetPointSize()

        post_command_event(self, self.FontSizeMsg, size=size)

    def OnBold(self, event):
        """Bold toggle button event handler"""

        post_command_event(self, self.FontBoldMsg)

    def OnItalics(self, event):
        """Bold toggle button event handler"""

        post_command_event(self, self.FontItalicsMsg)

    def OnUnderline(self, event):
        """Bold toggle button event handler"""

        post_command_event(self, self.FontUnderlineMsg)

    def OnStrikethrough(self, event):
        """Bold toggle button event handler"""

        post_command_event(self, self.FontStrikethroughMsg)

    def OnFreeze(self, event):
        """Bold toggle button event handler"""

        post_command_event(self, self.FrozenMsg)

    def OnJustification(self, event):
        """Justification toggle button event handler"""

        post_command_event(self, self.JustificationMsg)

    def OnAlignment(self, event):
        """Alignment toggle button event handler"""

        post_command_event(self, self.AlignmentMsg)

    def OnMerge(self, event):
        """Merge button event handler"""

        post_command_event(self, self.MergeMsg)

    def OnRotate(self, event):
        """Rotation spin control event handler"""

        angle = self.rotation_spinctrl.GetValue()

        post_command_event(self, self.TextRotationMsg, angle=angle)

# end of class AttributesToolbar
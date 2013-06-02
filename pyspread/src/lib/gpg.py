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

gpg
===

GPG handling functions

Provides
--------

 * genkey: Generates gpg key
 * sign: Returns detached signature for file
 * verify: verifies stream against signature

"""

import sys

import wx
import wx.lib.agw.genericmessagedialog as GMD
import gnupg

import src.lib.i18n as i18n
from src.config import config
from src.gui._gui_interfaces import get_key_params_from_user

#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


def choose_uid_key(keylist):
    """Displays gpg key choice and returns uid and key dict"""

    uid_strings = []
    uid_string2key = {}

    for key in keylist:
        for uid_string in key['uids']:
            uid_strings.append(uid_string)
            uid_string2key[uid_string] = key

    msg = _('Choose a GPG key for signing pyspread save files.\n'
            'The GPG key must not have a passphrase set.')

    dlg = wx.SingleChoiceDialog(None, msg, _('Choose key'), uid_strings,
                                wx.CHOICEDLG_STYLE)

    dlg.SetBestFittingSize()

    childlist = list(dlg.GetChildren())
    childlist[-3].SetLabel(_("Use chosen key"))
    childlist[-2].SetLabel(_("Create new key"))

    if dlg.ShowModal() == wx.ID_OK:
        uid = dlg.GetStringSelection()
        key = uid_string2key[uid]

    else:
        uid = None
        key = None

    dlg.Destroy()

    return uid, key


def genkey():
    """Creates a new standard GPG key"""

    gpg = gnupg.GPG()

    gpg.encoding = 'utf-8'

    # Check if standard key is already present

    pyspread_key_uid = str(config["gpg_key_uid"])
    gpg_private_keylist = gpg.list_keys(True)

    pyspread_key = None

    for private_key in gpg_private_keylist:
        if pyspread_key_uid in private_key["uids"]:
            pyspread_key = private_key

    if pyspread_key is None:
        # If no GPG key is set in config, choose one
        pyspread_key_uid, pyspread_key = choose_uid_key(gpg_private_keylist)

    if pyspread_key:
        # A key has been chosen
        config["gpg_key_uid"] = repr(pyspread_key_uid)

    else:
        # No key has been chosen --> Create new one
        gpg_key_parameters = get_key_params_from_user()

        input_data = gpg.gen_key_input(**gpg_key_parameters)

        # Generate key
        # ------------

        # Show infor dialog

        style = wx.ICON_INFORMATION | wx.DIALOG_NO_PARENT | wx.OK | wx.CANCEL
        pyspread_key_uid = gpg_key_parameters["name_real"]
        short_message = _("New GPG key").format(pyspread_key_uid)
        message = _("After confirming this dialog, a new GPG key ") + \
            _("'{key}' will be generated.").format(key=pyspread_key_uid) + \
            _(" \n \nThis may take some time.\nPlease wait.\n \n") + \
            _("Canceling this operation exits pyspread.")
        dlg = GMD.GenericMessageDialog(None, message, short_message, style)
        dlg.Centre()

        if dlg.ShowModal() == wx.ID_OK:
            dlg.Destroy()
            fingerprint = gpg.gen_key(input_data)

            for private_key in gpg.list_keys(True):
                if str(fingerprint) == private_key['fingerprint']:
                    config["gpg_key_uid"] = repr(private_key['uids'][0])

        else:
            dlg.Destroy()
            sys.exit()


def sign(filename):
    """Returns detached signature for file"""

    gpg = gnupg.GPG()

    signfile = open(filename, "rb")

    signed_data = gpg.sign_file(signfile, keyid=config["gpg_key_uid"],
                                detach=True)
    signfile.close()

    return signed_data


def verify(sigfilename, filefilename=None):
    """Verifies a signature, returns True if successful else False."""

    gpg = gnupg.GPG()

    sigfile = open(sigfilename, "rb")

    verified = gpg.verify_file(sigfile, filefilename)

    sigfile.close()

    return verified
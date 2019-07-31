#keymapper.py
#
# Copyright (C) 2018 John Moore
# Portions Copyright (C) 2014 Thomas Amland
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import xml.etree.ElementTree as ET
import shutil
import os
from threading import Timer
from time import sleep
from xbmcgui import Dialog, WindowXMLDialog
import xbmcaddon, xbmc

from util import GETTEXT, KEYMAPS_USERDATA_FOLDER, ADDONID, ADDON, ACTIVATIONKEY, PYVER
from resources.lib.Utilities.DebugPrint import DbgPrint

__Version__ = "1.0.1"

keymapfile = os.path.join(KEYMAPS_USERDATA_FOLDER,"gen.xml")

class keymapper(object):
    def __init__(self):
        self.dirty = False

    def backupXmlfile(self, src):
        dirname = os.path.dirname(src)
        basename = os.path.basename(src)
        name, ext = os.path.splitext(basename)

        for i in range(100):
            dst = os.path.join(dirname, "{}.bak.{:d}".format(name, i))
            if os.path.exists(dst):
                continue
            shutil.move(src, dst)
            # successfully renamed
            break

    def findKey(self, tree, key):
        for e in tree.iter('key'):
            if key in e.text:
                return e

        raise Exception("key not found")


    def setKey(self, tree, addonID, strNewkey):
        keyboardelem = tree.find('./global/keyboard')
        if keyboardelem is not None:
            elem = ET.SubElement(keyboardelem,'key',{'id':strNewkey})
            elem.text = "runaddon({})".format(addonID)
            elem.tail = "\n\t"
            self.dirty = True


    def saveXml(self, xmlFilename, tree):
        self.backupXmlfile(xmlFilename)
        tree.write(xmlFilename)

    @staticmethod
    def add_key(xmlFilename, addonID, newkey):
        DbgPrint("***xmlfilename:{}\taddonID:{}\tnewkey:{}".format(xmlFilename,addonID,newkey))
        strNewkey = newkey if type(newkey) == str else str(newkey)

        try:
            tree = ET.parse(xmlFilename)
        except:
            root = ET.Element('keymap')
            sg = ET.SubElement(root, 'global')
            sk = ET.SubElement(sg, 'keyboard')
            tree = ET.ElementTree(root)
            tree.write(xmlFilename)

        kmap = keymapper()

        try:
            elem = kmap.findKey(tree,addonID)
            if elem.attrib['id'] != strNewkey:
                elem.attrib['id'] = strNewkey
                kmap.dirty = True
        except:
            kmap.setKey(tree, addonID,strNewkey)

        if kmap.dirty:
            kmap.saveXml(xmlFilename, tree)

        # print(ET.dump(tree))

    @staticmethod
    def getCurrentActivationKey():
        filename = os.path.join(KEYMAPS_USERDATA_FOLDER, "gen.xml")
        kmap = keymapper()
        try:
            tree = ET.parse(filename)
            keyboardelem = tree.find('./global/keyboard')
            elem = kmap.findKey(keyboardelem, ADDONID)
            return elem.attrib['id']
        except: pass


class KeyListener(WindowXMLDialog):
    TIMEOUT = 5

    def __new__(cls):
        gui_api = tuple(map(int, xbmcaddon.Addon('xbmc.gui').getAddonInfo('version').split('.')))
        file_name = "DialogNotification2.xml" if gui_api >= (5, 11, 0) else "DialogKaiToast.xml"
        DbgPrint("******Dialog filename:{}".format(file_name))
        return super(KeyListener, cls).__new__(cls, file_name, xbmcaddon.Addon(ADDONID).getAddonInfo('path'))

    def __init__(self):
        self.key = None

    def onInit(self):
        if PYVER < 3.0:
            tmp = GETTEXT(30010).format(self.TIMEOUT)
        else:
            tmp = GETTEXT(30010).decode().format(self.TIMEOUT)

        try:
            self.getControl(401).addLabel(GETTEXT(30002))
            self.getControl(402).setText(tmp)
        except AttributeError as e:
            DbgPrint("****Label Attribute Error: {}".format(str(e)))
            self.getControl(401).addLabel(GETTEXT(30002))
            self.getControl(402).setText(tmp)

    def onAction(self, action):
        code = action.getButtonCode()
        self.key = None if code == 0 else str(code)
        self.close()

    @staticmethod
    def record_key():
        dialog = KeyListener()
        timeout = Timer(KeyListener.TIMEOUT, dialog.close)
        timeout.start()
        dialog.doModal()
        timeout.cancel()
        key = dialog.key
        del dialog
        return key


def setActivationKey():
    DbgPrint("******setActivationKey Called ....")
    key = KeyListener.record_key()
    currentkey = ADDON.getSetting(ACTIVATIONKEY)
    if key != currentkey and key is not None:
        ADDON.setSetting(ACTIVATIONKEY, key)
        keymapper.add_key(keymapfile, ADDONID, key)
        sleep(1)
        xbmc.executebuiltin('Action(reloadkeymaps)')


def reloadKeyMaps():
    DbgPrint("******reloadKeyMaps Called ....")
    currentkey = ADDON.getSetting(ACTIVATIONKEY)
    keymapper.add_key(keymapfile, ADDONID, currentkey)
    sleep(1)
    xbmc.executebuiltin('Action(reloadkeymaps)')



import sys
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os, sys
import urllib
import threading
import InfoDialog

from xml.dom.minidom import parse
from operator import itemgetter


#PIL fails on Android devices ?
hasPilModule = True
try:
    from PIL import Image
except:
    hasPilModule = False

class ColorPicker(xbmcgui.WindowXMLDialog):

    colorsList = None
    skinString = None
    colorsPath = None
    
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.colorsPath = xbmc.translatePath( 'special://home/addons/script.titanskin.helpers/resources/colors/' ).decode("utf-8")
        
    def addColorToList(self, colorname, colorstring):
        
        colorImageFile = os.path.join(self.colorsPath,colorstring + ".png")
        
        if not xbmcvfs.exists(colorImageFile) and hasPilModule:
            colorstring = colorstring.strip()
            if colorstring[0] == '#': colorstring = colorstring[1:]
            if len(colorstring) != 8:
                raise ValueError, "input #%s is not in #AARRGGBB format" % colorstring
            a, r, g, b = colorstring[:2], colorstring[2:4], colorstring[4:6], colorstring[6:]
            a, r, g, b = [int(n, 16) for n in (a, r, g, b)]
            color = (r, g, b, a)
            im = Image.new("RGBA", (64, 64), color)
            im.save(colorImageFile)
        elif not xbmcvfs.exists(colorImageFile) and not hasPilModule:
            return
        
        listitem = xbmcgui.ListItem(label=colorname, iconImage=colorImageFile)
        listitem.setProperty("colorstring",colorstring)
        self.colorsList.addItem(listitem)
        
    
    
    def onInit(self):
        self.action_exitkeys_id = [10, 13]

        if not xbmcvfs.exists(self.colorsPath):
            xbmcvfs.mkdir(self.colorsPath)
        
        self.colorsList = self.getControl(3110)
        self.win = xbmcgui.Window( 10000 )
        
        #get current color that is stored in the skin setting
        currentColor = xbmc.getInfoLabel("Skin.String(" + self.skinString + ')')
        selectItem = 0
        
        #get all colors from the colors xml file and fill a list with tuples to sort later on
        allColors = []
        colors_file = xbmc.translatePath( 'special://home/addons/script.titanskin.helpers/resources/colors/colors.xml' ).decode("utf-8")
        if xbmcvfs.exists( colors_file ):
            doc = parse( colors_file )
            listing = doc.documentElement.getElementsByTagName( 'color' )
            for count, color in enumerate(listing):
                name = color.attributes[ 'name' ].nodeValue.lower()
                colorstring = color.childNodes [ 0 ].nodeValue.lower()
                sortstring = colorstring[-6:]
                allColors.append((name,colorstring,sortstring))
                
        #sort list and fill the panel
        count = 0
        allColors = sorted(allColors,key=itemgetter(2))
        
        for color in allColors:
            self.addColorToList(color[0], color[1])
            if (currentColor == color[1] or currentColor == color[0]):
                selectItem = count
            count += 1

        #focus the current color
        if selectItem != 0:
            xbmc.executebuiltin("Control.SetFocus(3110)")
            self.colorsList.selectItem(selectItem)
            item =  self.colorsList.getSelectedItem()
            colorstring = item.getProperty("colorstring")
        else:
            xbmc.executebuiltin("Control.SetFocus(3010)")
            colorstring = currentColor
        
        self.win.setProperty("colorstring",colorstring)
        
        

    def onFocus(self, controlId):
        pass
        
    def onAction(self, action):

        ACTION_CANCEL_DIALOG = ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, )
        ACTION_SHOW_INFO = ( 11, )
        ACTION_SELECT_ITEM = 7
        ACTION_PARENT_DIR = 9
        
        if action.getId() in ACTION_CANCEL_DIALOG:
            self.closeDialog()
        else:
            item =  self.colorsList.getSelectedItem()
            colorstring = item.getProperty("colorstring")
            self.win.setProperty("colorstring",colorstring)


    def closeDialog(self):
        #self.close() ##crashes kodi ?
        xbmc.executebuiltin("Dialog.Close(all,true)")
        
    def onClick(self, controlID):

        if(controlID == 3110):       
            item = self.colorsList.getSelectedItem()
            colorstring = item.getLabel()
            xbmc.executebuiltin("Skin.SetString(" + self.skinString + ','+ colorstring + ')')
            self.closeDialog()
        elif(controlID == 3010):       
            dialog = xbmcgui.Dialog()
            colorstring = dialog.input("Color", self.win.getProperty("colorstring"), type=xbmcgui.INPUT_ALPHANUM)
            xbmc.executebuiltin("Skin.SetString(" + self.skinString + ','+ colorstring + ')')
            self.closeDialog()
        elif(controlID == 3011):       
            xbmc.executebuiltin("Skin.SetString(" + self.skinString + ',"None")')
            self.closeDialog()

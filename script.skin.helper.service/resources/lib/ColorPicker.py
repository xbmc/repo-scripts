import math

from xml.dom.minidom import parse
from operator import itemgetter
from Utils import *

#PIL fails on Android devices ?
hasPilModule = True
try:
    from PIL import Image
    im = Image.new("RGB", (1, 1))
    del im
except:
    hasPilModule = False

class ColorPicker(xbmcgui.WindowXMLDialog):

    colorsList = None
    skinString = None
    winProperty = None
    shortcutProperty = None
    colorsPath = None
    savedColor = None
    currentWindow = None
    headerLabel = None
    colors_file = None
    allColors = {}
    allPalettes = []
    activePalette = None
    
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.buildColorsList()
        self.result = -1
        
    def addColorToList(self, colorname, colorstring):
        colorImageFile = self.createColorSwatchImage(colorstring)
        listitem = xbmcgui.ListItem(label=colorname, iconImage=colorImageFile)
        listitem.setProperty("colorstring",colorstring)
        self.colorsList.addItem(listitem)
        
    def createColorSwatchImage(self, colorstring):
        paths = []
        paths.append(os.path.join(ADDON_PATH, 'resources', 'colors' ,colorstring + ".png"))
        if xbmcvfs.exists( "special://skin/extras/colors/colors.xml" ):
            paths.append(os.path.join(xbmc.translatePath("special://skin/extras/colors/").decode("utf-8") ,colorstring + ".png"))
        for colorImageFile in paths:
            if not xbmcvfs.exists(colorImageFile) and hasPilModule:
                try:
                    colorstring = colorstring.strip()
                    if colorstring[0] == '#': colorstring = colorstring[1:]
                    a, r, g, b = colorstring[:2], colorstring[2:4], colorstring[4:6], colorstring[6:]
                    a, r, g, b = [int(n, 16) for n in (a, r, g, b)]
                    color = (r, g, b, a)
                    im = Image.new("RGBA", (16, 16), color)
                    im.save(colorImageFile)
                except:
                    logMsg("ERROR in createColorSwatchImage for colorstring: " + colorstring, 0)
        return colorImageFile
    
    def buildColorsList(self):
        #prefer skin colors file
        if xbmcvfs.exists( "special://skin/extras/colors/colors.xml" ):
            colors_file = xbmc.translatePath("special://skin/extras/colors/colors.xml").decode("utf-8")
            self.colorsPath = xbmc.translatePath("special://skin/extras/colors/").decode("utf-8")
        else:
            colors_file = os.path.join(ADDON_PATH, 'resources', 'colors','colors.xml' ).decode("utf-8")
            self.colorsPath = os.path.join(ADDON_PATH, 'resources', 'colors' ).decode("utf-8")
        
        doc = parse( colors_file )
        paletteListing = doc.documentElement.getElementsByTagName( 'palette' )
        if paletteListing:
            #we have multiple palettes specified
            for count, item in enumerate(paletteListing):
                paletteName = item.attributes[ 'name' ].nodeValue
                self.allColors[paletteName] = self.getColorsFromXml(item)
                self.allPalettes.append(paletteName)
        else:        
            #we do not have multiple palettes
            self.allColors["all"] = self.getColorsFromXml(doc.documentElement)
            self.allPalettes.append("all")
        
    def getColorsFromXml(self,xmlelement):
        #listing = doc.documentElement.getElementsByTagName( 'color' )
        items = []
        listing = xmlelement.getElementsByTagName( 'color' )
        for count, color in enumerate(listing):
            name = color.attributes[ 'name' ].nodeValue.lower()
            colorstring = color.childNodes [ 0 ].nodeValue.lower()
            items.append( (name,colorstring) )
            
            #self.addColorToList(name, colorstring)
        return items
        
    def loadColorsForPalette(self,paletteName=""):
        self.colorsList.reset()
        if not paletteName:
            #just grab the first palette if none specified
            paletteName = self.allPalettes[0]
        # set window prop with active palette
        if paletteName != "all": self.currentWindow.setProperty("palettename",paletteName)
        if not self.allColors.get(paletteName):
            logMsg("ColorPicker ERROR - no palette exists with name " + paletteName,0)
            return
        for item in self.allColors[paletteName]:
            self.addColorToList(item[0], item[1])
    
    def onInit(self):
        self.action_exitkeys_id = [10, 13]
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        self.currentWindow = xbmcgui.Window( xbmcgui.getCurrentWindowDialogId() )
        
        self.colorsList = self.getControl(3110)
        self.win = xbmcgui.Window( 10000 )
        
        #set headerLabel
        try:
            self.getControl(1).setLabel(self.headerLabel) 
        except: pass
        
        #get current color that is stored in the skin setting
        if self.skinString:
            self.currentWindow.setProperty("colorstring", xbmc.getInfoLabel("Skin.String(" + self.skinString + ')'))
            self.currentWindow.setProperty("colorname", xbmc.getInfoLabel("Skin.String(" + self.skinString + '.name)'))
        
        #load colors in the list
        self.loadColorsForPalette(self.activePalette)
        
        #focus the current color
        if self.currentWindow.getProperty("colorstring"):
            self.currentWindow.setFocusId(3010)
        else:
            #no color setup so we just focus the colorslist
            self.currentWindow.setFocusId(3110)
            self.colorsList.selectItem(0)
        
        #set opacity slider
        if self.currentWindow.getProperty("colorstring"):
            self.setOpacitySlider()
        
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )

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
            if self.currentWindow.getFocusId() == 3110:
                item =  self.colorsList.getSelectedItem()
                colorstring = item.getProperty("colorstring")
                self.currentWindow.setProperty("colorstring",colorstring)
                self.currentWindow.setProperty("colorname",item.getLabel())
                self.setOpacitySlider()                

    def closeDialog(self):
        self.close()

    def setOpacitySlider(self):
        colorstring = self.currentWindow.getProperty("colorstring")
        try:
            if colorstring != "" and colorstring != None and colorstring.lower() != "none":
                a, r, g, b = colorstring[:2], colorstring[2:4], colorstring[4:6], colorstring[6:]
                a, r, g, b = [int(n, 16) for n in (a, r, g, b)]
                a = 100.0 * a / 255
                self.getControl( 3015 ).setPercent( float(a) )
        except: pass
        
    def onClick(self, controlID):
        colorname = self.currentWindow.getProperty("colorname")
        colorstring = self.currentWindow.getProperty("colorstring")
        if not colorname: colorname = colorstring
        if controlID == 3110:       
            self.currentWindow.setFocusId(3012)
            self.currentWindow.setProperty("color_chosen","true")
        elif controlID == 3010:  
            #manual input
            dialog = xbmcgui.Dialog()
            colorstring = dialog.input(ADDON.getLocalizedString(32012), self.currentWindow.getProperty("colorstring"), type=xbmcgui.INPUT_ALPHANUM)
            self.currentWindow.setProperty("colorname", ADDON.getLocalizedString(32050))
            self.currentWindow.setProperty("colorstring", colorstring)
            self.setOpacitySlider()
        elif controlID == 3011:
            # none button
            colorname = ADDON.getLocalizedString(32013)
            xbmc.executebuiltin("Skin.SetString(" + self.skinString + '.name,'+ colorname + ')')
            xbmc.executebuiltin("Skin.SetString(" + self.skinString + ',None)')
            xbmc.executebuiltin("Skin.Reset(" + self.skinString + '.base)')
            self.closeDialog()
        elif controlID == 3012:
            #save button clicked
            self.createColorSwatchImage(colorstring)
            if self.skinString and colorstring:
                xbmc.executebuiltin("Skin.SetString(" + self.skinString + '.name,'+ colorname + ')')
                colorbase = "ff" + colorstring[2:]
                xbmc.executebuiltin("Skin.SetString(" + self.skinString + ','+ colorstring + ')')
                xbmc.executebuiltin("Skin.SetString(" + self.skinString + '.base,'+ colorbase + ')')
                self.closeDialog()
            elif self.winProperty and colorstring:
                WINDOW.setProperty(self.winProperty, colorstring)
                WINDOW.setProperty(self.winProperty + ".name", colorname)
            elif self.shortcutProperty and colorstring:
                self.result = (colorstring,colorname)
                self.closeDialog()
          
        elif controlID == 3015:
            try:
                opacity = self.getControl( 3015 ).getPercent()
                num = opacity / 100.0 * 255
                e = num - math.floor( num )
                a = e < 0.5 and int( math.floor( num ) ) or int( math.ceil( num ) )
                colorstring = colorstring.strip()
                r, g, b = colorstring[2:4], colorstring[4:6], colorstring[6:]
                r, g, b = [int(n, 16) for n in (r, g, b)]
                color = (a, r, g, b)
                colorstringvalue = '%02x%02x%02x%02x' % color
                self.currentWindow.setProperty("colorstring",colorstringvalue)
            except: pass
            
        elif controlID == 3030:
            #change color palette
            ret = xbmcgui.Dialog().select(ADDON.getLocalizedString(32141), self.allPalettes)
            self.loadColorsForPalette(self.allPalettes[ret])

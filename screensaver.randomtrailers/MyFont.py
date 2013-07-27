# script constantes
__script__       = "MyFont.py"
__author__       = "Ppic, Frost"
__credits__      = "Team XBMC-Passion, http://passion-xbmc.org/"
__platform__     = "xbmc media center, [LINUX, OS X, WIN32, XBOX]"
__date__         = "08-01-2010"
__version__      = "1.1"

#python librairy to add font to the current skin. need to have font_filename.ttf in /resources/fonts/, this script will automatically add it to current skin when called.

import os
import elementtree as ET
import shutil
from traceback import print_exc
import xbmc
import xbmcaddon
addon = xbmcaddon.Addon()

skin_font_path = xbmc.translatePath("special://skin/fonts/")
script_font_path = os.path.join(addon.getAddonInfo('path') , "resources" , "fonts")
skin_dir = xbmc.translatePath("special://skin/")
list_dir = os.listdir( skin_dir )

print skin_font_path
print script_font_path


def getFontsXML():
    fontxml_paths = []
    try:
        for item in list_dir:
            item = os.path.join( skin_dir, item )
            if os.path.isdir( item ):
                font_xml = os.path.join( item, "Font.xml" )
                if os.path.exists( font_xml ):
                    fontxml_paths.append( font_xml )
    except:
        print_exc()
    return fontxml_paths


def isFontInstalled( fontxml_path, fontname ):
    name = "<name>%s</name>" % fontname
    if not name in file( fontxml_path, "r" ).read():
        return False
    else:
        return True


def addFont( fontname, filename, size, style="", aspect="" ):
    try:
        reload_skin = False
        fontxml_paths = getFontsXML()

        if fontxml_paths:
            for fontxml_path in fontxml_paths:
                if not isFontInstalled( fontxml_path, fontname ):
                    tree = ET.parse(fontxml_path)
                    root = tree.getroot()
                    print "modification du fichier: " + fontxml_path
                    for sets in root.getchildren():
                        sets.findall( "font" )[ -1 ].tail = "\n\t\t" #"\n\n\t\t"
                        new = ET.SubElement(sets, "font")
                        new.text, new.tail = "\n\t\t\t", "\n\t"
                        subnew1=ET.SubElement(new ,"name")
                        subnew1.text = fontname
                        subnew1.tail = "\n\t\t\t"
                        subnew2=ET.SubElement(new ,"filename")
                        subnew2.text = ( filename, "Arial.ttf" )[ sets.attrib.get( "id" ) == "Arial" ]
                        subnew2.tail = "\n\t\t\t"
                        subnew3=ET.SubElement(new ,"size")
                        subnew3.text = size
                        subnew3.tail = "\n\t\t\t"
                        last_elem = subnew3
                        if style in [ "normal", "bold", "italics", "bolditalics" ]:
                            subnew4=ET.SubElement(new ,"style")
                            subnew4.text = style
                            subnew4.tail = "\n\t\t\t"
                            last_elem = subnew4
                        if aspect:    
                            subnew5=ET.SubElement(new ,"aspect")
                            subnew5.text = aspect
                            subnew5.tail = "\n\t\t\t"
                            last_elem = subnew5
                        reload_skin = True
 
                        last_elem.tail = "\n\t\t"
                    tree.write(fontxml_path)
                    reload_skin = True
    except:
        print_exc()

    if reload_skin:
        if not os.path.exists( os.path.join( skin_font_path, filename ) ) and os.path.exists( os.path.join( script_font_path, filename ) ):
            shutil.copyfile( os.path.join( script_font_path, filename ), os.path.join( skin_font_path, filename ) )

        xbmc.executebuiltin( "XBMC.ReloadSkin()" )
        return True

    return False

if __name__ == "__main__":
    font_constant = "sportlive_font"

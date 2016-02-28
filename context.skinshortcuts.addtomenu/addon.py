import sys
import xbmc, xbmcgui
import urllib

if __name__ == '__main__':
    # Extract the info we'll send over to Skin Shortcuts
    filename = sys.listitem.getfilename()
    label = sys.listitem.getLabel()
    icon = xbmc.getInfoLabel( "ListItem.Icon" )
    content = xbmc.getInfoLabel( "Container.Content" )
    window = xbmcgui.getCurrentWindowId()

    # Call Skin Shortcuts
    runScript = "RunScript(script.skinshortcuts,type=context&filename=%s&label=%s&icon=%s&content=%s&window=%s)" %( urllib.quote( filename ), label, icon, content, window )
    xbmc.executebuiltin( "%s" %( runScript ) )

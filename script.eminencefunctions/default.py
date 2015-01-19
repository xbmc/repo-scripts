import xbmc, sys

def movetile():
    label = xbmc.getInfoLabel("Skin.String(home."+str(i)+".label)")
    path = xbmc.getInfoLabel("Skin.String(home."+str(i)+".path)")
    icon = xbmc.getInfoLabel("Skin.String(home."+str(i)+".icon)")
    bgcolor = xbmc.getInfoLabel("Skin.String(home."+str(i)+".bgcolor)")
    bgwidget = xbmc.getInfoLabel("Skin.String(home."+str(i)+".bgwidget)")
    bgwidgettype = xbmc.getInfoLabel("Skin.String(home."+str(i)+".bgwidget.type)")
    enabled = xbmc.getInfoLabel("Skin.HasSetting(home."+str(i)+".enabled)")
    
    # Disable the tile
    xbmc.executebuiltin("Skin.Reset(home."+str(i)+".enabled)")
    
    # Only move info and enable tile if it was enabled before
    if str(enabled) == "True":
        xbmc.executebuiltin("Skin.SetBool(home."+str(o)+".enabled)")
        xbmc.executebuiltin("Skin.SetString(home."+str(o)+".label,"+str(label)+")")
        xbmc.executebuiltin("Skin.SetString(home."+str(o)+".path,"+str(path)+")")
        xbmc.executebuiltin("Skin.SetString(home."+str(o)+".icon,"+str(icon)+")")
        xbmc.executebuiltin("Skin.SetString(home."+str(o)+".bgcolor,"+str(bgcolor)+")")
        xbmc.executebuiltin("Skin.SetString(home."+str(o)+".bgwidget,"+str(bgwidget)+")")
        xbmc.executebuiltin("Skin.SetString(home."+str(o)+".bgwidget.type,"+str(bgwidgettype)+")")

def removetile():
    xbmc.executebuiltin("Skin.Reset("+str(sys.argv[2])+".enabled)")
    xbmc.executebuiltin("Skin.Reset("+str(sys.argv[2])+".label)")
    xbmc.executebuiltin("Skin.Reset("+str(sys.argv[2])+".path)")
    xbmc.executebuiltin("Skin.Reset("+str(sys.argv[2])+".icon)")
    xbmc.executebuiltin("Skin.Reset("+str(sys.argv[2])+".bgwidget)")
    xbmc.executebuiltin("Skin.Reset("+str(sys.argv[2])+".bgwidget.type)")

if sys.argv[1] in ['inserttile']:
    if sys.argv[2]:
        insertpoint = str(sys.argv[2])
        insertpoint = insertpoint[-3:]
    else:
        exit

    # Do 329 to 320
    if int(insertpoint) < 320:
        for i in reversed(range(320,330)):
            o = i + 1
            movetile()
    else:
        for i in reversed(range(int(insertpoint),330)):
            o = i + 1
            movetile()
        removetile()
        exit

    # Need a special one for 312
    if int(insertpoint) < 313:
        i = 312
        o = 320
        movetile()
    else:
        removetile()
        exit

    # Do 300 to 311
    for i in reversed(range(int(insertpoint),312)):
        o = i + 1
        movetile()
    removetile()

if sys.argv[1] in ['swapitem']:
    i = str(sys.argv[2])
    i = i[-3:]
    o = str(sys.argv[3])
    o = o[-3:]
        
    label = xbmc.getInfoLabel("Skin.String(home."+str(i)+".label)")
    path = xbmc.getInfoLabel("Skin.String(home."+str(i)+".path)")
    icon = xbmc.getInfoLabel("Skin.String(home."+str(i)+".icon)")
    bgcolor = xbmc.getInfoLabel("Skin.String(home."+str(i)+".bgcolor)")
    bgwidget = xbmc.getInfoLabel("Skin.String(home."+str(i)+".bgwidget)")
    bgwidgettype = xbmc.getInfoLabel("Skin.String(home."+str(i)+".bgwidget.type)")
    enabled = xbmc.getInfoLabel("Skin.HasSetting(home."+str(i)+".enabled)")
    
    olabel = xbmc.getInfoLabel("Skin.String(home."+str(o)+".label)")
    opath = xbmc.getInfoLabel("Skin.String(home."+str(o)+".path)")
    oicon = xbmc.getInfoLabel("Skin.String(home."+str(o)+".icon)")
    obgcolor = xbmc.getInfoLabel("Skin.String(home."+str(o)+".bgcolor)")
    obgwidget = xbmc.getInfoLabel("Skin.String(home."+str(o)+".bgwidget)")
    obgwidgettype = xbmc.getInfoLabel("Skin.String(home."+str(o)+".bgwidget.type)")
    oenabled = xbmc.getInfoLabel("Skin.HasSetting(home."+str(o)+".enabled)")
    
    xbmc.executebuiltin("Skin.SetBool(home."+str(i)+".enabled)")
    xbmc.executebuiltin("Skin.SetString(home."+str(i)+".label,"+str(olabel)+")")
    xbmc.executebuiltin("Skin.SetString(home."+str(i)+".path,"+str(opath)+")")
    xbmc.executebuiltin("Skin.SetString(home."+str(i)+".icon,"+str(oicon)+")")
    xbmc.executebuiltin("Skin.SetString(home."+str(i)+".bgcolor,"+str(obgcolor)+")")
    xbmc.executebuiltin("Skin.SetString(home."+str(i)+".bgwidget,"+str(obgwidget)+")")
    xbmc.executebuiltin("Skin.SetString(home."+str(i)+".bgwidget.type,"+str(obgwidgettype)+")")
    
    xbmc.executebuiltin("Skin.SetBool(home."+str(o)+".enabled)")
    xbmc.executebuiltin("Skin.SetString(home."+str(o)+".label,"+str(label)+")")
    xbmc.executebuiltin("Skin.SetString(home."+str(o)+".path,"+str(path)+")")
    xbmc.executebuiltin("Skin.SetString(home."+str(o)+".icon,"+str(icon)+")")
    xbmc.executebuiltin("Skin.SetString(home."+str(o)+".bgcolor,"+str(bgcolor)+")")
    xbmc.executebuiltin("Skin.SetString(home."+str(o)+".bgwidget,"+str(bgwidget)+")")
    xbmc.executebuiltin("Skin.SetString(home."+str(o)+".bgwidget.type,"+str(bgwidgettype)+")")

if sys.argv[1] in ['setfavourite']:
    o = str(sys.argv[2])
    o = o[-3:]
    bgwidget = str(sys.argv[3])
    bgwidgettype = str(sys.argv[4])
    
    # Remove ActivateWindow Part
    bgwidget = bgwidget.replace('ActivateWindow(10025,','')
    bgwidget = bgwidget.replace('ActivateWindow(10502,','')
    bgwidget = bgwidget.replace(')','')
        
    # Set the strings
    xbmc.executebuiltin("Skin.SetString(home."+str(o)+".bgwidget,"+str(bgwidget)+")")
    xbmc.executebuiltin("Skin.SetString(home."+str(o)+".bgwidget.type,"+str(bgwidgettype)+")")

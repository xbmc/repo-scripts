import xbmcaddon
import xbmcgui

Addon = xbmcaddon.Addon('script.bluetooth.delay')

line1 = Addon.getSetting('line1')
line2 = Addon.getSetting('line2')
d1 = Addon.getSetting('Device1')
d2 = Addon.getSetting('Device2')
state = Addon.getSetting('state')
firstRun = Addon.getSetting('firstRun')
t = 1000

y = ((float(d2) * 1000000) - (float(d1) * 1000000)) / 25000
y = int(y)

arg = None
try:
   arg = sys.argv[1].lower()
except Exception:
   pass

def skin1():
    xbmc.executebuiltin('ActivateWindow(osdaudiosettings)')
    xbmc.executebuiltin('SetFocus(-73)')
    xbmc.executebuiltin("Action(select)")
    xbmc.executebuiltin('SetFocus(11)')
    xbmc.executebuiltin("Action(select)", wait=True)
    xbmc.executebuiltin("Action(close)", wait=True)

def skin2():
    xbmc.executebuiltin('ActivateWindow(osdaudiosettings)')
    xbmc.executebuiltin('SetFocus(-74)')
    xbmc.executebuiltin("Action(select)")
    xbmc.executebuiltin('SetFocus(11)')
    xbmc.executebuiltin("Action(select)", wait=True)
    xbmc.executebuiltin("Action(close)", wait=True)

# reset for first run kodi
def reset1():
    xbmc.executebuiltin('ActivateWindow(osdaudiosettings)')
    xbmc.executebuiltin('SetFocus(-77)')
    xbmc.executebuiltin("Action(select)")
    xbmc.executebuiltin('SetFocus(11)')
    xbmc.executebuiltin("Action(select)", wait=True)
    xbmc.executebuiltin("Action(close)", wait=True)

def reset2():
    xbmc.executebuiltin('ActivateWindow(osdaudiosettings)')
    xbmc.executebuiltin('SetFocus(-78)')
    xbmc.executebuiltin("Action(select)")
    xbmc.executebuiltin('SetFocus(11)')
    xbmc.executebuiltin("Action(select)", wait=True)
    xbmc.executebuiltin("Action(close)", wait=True)

if "ace2" in xbmc.getSkinDir():
    skin1 = skin2
    reset1 = reset2
elif "aeon.nox.silvo" in xbmc.getSkinDir():
    skin1 = skin2
    reset1 = reset2
elif "aeon.tajo" in xbmc.getSkinDir():
    skin1 = skin2
    reset1 = reset2
elif "aeonmq8" in xbmc.getSkinDir():
    skin1 = skin2
    reset1 = reset2
elif "ftv" in xbmc.getSkinDir():
    skin1 = skin2
    reset1 = reset2
elif "madnox" in xbmc.getSkinDir():
    skin1 = skin2
    reset1 = reset2
elif "pellucid" in xbmc.getSkinDir():
    skin1 = skin2
    reset1 = reset2
elif "quartz" in xbmc.getSkinDir():
     skin1 = skin2
     reset1 = reset2
elif "xperience1080" in xbmc.getSkinDir():
    skin1 = skin2
    reset1 = reset2
elif "mimic.lr" in xbmc.getSkinDir():
    skin1 = skin2
    reset1 = reset2

def bluetooth():
    Addon.setSettingBool('state', 0)
    for x in range(y):
        xbmc.executebuiltin("Action(AudioDelayPlus)")
    xbmcgui.Dialog().notification("",line2, "",t)

def speakers():
    Addon.setSettingBool('state', 1)
    for x in range(y):
        xbmc.executebuiltin("Action(AudioDelayMinus)")
    xbmcgui.Dialog().notification("",line1, "",t)

def main():

    if arg == "reset":
        xbmc.executebuiltin('PlayerControl(stop)')
        Addon.setSettingBool('state', 1)
        reset1()
        skin1()
        xbmcgui.Dialog().notification("",Addon.getLocalizedString(30006), "",t*2)

    elif d2 == d1:
        if firstRun == "false":
            xbmcgui.Dialog().ok(Addon.getLocalizedString(30007), Addon.getLocalizedString(30008))
            Addon.setSettingBool('firstRun', 1)
        xbmcaddon.Addon().openSettings()

    elif (xbmc.getCondVisibility('Player.HasMedia') == False):
        Addon.setSettingBool('state', 1)
        reset1()
        skin1()
        xbmcgui.Dialog().notification("",line1, "",t)
        xbmcgui.Dialog().notification("",Addon.getLocalizedString(30009), "",t)

    elif arg == None:
        if state == "true":
            bluetooth()
            skin1()
        else:
            speakers()
            skin1()

    elif arg == "0":
        if state == "false":
            speakers()
            skin1()
        else:
            xbmcgui.Dialog().notification("",line1, "",t)

    elif arg == "1":
        if state == "true":
            bluetooth()
            skin1()
        else:
            xbmcgui.Dialog().notification("",line2, "",t)

main()

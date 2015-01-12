import sys
import os
import xbmc
import xbmcaddon
import xbmcplugin
try:
    import buggalo
    buggalo.GMAIL_RECIPIENT = "phil65@kodi.tv"
except:
    pass
addon = xbmcaddon.Addon()
addon_version = addon.getAddonInfo('version')
addon_name = addon.getAddonInfo('name')
addon_path = addon.getAddonInfo('path').decode("utf-8")
sys.path.append(xbmc.translatePath(os.path.join(addon_path, 'resources', 'lib')).decode("utf-8"))
from process import StartInfoActions


class Main:

    def __init__(self):
        xbmc.log("version %s started" % addon_version)
        xbmc.executebuiltin('SetProperty(extendedinfo_running,True,home)')
        try:
            self._parse_argv()
            if self.infos:
                self.control = StartInfoActions(self.infos, self.params)
            elif not self.handle:
                import DialogVideoList
                dialog = DialogVideoList.DialogVideoList(u'script-%s-VideoList.xml' % addon_name, addon_path)
                dialog.doModal()
            if self.control == "plugin":
                xbmcplugin.endOfDirectory(self.handle)
            xbmc.executebuiltin('ClearProperty(extendedinfo_running,home)')
        except Exception:
            xbmc.executebuiltin('Dialog.Close(busydialog)')
            buggalo.onExceptionRaised()
            xbmc.executebuiltin('ClearProperty(extendedinfo_running,home)')

    def _parse_argv(self):
        if sys.argv[0] == 'plugin://script.extendedinfo/':
            args = sys.argv[2][1:].split("&&")
            self.handle = int(sys.argv[1])
            self.control = "plugin"
        else:
            self.control = None
            self.handle = None
            args = sys.argv
        self.infos = []
        self.params = {"handle": self.handle,
                       "control": self.control}
        for arg in args:
            if arg == 'script.extendedinfo':
                continue
            param = arg.replace('"', '').replace("'", " ")
            if param.startswith('info='):
                self.infos.append(param[5:])
            else:
                try:
                    self.params[param.split("=")[0].lower()] = "=".join(param.split("=")[1:]).strip()
                except:
                    pass

if (__name__ == "__main__"):
    Main()
xbmc.log('finished')

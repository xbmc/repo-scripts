# -*- coding: utf-8 -*-
import sys

if __name__ == '__main__':
    arg = None
    if len(sys.argv) > 1:
        arg = sys.argv[1] or False
    extra = sys.argv[2:]
    if arg and arg.startswith('key.'):  # Deprecated in Gotham - now using NotifyAll
        command = arg[4:]
        from lib import util
        util.sendCommand(command)
    elif arg and arg.startswith('keymap.'):
        command = arg[7:]
        from lib import keymapeditor
        keymapeditor.processCommand(command)
    elif arg == 'settings_dialog':
        from lib import util
        util.selectSetting(*extra)
    elif arg == 'player_dialog':  # Deprecated in 0.0.86 - now using NotifyAll
        from lib import util
        util.selectPlayer(*extra)
    elif arg == 'backend_dialog':  # Deprecated in 0.0.86 - now using NotifyAll
        from lib import util
        util.selectBackend()
    elif arg == 'settings':  # No longer used, using XBMC.Addon.OpenSettings(service.xbmc.tts) in keymap instead
        from lib import util
        util.xbmcaddon.Addon().openSettings()
    elif arg is None:
        from service import TTSService
        TTSService().start()

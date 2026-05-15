#!/usr/bin/python

########################

import sys
import xbmcgui

from resources.lib.helper import *
from resources.lib.utils import *

########################


class Main:
    # Explicit allowlist of actions exposed to skin XML via RunScript.
    # Restricting dispatch to this whitelist prevents arbitrary function
    # execution from user-controlled input.
    ALLOWED_ACTIONS = {
        'calc': calc,
        'toggleaddons': toggleaddons,
        'playitem': playitem,
        'playall': playall,
        'txtfile': txtfile,
        'multi_scan': multi_scan,
        'multi_scan_music': multi_scan_music,
        'reset_scan': reset_scan,
    }

    def __init__(self):
        self.action = False
        self.params = {}
        self._parse_argv()

        if self.action:
            self.getactions()
        else:
            DIALOG.ok(ADDON.getLocalizedString(32000), ADDON.getLocalizedString(32001))

    def _parse_argv(self):
        args = sys.argv

        for arg in args:
            if arg == ADDON_ID:
                continue
            if arg.startswith('action='):
                self.action = arg[7:].lower()
            else:
                try:
                    self.params[arg.split("=")[0].lower()] = "=".join(arg.split("=")[1:]).strip()
                except Exception:
                    self.params = {}

    def getactions(self):
        action_func = self.ALLOWED_ACTIONS.get(self.action)
        if action_func is not None:
            action_func(self.params)
        else:
            log('Invalid action requested: %s' % self.action)

# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
import sys
from resources.lib.skinvariables import SkinVariables
from resources.lib.viewtypes import ViewTypes


class Script(object):
    def __init__(self):
        self.params = {}

    def get_params(self):
        for arg in sys.argv:
            if arg == 'script.py':
                pass
            elif '=' in arg:
                arg_split = arg.split('=', 1)
                if arg_split[0] and arg_split[1]:
                    key, value = arg_split
                    self.params.setdefault(key, value)
            else:
                self.params.setdefault(arg, True)

    def router(self):
        if self.params.get('action') == 'buildviews':
            ViewTypes().update_xml(
                skinfolder=self.params.get('folder'),
                force=self.params.get('force'),
                configure=self.params.get('configure'),
                contentid=self.params.get('contentid'),
                viewid=self.params.get('viewid'),
                pluginname=self.params.get('pluginname'))
        else:
            SkinVariables().update_xml(
                skinfolder=self.params.get('folder'),
                force=self.params.get('force'))

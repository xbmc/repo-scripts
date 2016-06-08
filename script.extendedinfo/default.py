# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import sys

from resources.lib import process

from kodi65 import addon
from kodi65 import utils


def pass_list_to_skin(name, data, prefix="", limit=False):
    if data and limit and int(limit) < len(data):
        data = data[:int(limit)]
    if not data:
        addon.set_global('%s%s.Count' % (prefix, name), '0')
        return None
    for (count, result) in enumerate(data):
        for (key, value) in result.iteritems():
            addon.set_global('%s%s.%i.%s' % (prefix, name, count + 1, key), unicode(value))
        for key, value in result.get("properties", {}).iteritems():
            if not value:
                continue
            addon.set_global('%s%s.%i.%s' % (prefix, name, count + 1, key), unicode(value))
    addon.set_global('%s%s.Count' % (prefix, name), str(len(data)))


class Main:

    def __init__(self):
        utils.log("version %s started" % addon.VERSION)
        addon.set_global("extendedinfo_running", "true")
        self._parse_argv()
        for info in self.infos:
            listitems = process.start_info_actions(info, self.params)
            pass_list_to_skin(name=info,
                              data=listitems,
                              prefix=self.params.get("prefix", ""),
                              limit=self.params.get("limit", 20))
        if not self.infos:
            addon.set_global('infodialogs.active', "true")
            from resources.lib.WindowManager import wm
            wm.open_video_list()
            addon.clear_global('infodialogs.active')
        addon.clear_global("extendedinfo_running")

    def _parse_argv(self):
        self.infos = []
        self.params = {"handle": None}
        for arg in sys.argv[1:]:
            param = arg.replace('"', '').replace("'", " ")
            if param.startswith('info='):
                self.infos.append(param[5:])
            else:
                try:
                    self.params[param.split("=")[0].lower()] = "=".join(param.split("=")[1:]).strip().decode('utf-8')
                except Exception:
                    pass

if (__name__ == "__main__"):
    Main()
utils.log('finished')

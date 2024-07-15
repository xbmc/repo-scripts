# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# Modifications copyright (C) 2022 - Scott Smart <scott967@kodi.tv>
# This program is Free Software see LICENSE file for details
"""Module called by Runscript() as executable in Kodi
"""

from __future__ import annotations

import sys

from resources.kutil131 import addon

from resources.kutil131 import utils
from resources.lib import process


def pass_list_to_skin(name: str, data, prefix: str = "", limit: int = False) -> None:
    """Set home window properties from the data

    SetProperty(prefixname.%d.data_item key,data_item value, home) for 1 to
    limit number of items in data

    Args:
        name (str): Type of data being returned derived from runscript info
            parameter.  Used to construct the skin window property key
            eg. topratedmovies from invocation parameter info=
        data (kutils131.itemlist.ItemList): collection of ListItems
            (Video or Audio)
        prefix (str, optional):  Optional prefix for the name.  May be set
            as a param in runscript.  Defaults to "".
        limit (int, optional):  Number of items to return. May be set as a param
            in runscript.  Defaults to False.

    Returns:
        None
    """
    if data and limit and int(limit) < len(data):
        data = data[:int(limit)]
    if not data:
        addon.set_global(f'{prefix}{name}.Count', '0')
        return None
    for (count, result) in enumerate(data):
        for (key, value) in result.get_infos().items():
            addon.set_global(f'{prefix}{name}.{count + 1}.{key}', str(value))
        for key, value in result.get("properties", {}).items():
            if not value:
                continue
            addon.set_global(f'{prefix}{name}.{count + 1}.{key}', str(value))
    addon.set_global(f'{prefix}{name}.Count', str(len(data)))


class Main:
    """When called by Runscript provides all functionality.  Multiple instances
    of Main can be created.  No class attributes or methods are provided
    """

    def __init__(self):
        """Constructs the main process as object

        Parse the invocation argument strings to create self.infos (called with
        info= args) list and self.params dict  (called with param=value pairs)
        If started with no parameters, opens the video list dialog with movies
        from TMDB retrieved by popularity.
        """
        utils.log(f"version {addon.VERSION} started")
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
            try:
                from resources.lib.windowmanager import wm
                wm.open_video_list()
            finally:
                addon.clear_global('infodialogs.active')
        addon.clear_global("extendedinfo_running")

    def _parse_argv(self) -> None:
        """gets arguments passed by Runscript call and passes them as
        instance attributes of self.infos list (invoked with info=)
        and self.params dict
        """
        self.infos: list[str] = []
        self.params: dict[str, str] = {"handle": None}
        for arg in sys.argv[1:]:
            param = arg.replace('"', '').replace("'", " ")
            if param.startswith('info='):
                self.infos.append(param[5:])
            else:
                try:
                    self.params[param.split('=', maxsplit=1)[0].lower()] = "=".join(
                        param.split("=")[1:]).strip()
                except Exception:
                    pass


if (__name__ == "__main__"):
    Main()
utils.log('finished')

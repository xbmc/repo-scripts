# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# Modifications copyright (C) 2022 - Scott Smart <scott967@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmc
import xbmcgui
from resources.kutil131 import ActionHandler, addon

from resources.kutil131 import utils
from resources.lib import themoviedb as tmdb

from .dialogbaseinfo import DialogBaseInfo

BUTTONS = {8, 9, 10, 6001, 6002, 6003, 6005, 6006}

ID_BUTTON_PLOT = 132
ID_BUTTON_MANAGE = 445
ID_BUTTON_SETRATING = 6001
ID_BUTTON_FAV = 6003

ch = ActionHandler()


class DialogVideoInfo(DialogBaseInfo):
    """

    Args:
        DialogBaseInfo (_type_): _description_
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def onClick(self, control_id):
        super().onClick(control_id)
        ch.serve(control_id, self)

    def set_buttons(self):
        for button_id in BUTTONS:
            self.set_visible(button_id, False)

    @ch.click(ID_BUTTON_PLOT)
    def show_plot(self, control_id):
        xbmcgui.Dialog().textviewer(heading=addon.LANG(32037),
                                    text=self.info.get_info("plot"))

    def get_manage_options(self):
        return []

    def get_identifier(self):
        return self.info.get_property("id")

    @ch.click(ID_BUTTON_MANAGE)
    def show_manage_dialog(self, control_id):
        options = self.get_manage_options()
        index = xbmcgui.Dialog().select(heading=addon.LANG(32133),
                                        list=[i[0] for i in options])
        if index == -1:
            return None
        for item in options[index][1].split("||"):
            xbmc.executebuiltin(item)

    @ch.click(ID_BUTTON_FAV)
    def change_list_status(self, control_id):
        tmdb.change_fav_status(media_id=self.info.get_property("id"),
                               media_type=self.TYPE_ALT,
                               status=str(not bool(self.states["favorite"])).lower())
        self.update_states()

    @ch.click(ID_BUTTON_SETRATING)
    def set_rating_dialog(self, control_id):
        preselect = int(self.states["rated"]["value"]) if (
            self.states and self.states.get("rated")) else -1
        rating = utils.input_userrating(preselect=preselect)
        if rating == -1:
            return None
        if tmdb.set_rating(media_type=self.TYPE_ALT,
                           media_id=self.get_identifier(),
                           rating=rating,
                           dbid=self.info.get_info("dbid")):
            self.setProperty("rated", str(rating) if rating > 0 else "")
            self.update_states()

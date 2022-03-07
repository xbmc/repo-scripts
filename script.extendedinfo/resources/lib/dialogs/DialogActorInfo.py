# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# Modifications copyright (C) 2022 - Scott Smart <scott967@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmcgui
from kutils import ActionHandler, addon, imagetools
from resources.lib import TheMovieDB as tmdb

from .DialogBaseInfo import DialogBaseInfo

ID_CONTROL_PLOT = 132

ch = ActionHandler()


class DialogActorInfo(DialogBaseInfo):
    """creates a dialog window for actor info

    Args:
        DialogBaseInfo (_type_): handles common window details
    """
    TYPE = "Actor"
    LISTS = [(150, "movie_roles"),
             (250, "tvshow_roles"),
             (450, "images"),
             (550, "movie_crew_roles"),
             (650, "tvshow_crew_roles"),
             (750, "tagged_images")]

    def __init__(self, *args, **kwargs) -> None:
        """Constructs the dialog window with actor info from tmdb
        slef.info is a ListItem for the actor
        self.lists is a list of ListItems for the actor's movies and tv shows 

        Arguments:
            *args: dialog xml filename
                this addon path (for cache)
            **kwargs: id[str]: the tmdb actor id 

        Returns:
            None: if no tmdb extended actor info available
        """
        super(DialogActorInfo, self).__init__(*args, **kwargs)
        data = tmdb.extended_actor_info(actor_id=kwargs.get('id'))
        if not data:
            return None
        self.info, self.lists = data
        self.info.update_properties(
            imagetools.blur(self.info.get_art("thumb")))

    def onInit(self):
        self.get_youtube_vids(self.info.label)
        super(DialogActorInfo, self).onInit()

    def onClick(self, control_id):
        super(DialogActorInfo, self).onClick(control_id)
        ch.serve(control_id, self)

    @ch.click(ID_CONTROL_PLOT)
    def show_plot(self, control_id):
        xbmcgui.Dialog().textviewer(heading=addon.LANG(32037),
                                    text=self.info.get_property("biography"))

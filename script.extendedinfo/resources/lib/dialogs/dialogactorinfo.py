# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# Modifications copyright (C) 2022 - Scott Smart <scott967@kodi.tv>
# This program is Free Software see LICENSE file for details

"""Provides the DialogActorInfo class that implements a dialog
XML window.  The Actor Info is added to the window properties
from a kutils VideoItem.  Panels of VideoItems are added from
kutils ItemLists and a Youtube list.

The class hierarchy is:
    xbmcgui.Window
    --------------
    xbmcgui.WindowXML / xbmcgui.WindowDialogMixin
    ---------------
    xbmc.WindowDialogXML / kutils.windows.WindowMixin
    ---------------
    kutils.windows.DialogXML
    ---------------
    DialogBaseInfo
    ---------------
    DialogActorInfo

"""

import xbmcgui
from resources.kutil131 import ActionHandler, ItemList, addon

from resources.kutil131 import VideoItem, imagetools, utils
from resources.lib import themoviedb as tmdb

from .dialogbaseinfo import DialogBaseInfo

ID_CONTROL_PLOT = 132

ch = ActionHandler()


class DialogActorInfo(DialogBaseInfo):
    """creates a dialog XML window for actor info

    Args:
        DialogBaseInfo: handles common window details
    """
    TYPE = "Actor"
    LISTS = [(150, "movie_roles"),
             (250, "tvshow_roles"),
             (450, "images"),
             (550, "movie_crew_roles"),
             (650, "tvshow_crew_roles"),
             (750, "tagged_images")]

    def __init__(self, *args, **kwargs):
        """Constructs the dialog window with actor info from tmdb
        self.info is a ListItem for the actor
        self.lists is a list of ListItems for the actor's movies and tv shows
        if TMDB actor id is provided, gets extended info from TMDB 

        Arguments:
            *args: dialog xml filename
                this addon path (for cache)
            **kwargs: id(int): the tmdb actor id
        Returns:
            None: if no tmdb extended actor info available
            self.info and self.lists are set from extended actor info
        """
        super().__init__(*args, **kwargs)
        data: tuple = tmdb.extended_actor_info(actor_id=kwargs.get('id'))
        if not data:
            return None
        self.info, self.lists = data
        self.info.update_properties(
            imagetools.blur(self.info.get_art("thumb")))

    def onInit(self, *args, **kwargs):
        """callback function from Kodi when window is opened
        Also calls onInit in parent classes to set all info in the
        dialog window
        """
        self.get_youtube_vids(self.info.label)
        super().onInit()

    def onClick(self, control_id):
        """callback function from Kodi when control in window is
        clicked

        Args:
            control_id (int): id of window control that was clicked
        """
        super().onClick(control_id)
        ch.serve(control_id, self)

    @ch.click(ID_CONTROL_PLOT)
    def show_plot(self, control_id):
        """Opens info dialog textbox in a textviewer

        Args:
            control_id (int): window control id that was clicked
        """
        xbmcgui.Dialog().textviewer(heading=addon.LANG(32037),
                                    text=self.info.get_property("biography"))

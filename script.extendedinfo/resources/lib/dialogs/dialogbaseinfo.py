# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# Modifications copyright (C) 2022 - Scott Smart <scott967@kodi.tv>
# This program is Free Software see LICENSE file for details

import traceback

import xbmc
import xbmcgui
from resources.kutil131 import (ActionHandler, addon, kodijson, selectdialog, slideshow,
                    windows)

from resources.kutil131 import VideoItem, utils, youtube
from resources.lib import themoviedb as tmdb
from resources.lib.windowmanager import wm

ch = ActionHandler()

ID_LIST_YOUTUBE = 350
ID_LIST_IMAGES = 1250
ID_BUTTON_BOUNCEUP = 20000
ID_BUTTON_BOUNCEDOWN = 20001


class DialogBaseInfo(windows.DialogXML):
    """Class constructs a basic dialog xml window.   Subclasses augment for different
    dialog types (eg actor info or movie info)

    Args:
        windows.DialogXML (DialogXML): a kutils class derived from xbmcgui.WindowXMLDialog
        and kutils WindowMixin classes

    Returns:
        _type_: _description_
    """
    ACTION_PREVIOUS_MENU = [92, 9]
    ACTION_EXIT_SCRIPT = [13, 10]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logged_in: bool = tmdb.Login.check_login()
        self.bouncing = False
        self.last_focus = None
        self.lists = None
        self.states = False
        self.yt_listitems = []
        self.info = VideoItem() # kutils listitem
        self.last_control = None
        self.last_position = None

    def onInit(self, *args, **kwargs):
        super().onInit()
        # self.set_buttons()
        self.info.to_windowprops(window_id=self.window_id)  #kutils sets dialog window
        #properties from the info VideoItem(listitem)
        for container_id, key in self.LISTS:
            try:
                self.getControl(container_id).reset()
                items = [i.get_listitem() for i in self.lists[key]] # lists is a dict of ItemList get_listitem gets xbmc listitem from VideoItem
                self.getControl(container_id).addItems(items)
            except (IndexError, KeyError) as err:
                utils.log(f'Notice: No container with id {container_id} key {key} available due to {err}')
            except Exception as err:
                utils.log(f'Notice: No container with id {container_id} key {key} available due to {err}')
                utils.log(f'traceback for this exception\n{traceback.format_exc()}')
        if self.last_control:
            self.setFocusId(self.last_control)
        if self.last_control and self.last_position:
            try:
                self.getControl(self.last_control).selectItem(
                    self.last_position)
            except Exception:
                pass
        addon.set_global("ImageColor", self.info.get_property('ImageColor'))
        addon.set_global("ImageFilter", self.info.get_property('ImageFilter'))
        addon.set_global("infobackground", self.info.get_art('fanart_small'))
        self.setProperty("type", self.TYPE)
        self.setProperty("tmdb_logged_in", "true" if self.logged_in else "")

    def onAction(self, action):
        ch.serve_action(action, self.getFocusId(), self)

    def onClick(self, control_id: int):
        super().onClick(control_id)
        ch.serve(control_id, self)

    def onFocus(self, control_id):
        if control_id == ID_BUTTON_BOUNCEUP:
            if not self.bouncing:
                self.bounce("up")
            self.setFocusId(self.last_focus)
        elif control_id == ID_BUTTON_BOUNCEDOWN:
            if not self.bouncing:
                self.bounce("down")
            self.setFocusId(self.last_focus)
        self.last_focus = control_id

    def close(self):
        try:
            self.last_position = self.getFocus().getSelectedPosition()
        except Exception:
            self.last_position = None
        addon.set_global("infobackground", "")
        self.last_control = self.getFocusId()
        super().close()

    @utils.run_async
    def bounce(self, identifier):
        self.bouncing = True
        self.setProperty("Bounce.%s" % identifier, "true")
        xbmc.sleep(200)
        self.clearProperty("Bounce.%s" % identifier)
        self.bouncing = False

    @ch.click_by_type("music")
    # hack: use "music" until "pictures" got added to core
    def open_image(self, control_id):
        key = [key for container_id,
               key in self.LISTS if container_id == control_id][0]
        pos = slideshow.open(listitems=self.lists[key],
                             index=self.getControl(control_id).getSelectedPosition())
        self.getControl(control_id).selectItem(pos)

    @ch.click_by_type("video")
    def play_youtube_video(self, control_id):
        wm.play_youtube_video(youtube_id=self.FocusedItem(control_id).getProperty("youtube_id"),
                              listitem=self.FocusedItem(control_id))

    @ch.click_by_type("artist")
    def open_actor_info(self, control_id):
        wm.open_actor_info(actor_id=self.FocusedItem(control_id).getProperty("id"),
                            name=self.FocusedItem(control_id).getLabel())

    @ch.click_by_type("movie")
    def open_movie_info(self, control_id):
        wm.open_movie_info(movie_id=self.FocusedItem(control_id).getProperty("id"),
                           dbid=self.FocusedItem(control_id).getVideoInfoTag().getDbId())

    @ch.click_by_type("tvshow")
    def open_tvshow_info(self, control_id):
        wm.open_tvshow_info(tmdb_id=self.FocusedItem(control_id).getProperty("id"),
                            dbid=self.FocusedItem(control_id).getVideoInfoTag().getDbId())

    @ch.click_by_type("episode")
    def open_episode_info(self, control_id):
        info = self.FocusedItem(control_id).getVideoInfoTag()
        wm.open_episode_info(tvshow=self.info.get_info("tvshowtitle"),
                             tvshow_id=self.tvshow_id,
                             season=info.getSeason(),
                             episode=info.getEpisode())

    @ch.context("music")
    def thumbnail_options(self, control_id):
        listitem = self.FocusedItem(control_id)
        art_type = listitem.getProperty("type")
        options = []
        if self.info.get_info("dbid") and art_type == "poster":
            options.append(("db_art", addon.LANG(32006)))
        if self.info.get_info("dbid") and art_type == "fanart":
            options.append(("db_art", addon.LANG(32007)))
        movie_id = listitem.getProperty("movie_id")
        if movie_id:
            options.append(("movie_info", addon.LANG(10524)))
        if not options:
            return None
        action = utils.contextmenu(options=options)
        if action == "db_art":
            kodijson.set_art(media_type=self.getProperty("type"),
                             art={art_type: listitem.get_art("original")},
                             dbid=self.info.get_info("dbid"))
        elif action == "movie_info":
            wm.open_movie_info(movie_id=listitem.getProperty("movie_id"),
                               dbid=listitem.getVideoInfoTag().getDbId())

    @ch.context("video")
    def video_context_menu(self, control_id):
        index = xbmcgui.Dialog().contextmenu(list=[addon.LANG(33003)])
        if index == 0:
            #utils.download_video(self.FocusedItem(
            #    control_id).getProperty("youtube_id"))
            pass

    @ch.context("movie")
    def movie_context_menu(self, control_id):
        movie_id = self.FocusedItem(control_id).getProperty("id")
        dbid = self.FocusedItem(control_id).getVideoInfoTag().getDbId()
        options = [addon.LANG(32113)]
        if self.logged_in:
            options.append(addon.LANG(32083))
        index = xbmcgui.Dialog().contextmenu(list=options)
        if index == 0:
            rating = utils.input_userrating()
            if rating == -1:
                return None
            tmdb.set_rating(media_type="movie",
                            media_id=movie_id,
                            rating=rating,
                            dbid=dbid)
            xbmc.sleep(2000)
            tmdb.get_movie(movie_id=movie_id,
                           cache_days=0)
        elif index == 1:
            account_lists = tmdb.get_account_lists()
            if not account_lists:
                return False
            listitems = ["%s (%i)" % (i["name"], i["item_count"])
                         for i in account_lists]
            i = xbmcgui.Dialog().select(addon.LANG(32136), listitems)
            if i > -1:
                tmdb.change_list_status(list_id=account_lists[i]["id"],
                                        movie_id=movie_id,
                                        status=True)

    @ch.context("artist")
    def person_context_menu(self, control_id):
        listitem = self.FocusedItem(control_id)
        options = [addon.LANG(32009), addon.LANG(32070)]
        credit_id = listitem.getProperty("credit_id")
        if credit_id and self.TYPE == "TVShow":
            options.append(addon.LANG(32147))
        index = xbmcgui.Dialog().contextmenu(list=options)
        if index == 0:
            wm.open_actor_info(actor_id=listitem.getProperty("id"))
        if index == 1:
            filters = [{"id": listitem.getProperty("id"),
                        "type": "with_people",
                        "label": listitem.getLabel()}]
            wm.open_video_list(filters=filters)
        if index == 2:
            self.open_credit_dialog(credit_id)

    @ch.context("tvshow")
    def tvshow_context_menu(self, control_id):
        tvshow_id = self.FocusedItem(control_id).getProperty("id")
        dbid = self.FocusedItem(control_id).getVideoInfoTag().getDbId()
        credit_id = self.FocusedItem(control_id).getProperty("credit_id")
        options = [addon.LANG(32169)]
        if credit_id:
            options.append(addon.LANG(32147))
        index = xbmcgui.Dialog().contextmenu(list=options)
        if index == 0:
            rating = utils.input_userrating()
            if rating == -1:
                return None
            tmdb.set_rating(media_type="tvshow",
                            media_id=tvshow_id,
                            rating=rating,
                            dbid=dbid)
            xbmc.sleep(2000)
            tmdb.get_tvshow(tvshow_id=tvshow_id,
                            cache_days=0)
        if index == 1:
            self.open_credit_dialog(credit_id=credit_id)

    @ch.action("parentdir", "*")
    @ch.action("parentfolder", "*")
    def previous_menu(self, control_id):
        onback = self.getProperty("%i_onback" % control_id)
        if onback:
            xbmc.executebuiltin(onback)
        else:
            self.close()

    @ch.action("previousmenu", "*")
    def exit_script(self, *args):
        self.exit()

    # @utils.run_async
    def get_youtube_vids(self, search_str):
        try:
            youtube_list = self.getControl(ID_LIST_YOUTUBE)
        except Exception as err:
            utils.log(f'DialogBaseInfo.get_youtube_vids threw exception {err}')
            return None
        if not self.yt_listitems:
            user_key = addon.setting("Youtube API Key")
            search_str = search_str.replace('-', '')
            self.yt_listitems = youtube.search(
                search_str, limit=15, api_key=user_key)
        if not self.yt_listitems:
            return None
        vid_ids = [item.get_property(
            "key") for item in self.lists["videos"]] if "videos" in self.lists else []
        youtube_list.reset()
        youtube_list.addItems(
            [i.get_listitem() for i in self.yt_listitems if i.get_property("youtube_id") not in vid_ids])

    def open_credit_dialog(self, credit_id):
        info = tmdb.get_credit_info(credit_id)
        listitems = []
        if "seasons" in info["media"]:
            listitems += tmdb.handle_seasons(info["media"]["seasons"])
        if "episodes" in info["media"]:
            listitems += tmdb.handle_episodes(info["media"]["episodes"])
        if not listitems:
            listitems += [{"label": addon.LANG(19055)}]
        index = selectdialog.open(header=addon.LANG(32151),
                                  listitems=listitems)
        if index == -1:
            return None
        listitem = listitems[index]
        if listitem["mediatype"] == "episode":
            wm.open_episode_info(season=listitem["season"],
                                 episode=listitem["episode"],
                                 tvshow_id=info["media"]["id"])
        elif listitem["mediatype"] == "season":
            wm.open_season_info(season=listitem["season"],
                                tvshow_id=info["media"]["id"])

    def update_states(self):
        if not self.states:
            return None
        utils.dict_to_windowprops(data=tmdb.get_account_props(self.states),
                                  window_id=self.window_id)

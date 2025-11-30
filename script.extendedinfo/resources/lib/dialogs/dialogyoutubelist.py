# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# Modifications copyright (C) 2022 - Scott Smart <scott967@kodi.tv>
# This program is Free Software see LICENSE file for details

from __future__ import annotations

import datetime

import xbmcgui
from resources.kutil131 import ActionHandler, DialogBaseList, addon, busy, windows

from resources.kutil131 import utils, youtube
from resources.lib.windowmanager import wm

ch = ActionHandler()

ID_BUTTON_SORTTYPE = 5001
ID_BUTTON_PUBLISHEDFILTER = 5002
ID_BUTTON_LANGUAGEFILTER = 5003
ID_BUTTON_DIMENSIONFILTER = 5006
ID_BUTTON_DURATIONFILTER = 5008
ID_BUTTON_CAPTIONFILTER = 5009
ID_BUTTON_DEFINITIONFILTER = 5012
ID_BUTTON_TYPEFILTER = 5013

ISO_639_1_CODES = {
  "ar-ae": "Arabic (U.A.E.)",
  "ar-bh": "Arabic (Bahrain)",
  "ar-dz": "Arabic (Algeria)",
  "ar-eg": "Arabic (Egypt)",
  "ar-sa": "Arabic (Saudi Arabia)",
  "ar-sy": "Arabic (Syria)",
  "ar": "Arabic",
  "be": "Belarusian",
  "bg": "Bulgarian",
  "bn": "Bengali",
  "bs": "Bosnian",
  "cs": "Czech",
  "da": "Danish",
  "de-at": "German (Austria)",
  "de-ch": "German (Switzerland)",
  "de-de": "German (Germany)",
  "de-li": "German (Liechtenstein)",
  "de-lu": "German (Luxembourg)",
  "de": "German",
  "el": "Greek",
  "en-au": "English (Australia)",
  "en-ca": "English (Canada)",
  "en-gb": "English (United Kingdom)",
  "en-nz": "English (New Zealand)",
  "en-us": "English (United States)",
  "en-za": "English (South Africa)",
  "en": "English",
  "es-ar": "Spanish (Argentina)",
  "es-cl": "Spanish (Chile)",
  "es-es": "Spanish (Spain)",
  "es-mx": "Spanish (Mexico)",
  "es-pe": "Spanish (Peru)",
  "es-pr": "Spanish (Puerto Rico)",
  "es-us": "Spanish (United States)",
  "es": "Spanish",
  "et": "Estonian",
  "fa": "Farsi",
  "fi": "Finnish",
  "fr-be": "French (Belgium)",
  "fr-ca": "French (Canada)",
  "fr-ch": "French (Switzerland)",
  "fr-fr": "French (France)",
  "fr-lu": "French (Luxembourg)",
  "fr-mc": "French (Monaco)",
  "fr": "French",
  "ga": "Irish",
  "he": "Hebrew",
  "hi": "Hindi",
  "hr-ba": "Croatian (Bosnia and Herzegovina)",
  "hr-hr": "Croatian (Croatia)",
  "hr": "Croatian",
  "ht": "Haitian",
  "hu": "Hungarian",
  "hy": "Armenian",
  "id": "Indonesian",
  "in": "Indonesian",
  "is": "Icelandic",
  "it-ch": "Italian (Switzerland)",
  "it-it": "Italian (Italy)",
  "it": "Italian",
  "iw": "Hebrew",
  "ja": "Japanese",
  "km": "Cambodian",
  "kn": "Kannada",
  "ko": "Korean",
  "ks": "Kashmiri",
  "ku": "Kurdish",
  "ls": "Slovenian",
  "lt": "Lithuanian",
  "lv": "Latvian",
  "ml": "Malayalam",
  "ms-my": "Malay (Malaysia)",
  "ms": "Malay",
  "my": "Burmese",
  "nl-be": "Dutch (Belgium)",
  "nl-nl": "Dutch (Netherlands)",
  "nl": "Dutch",
  "nn": "Norwegian (Nynorsk)",
  "no": "Norwegian",
  "pa": "Punjabi",
  "pl": "Polish",
  "pt-br": "Portuguese (Brazil)",
  "pt-pt": "Portuguese (Portugal)",
  "pt": "Portuguese",
  "ro": "Romanian",
  "ru": "Russian",
  "se-fi": "Sami (Finland)",
  "se-no": "Sami (Norway)",
  "se-se": "Sami (Sweden)",
  "se": "Sami",
  "sh": "Serbo-Croatian",
  "sk": "Slovak",
  "sl": "Slovenian",
  "sq": "Albanian",
  "sr-ba": "Serbian (Bosnia and Herzegovina)",
  "sr-sp": "Serbian (Serbia and Montenegro)",
  "sr": "Serbian",
  "sv-fi": "Swedish (Finland)",
  "sv-se": "Swedish (Sweden)",
  "sv": "Swedish",
  "ta": "Tamil",
  "th": "Thai",
  "tr": "Turkish",
  "uk": "Ukrainian",
  "vi": "Vietnamese",
  "zh-cn": "Chinese (China)",
  "zh-hk": "Chinese (Hong Kong SAR)",
  "zh-mo": "Chinese (Macau SAR)",
  "zh-sg": "Chinese (Singapore)",
  "zh-tw": "Chinese (Taiwan)",
  "zh": "Chinese",
}


def get_window(window_type:type[xbmcgui.WindowXML]) -> type[DialogBaseList]:
    """Creates a DialogYoutubeList class inheriting from window_type class

    Args:
        window_type (xbmcgui.WindowXML): WindowXML or one of its subclasses (DialogXML)

    Returns:
        DialogYoutubeList class: Class inheriting from WindowXML or its subclasses
    """

    class DialogYoutubeList(DialogBaseList, window_type):
        """Creates WindowXML dialog

        Args:
            DialogBaseList (class): Parent class for dialog
            window_type (class): xbmcgui parent class

        Returns:
            DialogYoutubeList: dialog XML window
        """

        TYPES = ["video", "playlist", "channel"]

        FILTERS = {"channelId": addon.LANG(19029),
                   "publishedAfter": addon.LANG(172),
                   "regionCode": addon.LANG(248),
                   "relevanceLanguage": addon.LANG(248),
                   "videoDimension": addon.LANG(32057),
                   "videoDuration": addon.LANG(180),
                   "videoCaption": addon.LANG(287),
                   "videoDefinition": addon.LANG(32058),
                   "videoType": "Type",
                   "relatedToVideoId": addon.LANG(32058)}

        TRANSLATIONS = {"video": addon.LANG(157),
                        "playlist": addon.LANG(559),
                        "channel": addon.LANG(19029)}

        SORTS = {"video": {"date": addon.LANG(552),
                           "rating": addon.LANG(563),
                           "relevance": addon.LANG(32060),
                           "title": addon.LANG(369),
                           "viewCount": addon.LANG(567)},
                 "playlist": {"date": addon.LANG(552),
                              "rating": addon.LANG(563),
                              "relevance": addon.LANG(32060),
                              "title": addon.LANG(369),
                              "videoCount": addon.LANG(32068),
                              "viewCount": addon.LANG(567)},
                 "channel": {"date": addon.LANG(552),
                             "rating": addon.LANG(563),
                             "relevance": addon.LANG(32060),
                             "title": addon.LANG(369),
                             "videoCount": addon.LANG(32068),
                             "viewCount": addon.LANG(567)}}

        LABEL2 = {"date": lambda x: x.get_info("date"),
                  "relevance": lambda x: x.get_property("relevance"),
                  "title": lambda x: x.get_info("title"),
                  "viewCount": lambda x: x.get_property("viewCount"),
                  "videoCount": lambda x: x.get_property("videoCount"),
                  "rating": lambda x: x.get_info("rating")}

        @busy.set_busy
        def __init__(self, *args, **kwargs):
            self.type = kwargs.get('type', "video")
            super().__init__(*args, **kwargs)

        def onClick(self, control_id):
            super().onClick(control_id)
            ch.serve(control_id, self)

        def onAction(self, action):
            super().onAction(action)
            ch.serve_action(action, self.getFocusId(), self)

        @ch.click_by_type("video")
        def main_list_click(self, control_id: int):
            """handles user select action on container listitem

            Args:
                control_id (int): control id of focused container  
            """
            listitem = self.FocusedItem(control_id)
            youtube_id = listitem.getProperty("youtube_id")
            media_type = listitem.getProperty("type")
            if media_type == "channel":
                filter_ = [{"id": youtube_id,
                            "type": "channelId",
                            "label": listitem.getLabel()}]
                wm.open_youtube_list(filters=filter_)
            else:
                wm.play_youtube_video(youtube_id=youtube_id,
                                      listitem=listitem)

        @ch.click(ID_BUTTON_PUBLISHEDFILTER)
        def set_published_filter(self, control_id):
            """Sets youtube filter publishedAfter based on user input day/week/month/year/custom

            Args:
                control_id (_type_): _description_

            Returns:
                None
            """
            options = [(1, addon.LANG(32062)),
                       (7, addon.LANG(32063)),
                       (31, addon.LANG(32064)),
                       (365, addon.LANG(32065)),
                       ("custom", addon.LANG(636))]
            deltas = [i[0] for i in options]
            labels = [i[1] for i in options]
            index = xbmcgui.Dialog().select(heading=addon.LANG(32151),
                                            list=labels)
            if index == -1:
                return None
            delta = deltas[index]
            if delta == "custom":
                delta = xbmcgui.Dialog().input(heading=addon.LANG(32067),
                                               type=xbmcgui.INPUT_NUMERIC)
            if not delta:
                return None
            d = datetime.datetime.now() - datetime.timedelta(int(delta))
            self.add_filter(key="publishedAfter",
                            value=d.isoformat('T')[:-7] + "Z",
                            label=labels[index])

        @ch.click(ID_BUTTON_LANGUAGEFILTER)
        def set_language_filter(self, control_id):
            """Sets Youtube relevanceLanguage filter from ISO 639-1 two-letter language code.

            Args:
                control_id (_type_): _description_
            """
            options = [(k, v) for k, v in ISO_639_1_CODES.items()]
            self.choose_filter("relevanceLanguage", 32151, options)

        @ch.click(ID_BUTTON_DIMENSIONFILTER)
        def set_dimension_filter(self, control_id):
            """Sets Youtube videoDimension filter 

            Args:
                control_id (_type_): _description_
            """
            options = [("2d", "2D"),
                       ("3d", "3D"),
                       ("any", addon.LANG(593))]
            self.choose_filter("videoDimension", 32151, options)

        @ch.click(ID_BUTTON_DURATIONFILTER)
        def set_duration_filter(self, control_id):
            """Sets Youtube videoDuration filter
            long >20 min
            medium >4 and <20 min

            Args:
                control_id (_type_): _description_
            """
            options = [("long", addon.LANG(33013)),
                       ("medium", addon.LANG(601)),
                       ("short", addon.LANG(33012)),
                       ("any", addon.LANG(593))]
            self.choose_filter("videoDuration", 32151, options)

        @ch.click(ID_BUTTON_CAPTIONFILTER)
        def set_caption_filter(self, control_id):
            """Sets Youtube videoCaption filter

            Args:
                control_id (_type_): _description_
            """
            options = [("closedCaption", addon.LANG(107)),
                       ("none", addon.LANG(106)),
                       ("any", addon.LANG(593))]
            self.choose_filter("videoCaption", 287, options)

        @ch.click(ID_BUTTON_DEFINITIONFILTER)
        def set_definition_filter(self, control_id):
            """Sets Youtube videoCaption filter
            high >= 720 

            Args:
                control_id (_type_): _description_
            """
            options = [("high", addon.LANG(419)),
                       ("standard", addon.LANG(602)),
                       ("any", addon.LANG(593))]
            self.choose_filter("videoDefinition", 169, options)

        @ch.click(ID_BUTTON_TYPEFILTER)
        def set_type_filter(self, control_id):
            """Sets Youtube videoType filter

            Args:
                control_id (_type_): _description_
            """
            options = [("movie", addon.LANG(20338)),
                       ("episode", addon.LANG(20359)),
                       ("any", addon.LANG(593))]
            self.choose_filter("videoType", 32151, options)

        @ch.click(ID_BUTTON_SORTTYPE)
        def get_sort_type(self, control_id):
            """Sets the youtube ItemList sort order

            Args:
                control_id (_type_): _description_

            Returns:
                _type_: _description_
            """
            if not self.choose_sort_method(self.type):
                return None
            self.update()

        @ch.context("video")
        def context_menu(self, control_id):
            listitem = self.FocusedItem(control_id)
            if self.type == "video":
                more_vids = f"{addon.LANG(32081)} [B]{listitem.getProperty('channel_title')}[/B]"
                index = xbmcgui.Dialog().contextmenu(
                    list=[addon.LANG(32069), more_vids])
                if index < 0:
                    return None
                elif index == 0:
                    filter_ = [{"id": listitem.getProperty("youtube_id"),
                                "type": "relatedToVideoId",
                                "label": listitem.getLabel()}]
                    wm.open_youtube_list(filters=filter_)
                elif index == 1:
                    filter_ = [{"id": listitem.getProperty("channel_id"),
                                "type": "channelId",
                                "label": listitem.getProperty("channel_title")}]
                    wm.open_youtube_list(filters=filter_)

        def update_ui(self):
            is_video = self.type == "video"
            self.getControl(ID_BUTTON_DIMENSIONFILTER).setVisible(is_video)
            self.getControl(ID_BUTTON_DURATIONFILTER).setVisible(is_video)
            self.getControl(ID_BUTTON_CAPTIONFILTER).setVisible(is_video)
            self.getControl(ID_BUTTON_DEFINITIONFILTER).setVisible(is_video)
            super().update_ui()

        @property
        def default_sort(self):
            return "relevance"

        def add_filter(self, **kwargs):
            kwargs["typelabel"] = self.FILTERS[kwargs["key"]]
            super().add_filter(force_overwrite=True, **kwargs)

        def fetch_data(self, force=False):
            self.set_filter_label()
            if self.search_str:
                self.filter_label = addon.LANG(32146) % (
                    self.search_str) + "  " + self.filter_label
            user_key = addon.setting("Youtube API Key")
            return youtube.search(search_str=self.search_str,
                                  orderby=self.sort,
                                  extended=True,
                                  filters={item["type"]: item["id"]
                                           for item in self.filters},
                                  media_type=self.type,
                                  page=self.page_token,
                                  api_key=user_key)

    return DialogYoutubeList


def open(self, search_str="", filters=None, sort="relevance", filter_label="", media_type="video"):
    """
    open video list, deal with window stack
    """
    YouTube = get_window(windows.DialogXML)
    dialog = YouTube(f'script-{addon.NAME}-YoutubeList.xml', addon.PATH,
                     search_str=search_str,
                     filters=[] if not filters else filters,
                     filter_label=filter_label,
                     type=media_type)
    return dialog

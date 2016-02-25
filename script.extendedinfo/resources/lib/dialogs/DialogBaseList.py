# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmc
import xbmcgui
from ..Utils import *
from ..WindowManager import wm
from T9Search import T9Search
from ActionHandler import ActionHandler

ch = ActionHandler()

C_BUTTON_SEARCH = 6000
C_BUTTON_RESET_FILTERS = 5005
C_LIST_MAIN = 500


class DialogBaseList(object):

    def __init__(self, *args, **kwargs):
        super(DialogBaseList, self).__init__(*args, **kwargs)
        self.listitem_list = kwargs.get('listitems', None)
        self.search_str = kwargs.get('search_str', "").decode("utf-8")
        self.filter_label = kwargs.get("filter_label", "").decode("utf-8")
        self.mode = kwargs.get("mode", "filter")
        self.filters = kwargs.get('filters', [])
        self.color = kwargs.get('color', "FFAAAAAA")
        self.page = 1
        self.column = None
        self.last_position = 0
        self.total_pages = 1
        self.total_items = 0
        self.page_token = ""
        self.next_page_token = ""
        self.prev_page_token = ""

    def onInit(self):
        super(DialogBaseList, self).onInit()
        HOME.setProperty("WindowColor", self.color)
        self.setProperty("WindowColor", self.color)
        if SETTING("alt_browser_layout") == "true":
            self.setProperty("alt_layout", "true")
        self.update_ui()
        xbmc.sleep(200)
        if self.total_items > 0:
            self.setFocusId(C_LIST_MAIN)
            self.setCurrentListPosition(self.last_position)
        else:
            self.setFocusId(C_BUTTON_SEARCH)

    @ch.action("parentdir", "*")
    @ch.action("parentfolder", "*")
    def previous_menu(self):
        onback = self.getProperty("%i_onback" % self.control_id)
        if onback:
            xbmc.executebuiltin(onback)
        else:
            self.close()
            wm.pop_stack()

    @ch.action("previousmenu", "*")
    def exit_script(self):
        self.close()

    @ch.action("left", "*")
    @ch.action("right", "*")
    @ch.action("up", "*")
    @ch.action("down", "*")
    def save_position(self):
        self.position = self.getCurrentListPosition()

    def onAction(self, action):
        ch.serve_action(action, self.getFocusId(), self)

    def onFocus(self, control_id):
        old_page = self.page
        if control_id == 600:
            self.go_to_next_page()
        elif control_id == 700:
            self.go_to_prev_page()
        if self.page != old_page:
            self.update()

    @ch.click(C_BUTTON_RESET_FILTERS)
    def reset_filters(self):
        if len(self.filters) > 1:
            listitems = ["%s: %s" % (f["typelabel"], f["label"]) for f in self.filters]
            listitems.append(LANG(32078))
            index = xbmcgui.Dialog().select(heading=LANG(32077),
                                            list=listitems)
            if index == -1:
                return None
            elif index == len(listitems) - 1:
                self.filters = []
            else:
                del self.filters[index]
        else:
            self.filters = []
        self.page = 1
        self.mode = "filter"
        self.update()

    @ch.click(C_BUTTON_SEARCH)
    def open_search(self):
        if SETTING("classic_search") == "true":
            result = xbmcgui.Dialog().input(heading=LANG(16017),
                                            type=xbmcgui.INPUT_ALPHANUM)
            if result and result > -1:
                self.search(result.decode("utf-8"))
        else:
            T9Search(call=self.search,
                     start_value="",
                     history=self.__class__.__name__ + ".search")
        if self.total_items > 0:
            self.setFocusId(C_LIST_MAIN)

    def onClick(self, control_id):
        ch.serve(control_id, self)

    def search(self, label):
        if not label:
            return None
        self.search_str = label
        self.mode = "search"
        self.filters = []
        self.page = 1
        self.update_content()
        self.update_ui()

    def set_filter_label(self):
        filters = []
        for item in self.filters:
            filter_label = item["label"].replace("|", " | ").replace(",", " + ")
            filters.append("[COLOR FFAAAAAA]%s:[/COLOR] %s" % (item["typelabel"], filter_label))
        self.filter_label = "  -  ".join(filters)

    def update_content(self, force_update=False):
        data = self.fetch_data(force=force_update)
        if not data:
            return None
        self.listitems = data.get("listitems", [])
        self.total_pages = data.get("results_per_page", "")
        self.total_items = data.get("total_results", "")
        self.next_page_token = data.get("next_page_token", "")
        self.prev_page_token = data.get("prev_page_token", "")
        self.listitems = create_listitems(self.listitems)

    def update_ui(self):
        if not self.listitems and self.getFocusId() == C_LIST_MAIN:
            self.setFocusId(C_BUTTON_SEARCH)
        self.clearList()
        if self.listitems:
            for item in self.listitems:
                self.addItem(item)
            if self.column is not None:
                self.setCurrentListPosition(self.column)
        self.setProperty("TotalPages", str(self.total_pages))
        self.setProperty("TotalItems", str(self.total_items))
        self.setProperty("CurrentPage", str(self.page))
        self.setProperty("Filter_Label", self.filter_label)
        self.setProperty("Sort_Label", self.sort_label)
        if self.page == self.total_pages:
            self.clearProperty("ArrowDown")
        else:
            self.setProperty("ArrowDown", "True")
        if self.page > 1:
            self.setProperty("ArrowUp", "True")
        else:
            self.clearProperty("ArrowUp")
        if self.order == "asc":
            self.setProperty("Order_Label", LANG(584))
        else:
            self.setProperty("Order_Label", LANG(585))

    def go_to_next_page(self):
        self.get_column()
        if self.page < self.total_pages:
            self.page += 1
            self.prev_page_token = self.page_token
            self.page_token = self.next_page_token

    def go_to_prev_page(self):
        self.get_column()
        if self.page > 1:
            self.page -= 1
            self.next_page_token = self.page_token
            self.page_token = self.prev_page_token

    def get_column(self):
        for i in range(0, 10):
            if xbmc.getCondVisibility("Container(500).Column(%i)" % i):
                self.column = i
                break

    @busy_dialog
    def update(self, force_update=False):
        self.update_content(force_update=force_update)
        self.update_ui()

    def add_filter(self, key, value, typelabel, label, force_overwrite=False):
        if not value:
            return False
        new_filter = {"id": value,
                      "type": key,
                      "typelabel": typelabel,
                      "label": label}
        if new_filter in self.filters:
            return False
        index = -1
        for i, item in enumerate(self.filters):
            if item["type"] == key:
                index = i
                break
        if index == -1:
            self.filters.append(new_filter)
            return None
        if force_overwrite:
            self.filters[index]["id"] = str(value)
            self.filters[index]["label"] = str(label)
            return None
        ret = xbmcgui.Dialog().yesno(heading=LANG(587),
                                     line1=LANG(32106),
                                     nolabel="OR",
                                     yeslabel="AND")
        if ret:
            self.filters[index]["id"] += ",%s" % value
            self.filters[index]["label"] += ",%s" % label
        else:
            self.filters[index]["id"] += "|%s" % value
            self.filters[index]["label"] += "|%s" % label

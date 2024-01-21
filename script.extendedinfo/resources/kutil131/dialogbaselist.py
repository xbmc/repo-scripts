# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

from __future__ import annotations
import xbmc
import xbmcgui

from resources.kutil131 import ActionHandler, addon, busy, utils
from resources.kutil131.t9_search import T9Search

ch = ActionHandler()

ID_BUTTON_SEARCH = 6000
ID_BUTTON_RESETFILTERS = 5005
ID_BUTTON_PREV_PAGE = 700
ID_BUTTON_NEXT_PAGE = 600
ID_BUTTON_TOGGLETYPE = 5007


class DialogBaseList:
    viewid = {
        'WALL 3D' : '67',
        'BANNER' : '52',
        'BANNER INFO' : '53',
        'COVERFLOW' : '58',
        'GAMES' : '50',
        'GLASS LIST' : '57',
        'LANDSCAPEX' : '64',
        'LOW LIST' : '55',
        'MID LIST' : '70',
        'MULTI-LIST' : '71',
        'MULTIPLEX' : '61',
        'PANEL' : '62',
        'PHOTOSHOW' : '79',
        'POSTER' : '54',
        'RIGHT LIST' : '59',
        'SETS' : '65',
        'SHELF' : '63',
        'SHELFCASE' : '69',
        'SHOWART' : '60',
        'SHOWCASE' : '66',
        'WALL' : '56',
        'WIDE' : '51',
        'List' : '50',
        'IconWall' : '52',
        'Shift' : '53',
        'InfoWall' : '54',
        'WideList' : '55',
        'Banner' : '501',
        'Fanart' : '502'
    }



    """
    BaseList for MediaBrowsers (handles filtering, sorting)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.search_str = kwargs.get('search_str', "")
        self.filter_label = kwargs.get("filter_label", "")
        self.mode = kwargs.get("mode", "filter")
        self.order = kwargs.get('order', "desc")
        self.sort = kwargs.get('sort', self.default_sort)
        self.filters = []
        for item in kwargs.get('filters', []):
            self.add_filter(key=item["type"],
                            value=item["id"],
                            label=item["label"],
                            reset=False)
        self.page = 1
        self.listitems = None
        self.column = None
        self.set_sort(self.sort)
        self.last_position = 0
        self.total_pages = 1
        self.total_items = 0
        self.page_token = ""
        self.next_page_token = ""
        self.prev_page_token = ""
        self.listitems = kwargs.get('listitems')
        if self.listitems:
            self.listitems = self.listitems.create_listitems()
            self.total_items = len(self.listitems)
        else:
            self.update_content(force_update=kwargs.get('force', False))

    def onInit(self):
        super().onInit()
        viewtype = addon.setting("viewtype_selection")
        self.cur_viewtype = DialogBaseList.viewid.get(xbmc.getInfoLabel('Container.Viewmode'))
        if viewtype:
            xbmc.executebuiltin("Container.SetViewMode(%s)" % viewtype)
        self.update_ui()
        if self.total_items > 0:
            self.setFocusId(self.getCurrentContainerId())
            self.setCurrentListPosition(self.last_position)
        else:
            self.setFocusId(ID_BUTTON_SEARCH)

    def onClick(self, control_id):
        ch.serve(control_id, self)

    def onAction(self, action: xbmcgui.Action):
        ch.serve_action(action, self.getFocusId(), self)

    def onFocus(self, control_id):
        if control_id == ID_BUTTON_NEXT_PAGE:
            self.go_to_next_page()
        elif control_id == ID_BUTTON_PREV_PAGE:
            self.go_to_prev_page()

    @property
    def sort_key(self):
        """
        get key used for sorting
        """
        return self.type

    def close(self):
        """
        save viewtype and last focusposition
        """
        addon.set_setting("viewtype_selection", str(self.getCurrentContainerId()))
        self.last_position = self.getCurrentListPosition()
        xbmc.executebuiltin("Container.SetViewMode(%s)" % self.cur_viewtype)
        super().close()

    def set_sort(self, sort):
        """
        set sort method to *sort
        """
        self.sort = sort
        self.verify_sort()
        self.sort_label = self.SORTS[self.sort_key][self.sort]

    def verify_sort(self):
        """
        check if sort is valid. If not, change to default.
        """
        if self.sort not in [i for i in list(self.SORTS[self.sort_key].keys())]:
            self.set_sort(self.default_sort)

    @ch.click(ID_BUTTON_TOGGLETYPE)
    def toggle_type(self, control_id):
        """
        toggle type
        """
        self.filters = []
        self.type = self.TYPES[self.TYPES.index(self.type) - 1]
        self.verify_sort()
        self.reset()

    @ch.click(ID_BUTTON_RESETFILTERS)
    def reset_filters(self, control_id):
        """
        reset filters, show selectdialog if filtercount > 1
        """
        if len(self.filters) > 1:
            listitems = ["%s: %s" % (f["typelabel"], f["label"]) for f in self.filters]
            listitems.append(addon.LANG(32078))
            index = xbmcgui.Dialog().select(heading=addon.LANG(32077),
                                            list=listitems)
            if index == -1:
                return None
            elif index == len(listitems) - 1:
                self.filters = []
            else:
                del self.filters[index]
        else:
            self.filters = []
        self.reset()

    @ch.click(ID_BUTTON_SEARCH)
    def open_search(self, control_id):
        """
        open search dialog, update list with search results
        """
        if addon.bool_setting("classic_search"):
            result = xbmcgui.Dialog().input(heading=addon.LANG(16017),
                                            type=xbmcgui.INPUT_ALPHANUM)
            if result and result > -1:
                self.search(result)
        else:
            T9Search(call=self.search,
                     start_value="",
                     history=self.__class__.__name__ + ".search")
        if self.total_items > 0:
            self.setFocusId(self.getCurrentContainerId())

    @ch.action("parentdir", "*")
    @ch.action("parentfolder", "*")
    def previous_menu(self, control_id):
        """
        close the currently active dialog
        can also get overridden by skinners per control by setting a window prop
        """
        onback = self.getProperty("%i_onback" % control_id)
        if onback:
            xbmc.executebuiltin(onback)
        else:
            self.close()

    @ch.action("previousmenu", "*")
    def exit_script(self, control_id):
        """
        completely exit script
        """
        self.exit()

    @ch.action("left", "*")
    @ch.action("right", "*")
    @ch.action("up", "*")
    @ch.action("down", "*")
    def save_position(self, control_id):
        """
        save position for any navigation keypress
        """
        self.position = self.getCurrentListPosition()

        @ch.info("video")
        # @ch.click_by_type("movie")
        def open_video(self, control_id):
            self.close()
            xbmcgui.Dialog().info(self.FocusedItem(control_id))
            self.doModal()

    def search(self, label):
        """
        set search string and update the container
        """
        if not label:
            return None
        self.search_str = label
        self.filters = []
        busy.disable()
        self.reset("search")
        busy.enable()

    def set_filter_label(self):
        """
        build filter label for UI based on active filters
        """
        filters = []
        for item in self.filters:
            filter_label = item["label"].replace("|", " | ").replace(",", " + ")
            filters.append("[COLOR FFAAAAAA]%s:[/COLOR] %s" % (item["typelabel"], filter_label))
            self.filter_label: str = "  -  ".join(filters)

    def update_content(self, force_update=False):
        """
        fetch listitems and pagination info based on current state
        """
        self.data = self.fetch_data(force=force_update)
        if not self.data:
            return None
        self.listitems = self.data
        self.total_pages = self.data.total_pages
        self.total_items = self.data.totals
        self.next_page_token = self.data.next_page_token
        self.prev_page_token = self.data.prev_page_token

    def update_ui(self):
        """
        add listitems to list, set focusposition, set window properties
        """
        if not self.listitems and self.getFocusId() == self.getCurrentContainerId():
            self.setFocusId(ID_BUTTON_SEARCH)
        self.clearList()
        if self.listitems:
            items = []
            for item in self.listitems:
                item.set_label2(self.LABEL2[self.sort](item))
                items.append(item.get_listitem())
            self.addItems(items)
            if self.column is not None:
                self.setCurrentListPosition(self.column)
        # self.setContent(self.listitems.content_type)
        self.setProperty("TotalPages", str(self.total_pages))
        self.setProperty("TotalItems", str(self.total_items))
        self.setProperty("CurrentPage", str(self.page))
        self.setProperty("Filter_Label", self.filter_label)
        self.setProperty("Sort_Label", self.sort_label)
        self.setProperty("ArrowDown", "True" if self.page != self.total_pages else "")
        self.setProperty("ArrowUp", "True" if self.page > 1 else "")
        self.setProperty("Order_Label", addon.LANG(584 if self.order == "asc" else 585))
        self.setProperty("Type", self.TRANSLATIONS[self.type])

    def reset(self, mode="filter"):
        """
        resets the container to its default mode and updates
        """
        self.page = 1
        self.mode = mode
        self.verify_sort()
        self.update()

    def go_to_next_page(self):
        """
        go to the next page (for paginated results)
        """
        self.get_column()
        if self.page < self.total_pages:
            self.page += 1
            self.prev_page_token = self.page_token
            self.page_token = self.next_page_token
            self.update()

    def go_to_prev_page(self):
        """
        go to the previous page (for paginated results)
        """
        self.get_column()
        if self.page > 1:
            self.page -= 1
            self.next_page_token = self.page_token
            self.page_token = self.prev_page_token
            self.update()

    def get_column(self):
        """
        save the column of the currently focused item
        """
        col = xbmc.getInfoLabel("Container(%s).Column" % self.getCurrentContainerId())
        self.column = int(col) if col != "" else None

    @busy.set_busy
    def update(self, force_update=False):
        """
        complete refresh of both content and ui
        """
        self.update_content(force_update=force_update)
        self.update_ui()

    def choose_sort_method(self, sort_key):
        """
        open dialog and let user choose sortmethod
        returns True if sorthmethod changed
        """
        listitems = list(self.SORTS[sort_key].values())
        sort_strings = list(self.SORTS[sort_key].keys())
        preselect = listitems.index(self.sort_label) if self.sort_label in listitems else -1
        index = xbmcgui.Dialog().select(heading=addon.LANG(32104),
                                        list=listitems,
                                        preselect=preselect)
        if index == -1 or listitems[index] == self.sort_label:
            return False
        self.sort = sort_strings[index]
        self.sort_label = listitems[index]
        return True

    def choose_filter(self, filter_code, header, options):
        """
        open dialog and let user choose filter from *options
        filter gets removed in case value is empty
        filter_code: filter code from API
        options: list of tuples with 2 items each: first is value, second is label
        """
        values = [i[0] for i in options]
        labels = [i[1] for i in options]
        index = xbmcgui.Dialog().select(heading=addon.LANG(header),
                                        list=labels)
        if index == -1:
            return None
        if not values[index]:
            self.remove_filter(filter_code)
        self.add_filter(key=filter_code,
                        value=values[index],
                        label=labels[index])

    def toggle_filter(self, filter_code):
        """
        automatically add / remove filter with *filter_code
        """
        index = self.find_filter_position(filter_code)
        if index > -1:
            del self.filters[index]
        else:
            pass  # add filter...

    def find_filter_position(self, filter_code):
        """
        find position of specific filter in filter list
        """
        for i, item in enumerate(self.filters):
            if item["type"] == filter_code:
                return i
        return -1

    def remove_filter(self, filter_code):
        """
        remove filter with specific filter_code from filter list
        """
        index = self.find_filter_position(filter_code)
        if index > -1:
            del self.filters[index]
        self.reset()

    def add_filter(self, key, value, label, typelabel="", force_overwrite=False, reset=True):
        """
        add a filter to the filter list
        a filter consists of a key and value (for api call), and label as well as
        typelabel for displaying in UI.
        *reset updates the container after modifying filters
        *force_overwrite is used for filters which do not support ANDing
        """
        if not value:
            return False
        new_filter = {"id": str(value),
                      "type": key,
                      "typelabel": typelabel,
                      "label": label}
        if new_filter in self.filters:
            return False
        index = self.find_filter_position(key)
        if index == -1:
            self.filters.append(new_filter)
            if reset:
                self.reset()
            return None
        if force_overwrite:
            self.filters[index]["id"] = str(value)
            self.filters[index]["label"] = str(label)
            if reset:
                self.reset()
            return None
        self.filters[index]["id"] += ",%s" % value
        self.filters[index]["label"] += ",%s" % label
        ids = self.filters[index]["id"].split(",")
        labels = self.filters[index]["label"].split(",")
        self.filters[index]["id"] = ",".join(list(set(ids)))
        self.filters[index]["label"] = ",".join(list(set(labels)))
        if reset:
            self.reset()

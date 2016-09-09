# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import time
from threading import Timer
import xbmcgui
import os
from collections import deque
import ast
from kodi65 import utils
from kodi65 import addon
from kodi65 import ActionHandler
import AutoCompletion

ch = ActionHandler()

# (1st label, 2nd label)
KEYS = (("1", "ABC1"),
        ("2", "DEF2"),
        ("3", "GHI3"),
        ("4", "JKL4"),
        ("5", "MNO5"),
        ("6", "PQR6"),
        ("7", "STU7"),
        ("8", "VWX8"),
        ("9", "YZ90"),
        ("DEL", "<--"),
        (" ", "___"),
        ("KEYB", "CLASSIC"))


class T9Search(object):

    def __init__(self, call=None, start_value="", history="Default"):
        dialog = T9SearchDialog(u'script-script.module.kodi65-t9search.xml',
                                os.path.join(os.path.dirname(__file__), "..", ".."),
                                call=call,
                                start_value=start_value,
                                history=history)
        dialog.doModal()
        self.search_str = dialog.search_str


class T9SearchDialog(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        self.callback = kwargs.get("call")
        self.search_str = kwargs.get("start_value", "")
        self.previous = False
        self.prev_time = 0
        self.timer = None
        self.color_timer = None
        self.setting_name = kwargs.get("history")
        setting_string = addon.setting(self.setting_name)
        if self.setting_name and setting_string:
            self.last_searches = deque(ast.literal_eval(setting_string), maxlen=10)
        else:
            self.last_searches = deque(maxlen=10)

    def onInit(self):
        self.get_autocomplete_labels_async()
        self.update_search_label_async()
        listitems = []
        for i, item in enumerate(KEYS):
            li = {"label": "[B]%s[/B]" % item[0],
                  "label2": item[1],
                  "key": item[0],
                  "value": item[1],
                  "index": str(i)
                  }
            listitems.append(li)
        self.getControl(9090).addItems(utils.dict_to_listitems(listitems))
        self.setFocusId(9090)
        self.getControl(600).setLabel("[B]%s[/B]_" % self.search_str)

    def onClick(self, control_id):
        ch.serve(control_id, self)

    def onAction(self, action):
        ch.serve_action(action, self.getFocusId(), self)

    @ch.click(9090)
    def panel_click(self, control_id):
        listitem = self.getControl(control_id).getSelectedItem()
        self.set_t9_letter(letters=listitem.getProperty("value"),
                           number=listitem.getProperty("key"),
                           button=int(listitem.getProperty("index")))

    @ch.click(9091)
    def set_autocomplete(self, control_id):
        listitem = self.getControl(control_id).getSelectedItem()
        self.search_str = listitem.getLabel()
        self.getControl(600).setLabel("[B]%s[/B]_" % self.search_str)
        self.get_autocomplete_labels_async()
        if self.timer:
            self.timer.cancel()
        self.timer = Timer(0.0, self.search, (self.search_str,))
        self.timer.start()

    @ch.action("parentdir", "*")
    @ch.action("parentfolder", "*")
    @ch.action("previousmenu", "*")
    def close_dialog(self, control_id):
        self.save_autocomplete()
        self.close()

    @ch.action("number0", "*")
    def set_0(self, control_id):
        listitem = self.getControl(control_id).getListItem(10)
        self.set_t9_letter(letters=listitem.getProperty("value"),
                           number=listitem.getProperty("key"),
                           button=int(listitem.getProperty("index")))

    @ch.action("number1", "*")
    @ch.action("number2", "*")
    @ch.action("number3", "*")
    @ch.action("number4", "*")
    @ch.action("number5", "*")
    @ch.action("number6", "*")
    @ch.action("number7", "*")
    @ch.action("number8", "*")
    @ch.action("number9", "*")
    def t_9_button_click(self, control_id):
        item_id = self.action_id - xbmcgui.REMOTE_1
        listitem = self.getControl(control_id).getListItem(item_id)
        self.set_t9_letter(letters=listitem.getProperty("value"),
                           number=listitem.getProperty("key"),
                           button=int(listitem.getProperty("index")))

    @utils.run_async
    def update_search_label_async(self):
        while True:
            time.sleep(1)
            if int(time.time()) % 2 == 0:
                self.getControl(600).setLabel("[B]%s[/B]_" % self.search_str)
            else:
                self.getControl(600).setLabel("[B]%s[/B][COLOR 00FFFFFF]_[/COLOR]" % self.search_str)

    @utils.run_async
    def get_autocomplete_labels_async(self):
        self.getControl(9091).reset()
        if self.search_str:
            listitems = AutoCompletion.get_autocomplete_items(self.search_str)
        else:
            listitems = list(self.last_searches)
        self.getControl(9091).addItems(utils.dict_to_listitems(listitems))

    def save_autocomplete(self):
        if not self.search_str:
            return None
        listitem = {"label": self.search_str}
        if listitem in self.last_searches:
            self.last_searches.remove(listitem)
        self.last_searches.appendleft(listitem)
        addon.set_setting(self.setting_name, str(list(self.last_searches)))

    def set_t9_letter(self, letters, number, button):
        now = time.time()
        time_diff = now - self.prev_time
        if number == "DEL":
            self.search_str = self.search_str[:-1]
        elif number == " ":
            if self.search_str:
                self.search_str += " "
        elif number == "KEYB":
            self.use_classic_search()
        elif self.previous != letters or time_diff >= 1:
            self.prev_time = now
            self.previous = letters
            self.search_str += letters[0]
            self.color_labels(0, letters, button)
        elif time_diff < 1:
            if self.color_timer:
                self.color_timer.cancel()
            self.prev_time = now
            idx = (letters.index(self.search_str[-1]) + 1) % len(letters)
            self.search_str = self.search_str[:-1] + letters[idx]
            self.color_labels(idx, letters, button)
        if self.timer:
            self.timer.cancel()
        self.timer = Timer(1.0, self.search, (self.search_str,))
        self.timer.start()
        self.getControl(600).setLabel("[B]%s[/B]_" % self.search_str)
        self.get_autocomplete_labels_async()

    def use_classic_search(self):
        self.close()
        result = xbmcgui.Dialog().input(heading=addon.LANG(16017),
                                        type=xbmcgui.INPUT_ALPHANUM)
        if result and result > -1:
            self.search_str = result.decode("utf-8")
            self.callback(self.search_str)
            self.save_autocomplete()

    def search(self, search_str):
        self.callback(search_str)

    def color_labels(self, index, letters, button):
        letter = letters[index]
        label = "[COLOR=FFFF3333]%s[/COLOR]" % letter
        self.getControl(9090).getListItem(button).setLabel2(letters.replace(letter, label))
        self.color_timer = Timer(1.0, utils.reset_color, (self.getControl(9090).getListItem(button),))
        self.color_timer.start()

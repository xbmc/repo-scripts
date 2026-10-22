# -*- coding: utf-8 -*-
"""Finding a manual for a game that has none.

Each installed provider is asked in the background; picking a result fetches
it into the manuals folder beside the game, or into the profile when that
folder can't be written to, and the viewer then opens it.
"""

import threading

import xbmc
import xbmcgui

from . import fetch, providers
from .main import jsonrpc, localize

RESULTS = 200
PROVIDER = 300
MORE = 310
CANCEL = 320
BAR_TRACK = 400
BAR_FILL = 410


def find_providers(enabled=True):
    """The installed add-ons that find manuals, as (id, name, icon)."""
    found = []
    answer = jsonrpc("Addons.GetAddons", {"type": "xbmc.python.pluginsource", "enabled": enabled,
                                          "properties": ["name", "thumbnail"]}) or {}
    for addon in answer.get("addons") or []:
        addon_id = addon["addonid"]
        if providers.is_provider(addon_id):
            found.append((addon_id, addon.get("name") or addon_id, addon.get("thumbnail") or ""))
    return found


def offer_disabled_provider():
    """Offer to enable a provider that is installed but disabled, when none is enabled."""
    if find_providers():
        return
    for addon_id, _, _ in find_providers(enabled=False)[:1]:
        xbmc.executebuiltin("EnableAddon(%s)" % addon_id, True)


class Finder(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super(Finder, self).__init__(*args)
        self.game = kwargs["game"]
        self.title = kwargs["title"]
        self.downloaded = ""
        self.install = ""
        self.providers = []
        self.provider = 0
        self.searches = 0
        self.busy = False

    def onInit(self):
        self.setProperty("game", self.title)
        self.providers = find_providers()
        self.setProperty("providers", str(len(self.providers)))
        if not self.providers:
            status = 32039 if find_providers(enabled=False) else 32005
            self.set_state("noproviders", localize(status), localize(32024))
            self.setFocusId(MORE)
            return
        self.search()

    def set_state(self, state, status="", hint=""):
        self.setProperty("state", state)
        self.setProperty("status", status)
        self.setProperty("hint", hint)

    def search(self):
        addon_id, name, icon = self.providers[self.provider]
        self.setProperty("provider", name)
        self.setProperty("provider.icon", icon)
        self.set_state("searching", localize(32023).format(name))
        self.getControl(RESULTS).reset()
        self.searches += 1
        threading.Thread(target=self._search, args=(addon_id, name, self.searches)).start()

    def _search(self, addon_id, name, search):
        url = providers.search_url(addon_id, self.game, self.title)
        answer = jsonrpc("Files.GetDirectory", {"directory": url, "media": "files",
                                                "properties": ["title", "art", "customproperties"]})
        # Another provider was asked while this one was answering
        if search != self.searches:
            return
        if answer is None:
            self.set_state("failed", localize(32026).format(name), localize(32013))
            self.setFocusId(PROVIDER if len(self.providers) > 1 else MORE)
            return
        items = []
        for result in answer.get("files") or []:
            item = xbmcgui.ListItem(result.get("label") or result.get("title") or "")
            item.setArt(result.get("art") or {})
            item.setProperties(result.get("customproperties") or {})
            item.setProperty("url", result.get("file") or "")
            items.append(item)
        self.getControl(RESULTS).addItems(items)
        if items:
            self.set_state("results")
            self.setFocusId(RESULTS)
        else:
            self.set_state("empty", localize(32004), localize(32013))
            self.setFocusId(PROVIDER if len(self.providers) > 1 else MORE)

    def onClick(self, control_id):
        if self.busy:
            return
        if control_id == RESULTS:
            item = self.getControl(RESULTS).getSelectedItem()
            if item and item.getProperty("url"):
                threading.Thread(target=self.download, args=(item.getProperty("url"),)).start()
        elif control_id == PROVIDER and len(self.providers) > 1:
            self.provider = (self.provider + 1) % len(self.providers)
            self.search()
        elif control_id == MORE:
            missing = [addon_id for addon_id in providers.KNOWN
                       if not xbmc.getCondVisibility("System.HasAddon(%s)" % addon_id)]
            self.close()
            if missing:
                self.install = missing[0]
                return
            # Kodi won't open a window over a dialog, such as the menu of the
            # game being played
            xbmc.executebuiltin("Dialog.Close(all,true)", True)
            xbmc.executebuiltin("ActivateWindow(addonbrowser,addons://search/manuals/,return)")
        elif control_id == CANCEL:
            self.close()

    def onAction(self, action):
        # Back is ignored mid-download: the file would be left half written
        if action.getId() in (10, 92) and not self.busy:
            self.close()

    def show_progress(self, done):
        self.setProperty("progress", "%d%%" % int(done * 100))
        try:
            track = self.getControl(BAR_TRACK).getWidth()
            self.getControl(BAR_FILL).setWidth(max(12, int(track * done)))
        except RuntimeError:
            # A skin's own window may show the progress as text alone
            pass

    def download(self, url):
        self.busy = True
        self.set_state("downloading")
        self.show_progress(0)
        target = fetch.download(url, self.game, self.show_progress)
        self.busy = False
        if not target:
            self.set_state("failed", localize(32008), localize(32025))
            self.setFocusId(CANCEL)
            return
        self.show_progress(1)
        self.downloaded = target
        self.close()

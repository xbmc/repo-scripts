"""Content listing for skin widgets and home-menu items.

Some skins ask an add-on on the home menu for a directory to show as
a preview widget (plugin://script.cablebox42/).  We answer with the channel
lineup and what's on now; selecting a channel turns the TV on at that channel.
"""
import time
from urllib.parse import parse_qs

import xbmc
import xbmcgui
import xbmcplugin

from . import kodiutil as K
from . import channels as C
from . import scheduler
from .kodiutil import _

BASE = "plugin://script.cablebox42/"


def _clock(ts):
    try:
        f = xbmc.getRegion("time").replace(":%S", "")
    except Exception:
        f = "%I:%M %p"
    s = time.strftime(f, time.localtime(ts))
    return s[1:] if s.startswith("0") else s


def run(argv):
    handle = int(argv[1]) if len(argv) > 1 and argv[1].lstrip("-").isdigit() else -1
    query = parse_qs(argv[2].lstrip("?")) if len(argv) > 2 else {}

    if "watch" in query or "menu" in query:
        # An item was selected: hand over to the real script (outside the
        # widget's directory request) and tell Kodi there is nothing to play.
        if "watch" in query:
            n = query["watch"][0]
            cmd = "RunScript(script.cablebox42,watch%s)" % ("," + n if n.isdigit() else "")
        else:
            cmd = "RunScript(script.cablebox42)"
        xbmc.executebuiltin(cmd)
        if handle >= 0:
            xbmcplugin.endOfDirectory(handle, succeeded=False, updateListing=False, cacheToDisc=False)
        return

    if handle < 0:
        return
    icon = K.media("icon.png")
    fanart = K.media("fanart.jpg")
    items = []
    chans = C.load()
    if not chans:
        li = xbmcgui.ListItem(_("Open CableBox 42"), _("Build your channel lineup"))
        li.setArt({"icon": icon, "thumb": icon, "fanart": fanart})
        items.append((BASE + "?menu=1", li, False))
    else:
        lineup = scheduler.Lineup(K.schedule_cfg())
        now = time.time()
        li = xbmcgui.ListItem(_("Watch TV"), _("Turn on the TV"))
        li.setArt({"icon": icon, "thumb": icon, "fanart": fanart})
        items.append((BASE + "?watch=last", li, False))
        for ch in chans:
            sched = lineup.schedule(ch, ensure=False)  # never build schedules from a widget
            b = sched.block_at(now)
            nb = sched.next_block(now)
            label = "%d  %s" % (ch["number"], ch["name"])
            on_now = b["t"] if b else ""
            li = xbmcgui.ListItem(label, on_now)
            plot = []
            if b:
                plot.append(_("Now: %s  (until %s)") % (b["t"], _clock(b["e"])))
            if nb:
                plot.append(_("Next: %s  %s") % (_clock(nb["s"]), nb["t"]))
            try:
                tag = li.getVideoInfoTag()
                tag.setTitle(label)
                tag.setPlot("[CR]".join(plot))
                tag.setMediaType("video")
            except Exception:
                pass
            li.setProperty("ChannelNumber", str(ch["number"]))
            li.setProperty("NowPlaying", on_now)
            li.setArt({"icon": icon, "thumb": icon, "fanart": fanart})
            items.append((BASE + "?watch=%d" % ch["number"], li, False))
    xbmcplugin.addDirectoryItems(handle, items, len(items))
    xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)

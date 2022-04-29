import sys
import xbmcgui
import xbmcvfs
import xbmcaddon

from ..subtitle.controller import Controller
from . import loadsubfile

ADDON = xbmcaddon.Addon()
__addon__     = xbmcaddon.Addon()
_  = __addon__.getLocalizedString

UNLIKELY_SIZE_FOR_SUBTITLE = 1048576 # 1mb

def select_file(with_warning_shown):
    #Sublissimo, select sub, select sub
    if with_warning_shown:
        xbmcgui.Dialog().ok(_(31001), _(32034))
    filename = xbmcgui.Dialog().browse(1, _(32035), 'video', ".srt|.sub")
    if filename == "":
        sys.exit()
    return filename

def check_file_size(filename):
    with xbmcvfs.File(filename) as file:
        size = file.size()
    if size > UNLIKELY_SIZE_FOR_SUBTITLE:
        return False
    return True

def loader(filename):
    if not check_file_size(filename):
        choice = xbmcgui.Dialog().yesno(_(35030), _(35031),
                                         yeslabel=_(35029),
                                         nolabel=_(31009))
        if not choice:
            filename = select_file(False)
            return loader(filename)
    controller = Controller(filename)
    try:
        if filename.endswith(".srt"):
            controller.create_srt_subtitle()
            subtitle = controller.get_subtitle()
            return subtitle
        if filename.endswith(".sub"):
            frame_rate, videodbfilename = loadsubfile.load_sub_subtitlefile(filename)
            if frame_rate:
                controller.create_sub_subtitle(frame_rate)
                subtitle = controller.get_subtitle()
                subtitle.videodbfilename = videodbfilename
                return subtitle
            return without_warning()
    except TypeError:
        pass
    return error_handling(controller)

def error_handling(controller):
    choice = xbmcgui.Dialog().yesnocustom(_(35032), _(35033),
                                           yeslabel=_(35028),
                                           customlabel=_(32126),
                                           nolabel=_(31009))
    if choice == 1:
        xbmcgui.Dialog().select(_(32010), controller.subtitlefile)
        return without_warning()
    if choice == 2:
        return without_warning()
    sys.exit()
    return None

def with_warning():
    filename = select_file(True)
    return loader(filename)

def without_warning():
    filename = select_file(False)
    return loader(filename)

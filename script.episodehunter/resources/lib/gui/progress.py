import xbmcgui

__title__ = "EpisodeHunter"


def create(msg):
    """
    Creating an xbmc progress
    Setting title to episodehunter

    :rtype : object
    """
    progress = xbmcgui.DialogProgress()
    progress.create(__title__, msg)
    return progress

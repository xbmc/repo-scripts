import resources.lib.utils as utils
from resources.lib.upnext import UpNext
from resources.lib.stillwatching import StillWatching


def set_up_pages():
    if utils.settings("simpleMode") == "0":
        next_up_page = UpNext("script-upnext-upnext-simple.xml",
                              utils.addon_path(), "default", "1080i")
        still_watching_page = StillWatching(
            "script-upnext-stillwatching-simple.xml",
            utils.addon_path(), "default", "1080i")
    else:
        next_up_page = UpNext("script-upnext-upnext.xml",
                              utils.addon_path(), "default", "1080i")
        still_watching_page = StillWatching(
            "script-upnext-stillwatching.xml",
            utils.addon_path(), "default", "1080i")
    return next_up_page, still_watching_page


def set_up_developer_pages(episode):
    next_up_page_simple = UpNext("script-upnext-upnext-simple.xml",
                                 utils.addon_path(), "default", "1080i")
    still_watching_page_simple = StillWatching(
        "script-upnext-stillwatching-simple.xml",
        utils.addon_path(), "default", "1080i")
    next_up_page = UpNext("script-upnext-upnext.xml",
                          utils.addon_path(), "default", "1080i")
    still_watching_page = StillWatching(
        "script-upnext-stillwatching.xml",
        utils.addon_path(), "default", "1080i")
    next_up_page.setItem(episode)
    next_up_page_simple.setItem(episode)
    still_watching_page.setItem(episode)
    still_watching_page_simple.setItem(episode)
    notification_time = utils.settings("autoPlaySeasonTime")
    progress_step_size = utils.calculate_progress_steps(notification_time)
    next_up_page.setProgressStepSize(progress_step_size)
    next_up_page_simple.setProgressStepSize(progress_step_size)
    still_watching_page.setProgressStepSize(progress_step_size)
    still_watching_page_simple.setProgressStepSize(progress_step_size)
    return next_up_page, next_up_page_simple, still_watching_page, still_watching_page_simple



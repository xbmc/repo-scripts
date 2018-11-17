import xbmc
import resources.lib.utils as utils
import resources.lib.pages as pages


class Developer:
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state

    @staticmethod
    def developer_play_back():
        episode = utils.load_test_data()
        next_up_page, next_up_page_simple, still_watching_page, still_watching_page_simple = (
            pages.set_up_developer_pages(episode))
        if utils.settings("windowMode") == "0":
            next_up_page.show()
        elif utils.settings("windowMode") == "1":
            next_up_page_simple.show()
        elif utils.settings("windowMode") == "2":
            still_watching_page.show()
        elif utils.settings("windowMode") == "3":
            still_watching_page_simple.show()
        utils.window('service.upnext.dialog', 'true')

        player = xbmc.Player()
        while (player.isPlaying() and not next_up_page.isCancel() and
                not next_up_page.isWatchNow() and not still_watching_page.isStillWatching() and
                not still_watching_page.isCancel()):
            xbmc.sleep(100)
            next_up_page.updateProgressControl()
            next_up_page_simple.updateProgressControl()
            still_watching_page.updateProgressControl()
            still_watching_page_simple.updateProgressControl()

        if utils.settings("windowMode") == "0":
            next_up_page.close()
        elif utils.settings("windowMode") == "1":
            next_up_page_simple.close()
        elif utils.settings("windowMode") == "2":
            still_watching_page.close()
        elif utils.settings("windowMode") == "3":
            still_watching_page_simple.close()
        utils.window('service.upnext.dialog', clear=True)



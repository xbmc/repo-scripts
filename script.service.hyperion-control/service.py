"""Hyperion control addon entrypoint."""
import xbmcaddon
from resources.lib.api_client import ApiClient
from resources.lib.gui import GuiHandler
from resources.lib.hyperion import Hyperion
from resources.lib.logger import Logger
from resources.lib.monitor import XBMCMonitor
from resources.lib.player import Player
from resources.lib.settings_manager import SettingsManager
from resources.lib.utils import get_stereoscopic_mode

ADDON_NAME = "script.service.hyperion-control"


def main() -> None:
    addon = xbmcaddon.Addon(ADDON_NAME)
    logger = Logger(addon.getAddonInfo("name"))
    settings_manager = SettingsManager(addon.getSettings(), logger, addon)
    gui_handler = GuiHandler(addon, settings_manager)
    api_client = ApiClient(logger, gui_handler, settings_manager)

    def get_video_mode_fn() -> str:
        return get_stereoscopic_mode(logger)

    hyperion = Hyperion(
        settings_manager,
        logger,
        gui_handler,
        api_client,
        get_video_mode_fn,
        addon.getAddonInfo("version"),
    )
    player = Player()
    player.register_observer(hyperion)
    monitor = XBMCMonitor()
    monitor.register_observer(hyperion)

    while not monitor.abortRequested():
        if monitor.waitForAbort(10):
            hyperion.stop()
            break


if __name__ == "__main__":
    main()

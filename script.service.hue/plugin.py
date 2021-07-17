# -*- coding: utf-8 -*-


from resources.lib import menu, logger, ADDONVERSION, KODIVERSION,reporting


logger.debug("*** Starting plugin.py, version {}, Kodi: {}".format(ADDONVERSION, KODIVERSION))
try:
    menu.menu()  # Run menu
except Exception as exc:
    logger.debug("Command exception")
    reporting.process_exception(exc)
logger.debug("*** Shutting down plugin.py, version {}, Kodi: {}".format(ADDONVERSION, KODIVERSION))

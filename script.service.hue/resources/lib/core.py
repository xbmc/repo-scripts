# -*- coding: utf-8 -*-

import sys
from requests.exceptions import ConnectionError, ReadTimeout, ConnectTimeout

import xbmcgui

from resources.lib import kodisettings
from resources.lib import reporting
from resources.lib.kodisettings import settings_storage
from . import logger, ADDON, cache, SETTINGS_CHANGED, ADDONVERSION

from resources.lib import kodiHue
from resources.lib.language import get_string as _
from resources.lib import AmbiGroup


def core():
    logger.debug("service started, version: {}".format(ADDON.getAddonInfo("version")))
    logger.debug("Args: {}".format(sys.argv))
    kodisettings.read_settings()

    if len(sys.argv) > 1:
        command = sys.argv[1]
    else:
        command = ""

    monitor = kodiHue.HueMonitor()
    if command:
        commands(monitor, command)
    else:
        service(monitor)


def commands(monitor, command):
    if command == "discover":
        logger.debug("Started with Discovery")
        bridge_discovered = kodiHue.bridgeDiscover(monitor)
        if bridge_discovered:
            bridge = kodiHue.connectBridge(monitor, silent=True)
            if bridge:
                logger.debug("Found bridge. Running model check & starting service.")
                kodiHue.checkBridgeModel(bridge)
                ADDON.openSettings()
                service(monitor)

    elif command == "createHueScene":
        logger.debug("Started with {}".format(command))
        bridge = kodiHue.connectBridge(monitor, silent=True)  # don't rediscover, proceed silently
        if bridge is not None:
            kodiHue.createHueScene(bridge)
        else:
            logger.debug("No bridge found. createHueScene cancelled.")
            xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif command == "deleteHueScene":
        logger.debug("Started with {}".format(command))

        bridge = kodiHue.connectBridge(monitor, silent=True)  # don't rediscover, proceed silently
        if bridge is not None:
            kodiHue.deleteHueScene(bridge)
        else:
            logger.debug("No bridge found. deleteHueScene cancelled.")
            xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif command == "sceneSelect":  # sceneSelect=kgroup,action  / sceneSelect=0,play
        kgroup = sys.argv[2]
        action = sys.argv[3]
        logger.debug("Started with {}, kgroup: {}, kaction: {}".format(command, kgroup, action))

        bridge = kodiHue.connectBridge(monitor, silent=True)  # don't rediscover, proceed silently
        if bridge is not None:
            kodiHue.configureScene(bridge, kgroup, action)
        else:
            logger.debug("No bridge found. sceneSelect cancelled.")
            xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif command == "ambiLightSelect":  # ambiLightSelect=kgroupID
        kgroup = sys.argv[2]
        logger.debug("Started with {}, kgroupID: {}".format(command, kgroup))

        bridge = kodiHue.connectBridge(monitor, silent=True)  # don't rediscover, proceed silently
        if bridge is not None:
            kodiHue.configureAmbiLights(bridge, kgroup)
        else:
            logger.debug("No bridge found. scene ambi lights cancelled.")
            xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))
    else:
        logger.debug("Unknown command")
        return


def service(monitor):
    kodisettings.read_settings()
    bridge = kodiHue.connectBridge(monitor, silent=settings_storage['disable_connection_message'])
    service_enabled = cache.get("script.service.hue.service_enabled")

    if bridge is not None:
        kgroups = kodiHue.setupGroups(bridge, settings_storage['initialFlash'])
        if settings_storage['ambiEnabled']:
            ambi_group = AmbiGroup.AmbiGroup()
            ambi_group.setup(monitor, bridge, kgroupID=3, flash=settings_storage['initialFlash'])
            #ambi_group = AmbiGroup.AmbiGroup(monitor, bridge, kgroupID=3, flash=settings_storage['reloadFlash'])

        connection_retries = 0
        timer = 60
        daylight = kodiHue.getDaylight(bridge)
        cache.set("script.service.hue.daylight", daylight)
        cache.set("script.service.hue.service_enabled", True)
        logger.debug("Core service starting")

        while settings_storage['connected'] and not monitor.abortRequested():

            # check if service was just renabled and if so restart groups
            prev_service_enabled = service_enabled
            service_enabled = cache.get("script.service.hue.service_enabled")
            if service_enabled and not prev_service_enabled:
                try:
                    kodiHue.activate(bridge, kgroups, ambi_group)
                except UnboundLocalError:
                    ambi_group = AmbiGroup.AmbiGroup()
                    ambi_group.setup(monitor, bridge, kgroupID=3, flash=settings_storage['reloadFlash'])
                    kodiHue.activate(bridge, kgroups, ambi_group)


            #process cached waiting commands
            action = cache.get("script.service.hue.action")
            if action:
                process_actions(action, kgroups)

            #reload if settings changed
            if SETTINGS_CHANGED.is_set():
                kgroups = kodiHue.setupGroups(bridge, settings_storage['reloadFlash'])
                if settings_storage['ambiEnabled']:
                    try:
                        ambi_group.setup(monitor, bridge, kgroupID=3, flash=settings_storage['reloadFlash'])
                    except UnboundLocalError:
                        ambi_group = AmbiGroup.AmbiGroup()
                        ambi_group.setup(monitor, bridge, kgroupID=3, flash=settings_storage['reloadFlash'])
                SETTINGS_CHANGED.clear()

            #check for sunset & connection every minute
            if timer > 59:
                timer = 0

                try:
                    if connection_retries > 0:
                        bridge = kodiHue.connectBridge(monitor, silent=True)
                        if bridge is not None:
                            new_daylight = kodiHue.getDaylight(bridge)
                            connection_retries = 0
                    else:
                        new_daylight = kodiHue.getDaylight(bridge)

                except (ConnectionError, ReadTimeout, ConnectTimeout) as error:
                    connection_retries = connection_retries + 1
                    if connection_retries <= 10:
                        logger.debug("Bridge Connection Error. Attempt: {}/10 : {}".format(connection_retries, error))
                        xbmcgui.Dialog().notification(_("Hue Service"), _("Connection lost. Trying again in 2 minutes"))
                        timer = -60

                    else:
                        logger.debug("Bridge Connection Error. Attempt: {}/5. Shutting down : {}".format(connection_retries, error))
                        xbmcgui.Dialog().notification(_("Hue Service"), _("Connection lost. Check settings. Shutting down"))
                        settings_storage['connected'] = False

                except Exception as exc:
                    logger.debug("Get daylight exception")
                    reporting.process_exception(exc)


                # check if sunset took place
                # daylight = cache.get("script.service.hue.daylight")
                if new_daylight != daylight:
                    logger.debug("Daylight change. current: {}, new: {}".format(daylight, new_daylight))
                    daylight = new_daylight
                    cache.set("script.service.hue.daylight", daylight)
                    if not daylight and service_enabled:
                        logger.debug("Sunset activate")
                        try:
                            kodiHue.activate(bridge, kgroups, ambi_group)
                        except UnboundLocalError as exc:
                            kodiHue.activate(bridge, kgroups)
                        except Exception as exc:
                            logger.debug("Get daylight exception")
                            reporting.process_exception(exc)
            timer += 1
            monitor.waitForAbort(1)
        logger.debug("Process exiting...")
        return
    logger.debug("No connected bridge, exiting...")
    return


def process_actions(action, kgroups):
    # process an action command stored in the cache.
    action_action = action[0]
    action_kgroupid = int(action[1]) - 1
    logger.debug("Action command: {}, action_action: {}, action_kgroupid: {}".format(action, action_action,
                                                                                     action_kgroupid))
    if action_action == "play":
        kgroups[action_kgroupid].run_play()
    if action_action == "pause":
        kgroups[action_kgroupid].run_pause()
    if action_action == "stop":
        kgroups[action_kgroupid].run_stop()
    cache.set("script.service.hue.action", None)

# coding=utf-8
from __future__ import absolute_import
import logging
import tempfile
import sys

from lib.logging import log
# noinspection PyUnresolvedReferences
from lib.kodi_util import translatePath, xbmc, setGlobalProperty, getGlobalProperty
from tendo_singleton import SingleInstance, SingleInstanceException


# tempfile's standard temp dirs won't work on specific OS's (android)
tempfile.tempdir = translatePath("special://temp/")


class KodiLogProxyHandler(logging.Handler):
    def emit(self, record):
        try:
            log(self.format(record))
        except:
            self.handleError(record)


# add custom logger for tendo.singleton, so we can capture its messages
logger = logging.getLogger("tendo.singleton")
logger.addHandler(KodiLogProxyHandler())
logger.setLevel(logging.DEBUG)

boot_delay = False
if len(sys.argv) > 1:
    boot_delay = int(sys.argv[1])

started = False
set_waiting_for_start = False
try:
    if getGlobalProperty('running'):
        try:
            xbmc.executebuiltin('NotifyAll({0},{1},{2})'.format('script.plexmod', 'RESTORE', '{}'))
        except:
            log('Main: script.plex: Already running, couldn\'t reactivate other instance, exiting.')
    else:
        if not getGlobalProperty('started'):
            if getGlobalProperty('waiting_for_start'):
                setGlobalProperty('waiting_for_start', '')
                log('Main: script.plex: Currently waiting for start, immediate start was requested.')
                sys.exit(0)

            with SingleInstance("pm4k"):
                started = True
                from lib import main
                waited = 0
                if boot_delay:
                    set_waiting_for_start = True
                    setGlobalProperty('waiting_for_start', '1')
                    log('Main: script.plex: Delaying start for {}s.', boot_delay)
                    while (not main.util.MONITOR.abortRequested() and waited < boot_delay
                           and getGlobalProperty('waiting_for_start')):
                        waited += 0.1
                        main.util.MONITOR.waitForAbort(0.1)
                if waited < boot_delay:
                    log('Main: script.plex: Forced start before auto-start delay ({:.1f}/{} s).', waited, boot_delay)
                setGlobalProperty('waiting_for_start', '')
                setGlobalProperty('started', '1')

                main.main()
        else:
            log('Main: script.plex: Already running, exiting')

except SingleInstanceException:
    pass

except SystemExit as e:
    if e.code not in (-1, 0):
        raise

finally:
    if started:
        setGlobalProperty('started', '')
    if set_waiting_for_start:
        setGlobalProperty('waiting_for_start', '')

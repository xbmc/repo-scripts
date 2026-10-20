# SPDX-License-Identifier: GPL-2.0-only
"""Composition root and tick loop.

The loop is the only pump for Kodi's Python callback queue, so it must survive anything the
tick throws: a returned main() means no further callback is ever delivered.
"""

import threading
import time
import uuid
from dataclasses import replace

from resources.lib import log as logmod
from resources.lib import paths
from resources.lib.advanced_settings import read_thresholds
from resources.lib.config import read_settings, write_back_pasted_url
from resources.lib.constants import ADDON_ID, SHUTDOWN_DRAIN_SECONDS
from resources.lib.device import device_identity
from resources.lib.kodi import KodiApi, KodiRuntime
from resources.lib.media import MediaResolver
from resources.lib.reporter import ReporterQueue
from resources.lib.service.controller import Controller
from resources.lib.service.delivery import Delivery
from resources.lib.service.playback_monitor import PlaybackMonitor
from resources.lib.service.service_monitor import ServiceMonitor
from resources.lib.storage import JsonViewerStore, PromptMemory, RouteStore

TICK_SECONDS = 1.0


def _timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def apply_settings(
    kodi: KodiApi, controller: Controller, queue: ReporterQueue, delivery: Delivery, log: logmod.StructuredLogger
) -> None:
    """Everything a settings change means to a running service, including a new connection."""
    fresh = read_settings(kodi)
    # Its own writes wake this again; by then the URL is plain and nothing is written.
    write_back_pasted_url(kodi, fresh)
    logmod.set_secret(fresh.webhook_token)
    logmod.set_debug(fresh.debug_logging)
    controller.on_settings_changed(fresh, read_thresholds(kodi))
    if delivery.changed(fresh):
        queue.replace(*delivery.build(fresh))
        controller.ping_now()
        log.info("service.connection_changed", configured=fresh.webhook_url() is not None)
    log.info("service.settings_reloaded", debug=fresh.debug_logging)


def main() -> None:
    player = PlaybackMonitor(None)  # controller attached below; construction registers the callback target
    kodi = KodiRuntime(player=player)
    settings = read_settings(kodi)
    write_back_pasted_url(kodi, settings)
    logmod.configure(log_dir=paths.log_dir(kodi), debug=settings.debug_logging, sink=kodi.log)
    # Registered before anything can log: an illegal token makes http.client raise with the
    # value in the message, and that message is logged as a field on a retryable path.
    logmod.set_secret(settings.webhook_token)
    log = logmod.get_logger("service")
    log.info("service.starting", addon=ADDON_ID, version=kodi.addon_version())

    # Created here because both sides need it and neither may default it: the queue sets it
    # on stop, the reporter waits on it during a retry backoff.
    abort = threading.Event()
    # One instance each, shared: the controller and the delivery both read and write them.
    viewer_store = JsonViewerStore(paths.viewers_path(kodi))
    memory = PromptMemory(paths.prompts_path(kodi))
    delivery = Delivery(
        kodi,
        paths.outbox_path(kodi),
        abort,
        routes=RouteStore(paths.routes_path(kodi)),
        viewers=viewer_store,
        memory=memory,
        # The controller needs the sink built here, so it comes later; a rename is only
        # applied from the tick loop below, by which time it exists.
        on_renamed=lambda old, new: controller.rename_viewer(old, new),
    )
    sink, lane = delivery.build(settings)
    # device_identity owns identity, not versioning, and is used by tests that should not
    # need a Kodi handle just to produce a version string.
    device = replace(device_identity(kodi, settings, paths.device_path(kodi)), addon_version=kodi.addon_version())
    queue = ReporterQueue(sink, device, abort, outbox=lane)
    controller = Controller(
        kodi=kodi,
        viewer_store=viewer_store,
        memory=memory,
        media_resolver=MediaResolver(kodi),
        queue=queue,
        settings=settings,
        thresholds=read_thresholds(kodi),
        clock=_timestamp,
        monotonic=time.monotonic,
        ids=lambda: str(uuid.uuid4()),
    )
    player._controller = controller

    monitor = ServiceMonitor(controller, on_settings_changed=lambda: apply_settings(kodi, controller, queue, delivery, log))
    reason = "abort"
    try:
        while not monitor.abortRequested():
            try:
                controller.on_tick(shutting_down=monitor.abortRequested())
                delivery.publish_status()
            except Exception as exc:
                # The loop is the only callback pump. Losing it silently disables the addon.
                log.error("service.tick_failed", error=str(exc))
            if monitor.waitForAbort(TICK_SECONDS):
                break
    except Exception as exc:
        reason = "error"
        log.error("service.loop_failed", error=str(exc))
    finally:
        controller.on_abort()
        undelivered = queue.stop(deadline=SHUTDOWN_DRAIN_SECONDS)
        log.info("service.stopping", reason=reason, undelivered=undelivered)

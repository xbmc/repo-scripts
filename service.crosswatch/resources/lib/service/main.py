# SPDX-License-Identifier: GPL-2.0-only
"""Composition root and tick loop.

The loop is the only pump for Kodi's Python callback queue, so it must survive anything the
tick throws: a returned main() means no further callback is ever delivered.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import replace

from resources.lib import log as logmod
from resources.lib import paths
from resources.lib.advanced_settings import read_thresholds
from resources.lib.config import Settings, read_settings, write_back_pasted_url
from resources.lib.constants import ADDON_ID, SHUTDOWN_DRAIN_SECONDS, TICK_SECONDS
from resources.lib.device import device_identity
from resources.lib.kodi import KodiApi, KodiRuntime
from resources.lib.media import MediaResolver
from resources.lib.models import Device
from resources.lib.reporter import ReporterQueue
from resources.lib.service.controller import Controller
from resources.lib.service.delivery import Delivery
from resources.lib.service.playback_monitor import PlaybackMonitor
from resources.lib.service.service_monitor import ServiceMonitor
from resources.lib.service.sync_hooks import SyncHooks
from resources.lib.storage import JsonViewerStore, PromptMemory, RouteStore
from resources.lib.sync.engine import SyncEngine, SyncPaths
from resources.lib.sync.files import Inbox
from resources.lib.sync.ids import ensure_sync_ids
from resources.lib.sync.local import FileIndex, MarkGate, PersonBuffer, file_signature, plays_at_start
from resources.lib.sync.ping import PingBlocks
from resources.lib.sync.reply import parse_reply
from resources.lib.sync.writer import OwnWrites

# Kodi gives the service 5 s after abort (PythonInvoker.cpp:62); the reporter's drain and the
# sync worker's stop run side by side inside it.
SYNC_STOP_SECONDS = 2.0


def _timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _device(kodi: KodiApi, settings: Settings) -> Device:
    # device_identity owns identity, not versioning, and is used by tests that should not
    # need a Kodi handle just to produce a version string.
    return replace(device_identity(kodi, settings, paths.device_path(kodi)), addon_version=kodi.addon_version())


def apply_settings(
    kodi: KodiApi,
    controller: Controller,
    queue: ReporterQueue,
    delivery: Delivery,
    log: logmod.StructuredLogger,
    hooks: SyncHooks | None = None,
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
    # After the connection: a failing id lookup must not keep events going to the old server.
    device, before = _device(kodi, fresh), queue.device
    if device != before:
        # The id is a setting: library sync's sync device is the device with this id, so
        # CrossWatch hears of a change at once.
        queue.set_device(device)
        controller.ping_now()
        log.info("service.device_changed", id_changed=device.id != before.id)
    if hooks is not None:
        hooks.on_settings(fresh)
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
        # The sync engine is built below; a reply is only handed over from the tick loop,
        # by which time it exists.
        on_library_sync=lambda block, ticket: engine.on_ping_reply(parse_reply(block), ticket),
    )
    sink, lane = delivery.build(settings)
    queue = ReporterQueue(sink, _device(kodi, settings), abort, outbox=lane)

    # Library sync: the pieces the service thread and the worker share, made before either.
    ensure_sync_ids(viewer_store)
    sync_paths = SyncPaths.of(kodi)
    own, files, buffer = OwnWrites(), FileIndex(), PersonBuffer()
    inbox = Inbox(sync_paths.inbox)
    plays = plays_at_start(kodi, time.monotonic())
    gate = MarkGate(sync_paths.started, file_signature, device_id=lambda: queue.device.id)
    ping_requested, rebuild_requested = threading.Event(), threading.Event()
    engine = SyncEngine(
        kodi=kodi,
        viewer_store=viewer_store,
        memory=memory,
        inbox=inbox,
        files=files,
        ping_requested=ping_requested,
        rebuild_requested=rebuild_requested,
        sync_paths=sync_paths,
        utc_now=_timestamp,
        own=own,
        device_id=lambda: queue.device.id,
    )
    hooks = SyncHooks(
        kodi=kodi,
        engine=engine,
        own=own,
        plays=plays,
        files=files,
        gate=gate,
        buffer=buffer,
        clock=time.monotonic,
        utc_now=_timestamp,
        viewers=lambda: file_signature(paths.viewers_path(kodi)),
        on_viewers_changed=lambda: ensure_sync_ids(viewer_store),
    )
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
        library_sync_block=PingBlocks(
            kodi,
            viewer_store,
            sync_paths.started,
            clock=time.monotonic,
            device_id=lambda: queue.device.id,
            epochs=lambda: engine.epochs,
        ),
        rebuild_requested=rebuild_requested,
        ping_requested=ping_requested,
        recent_plays=plays,
        person_buffer=buffer,
        inbox=inbox,
        on_inbox=engine.on_inbox,
        own=own,
        on_rating_written=engine.on_rating_written,
        on_window=hooks.on_window,
    )
    player._controller = controller

    hooks.on_settings(settings)
    monitor = ServiceMonitor(
        controller,
        on_settings_changed=lambda: apply_settings(kodi, controller, queue, delivery, log, hooks),
        on_notification=hooks.on_notification,
    )
    # After everything that can raise above: a worker started for a service that then fails
    # to start would outlive it.
    engine.start()
    reason = "abort"
    try:
        while not monitor.abortRequested():
            try:
                controller.on_tick(shutting_down=monitor.abortRequested())
                delivery.publish_status()
            except Exception as exc:
                # The loop is the only callback pump. Losing it silently disables the addon.
                log.error("service.tick_failed", error=str(exc))
            try:
                # Separate: a failing playback tick must not stop library sync's signals.
                hooks.tick(playing=kodi.is_playing(), snapshot=controller.snapshot)
            except Exception as exc:
                log.error("service.sync_tick_failed", error=str(exc))
            if monitor.waitForAbort(TICK_SECONDS):
                break
    except Exception as exc:
        reason = "error"
        log.error("service.loop_failed", error=str(exc))
    finally:
        controller.on_abort()
        # Side by side, so both fit Kodi's window: the worker also stops a request in flight.
        stopper = threading.Thread(target=engine.stop, args=(SYNC_STOP_SECONDS,), name="crosswatch-sync-stop")
        stopper.start()
        undelivered = queue.stop(deadline=SHUTDOWN_DRAIN_SECONDS)
        stopper.join(SYNC_STOP_SECONDS)
        log.info("service.stopping", reason=reason, undelivered=undelivered)

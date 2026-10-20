# SPDX-License-Identifier: GPL-2.0-only
"""All playback logic, with no Kodi classes in sight.

The adapters forward to this, which is what makes the whole lifecycle unit testable. The
clock, the monotonic source and the id generator are injected for the same reason.

Everything here runs on the service thread, including the callbacks: Kodi queues them and
executes them from Monitor.waitForAbort. There is therefore no concurrency to guard, and no
locks. Callbacks can however arrive nested: the prompt window's doModal runs them too, in the
middle of _flush_pending, which is written for that, and so do the rating windows that
follow a stop. The reporter worker is the only other thread and it touches only its own queue.
"""

from collections.abc import Callable
from dataclasses import replace

from resources.lib import identity as identity_mod
from resources.lib import prompt as prompt_mod
from resources.lib import rating as rating_mod
from resources.lib.advanced_settings import Thresholds
from resources.lib.config import Settings
from resources.lib.constants import (
    FAILURE_BACKOFF_SECONDS,
    INDEX_MAX_AGE_MULTIPLIER,
    MAX_FAILURE_BACKOFF_SECONDS,
    NOTIFY_HEADING,
    NOTIFY_UNREADABLE,
    PING_INTERVAL_SECONDS,
    PROMPT_AUTOCLOSE_SECONDS,
    RATING_AUTOCLOSE_SECONDS,
)
from resources.lib.kodi import WINDOW_INVALID, KodiApi
from resources.lib.log import get_logger
from resources.lib.media import MediaResolver
from resources.lib.models import EventKind, MediaItem, PingEvent, PlaybackEvent, Viewer
from resources.lib.playlist_index import IndexBuilder, PlaylistIndex
from resources.lib.reporter import EventQueue
from resources.lib.service.session import PlaybackSession
from resources.lib.storage import PromptMemory, ViewerStore
from resources.lib.ui.rating import RATE_FAILED, RateRequest, counter_text, question_text

_log = get_logger("service")


class Controller:
    def __init__(
        self,
        kodi: KodiApi,
        viewer_store: ViewerStore,
        memory: PromptMemory,
        media_resolver: MediaResolver,
        queue: EventQueue,
        settings: Settings,
        thresholds: Thresholds,
        clock: Callable[[], str],
        monotonic: Callable[[], float],
        ids: Callable[[], str],
    ) -> None:
        self._kodi = kodi
        self._store = viewer_store
        self._memory = memory
        self._media = media_resolver
        self._queue = queue
        self._settings = settings
        self._thresholds = thresholds
        self._clock = clock
        self._monotonic = monotonic
        self._ids = ids

        self._session: PlaybackSession | None = None
        self._pending_stop: PlaybackSession | None = None
        self._paused = False
        self._index: PlaylistIndex | None = None
        # The viewers an index was built from: a change in the settings screen rebuilds it.
        self._index_viewers: tuple[Viewer, ...] = ()
        self._building_for: tuple[Viewer, ...] = ()
        self._builder: IndexBuilder | None = None
        self._index_dirty = True
        self._index_retired = False
        self._notified_unreadable: frozenset[str] = frozenset()
        self._failures = 0
        self._failed_at: float | None = None
        # Read by the ping, which is the only place it is reported.
        self.pkc_skipped = 0
        self._last_ping_at: float | None = None
        self._pinged_names: tuple[str, ...] | None = None
        self._shutting_down = False
        self._ratings = rating_mod.RatingQueue()

    # -- lifecycle ---------------------------------------------------------

    def on_settings_changed(self, settings: Settings, thresholds: Thresholds) -> None:
        if not (settings.rating_at_end and settings.rating_kinds):
            # Watches queued under the old setting would otherwise come back the next time it
            # is switched on, maybe days later.
            dropped = self._ratings.clear()
            if dropped:
                _log.info("rating.dropped", reason="settings", count=dropped)
        self._settings = settings
        self._thresholds = thresholds
        self.invalidate_index()

    def ping_now(self) -> None:
        """Ping on the next tick rather than at the end of the interval.

        For a new connection: its first ping is how CrossWatch learns a Link worked, and the
        reply names the instance for the status line.
        """
        self._last_ping_at = None

    def rename_viewer(self, old: str, new: str) -> None:
        """Carry a viewer renamed in CrossWatch into everything not yet sent or asked.

        The names are fixed when playback starts, and a stop under the old name matches no
        route: CrossWatch ignores it and the watch is lost. Called on the service thread
        after viewers.json holds the new name, so a queued rating still finds the viewer.
        """
        for session in (self._session, self._pending_stop):
            if session is not None and old in session.identity.viewers:
                names = tuple(new if n == old else n for n in session.identity.viewers)
                session.identity = replace(session.identity, viewers=names)
        self._ratings.rename_viewer(old, new)
        # The playlists are unchanged, so the index is renamed rather than rebuilt: the next
        # episode of a binge starts before an idle tick could rebuild it. A build in progress
        # holds the old names and starts again.
        if self._index is not None:
            self._index = self._index.renamed(old, new)
            self._index_viewers = tuple(replace(v, name=new) if v.name == old else v for v in self._index_viewers)
        self._builder = None

    def invalidate_index(self) -> None:
        self._index_dirty = True
        self._builder = None
        self._failures = 0
        self._failed_at = None
        self._media.forget_shows()
        _log.info("service.index_invalidated")

    # -- playback callbacks ------------------------------------------------

    def on_av_started(self) -> None:
        # A parked stop goes out unattributed rather than delaying the next item: in a binge
        # nobody would answer a prompt about the episode that just finished.
        self._flush_pending(allow_prompt=False)
        if self._session is not None:
            self._park(self._session, reason="superseded")
            self._flush_pending(allow_prompt=False)
        # Cleared here, not after a successful resolve. An early return below must not leave
        # a stopped session installed: the tick would then sample the new item into it and
        # emit a second stop under the same session_id.
        self._session = None

        try:
            media = self._media.resolve()
        except Exception as exc:
            _log.warning("service.resolve_failed", error=str(exc))
            return
        if media is None:
            return
        if media.is_pkc and self._settings.skip_pkc:
            # Skipped before a session exists. A session that never emits would still hold
            # the index build off the idle tick for the whole playback.
            self.pkc_skipped += 1
            _log.info("service.playback_skipped", reason="plexkodiconnect", count=self.pkc_skipped)
            return

        viewers = self._viewers()
        who = identity_mod.resolve(
            self._servable_index(viewers), viewers, media, self._profile_label(), self._recall(media, viewers)
        )
        session = PlaybackSession(session_id=self._ids(), media=media, identity=who)
        session.sample(*self._kodi.player_times())
        self._paused = False
        self._session = session
        self._emit("start", session)

    def on_paused(self) -> None:
        self._paused = True
        self._emit_for_live("pause")

    def on_resumed(self) -> None:
        self._paused = False
        self._emit_for_live("resume")

    def on_seek(self) -> None:
        """Record the jump. The tick emits, because a callback must not submit."""
        session = self._session
        if session is None:
            _log.info("service.event_dropped", kind="seek", reason="no_session")
            return
        session.note_seek()

    def on_stopped(self, completed: bool) -> None:
        """Park only. Emission happens from the tick, so the callback stays trivial."""
        session = self._session
        self._session = None
        if session is None:
            _log.info("service.event_dropped", kind="stop", reason="no_session")
            return
        self._park(session, reason="callback", completed=completed)

    def on_abort(self) -> None:
        self._shutting_down = True
        dropped = self._ratings.clear()
        if dropped:
            _log.info("rating.dropped", reason="shutdown", count=dropped)
        if self._session is not None:
            self._park(self._session, reason="abort")
            self._session = None
        self._flush_pending(allow_prompt=False)

    # -- tick --------------------------------------------------------------

    def on_tick(self, shutting_down: bool = False) -> None:
        # Sampled from the monitor, not from on_abort: no tick runs after abort, so a flag
        # set there could never reach the gate.
        self._shutting_down = shutting_down
        self._flush_pending(allow_prompt=True)
        # After the flush, never before: the queue is FIFO and the worker blocks, so a ping
        # submitted first sits in front of the parked stop and can cost it at shutdown.
        self._maybe_ping()
        session = self._session
        if session is not None:
            self._tick_playing(session)
            if not self._paused:
                return
            # A paused session decodes nothing, so the rebuild may proceed. Without this an
            # overnight pause blocks every refresh until playback resumes and ends.
        elif self._kodi.is_playing():
            # "No session I own" is a resolution fact, not a playback fact. Live TV, PVR,
            # music and unsupported streams all leave _session None while the decoder runs,
            # and the index build is the most expensive thing the addon does.
            return
        self._tick_idle()

    def _tick_playing(self, session: PlaybackSession) -> None:
        if not self._kodi.is_playing():
            # Kodi discards queued playback messages when new playback starts, so a stop
            # callback is not guaranteed. Reconcile rather than wait for one.
            _log.info("service.stop_reconciled", session_id=session.session_id)
            self._session = None
            self._park(session, reason="liveness")
            return
        session.sample(*self._kodi.player_times())
        if session.should_emit_progress(
            self._monotonic(), self._settings.progress_interval_seconds, self._paused
        ):
            self._emit("progress", session)

    def _tick_idle(self) -> None:
        """Heavy work happens here and only here, one playlist per tick.

        A .xsp expansion costs a whole-library query, so it must never land on the start of
        playback, and it must not run long enough in one tick to delay a callback.
        """
        if self._builder is None:
            if not self._needs_index():
                return
            viewers = self._viewers()
            self._builder = IndexBuilder(self._kodi, viewers, self._monotonic)
            self._building_for = tuple(viewers)
        if not self._builder.step():
            return
        built = self._builder.result()
        self._builder = None
        if built is not None:
            self._index = built
            self._index_viewers = self._building_for
            if built.degraded:
                # Published, but not current. A degraded viewer has no membership at all
                # until a build succeeds, so the index stays dirty and the failure backoff
                # governs the retry. Treating this as success would make them wait a full
                # TTL, which is a worse recovery than the all-or-nothing build had.
                self._failures += 1
                self._failed_at = self._monotonic()
                _log.warning("service.index_degraded", viewers=len(built.degraded), consecutive=self._failures)
                self._notify_unreadable(built.unreadable)
                return
            self._index_dirty = False
            self._index_retired = False
            # Cleared on recovery, so a playlist that breaks again is reported again rather
            # than latching for ever and hiding a second, different breakage.
            self._notified_unreadable = frozenset()
            self._failures = 0
            self._failed_at = None
            return
        # Only reachable if a builder reports finished without a result, which it does not
        # do today. Kept so a future builder change cannot silently drop the retry.
        self._failures += 1
        self._failed_at = self._monotonic()
        _log.warning("service.index_build_failed", consecutive=self._failures)

    def _notify_unreadable(self, unreadable: frozenset[str]) -> None:
        """Tell the household, once per distinct set of broken playlists.

        The build retries on a backoff for as long as the playlist stays missing, so this
        must not fire per attempt. It is the only place a playlist name is allowed out:
        a toast goes to their own screen, while Kodi's log gets attached to bug reports.
        """
        if not unreadable or unreadable == self._notified_unreadable:
            return
        self._notified_unreadable = unreadable
        names = ", ".join(sorted(unreadable))
        text = self._kodi.localised(NOTIFY_UNREADABLE)
        # Appended when the placeholder is absent. A translation that drops %s would
        # otherwise produce a notification that says something is wrong and not what.
        message = text.replace("%s", names) if "%s" in text else f"{text} {names}".strip()
        self._kodi.notify(self._kodi.localised(NOTIFY_HEADING), message)

    def _servable_index(self, viewers: list[Viewer]) -> PlaylistIndex | None:
        """The index, unless it is too old to be trusted and there is someone to get wrong.

        Nothing else retires an index: _needs_index governs whether to rebuild, so a build
        that keeps failing would otherwise serve the same snapshot for ever.
        """
        index = self._index
        if index is None:
            return None
        if len(viewers) < 2:
            # Retirement prevents misattribution between household members. With one viewer
            # there is nobody to misattribute to, so retiring would buy nothing.
            return index
        age = self._monotonic() - index.built_at
        if age < self._settings.index_ttl_seconds * INDEX_MAX_AGE_MULTIPLIER:
            return index
        if not self._index_retired:
            # Once per retirement, not once per playback: a binge would otherwise repeat it
            # per episode. Cleared when a clean index is published.
            self._index_retired = True
            _log.warning("service.index_retired", age_seconds=int(age), viewers=len(viewers))
        return None

    def _needs_index(self) -> bool:
        if self._failed_at is not None:
            # Backoff, so a permanently unexpandable playlist cannot pin the addon into a
            # continuous whole-library rebuild loop.
            backoff = min(FAILURE_BACKOFF_SECONDS * (2 ** min(self._failures - 1, 5)), MAX_FAILURE_BACKOFF_SECONDS)
            if self._monotonic() - self._failed_at < backoff:
                return False
        if self._index_dirty or self._index is None:
            return True
        # The settings screen runs in its own interpreter and saves at once; reading the
        # small viewers file here is how its changes reach the index.
        if tuple(self._viewers()) != self._index_viewers:
            return True
        return (self._monotonic() - self._index.built_at) >= self._settings.index_ttl_seconds

    # -- stop handling -----------------------------------------------------

    def _park(self, session: PlaybackSession, reason: str, completed: bool | None = None) -> None:
        """Park a finished session for the tick to emit.

        A reconciled stop has no callback to tell it whether the item finished, so completion
        is derived from the last sample against Kodi's own end threshold. That is what
        ignore_percent_at_end is for.
        """
        self._paused = False
        if completed is None:
            percent = session.percent()
            completed = percent is not None and percent >= (100.0 - self._thresholds.ignore_percent_at_end)
        if completed:
            session.mark_complete()
        self._pending_stop = session
        _log.debug("service.stop_parked", session_id=session.session_id, reason=reason, completed=completed)

    def _flush_pending(self, allow_prompt: bool) -> None:
        session = self._pending_stop
        if session is None:
            return
        # Taken out of the slot before the prompt: the prompt window's doModal runs this
        # thread's queued player callbacks while it is open, so a nested on_av_started must
        # not find this stop and send it a second time, and a stop parked meanwhile by a
        # nested on_stopped must stay parked rather than be cleared on the way out.
        self._pending_stop = None
        asked = ""
        try:
            if allow_prompt and not session.identity.viewers:
                asked = self._attribute_by_prompt(session)
        finally:
            queued = False
            try:
                queued = self._emit("stop", session)
                if not queued:
                    _log.warning("service.stop_not_queued", session_id=session.session_id)
            except Exception as exc:
                _log.error("service.stop_emit_failed", session_id=session.session_id, error=str(exc))
            try:
                self._after_stop(session, queued, allow_prompt, asked)
            except Exception as exc:
                # The stop is already queued: a rating that fails costs only the rating.
                _log.warning("rating.failed", error=str(exc))

    def _attribute_by_prompt(self, session: PlaybackSession) -> str:
        """Attribute by asking: "answered", "declined" (asked, nobody answered), or "" (not asked)."""
        try:
            viewers = self._viewers()
            decision = prompt_mod.gate(
                identity=session.identity,
                viewers=viewers,
                media=session.media,
                position_ms=session.position_ms,
                thresholds=self._thresholds,
                movie_prompts_enabled=self._settings.movie_prompts,
                dialog_id=self._kodi.topmost_dialog_id(),
                shutting_down=self._shutting_down,
            )
            if not decision.ask:
                return ""
            names = prompt_mod.ask(self._kodi, viewers, session.media, PROMPT_AUTOCLOSE_SECONDS)
            if not names:
                return "declined"
            session.identity = identity_mod.Identity(names, "prompt")
            prompt_mod.remember(self._memory, session.media, names)
            return "answered"
        except Exception as exc:
            _log.warning("service.prompt_failed", error=str(exc))
        return ""

    # -- rating ------------------------------------------------------------

    def _after_stop(self, session: PlaybackSession, queued: bool, allow_prompt: bool, asked: str) -> None:
        completes = self._completes_watch(session.completed, session.percent())
        rateable = queued and rating_mod.rateable(
            self._settings, session.media, completes, self._has_usable_id(session.media)
        )
        watch = rating_mod.Watch(session.session_id, session.media, session.identity.viewers, asked == "declined")
        # A window of our own just closed: Kodi keeps it as the topmost dialog while it
        # animates out, which must not read as someone else's dialog being open.
        after_window = bool(asked)
        if self._settings.rating_at_end:
            if rateable:
                self._ratings.add(watch)
            # Any stop that leaves Kodi idle ends the session, also one that is not itself
            # rated: a binge usually ends with the next episode stopped partway.
            if allow_prompt and len(self._ratings) and not self._kodi.is_playing():
                # Taken before the first window: a stop flushed by a callback that window runs
                # queues for the next run, not for this one.
                self._run_ratings(self._ratings.take_all(), after_window)
        elif rateable and allow_prompt:
            self._run_ratings([watch], after_window)
        # After each watch, a stop flushed because the next item started is not rated: the
        # household is watching that next item.

    def _run_ratings(self, watches: list[rating_mod.Watch], after_window: bool) -> None:
        viewers = self._viewers()
        plan = [(w, rating_mod.questions(w, viewers, self._settings.rating_shared)) for w in watches]
        total = sum(len(qs) for _, qs in plan)
        index = 0
        for watch, questions in plan:
            if not questions:
                continue
            # Someone else's dialog can only be open before the first of our windows; after one,
            # the topmost dialog is ours, closing.
            dialog_id = WINDOW_INVALID if after_window else self._kodi.topmost_dialog_id()
            reason = rating_mod.may_ask(watch, dialog_id, self._shutting_down, self._kodi.is_playing())
            if reason == "declined":
                index += len(questions)
                continue
            if reason:
                self._abandon(total - index)
                return
            subtitle, poster = prompt_mod.header(self._kodi, watch.media)
            scores: list[int] = []
            for question in questions:
                index += 1
                request = RateRequest(
                    title=watch.media.title or "",
                    subtitle=subtitle,
                    poster=poster,
                    question=question_text(self._kodi.localised, question.viewer),
                    counter=counter_text(self._kodi.localised, index, total),
                    autoclose_seconds=RATING_AUTOCLOSE_SECONDS,
                    close_on_playback=True,
                )
                score = self._kodi.rate(request)
                after_window = True
                if score == RATE_FAILED:
                    # Already logged as ui.window_failed; every later window would fail too.
                    self._abandon(total - index)
                    return
                if score is not None:
                    scores.append(score)
                    for target in question.targets or (None,):
                        self._emit_rate(watch, target, score)
                if self._kodi.is_playing():
                    self._write_back(watch, scores)
                    self._abandon(total - index)
                    return
            self._write_back(watch, scores)

    def _abandon(self, left: int) -> None:
        dropped = self._ratings.clear()
        if left or dropped:
            _log.info("rating.abandoned", left=left + dropped)

    def _emit_rate(self, watch: rating_mod.Watch, viewer: str | None, score: int) -> None:
        event = PlaybackEvent(
            kind="rate",
            event_id=self._ids(),
            session_id=watch.session_id,
            sent_at=self._clock(),
            media=watch.media,
            viewers=(viewer,) if viewer else (),
            viewers_source=None,
            position_ms=None,
            duration_ms=None,
            percent=None,
            rating=score,
        )
        _log.info("rating.given", media_type=watch.media.media_type, library_id=watch.media.library_id, rating=score)
        if not self._queue.submit(event):
            _log.warning("rating.not_queued", session_id=watch.session_id)

    def _write_back(self, watch: rating_mod.Watch, scores: list[int]) -> None:
        if not self._settings.rating_write_library or not scores:
            return
        media = watch.media
        if media.library_id is None or media.is_pkc:
            _log.debug("rating.library_skipped", media_type=media.media_type, reason="not_in_library")
            return
        value = rating_mod.single_score(scores)
        if value is None:
            _log.info("rating.library_skipped", media_type=media.media_type, reason="scores_differ")
            return
        if self._kodi.set_user_rating(media.media_type, media.library_id, value):
            _log.info("rating.library_written", media_type=media.media_type, library_id=media.library_id)

    # -- helpers -----------------------------------------------------------

    def _viewers(self) -> list[Viewer]:
        return self._store.viewers()

    def _maybe_ping(self) -> None:
        """Tell CrossWatch this Kodi is reporting, so it stops polling.

        Sent whether or not something is playing: the server falls back to polling after 15
        minutes of silence, and going quiet during a long film would have it start polling
        mid-playback.
        """
        if self._shutting_down:
            return
        now = self._monotonic()
        names = tuple(v.name for v in self._viewers())
        # A changed set of names goes out at once: the reply is what marks a viewer no
        # CrossWatch route takes, and after a rename that should not wait five minutes.
        recent = self._last_ping_at is not None and (now - self._last_ping_at) < PING_INTERVAL_SECONDS
        if recent and names == self._pinged_names:
            return
        queued = self._queue.submit(
            PingEvent(
                event_id=self._ids(),
                sent_at=self._clock(),
                viewers=names,
                pkc_skipped=self.pkc_skipped,
            )
        )
        if not queued:
            # Do not advance the interval. A ping refused by a full queue would otherwise be
            # suppressed for another five minutes, during exactly the conditions it reports.
            _log.warning("service.ping_not_queued")
            return
        self._last_ping_at = now
        self._pinged_names = names
        _log.info("service.ping", viewers_count=len(names), pkc_skipped=self.pkc_skipped)

    @staticmethod
    def _has_usable_id(media: MediaItem) -> bool:
        """The receiver routes on ids. Without one there is nothing for it to match."""
        return bool(media.show_ids or media.episode_ids or media.plex_rating_key)

    def _recall(self, media: MediaItem, viewers: list[Viewer]) -> tuple[str, ...]:
        """Remembered names for this show, reconciled against the configured viewers.

        Consulted at start as well as at stop, so a show answered once resolves its next
        episode before playback begins.
        """
        known = {v.name for v in viewers}
        return tuple(name for name in prompt_mod.recall(self._memory, media) if name in known)

    def _profile_label(self) -> str:
        try:
            return str(self._kodi.jsonrpc("Profiles.GetCurrentProfile").get("label") or "").strip()
        except Exception as exc:
            # Profiles.GetCurrentProfile returns label at the top level, not nested.
            _log.warning("service.profile_lookup_failed", error=str(exc))
            return ""

    def _emit_for_live(self, kind: EventKind) -> None:
        session = self._session
        if session is None:
            _log.info("service.event_dropped", kind=kind, reason="no_session")
            return
        session.sample(*self._kodi.player_times())
        self._emit(kind, session)

    def _emit(self, kind: EventKind, session: PlaybackSession) -> bool:
        if not self._has_usable_id(session.media):
            _log.info(
                "service.event_dropped",
                kind=kind,
                reason="no_usable_id",
                media_type=session.media.media_type,
                library_id=session.media.library_id,
            )
            return False
        percent = session.percent()
        event = PlaybackEvent(
            kind=kind,
            event_id=self._ids(),
            session_id=session.session_id,
            sent_at=self._clock(),
            media=session.media,
            viewers=session.identity.viewers,
            viewers_source=session.identity.source,
            position_ms=session.position_ms,
            duration_ms=session.duration_ms,
            percent=percent,
            completed=session.completed,
            completes_watch=kind == "stop" and self._completes_watch(session.completed, percent),
        )
        return self._queue.submit(event)

    def _completes_watch(self, completed: bool, percent: float | None) -> bool:
        """Kodi's own watched rule, so the addon keeps what Kodi marks watched.

        CrossWatch applies its own threshold; if that one is lower, a stop between the two
        counts there but is not kept through an outage here. Kodi's is the threshold the
        household configured.
        """
        return completed or (percent is not None and percent >= self._thresholds.playcount_minimum_percent)

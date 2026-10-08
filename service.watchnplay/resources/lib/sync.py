# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT
"""Ablaufsteuerung des Dienstes: Abgleich, Warteschlange, Fehlerzustaende.

Ohne direkten Kodi-Bezug, damit sie offline testbar ist: Bibliothek, API und
Oberflaeche kommen als Objekte herein.
"""

import hashlib
import time

from . import library
from .api import ApiError, ProRequired, Retryable, Unauthorized

# Fehler, nach denen derselbe Stapel spaeter wieder gesendet wird
KEEP_ERRORS = (Retryable, Unauthorized, ProRequired)

STATUS_EVERY = 5 * 60
FULL_EVERY = 6 * 3600
PRO_RETRY = 6 * 3600
DEBOUNCE = 5
GUARD_TTL = 120
BACKOFF = (30, 120, 600, 1800)
PLAYS_PER_REQUEST = 100
# Server: 120 Anfragen/min je Konto, geteilt von allen Geraeten
CHUNK_PAUSE = 1.0
# Rueck-Sync: fehlgeschlagenes Schreiben in Kodi erneut versuchen
WRITE_RETRY = 60
WRITE_TRIES = 5
# Mehr Einzel-Aenderungen auf einmal (ganze Staffel/Serie markiert): statt jeden Titel
# einzeln nachzulesen ein voller Abgleich
MASS_DELTAS = 200


def _sleep(seconds):
    time.sleep(seconds)
    return False


class _Stale(Exception):
    """Waehrend eines Durchgangs neu gekoppelt oder getrennt: abbrechen, nichts schreiben."""


class SyncEngine(object):
    """
    lib: collect_all(), get_item(kid), set_watched(kid, watched, has_lastplayed), chunks(items)
         get_item wirft bei einem voruebergehenden Lesefehler, None heisst: nicht (mehr) da
    ui:  notify(string_id, *args), status(paired, user, device, pro_paused), log(msg), warn(msg)
    make_api(token) -> Api
    wait(seconds) -> True bei Kodi-Abbruch (Monitor.waitForAbort)
    min_percent() -> Kodis Gesehen-Schwelle (50..100), geht als minPercent an /plays
    is_playing() -> True, solange ein Video laeuft (voller Abgleich wartet dann)
    """

    def __init__(self, store, lib, ui, make_api, clock=time.time, wait=None, min_percent=None,
                 is_playing=None):
        self.store = store
        self.lib = lib
        self.ui = ui
        self.make_api = make_api
        self.clock = clock
        self.wait = wait or _sleep
        self.min_percent = min_percent
        self.is_playing = is_playing
        # kid -> (Ablauf, von uns gesetzter Gesehen-Stand)
        self.guard = {}
        # kid -> {'watched', 'lp', 'tries', 'at'}: Rueck-Sync-Schreiben, das Kodi abgelehnt hat
        self.write_retry = {}
        self.fails = 0
        self.next_retry = 0
        self.full_pending = True
        # zaehlt Anforderungen eines vollen Abgleichs; eine waehrend des Durchgangs
        # eingegangene bleibt dadurch stehen
        self.full_gen = 1
        # 'Jetzt synchronisieren': auch waehrend einer Wiedergabe
        self.full_forced = False
        # zaehlt Kopplung/Trennung; ein laufender Durchgang erkennt so, dass er veraltet ist
        self.session = 0
        self.last_status = 0
        self.notified_401 = False
        # Id-Index der Kodi-Bibliothek aus dem letzten Lesen (None = noch nie gelesen)
        self.library_index = None

    # --- Zustand ---
    @property
    def paired(self):
        return bool(self.store.token)

    @property
    def pro_paused(self):
        return bool(self.store.state.get('proPaused'))

    def _api(self):
        return self.make_api(self.store.token)

    def refresh_ui(self):
        st = self.store.state
        auth = self.store.auth
        self.ui.status(self.paired, st.get('userName') or auth.get('userName'),
                       st.get('deviceName'), self.pro_paused)

    def _reset_session(self):
        self.session += 1
        self.store.reset_state()
        self.store.clear_queue()
        self.guard.clear()
        self.write_retry.clear()

    def on_paired(self):
        """Nach Kopplung: Zustand frisch, sofort voller Abgleich.

        Die Warteschlange gehoert zum vorigen Konto und wird nicht unter dem neuen gesendet."""
        self.store.reload_auth(force=True)
        self._reset_session()
        self.notified_401 = False
        self.request_full(now=True)
        self.last_status = 0

    def on_unpaired(self):
        self.store.reload_auth(force=True)
        self._reset_session()
        self.refresh_ui()

    def request_full(self, now=False, forced=False):
        self.full_pending = True
        self.full_gen += 1
        if forced:
            self.full_forced = True
        if now:
            self.fails = 0
            self.next_retry = 0

    def sync_now(self):
        """'Jetzt synchronisieren': sofort /status und voller Abgleich, auch aus der Pro-Pause
        und waehrend einer Wiedergabe."""
        self.request_full(now=True, forced=True)
        self.last_status = 0
        if self.store.state.pop('proCheckAt', None) is not None:
            self.store.save_state()

    def _check_session(self, session):
        if session != self.session or not self.paired:
            raise _Stale()

    # --- Schleifenschutz ---
    def guard_kid(self, kid, watched):
        self.guard[kid] = (self.clock() + GUARD_TTL, bool(watched))

    def is_guarded(self, kid, watched=None):
        """True, wenn die Meldung unsere eigene Aenderung ist.

        Mit bekanntem Stand nur, wenn er dem von uns gesetzten entspricht: korrigiert der
        Nutzer unsere Markierung gleich danach, geht die Korrektur normal durch."""
        now = self.clock()
        for k in [k for k, (exp, _) in self.guard.items() if exp <= now]:
            del self.guard[k]
        entry = self.guard.get(kid)
        if entry is None:
            return False
        return watched is None or entry[1] == bool(watched)

    # --- Eingaenge ---
    def on_library_update(self, kid, playcount=None):
        """Kodi hat playcount geaendert. Eigene Markierungen nicht zurueckmelden."""
        watched = None if playcount is None else playcount > 0
        if not self.paired or self.is_guarded(kid, watched):
            return False
        # gespeichert wird gesammelt im naechsten tick (ganze Staffel = viele Meldungen)
        self.store.add_delta(kid, self.clock())
        return True

    def queue_play(self, play):
        if not self.paired:
            return False
        if library.in_index(self.library_index, play):
            # steht in Kodis Bibliothek: kommt ueber den playcount, nicht doppelt melden
            self.ui.log('playback belongs to a Kodi library item, not queued')
            return False
        self.store.add_play(play)
        return True

    # --- Fehlerbehandlung ---
    def _backoff(self):
        delay = BACKOFF[min(self.fails, len(BACKOFF) - 1)]
        self.fails += 1
        self.next_retry = self.clock() + delay
        return delay

    def _pause_pro(self):
        st = self.store.state
        now = self.clock()
        st['proPaused'] = True
        st['proCheckAt'] = now + PRO_RETRY
        today = time.strftime('%Y-%m-%d', time.localtime(now))
        if st.get('proNotifiedDay') != today:
            st['proNotifiedDay'] = today
            self.ui.notify(32019)
        self.store.save_state()
        self.refresh_ui()

    def _handle(self, exc):
        if isinstance(exc, Unauthorized):
            used = getattr(exc, 'token', None)
            if used is not None and used != self.store.token:
                # Anfrage lief noch mit dem alten Token, inzwischen neu gekoppelt: nichts loeschen
                self.ui.log('401 for a previous token, current connection kept')
                return
            self.ui.warn('token rejected (401), connection removed')
            self.store.clear_auth()
            self._reset_session()
            if not self.notified_401:
                self.notified_401 = True
                self.ui.notify(32018)
            self.refresh_ui()
            return
        if isinstance(exc, ProRequired):
            self._pause_pro()
            return
        if isinstance(exc, Retryable):
            delay = self._backoff()
            if exc.kodi_disabled:
                # Betreiber-Schalter fuer dieses Konto aus: nur warten, kein Hinweis
                self.ui.log('sync switched off for this account (KODI_DISABLED), retry in %ss' % delay)
            else:
                self.ui.warn('request failed (%s), retry in %ss' % (exc.status, delay))
            return
        self.ui.warn('request rejected (%s), dropping batch' % getattr(exc, 'status', '?'))

    def _ok(self):
        self.fails = 0
        self.next_retry = 0

    def _adopt_version(self, version):
        if version is not None and version != self.store.state.get('version'):
            self.store.state['version'] = version
            self.store.save_state()

    def _read_failed(self, exc):
        delay = self._backoff()
        self.ui.warn('library read failed: %s, retry in %ss' % (exc, delay))

    # --- Hauptschleife ---
    def tick(self):
        """Regelmaessig (etwa sekuendlich) aufrufen."""
        self.store.save_if_dirty()
        if not self.paired:
            return
        now = self.clock()
        self.retry_writes()
        st = self.store.state
        if self.pro_paused:
            # Waehrend der Pause nur alle 6 h /status; Wiedergaben werden weiter gesammelt
            if now >= st.get('proCheckAt', 0) and now >= self.next_retry:
                self.check_status()
            return
        if now < self.next_retry:
            return
        if now - self.last_status >= STATUS_EVERY:
            if not self.check_status():
                return
        if self.full_pending or now - st.get('lastFull', 0) >= FULL_EVERY:
            if self._playing() and not self.full_forced:
                # grosser Abgleich ruckelt auf schwachen Boxen: nach der Wiedergabe
                pass
            elif not self.full_reconcile():
                return
        if not self.flush_deltas():
            return
        self.flush_plays()

    def _playing(self):
        if self.is_playing is None:
            return False
        try:
            return bool(self.is_playing())
        except Exception:
            return False

    def check_status(self):
        self.last_status = self.clock()
        try:
            res = self._api().status()
        except ApiError as exc:
            # 402 hier: weiter pausiert, naechster Versuch in 6 h, Hinweis hoechstens einmal am Tag
            self._handle(exc)
            return False
        self._ok()
        st = self.store.state
        was_paused = bool(st.get('proPaused'))
        st['userName'] = res.get('userName')
        st['deviceName'] = res.get('deviceName')
        back_sync = bool(res.get('backSync'))
        if st.get('backSync') is not None and bool(st.get('backSync')) != back_sync:
            # Rueck-Sync an: der Server braucht die ganze Bibliothek; aus: nur noch Gesehenes
            self.request_full()
        st['backSync'] = back_sync
        st['pro'] = res.get('pro') is not False
        if not st['pro']:
            # /status selbst braucht kein Pro: ohne Pro gar nicht erst senden (sonst 402)
            self._pause_pro()
            return False
        st['proPaused'] = False
        st.pop('proCheckAt', None)
        version = res.get('version')
        if version is not None and version != st.get('version'):
            # Nur mit Rueck-Sync muss eine Aenderung in WatchNPlay nach Kodi; ohne laufen
            # Buchungen ueber Deltas und den 6-stuendlichen vollen Abgleich
            if st.get('version') is not None and st['backSync']:
                self.request_full()
            st['version'] = version
        if was_paused:
            self.request_full()
        self.store.save_state()
        self.refresh_ui()
        return True

    def _get_item(self, kid):
        """None = nicht (mehr) in Kodis Bibliothek; ein Lesefehler geht als Exception weiter."""
        return self.lib.get_item(kid)

    def _apply(self, res, known):
        """mark/unmark vom Server in Kodi anwenden; known: {kid: LibItem}."""
        if 'backSync' in res:
            back_sync = bool(res.get('backSync'))
            prev = self.store.state.get('backSync')
            if prev is not None and bool(prev) != back_sync:
                # umgeschaltet: der naechste Durchgang sendet die passende Auswahl
                self.request_full()
            self.store.state['backSync'] = back_sync
        changed = 0
        for watched, kids in ((True, res.get('mark') or []), (False, res.get('unmark') or [])):
            for kid in kids:
                item = known.get(kid)
                if item is None:
                    try:
                        item = self._get_item(kid)
                    except Exception as exc:
                        self.ui.warn('could not read %s: %s' % (kid, exc))
                        continue
                    if item is None:
                        continue
                if bool(item.get('watched')) == watched:
                    self.write_retry.pop(kid, None)
                    continue
                if self._write(kid, watched, bool(item.get('lastPlayed'))):
                    item['watched'] = watched
                    changed += 1
        return changed

    def _write(self, kid, watched, has_lastplayed):
        """In Kodi markieren; schlaegt es fehl, spaeter erneut (nicht erst beim naechsten vollen Abgleich)."""
        self.guard_kid(kid, watched)
        if self.lib.set_watched(kid, watched, has_lastplayed):
            self.write_retry.pop(kid, None)
            return True
        entry = self.write_retry.get(kid)
        if entry is None or entry['watched'] != watched:
            entry = {'watched': watched, 'lp': has_lastplayed, 'tries': 0}
        entry['tries'] += 1
        if entry['tries'] >= WRITE_TRIES:
            self.ui.warn('could not update %s in Kodi after %d tries' % (kid, entry['tries']))
            self.write_retry.pop(kid, None)
            return False
        entry['at'] = self.clock() + WRITE_RETRY
        self.write_retry[kid] = entry
        return False

    def retry_writes(self):
        now = self.clock()
        for kid, entry in list(self.write_retry.items()):
            if now < entry['at']:
                continue
            try:
                current = self._get_item(kid)
            except Exception:
                entry['at'] = now + WRITE_RETRY
                continue
            if current is None or bool(current.get('watched')) == entry['watched']:
                # Titel weg oder inzwischen schon im gewuenschten Stand
                self.write_retry.pop(kid, None)
                continue
            self._write(kid, entry['watched'], entry['lp'])

    def _items_to_send(self, items):
        """Mit Rueck-Sync braucht der Server die ganze Bibliothek (er markiert auch Titel,
        die erst spaeter dazukommen). Ohne nur Gesehenes, dazu Titel mit offener
        Einzel-Aenderung (zurueckgenommen in Kodi)."""
        if self.store.state.get('backSync'):
            return items, 'all'
        pending = self.store.deltas
        return [i for i in items if i.get('watched') or i['kid'] in pending], 'seen'

    def full_reconcile(self):
        """Bibliothek in Haeppchen senden, mit Pause dazwischen.

        Der laufende Durchgang (state['fullPass']) merkt sich das naechste Haeppchen; nach
        429/Netzfehler/Neustart geht es dort weiter statt wieder bei 1. Neu beginnt er, wenn
        sich die Eintraege geaendert haben (Fingerabdruck aller Ids in Reihenfolge, nicht nur
        die Anzahl: sonst rutscht ein neuer Titel in ein schon gesendetes Haeppchen).
        Lehnt der Server ein Haeppchen endgueltig ab, faellt nur dieses weg.

        Uebernommen wird der Stand (version) aus der Antwort auf das ERSTE Haeppchen des
        Durchgangs: eine Aenderung in WatchNPlay waehrend des Durchgangs an einem Titel aus
        einem schon gesendeten Haeppchen loest so den naechsten Abgleich aus.
        """
        session = self.session
        gen = self.full_gen
        now = self.clock()
        try:
            all_items = self.lib.collect_all()
        except Exception as exc:
            self._read_failed(exc)
            return False
        self.library_index = library.build_index(all_items)
        items, mode = self._items_to_send(all_items)
        st = self.store.state
        sig = hashlib.sha1((mode + '\n' + '\n'.join(i['kid'] for i in items)).encode('utf-8')).hexdigest()
        fpass = st.get('fullPass')
        if not isinstance(fpass, dict) or fpass.get('sig') != sig:
            fpass = {'sig': sig, 'next': 0, 'started': now}
        started = fpass.get('started', now)
        chunks = list(self.lib.chunks(items))
        start = min(max(0, int(fpass.get('next') or 0)), len(chunks))
        if start:
            self.ui.log('full reconcile resumes at part %d of %d' % (start + 1, len(chunks)))
        applied = 0
        rejected = set()
        known = dict((i['kid'], i) for i in items)
        try:
            api = self._api()
            for idx in range(start, len(chunks)):
                if idx > start:
                    aborted = self.wait(CHUNK_PAUSE)
                    self._check_session(session)
                    if aborted:
                        self._save_pass(fpass, idx)
                        return False
                try:
                    part = api.library(chunks[idx], True)
                except ApiError as exc:
                    self._check_session(session)
                    if isinstance(exc, KEEP_ERRORS):
                        raise
                    self._handle(exc)
                    fpass['dropped'] = True
                    rejected.update(i['kid'] for i in chunks[idx])
                else:
                    self._check_session(session)
                    if 'version' not in fpass:
                        fpass['version'] = part.get('version')
                    applied += self._apply(part, known)
                self._save_pass(fpass, idx + 1)
            if not chunks:
                part = api.library([], True)
                self._check_session(session)
                fpass['version'] = part.get('version')
        except _Stale:
            self.ui.log('full reconcile stopped: connection changed')
            return False
        except ApiError as exc:
            self._handle(exc)
            return False
        self._ok()
        if not fpass.get('dropped'):
            self._adopt_version(fpass.get('version'))
        self._finish_full(started, gen, keep=rejected)
        self.ui.log('full reconcile: %d of %d items sent (%s), %d changed in Kodi%s'
                    % (len(items), len(all_items), mode, applied,
                       ', parts rejected' if fpass.get('dropped') else ''))
        return True

    def _save_pass(self, fpass, next_idx):
        fpass['next'] = next_idx
        self.store.state['fullPass'] = fpass
        self.store.save_state()

    def _finish_full(self, started, gen, keep=()):
        if gen == self.full_gen:
            # keine neue Anforderung waehrend des Durchgangs (Scan, 'Jetzt synchronisieren')
            self.full_pending = False
            self.full_forced = False
        self.store.state.pop('fullPass', None)
        self.store.state['lastFull'] = started
        self.store.save_state()
        # Einzel-Aenderungen vor dem Beginn des Durchgangs sind darin enthalten (ausser im
        # abgelehnten Haeppchen: die gehen weiter einzeln)
        for kid, ts in list(self.store.deltas.items()):
            if ts <= started and kid not in keep:
                del self.store.deltas[kid]
        self.store.save_queue()

    def flush_deltas(self):
        """Einzel-Aenderungen senden. Der Stand (version) aus der Antwort wird NICHT
        uebernommen: er gilt fuer das ganze Konto, mark/unmark nur fuer die gesendeten Titel."""
        now = self.clock()
        due = [(k, ts) for k, ts in self.store.deltas.items() if now - ts >= DEBOUNCE]
        if not due:
            return True
        if len(due) > MASS_DELTAS:
            if not self.full_pending:
                self.ui.log('%d changes at once, full reconcile instead' % len(due))
                self.request_full()
            return True
        session = self.session
        stamps = dict(due)
        items = []
        for kid, ts in due:
            try:
                item = self._get_item(kid)
            except Exception as exc:
                # Datenbank gerade beschaeftigt (Scan): Aenderungen bleiben, spaeter erneut
                self._read_failed(exc)
                return False
            if item:
                items.append(item)
            else:
                # nicht mehr in Kodis Bibliothek
                self._drop_deltas([kid], stamps)
        api = self._api()
        try:
            for idx, chunk in enumerate(self.lib.chunks(items)):
                if idx:
                    aborted = self.wait(CHUNK_PAUSE)
                    self._check_session(session)
                    if aborted:
                        self.store.save_queue()
                        return False
                try:
                    part = api.library(chunk, False)
                except ApiError as exc:
                    self._check_session(session)
                    self._handle(exc)
                    if isinstance(exc, KEEP_ERRORS):
                        # dieses und alle folgenden Haeppchen bleiben in der Warteschlange
                        self.store.save_queue()
                        return False
                else:
                    self._check_session(session)
                    self._apply(part, dict((i['kid'], i) for i in chunk))
                # gesendet oder endgueltig abgelehnt: nur dieses Haeppchen aus der Warteschlange
                self._drop_deltas([i['kid'] for i in chunk], stamps)
        except _Stale:
            return False
        self._ok()
        self.store.save_queue()
        return True

    def _drop_deltas(self, kids, stamps):
        """Nur entfernen, wenn seit dem Lesen keine neuere Aenderung dazukam."""
        for kid in kids:
            if self.store.deltas.get(kid) == stamps.get(kid):
                del self.store.deltas[kid]

    def flush_plays(self):
        if not self.store.plays:
            return True
        # Inzwischen in Kodis Bibliothek (z. B. vor dem ersten Lesen gemerkt): meldet der playcount
        if self.library_index:
            kept = [p for p in self.store.plays if not library.in_index(self.library_index, p)]
            if len(kept) != len(self.store.plays):
                self.ui.log('dropped %d plays of Kodi library items' % (len(self.store.plays) - len(kept)))
                self.store.plays = kept
                self.store.save_queue()
                if not kept:
                    return True
        session = self.session
        batch = self.store.plays[:PLAYS_PER_REQUEST]
        min_percent = None
        if self.min_percent is not None:
            try:
                min_percent = self.min_percent()
            except Exception:
                min_percent = None
        try:
            res = self._api().plays(batch, min_percent=min_percent)
        except ApiError as exc:
            if session != self.session:
                return False
            self._handle(exc)
            if isinstance(exc, KEEP_ERRORS):
                return False
            res = {}
        else:
            if session != self.session:
                return False
            self._ok()
            self.ui.log('plays sent: %d, accepted %s' % (len(batch), res.get('accepted')))
        self.store.plays = self.store.plays[len(batch):]
        self.store.save_queue()
        return True

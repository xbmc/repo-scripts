"""Deciding which score changes are worth interrupting a viewer for.

Pure module: it compares the previous poll's snapshots with this poll's and
returns a list of events. No Kodi, no network, so every rule is testable.

Only four things earn a notification:

``MATCH_LIVE``   a match we had not seen before is in play
``SET_DONE``     the completed-set count went up
``MATCH_DONE``   the match finished
``BREAK_POINT``  the receiver is a point from breaking serve (opt-in)

Detecting a finish needs care, and is the one place this add-on infers rather
than observes. ``/matches?status=live`` only ever returns matches whose status
is ``live``, so a finished match is never reported as finished -- it simply
stops appearing. A single absence is not proof of a finish (a feed gap looks
identical), so a tracked match must be missing from ``ABSENCES_BEFORE_DONE``
consecutive polls before its finish is announced. That threshold is the whole
safeguard, which is why it is more than one: at the default cadence it means a
match must be gone for an hour. A feed outage longer than that will still
produce a "finished" notification for a match that is still being played; the
add-on cannot tell the two apart without spending a request per disappearance,
which the provider's free daily allowance does not stretch to.
"""

from . import scoring

MATCH_LIVE = "match_live"
SET_DONE = "set_done"
MATCH_DONE = "match_done"
BREAK_POINT = "break_point"

# Consecutive polls a tracked match must be absent from the live list before
# its disappearance is treated as the match having finished. Three, not two,
# because the cost of waiting one more cycle is a later notification whereas
# the cost of being wrong is announcing the end of a match still in progress.
ABSENCES_BEFORE_DONE = 3


class Event:
    """One notification-worthy change."""

    __slots__ = ("kind", "match_id", "label", "detail", "snapshot")

    def __init__(self, kind, match_id, label, detail="", snapshot=None):
        self.kind = kind
        self.match_id = match_id
        self.label = label
        self.detail = detail
        self.snapshot = snapshot or {}

    def __repr__(self):
        return f"Event({self.kind!r}, {self.label!r}, {self.detail!r})"


def _detail_for_score(snap):
    """``"6-4 3-4  40-30"`` -- whatever of the score is actually published."""
    parts = [snap.get("sets_text") or "", snap.get("points_text") or ""]
    return "  ".join(part for part in parts if part)


def diff(previous, matches, notify_break_points=False, first_poll=False):
    """Compare the last poll to this one.

    :param previous: ``{match_id: snapshot}`` from the last call.
    :param matches: the decoded ``data`` array of ``/matches?status=live``.
    :param notify_break_points: emit ``BREAK_POINT`` events.
    :param first_poll: True only for the session's very first successful poll,
        where every match in play would otherwise arrive at once as "now live".
        This must be told to us rather than inferred from ``previous`` being
        empty: an empty ``previous`` is also the normal state after a quiet
        spell with nothing on court, and treating that as a first poll would
        silently swallow the next match to start.
    :returns: ``(events, current)`` where ``current`` is the state to pass back
        in as ``previous`` next time.
    """
    previous = dict(previous or {})
    events = []
    current = {}

    for match in matches:
        snap = scoring.snapshot(match)
        key = snap["id"]
        if key is None or key in current:
            # No usable id, or the same id twice in one page: keep the first.
            continue
        before = previous.pop(key, None)
        current[key] = snap

        if before is None:
            if snap["status"] and snap["status"] != "live":
                # First sight of this match and it is already over. It is not
                # news that it went on court, and its finish happened before we
                # were watching, so neither is announced.
                snap["done_announced"] = True
            elif not first_poll:
                events.append(Event(MATCH_LIVE, key, snap["label"],
                                    snap.get("tournament", ""), snap))
            continue

        # Carried forward so a match that lingers in the list as `completed` is
        # announced once, not on every poll for as long as it is listed.
        if before.get("done_announced"):
            snap["done_announced"] = True
            continue

        if snap["status"] and snap["status"] != "live":
            snap["done_announced"] = True
            events.append(Event(MATCH_DONE, key, snap["label"],
                                _finish_detail(snap), snap))
            continue

        if snap["sets_done"] > before.get("sets_done", 0):
            events.append(Event(SET_DONE, key, snap["label"],
                                snap.get("sets_text", ""), snap))

        # Remember which GAME a break point was announced for, rather than
        # just that the last poll had one. Keying on a boolean would swallow a
        # genuinely new break point whenever the previous poll also caught one
        # -- and two polls fifteen minutes apart are never the same game. This
        # announces at most one break point per game, and does not miss one
        # just because the same game was already seen in a non-break state.
        announced_for = before.get("bp_announced_for")
        if (notify_break_points and snap["break_point"]
                and announced_for != snap["game_key"]):
            announced_for = snap["game_key"]
            events.append(Event(BREAK_POINT, key, snap["label"],
                                _detail_for_score(snap), snap))
        snap["bp_announced_for"] = announced_for

    # Whatever is left in `previous` was tracked last poll and is not listed now.
    for key, before in previous.items():
        if before.get("done_announced"):
            # Already announced as finished while it lingered in the list, and
            # now dropped out of it. Forget it without announcing it twice.
            continue
        misses = int(before.get("missing_polls", 0)) + 1
        if misses >= ABSENCES_BEFORE_DONE:
            events.append(Event(MATCH_DONE, key, before.get("label", ""),
                                _finish_detail(before), before))
            continue
        # Keep tracking it for another poll before calling it finished.
        carried = dict(before)
        carried["missing_polls"] = misses
        current[key] = carried

    return events, current


def _finish_detail(snap):
    """The line under a "finished" heading: score, winner and any oddity.

    The winner is only ever shown when the feed named one. A match inferred
    finished from its disappearance has no winner, so it shows the last score
    seen and nothing more -- it never guesses who won.
    """
    parts = []
    sets_text = snap.get("sets_text") or ""
    if sets_text:
        parts.append(sets_text)
    winner = snap.get("winner") or ""
    if winner:
        parts.append(winner)
    event_status = snap.get("event_status") or ""
    if event_status and event_status.lower() not in ("", "none"):
        # Retired / Walk Over / Cancelled / Postponed / Interrupted.
        parts.append(f"({event_status})")
    return "  ".join(parts)

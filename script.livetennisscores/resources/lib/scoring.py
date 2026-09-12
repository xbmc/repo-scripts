"""Pure tennis-score logic for script.livetennisscores.

Nothing in this module imports Kodi, touches the network or reads settings, so
every rule below can be exercised on its own.

Shape of the data, as documented by the provider
(https://docs.livetennisapi.com/openapi.yaml, schema ``Score``):

* ``sets``   -- ``[sets_won_p1, sets_won_p2]``.
* ``games``  -- PLAYER-MAJOR: ``[games_p1, games_p2]`` where each entry is that
  player's per-set list. ``[[6, 3], [4, 4]]`` therefore reads 6-4, 3-4.
* ``points`` -- ``["0", "15", "30", "40", "AD"]`` in a normal game, but the
  running tiebreak count as plain integer strings during a tiebreak.
  ``is_tiebreak`` tells the two notations apart. Entries may be NULL, which is
  observed live on completed matches -- those also carry empty ``games``.
* ``server`` -- ``1``, ``2`` or NULL.

Because every one of those may be absent or null, each helper here takes the
raw decoded JSON and is total: it returns a sensible empty value instead of
raising.
"""

# The four ordinary in-game point tokens that can precede a break point, plus
# the advantage token. Anything outside this vocabulary (a tiebreak count, a
# value the feed invented) is treated as "not a break point".
_SERVER_BEHIND_TOKENS = frozenset({"0", "15", "30"})
_ADVANTAGE = "AD"
_FORTY = "40"


def _as_list(value):
    """Return ``value`` when it is a list, else an empty list."""
    return value if isinstance(value, list) else []


def _as_int(value):
    """Coerce a feed number to int, returning None when that is not possible."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def get_score(match):
    """The match's ``score`` object, or an empty dict.

    ``score`` is declared nullable, so a live match can legitimately arrive
    with ``"score": null``.
    """
    if not isinstance(match, dict):
        return {}
    score = match.get("score")
    return score if isinstance(score, dict) else {}


def server_of(score):
    """The serving player as 1 or 2, or None when the feed did not say."""
    server = _as_int(score.get("server")) if isinstance(score, dict) else None
    return server if server in (1, 2) else None


def receiver_of(score):
    """The receiving player as 1 or 2, or None when the server is unknown."""
    server = server_of(score)
    if server == 1:
        return 2
    if server == 2:
        return 1
    return None


def is_tiebreak(score):
    """True only when the feed positively states a tiebreak is in progress."""
    return isinstance(score, dict) and score.get("is_tiebreak") is True


def point_tokens(score):
    """The two in-game point strings, or ``[]`` when they are not both present.

    Guards the documented null case: ``points`` entries "can be NULL --
    observed live on completed matches".
    """
    if not isinstance(score, dict):
        return []
    points = _as_list(score.get("points"))
    if len(points) < 2:
        return []
    first, second = points[0], points[1]
    if not isinstance(first, str) or not isinstance(second, str):
        return []
    return [first, second]


def is_break_point(score):
    """True when the receiver is one point from breaking serve.

    The rule, and only this rule:

    * never during a tiebreak -- there is no serve to break, and the point
      strings there are a running integer count, so "40" could otherwise be
      misread out of a long tiebreak;
    * receiver at AD (advantage receiver), or
    * receiver at 40 while the server is at 0, 15 or 30.

    40-40 is deuce, not a break point, which falls out of excluding "40" from
    the server's tokens. Returns False rather than raising whenever the server,
    the point strings or the score itself are missing or null.
    """
    if not isinstance(score, dict):
        return False
    if is_tiebreak(score):
        return False

    receiver = receiver_of(score)
    if receiver is None:
        return False

    tokens = point_tokens(score)
    if not tokens:
        return False

    receiver_point = tokens[receiver - 1]
    server_point = tokens[0 if receiver == 2 else 1]

    if receiver_point == _ADVANTAGE:
        return True
    return receiver_point == _FORTY and server_point in _SERVER_BEHIND_TOKENS


def sets_won(score):
    """``[sets_p1, sets_p2]`` as ints, defaulting to ``[0, 0]``."""
    raw = _as_list(score.get("sets")) if isinstance(score, dict) else []
    out = []
    for index in range(2):
        value = _as_int(raw[index]) if index < len(raw) else None
        out.append(value if value is not None and value >= 0 else 0)
    return out


def completed_set_count(score):
    """How many sets are finished, used to detect that a set just ended.

    Prefers the ``sets`` tally. Falls back to the number of fully populated
    ``games`` columns when ``sets`` is absent, so an empty tally does not read
    as "no set has ever finished" on a match that clearly has set scores.
    """
    total = sum(sets_won(score))
    if total:
        return total
    pairs = game_pairs(score)
    if len(pairs) <= 1:
        return 0
    # Every set but the one in progress is finished.
    return len(pairs) - 1


def game_pairs(score):
    """Per-set ``(games_p1, games_p2)`` pairs, oldest set first.

    ``games`` is player-major, so this transposes it. A set present for only
    one player (a partially published column) is filled with 0 for the other
    rather than dropped.
    """
    if not isinstance(score, dict):
        return []
    games = _as_list(score.get("games"))
    if len(games) < 2:
        return []
    p1 = _as_list(games[0])
    p2 = _as_list(games[1])
    pairs = []
    for index in range(max(len(p1), len(p2))):
        left = _as_int(p1[index]) if index < len(p1) else None
        right = _as_int(p2[index]) if index < len(p2) else None
        if left is None and right is None:
            continue
        pairs.append((left or 0, right or 0))
    return pairs


def format_sets(score):
    """The set scores as ``"6-4 3-4"``, or ``""`` when none are published."""
    return " ".join(f"{left}-{right}" for left, right in game_pairs(score))


def format_points(score):
    """The current game as ``"40-30"``, ``""`` when the points are not usable.

    In a tiebreak the same two strings are the running tiebreak count, so the
    result is tagged to stop it being read as 15/30/40.
    """
    tokens = point_tokens(score)
    if not tokens:
        return ""
    rendered = f"{tokens[0]}-{tokens[1]}"
    return f"TB {rendered}" if is_tiebreak(score) else rendered


def player_names(match):
    """``(name_p1, name_p2)``, falling back to a placeholder for either."""
    players = match.get("players") if isinstance(match, dict) else None
    players = players if isinstance(players, dict) else {}
    names = []
    for key in ("p1", "p2"):
        player = players.get(key)
        name = player.get("name") if isinstance(player, dict) else None
        names.append(name.strip() if isinstance(name, str) and name.strip() else "?")
    return names[0], names[1]


def match_label(match):
    """``"Alcaraz v Sinner"`` -- the short headline for a notification."""
    first, second = player_names(match)
    return f"{first} v {second}"


def match_id(match):
    """The match id as a string key, or None when there is not one."""
    if not isinstance(match, dict):
        return None
    raw = match.get("id")
    if raw is None or isinstance(raw, bool):
        return None
    text = str(raw).strip()
    return text or None


def winner_name(match):
    """The winner's name when the feed named a winner, else ""."""
    winner = _as_int(match.get("winner")) if isinstance(match, dict) else None
    if winner not in (1, 2):
        return ""
    return player_names(match)[winner - 1]


def game_key(score):
    """An identifier for the game currently being played.

    Used to tell one break point from the next. Two different games always
    differ in the set they belong to, the games standing within that set, or
    who is serving, so the triple is enough -- and it changes as soon as the
    game is won, which is what stops a later break point being mistaken for
    the one already announced.
    """
    pairs = game_pairs(score)
    current_set = len(pairs)
    standing = pairs[-1] if pairs else (0, 0)
    return (current_set, standing, server_of(score))


def snapshot(match):
    """Reduce a match to the few fields a state change is decided from.

    Kept deliberately small and JSON-ish: it is compared against the previous
    poll's snapshot, and nothing else about the payload is remembered.
    """
    score = get_score(match)
    return {
        "id": match_id(match),
        "label": match_label(match),
        "status": (match.get("status") or "") if isinstance(match, dict) else "",
        "event_status": (match.get("event_status") or "") if isinstance(match, dict) else "",
        "tournament": (match.get("tournament") or "") if isinstance(match, dict) else "",
        "sets_text": format_sets(score),
        "sets_done": completed_set_count(score),
        "points_text": format_points(score),
        "server": server_of(score),
        "break_point": is_break_point(score),
        "game_key": game_key(score),
        "winner": winner_name(match),
        "missing_polls": 0,
    }


def parse_matches(payload):
    """The ``data`` array of a ``/matches`` response, as a list of dicts.

    The provider wraps every list in ``{"data": [...], "meta": {...}}``. A
    bare list is accepted too so a change of envelope does not break the
    add-on outright.
    """
    if isinstance(payload, dict):
        data = payload.get("data")
    else:
        data = payload
    return [item for item in _as_list(data) if isinstance(item, dict)]


def board_lines(matches):
    """The scoreboard body: one line per match in play.

    ``*`` marks the server against the player who is serving and ``BP`` flags a
    break point, which is why the line is built here and not in the window.
    """
    lines = []
    for match in matches:
        score = get_score(match)
        first, second = player_names(match)
        server = server_of(score)
        left = f"{'* ' if server == 1 else '  '}{first}"
        right = f"{'* ' if server == 2 else '  '}{second}"

        detail = []
        sets_text = format_sets(score)
        if sets_text:
            detail.append(sets_text)
        points_text = format_points(score)
        if points_text:
            detail.append(points_text)
        if is_break_point(score):
            detail.append("BP")

        tournament = match.get("tournament") or ""
        round_name = match.get("round") or ""
        header = " - ".join(part for part in (tournament, round_name) if part)

        block = [f"{left} v {right.strip()}"]
        if header:
            block.insert(0, header)
        if detail:
            block.append("   " + "   ".join(detail))
        lines.append("\n".join(block))
    return lines

"""Pure decision functions: offset gating, profile completeness, delay
parsing, and the seek quiet-window policy.

Pure Python: no Kodi imports, no I/O. Callers resolve settings/state and pass
explicit values; these functions only decide.
"""

from resources.lib.aome.domain import formats


def parse_delay_ms(delay_str):
    """Parse Kodi's localized ``Player.AudioDelay`` string to ms, or None.

    Handles '-0.075 s', comma decimals ('-0,075 s'), a Unicode minus
    (U+2212, some CLDR locales), and narrow no-break spaces around the
    unit. Clamps to +/-10 s.

    Two non-obvious choices: a narrow no-break space (the CLDR unit
    separator) is normalized to a regular space before the unit is
    stripped, not deleted (deleting it would leave '-0.075s' for float);
    and the ms conversion rounds, since float('-0.115') * 1000 is
    -114.999... and truncation would report -114 for a -115 ms value.
    """
    try:
        normalized = (delay_str.replace('\u202f', ' ')  # narrow no-break space
                      .replace('\u2212', '-')  # Unicode minus sign (CLDR locales)
                      .replace(',', '.')
                      .strip())
        # Strip the trailing unit however it is separated: 's' never appears
        # inside a parseable number, so dropping one trailing 's' (plus any
        # remaining spaces) is unambiguous.
        if normalized.endswith('s'):
            normalized = normalized[:-1]
        normalized = normalized.replace(' ', '')
        delay_seconds = float(normalized)
        # Clamp to reasonable bounds (-10s to +10s) to avoid junk values
        delay_seconds = max(-10.0, min(delay_seconds, 10.0))
        return int(round(delay_seconds * 1000))
    except (ValueError, AttributeError):
        return None


def is_complete(profile):
    """True when the profile carries enough facts to key the store.

    The HDR axis always resolves (the detector defaults an absent reading
    to 'sdr'), so completeness means an audio format was reported and the
    fps rate parsed. Requiring fps keeps discovery patient while a stream's
    rate is still unreadable, and guarantees the per-fps write key is always
    composable for a complete profile.
    """
    if profile is None:
        return False
    return (profile.audio_format != formats.UNKNOWN
            and profile.hdr_type != formats.UNKNOWN
            and profile.video_fps is not None)


def stream_identity(profile, per_fps, distinct_spatial=True,
                    distinct_channels=False):
    """The "same stream" comparison key at the granularity that matters.

    Identity tracks the lookup key's granularity on every axis. With
    per_fps off the fps axis is excluded, so a VFR rate wiggle between
    gathers does not read as a stream change; with it on, the truncated
    rate is part of the identity. With distinct_spatial off the audio axis
    is the spatial base, so a track switch between a codec and its
    object-audio variant (same key, same offset) is not a stream change
    either. With distinct_channels on the normalized count joins the
    identity (an unusable count normalizes to None, matching the 'all'
    key both such profiles resolve to); off, a count wiggle is not a
    stream change.
    """
    audio = (profile.audio_format if distinct_spatial
             else formats.spatial_base(profile.audio_format))
    identity = [profile.hdr_type]
    if per_fps:
        identity.append(profile.fps_int())
    identity.append(audio)
    if distinct_channels:
        identity.append(profile.channels_int())
    return tuple(identity)


def seek_decision(now, requested_at, last_activity, last_own_seek,
                  quiet_window, deadline, yield_to_activity=False):
    """Decide one seek-back request: 'seek' | 'defer' | 'abandon' | 'yield'.

    The rule: do not seek until there has been no seek activity (ours,
    another addon's, or the user's) for ``quiet_window`` seconds; defer
    until then; give up ``deadline`` seconds after the request. A request
    already served by one of our own seeks (executed at or after the
    request; same-instant counts as served) is abandoned.

    ``yield_to_activity`` is the stronger rule for triggers an external
    actor may mirror (the scheduler passes it for 'unpause'): any seek
    activity at or after ``requested_at`` yields the request rather than
    deferring it, because someone else moved the playhead since the trigger
    and replaying would double their seek. Activity strictly before the
    request never yields (the quiet window handles it). The caller's
    activity view is a generic aggregate (SeekOccurred, the vendor busy
    list, our own seeks), never a specific addon.

    Args (timestamps monotonic; the caller resolves them):
        now: current time.
        requested_at: when this seek was requested.
        last_activity: most recent seek-like activity, including session
            start (which gives playback a settle window after start).
        last_own_seek: when we last executed a seek this session, or None.
        quiet_window: required quiet seconds before seeking.
        deadline: max seconds after requested_at before giving up.
        yield_to_activity: apply the yield rule above (default off).

    Verdicts are evaluated in a fixed order: served, yielded, deadline,
    quietness. Deadline before quietness means a request that aged out is
    abandoned even if the window is quiet now, since a very late replay
    would itself be disruptive. 'yield' is its own verdict so the caller's
    log can state why the replay stood down.
    """
    if last_own_seek is not None and last_own_seek >= requested_at:
        return 'abandon'
    if yield_to_activity and last_activity >= requested_at:
        return 'yield'
    if now - requested_at >= deadline:
        return 'abandon'
    if now - last_activity < quiet_window:
        return 'defer'
    return 'seek'


def should_apply(profile, apply_enabled):
    """Decide whether an offset may be applied for this profile.

    Applying requires the apply toggle (which gates applying only, never
    learning) and a profile complete enough to key the store.

    Args:
        profile: StreamProfile or None.
        apply_enabled: bool, the apply toggle (caller resolves it).

    Returns:
        (allowed, reason) — reason is None when allowed, else one of
        'apply_off', 'no_profile', 'unknown_format'.
    """
    if not apply_enabled:
        return False, 'apply_off'
    if profile is None:
        return False, 'no_profile'
    if not is_complete(profile):
        return False, 'unknown_format'
    return True, None

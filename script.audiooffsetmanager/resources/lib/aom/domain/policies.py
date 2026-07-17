"""Pure decision functions: offset gating, profile completeness, delay
parsing, and the seek quiet-window policy.

Pure Python: no Kodi imports, no I/O. Callers resolve settings/state and pass
explicit values; these functions only decide.
"""

from resources.lib.aom.domain import formats


def parse_delay_ms(delay_str):
    """Parse Kodi's localized `Player.AudioDelay` infolabel string to ms.

    Handles '-0.075 s', comma decimals ('-0,075 s'), a Unicode minus sign
    (U+2212, used by some CLDR locales), and narrow no-break spaces anywhere
    around the unit. Clamps to +/-10 s. Returns None on unparseable input.

    Two subtleties:

    - A narrow no-break space as the SOLE separator before the unit
      ('-0.075<U+202F>s', the CLDR unit-separator convention) parses:
      NNBSP is normalized to a regular space BEFORE the unit is stripped,
      so the number survives for float().
    - The ms conversion rounds instead of truncating: float('-0.115') * 1000
      is -114.999..., which a plain int() would give back as -114 for a
      slider value of -115 ms.
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
    """True when every axis of the profile was detected (no 'unknown')."""
    if profile is None:
        return False
    return formats.UNKNOWN not in (
        profile.hdr_type,
        str(profile.fps_type),
        profile.audio_format,
    )


def seek_decision(now, requested_at, last_activity, last_own_seek,
                  quiet_window, deadline):
    """The seek quiet-window policy, stated as one rule.

    Do not seek until there has been no seek activity — ours, another
    addon's, or the user's — for ``quiet_window`` seconds; defer otherwise;
    give up ``deadline`` seconds after the request. A request that another
    of our own seeks has already served (executed AT or AFTER the moment
    this request was made — same-instant counts as served, the safe side
    against a double rewind) is abandoned: its purpose — replaying the
    glitched seconds — is done.

    Args (all timestamps monotonic; the caller resolves them):
        now: current time.
        requested_at: when this seek was requested.
        last_activity: most recent seek-like activity — any SeekOccurred,
            vendor busy signal, our own executed seek, or session start
            (session start counting as activity is what gives the natural
            post-start settle without a bespoke constant).
        last_own_seek: when WE last executed a seek this session, or None.
        quiet_window: required quiet seconds before seeking.
        deadline: max seconds after requested_at before giving up.

    Returns:
        'seek' | 'defer' | 'abandon'. Deadline is checked before quietness:
        a request that aged past the deadline is abandoned even if the
        window happens to be quiet now.
    """
    if last_own_seek is not None and last_own_seek >= requested_at:
        return 'abandon'
    if now - requested_at >= deadline:
        return 'abandon'
    if now - last_activity < quiet_window:
        return 'defer'
    return 'seek'


def should_apply(profile, new_install, hdr_enabled):
    """Decide whether an offset may be applied for this profile.

    Args:
        profile: StreamProfile or None.
        new_install: bool — onboarding not completed yet.
        hdr_enabled: bool — the `enable_<hdr>` setting for profile.hdr_type
            (caller resolves it; pass False when profile is None).

    Returns:
        (allowed, reason) — reason is None when allowed, else one of
        'new_install', 'no_profile', 'unknown_format', 'hdr_disabled'.
    """
    if new_install:
        return False, 'new_install'
    if profile is None:
        return False, 'no_profile'
    if not is_complete(profile):
        return False, 'unknown_format'
    if not hdr_enabled:
        return False, 'hdr_disabled'
    return True, None

"""Lookup and write-key semantics for the sparse store.

This module is the key-schema decision table, and both rules are
deliberately trivial.

Lookup composes exactly ONE candidate key per call, ``<hdr>|<fps>|<audio>|
<ch>|<dev>``, each axis at the granularity its toggle asks for: off is the
literal 'all', on is the reported value (the truncated rate, the source
count, the device's id half), and the audio axis instead collapses a spatial
variant to its base codec when distinct-spatial is off. There is no fallback
between the levels, so the answer is exact or miss.

Flipping any toggle is non-destructive. The fps, channel and device modes
are symmetric for streams that carry the axis: axis-specific entries are
dormant while their toggle is off, ``all`` entries while it is on. The
spatial mode is one-sided, because a base-codec key is legitimate verbatim
in both modes.

Three degradation seams all mean "this stream has no such axis, so its
candidate IS the ``all`` key": an fps that cannot be parsed under the toggle
(defensive only, since completeness gating keeps unparseable rates out of
the apply path), an unusable channel count, and a device reading that names
none. The last two are handled inside their own segment functions,
identically for lookup and write, because nothing upstream screens either. A
device read that FAILED never arrives here at all: ``policies.is_complete``
rejects the profile, so the session keeps the device it is already keyed on
instead of collapsing onto the all-devices bucket.

A miss applies nothing unless the consulted key carries a reset marker,
meaning the user deleted it; ``reset_keys`` names it so the applier can
force the promised 0. A hit never carries a marker, since the store
supersedes a key's marker on set.

Write: one rule, no history-dependence. The write key is derived at store
instant from the current profile facts plus the current toggle, never
conditional on what a lookup hit.

Pure Python: composes ``keys`` and consumes an ``OffsetStore``-shaped object
(``get(key) -> entry | None``, ``reset_pending(key) -> bool``); no Kodi.
"""

from collections import namedtuple

from resources.lib.aome.store import keys

# hit_kind values (travel to logging and notification wording only).
EXACT = 'exact'
MISS = 'miss'

# entry: the stored dict, or None on a miss.
# hit_kind: EXACT / MISS.
# key: the key that hit, or None on a miss.
# tried: the consulted key as a 1-tuple, logged so a miss shows what missed.
# reset_keys: consulted keys carrying a pending reset marker; non-empty on a
#             miss means "force 0, not no-op". Defaulted to () so hand-built
#             Resolutions stay valid; resolve() always fills it.
class Resolution(namedtuple('Resolution',
                            ['entry', 'hit_kind', 'key', 'tried',
                             'reset_keys'],
                            defaults=((),))):
    __slots__ = ()

    @property
    def ms(self):
        """The stored ms, or None on a miss (keeps the entry dict shape
        inside the store package)."""
        if self.entry is None:
            return None
        return self.entry['delay_ms']


def resolve(store, hdr_raw, fps, audio_raw, channels=None, *, per_fps,
            distinct_spatial, distinct_channels, device=None,
            distinct_devices=False):
    """Look up the offset entry for the given stream facts; never raises.

    Exactly one candidate key per call, each axis composed at the
    granularity its toggle asks for. An unparseable fps under ``per_fps``
    degrades to the ``all`` key rather than turning a benign miss into an
    exception; the channel and device axes degrade inside their own segment
    functions and need no handling here.
    """
    if not per_fps:
        candidate = keys.all_key(hdr_raw, audio_raw,
                                 distinct_spatial=distinct_spatial,
                                 channels=channels,
                                 distinct_channels=distinct_channels,
                                 device=device,
                                 distinct_devices=distinct_devices)
    else:
        try:
            candidate = keys.profile_key(hdr_raw, fps, audio_raw,
                                         per_fps=True,
                                         distinct_spatial=distinct_spatial,
                                         channels=channels,
                                         distinct_channels=distinct_channels,
                                         device=device,
                                         distinct_devices=distinct_devices)
        except ValueError:
            # No fps axis on this stream: the all key IS its exact key.
            candidate = keys.all_key(hdr_raw, audio_raw,
                                     distinct_spatial=distinct_spatial,
                                     channels=channels,
                                     distinct_channels=distinct_channels,
                                     device=device,
                                     distinct_devices=distinct_devices)
    entry = store.get(candidate)
    if entry is not None:
        return Resolution(entry, EXACT, candidate, (candidate,), ())
    return Resolution(None, MISS, None, (candidate,),
                      _pending((candidate,), store))


def _pending(consulted, store):
    """The consulted keys carrying reset markers, in lookup order."""
    return tuple(key for key in consulted if store.reset_pending(key))


def write_key(hdr_raw, fps, audio_raw, channels=None, *, per_fps,
              distinct_spatial, distinct_channels, device=None,
              distinct_devices=False):
    """The single key a manual adjustment is stored under.

    Derived from the current profile facts and toggles at store time, never
    from lookup history, and degrading on the channel and device axes
    exactly as lookup does.
    """
    return keys.profile_key(hdr_raw, fps, audio_raw, per_fps=per_fps,
                            distinct_spatial=distinct_spatial,
                            channels=channels,
                            distinct_channels=distinct_channels,
                            device=device,
                            distinct_devices=distinct_devices)

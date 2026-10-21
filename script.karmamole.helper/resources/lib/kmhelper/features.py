# KarmaMole Skin Helper (script.karmamole.helper)
# Copyright (C) 2026 Omar Kamel
# SPDX-License-Identifier: GPL-2.0-or-later
"""Which features the helper runs, for which skin. The helper does nothing a skin didn't ask for.

A skin gets a feature in one of two ways (the union counts):
  1. SKIN_FEATURES below: the KarmaMole skins that use the helper, keyed on the running skin's id (xbmc.getSkinDir()).
  2. Opt in at run time: SetProperty(KarmaMole.Helper.Features,"colours,spines",home) (comma or space separated,
     case-insensitive; unknown names are ignored). Clear it to opt out. The service re-reads it once a second.

Features:
  colours   focused-item and playing-album colours (Groove.*, Groove.Player.*), RunScript action=colours
  softart   the soft-art / halo PNGs that go with the colours (Art.Soft, Art.SoftLight, Art.Halo); implies colours
  spines    album spine strips for the music library (Groove.Spines.*)
  queue     RunScript action=queue_move / queue_remove (Up next reordering)
  wheel     plugin:// genre / style / mood listings and the play_slice action
  shuffle   RunScript action=play_shuffled (random order built by the helper; Kodi shuffle state untouched)

With no features for the running skin the service only checks the skin and that property once a second.
On-demand calls (RunScript / plugin) for a feature the skin hasn't asked for are logged and ignored; a plugin listing
comes back empty. The decision is a pure function (resolve) so it is unit-tested without Kodi.
"""
FEATURES = ('colours', 'softart', 'spines', 'queue', 'wheel', 'shuffle')
IMPLIES = {'softart': ('colours',)}
OPT_IN = 'KarmaMole.Helper.Features'

SKIN_FEATURES = {
    'skin.groove': ('colours', 'softart', 'spines', 'queue', 'wheel', 'shuffle'),
}


def parse(text):
    """'Colours, spines nonsense' -> frozenset({'colours', 'spines'})."""
    out = set()
    for word in (text or '').replace(',', ' ').split():
        word = word.strip().lower()
        if word in FEATURES:
            out.add(word)
            out.update(IMPLIES.get(word, ()))
    return frozenset(out)


def resolve(skin_id, opt_in=''):
    """The features to run for this skin: its table entry plus whatever it opted in to."""
    return parse(' '.join(SKIN_FEATURES.get(skin_id or '', ()))) | parse(opt_in)


def active():
    """The features for the skin running right now (reads Kodi; cheap: one skin id + one property)."""
    import xbmc
    from .common import prop
    return resolve(xbmc.getSkinDir(), prop(OPT_IN))


def allowed(feature):
    """True when the running skin asked for this feature; logs a refusal so a missing opt-in is easy to spot."""
    if feature in active():
        return True
    import xbmc
    from .common import log
    log('feature %r is not on for skin %s (add it to Window(Home).Property(%s))'
        % (feature, xbmc.getSkinDir(), OPT_IN), xbmc.LOGINFO)
    return False

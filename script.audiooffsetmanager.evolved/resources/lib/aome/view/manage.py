"""ManageView: the script-process stored-offsets management surface.

Honours the store mutation channel's boundary from the view side:
inspection, delete/clear, and the copy that seeds Kodi's configured output
devices from another device's entries. No value entry exists anywhere here,
since offsets are learned during playback rather than typed, and it never
writes the store file, reading through the injected read-only reader and
asking the service to mutate over the channel.

The seam is four injected callables, wired by the script router:

* ``read_entries()`` returns a ``{key: entry}`` snapshot (each entry has
  ``delay_ms``, ``updated``, ``source``, optional ``video_fps`` and
  ``device_name``) and may raise :class:`StoreUnreadable`.
* ``gui`` is the plain-dialog surface (``select``/``yesno``/``ok`` plus
  ``localized``); ``select`` takes plain-string rows and/or
  ``(label, detail)`` tuples and returns the chosen index, -1 on cancel.
* ``send_mutation(op, key=None, device=None)`` posts one mutation over the
  channel and returns the service's ack dict, or ``None`` on timeout, which
  is the report-only "service not running" signal. There is no fallback
  write path.
* ``current_key()`` returns the canonical store key the service published
  for the live playback, or '' for "nothing playing".

``run()`` is a re-read-and-render loop: every pass reads the store fresh, so
a delete's effect is the next render. Values render verbatim, and the empty
state is the first-run education.

Navigation nests two index levels above the entry rows: output devices at the
top, HDR types inside the open device. A level that would hold a single
member does not exist, and that collapse is decided on GROUP counts rather
than entry counts, so a delete can never dissolve a level into a flat list
whose rows all share one name. Each level owns the clear whose scope it
represents.

Display is toggle-aware but never filtered: dormancy mirrors the lookup rule
(``_is_dormant``) and dormant rows are tagged rather than hidden, so
clear-all's confirmation never under-represents what it deletes. Two rows
never share a device label, because the service and this view resolve labels
through one function over the same entries; two TOASTS can still read alike,
which is an accepted width limit rather than something these rows pay for.

The entry matching ``current_key()`` is the playing row, re-read every pass.
A playing row is never dormant, and ``_build_rows`` enforces that because the
two states are read from different processes' toggle values.

Kodi label markup is applied at render time only, so the ``_Row`` strings
stay plain for the confirmations that reuse them. No color is hardcoded
beyond the dormant gray, since a fixed accent clashes with foreign skin
palettes, and bold degrades to regular weight on skins lacking a bold list
font, so no information lives in markup alone.
"""

from collections import namedtuple

from resources.lib.aome.domain.formats import DEVICE_ALL, spatial_base
from resources.lib.aome.store.keys import (AXIS_DEVICE, HDR_DISPLAY,
                                          describe_key, describe_key_in_group,
                                          device_labels, device_names,
                                          display_device, key_device, sort_key,
                                          split_key)
from resources.lib.aome.store.offset_store import StoreUnreadable

# Localized string ids owned by this view (defined in strings.po).
_HEADING = 32115           # "Manage stored offsets"
_MSG_EMPTY = 32122         # first-run education / empty store
_MSG_CONFIRM_DELETE = 32123
_MSG_CONFIRM_CLEAR = 32124
_MSG_NO_SERVICE = 32125    # ack timeout: service not running
_LABEL_CLEAR_ALL = 32126
_MSG_UNREADABLE = 32127    # StoreUnreadable (corrupt: will be quarantined)
_MSG_MUTATION_FAILED = 32128
_MSG_FUTURE = 32131        # StoreUnreadable(future=True): preserved, not shown
_LABEL_GROUP_ENTRY = 32135    # "{0} entry" — group-index count, singular
_LABEL_GROUP_ENTRIES = 32136  # "{0} entries" — group-index count, plural
_LABEL_OTHER_GROUP = 32137    # "Other" — the unsplittable-key bucket
_LABEL_CLEAR_GROUP = 32138    # the scoped clear row inside an open group
_MSG_CONFIRM_CLEAR_GROUP = 32139
_LABEL_INACTIVE = 32167       # "{0} — inactive" — the dormant row's value line
_LABEL_GROUP_INACTIVE = 32170  # "({0} inactive)" — group-row count suffix
_LABEL_PLAYING = 32172        # "{0} · playing now" — the playing row/group tag
_LABEL_PLAYING_MARK = 32174   # "» {0}" — playing row's list-only lead marker
_LABEL_CLEAR_DEVICE = 32181   # the scoped clear row inside an open device
_MSG_CONFIRM_CLEAR_DEVICE = 32182
_LABEL_COPY_DEVICE = 32185    # the copy row for the device in scope
_MSG_CONFIRM_COPY_DEVICE = 32186
_MSG_COPIED = 32187           # "Copied {0} to {1}" — count, destination label
_MSG_COPY_SAME_DEVICE = 32188
_MSG_COPY_ALL_PRESENT = 32189

# English fallbacks for strings that must never render blank, since
# localized() degrades to '' on a transient failure. Confirmations are absent
# because they carry the entry description alongside their text; the
# group-index strings are present because 'Other' is a row's entire label,
# the count templates are the only content beside the group name, and the
# inactive tag is the dormant row's whole explanation.
_FALLBACKS = {
    _MSG_EMPTY: ("Nothing is stored yet. Adjust Kodi's audio offset during "
                 "playback and the value will be saved for that stream "
                 "profile."),
    _MSG_NO_SERVICE: ("The Audio Offset Manager service is not running. "
                      "The change could not be made."),
    _MSG_UNREADABLE: ("The stored offsets file is unreadable. The service "
                      "will quarantine and reset it the next time it "
                      "starts."),
    _MSG_MUTATION_FAILED: "Could not update the stored offsets",
    _MSG_FUTURE: ("The stored offsets were saved by a newer version of "
                  "this addon. They are preserved untouched, but this "
                  "version cannot show or change them."),
    _LABEL_GROUP_ENTRY: "{0} entry",
    _LABEL_GROUP_ENTRIES: "{0} entries",
    _LABEL_OTHER_GROUP: "Other",
    _LABEL_CLEAR_GROUP: "Clear all offsets in this group",
    _MSG_CONFIRM_CLEAR_GROUP: "Delete all stored offsets in this group?",
    _LABEL_CLEAR_DEVICE: "Clear all offsets for this device",
    _MSG_CONFIRM_CLEAR_DEVICE: "Delete all stored offsets for this device?",
    _LABEL_COPY_DEVICE: "Copy these offsets to the current audio output",
    _MSG_CONFIRM_COPY_DEVICE: ("Copy these offsets to the current audio "
                               "output? Offsets already stored there are "
                               "kept."),
    _MSG_COPIED: "Copied {0} to {1}",
    _MSG_COPY_SAME_DEVICE: ("These offsets already belong to the current "
                            "audio output."),
    _MSG_COPY_ALL_PRESENT: ("The current audio output already has an offset "
                            "for every one of these. Nothing was copied."),
    _LABEL_INACTIVE: "{0} — inactive",
    _LABEL_GROUP_INACTIVE: "({0} inactive)",
    _LABEL_PLAYING: "{0} · playing now",
    _LABEL_PLAYING_MARK: "» {0}",
}

# The copy outcomes this view words itself; every other detail reports
# through the generic mutation failure.
_COPY_REFUSALS = {
    'same_device': _MSG_COPY_SAME_DEVICE,
    'all_present': _MSG_COPY_ALL_PRESENT,
}

# One presentable entry, rendered for every level at build time so no string
# depends on navigation state read a pass later: the full profile line, the
# in-group line (codec leading, HDR dropped), the value line with and
# without the device name, the literal store key the delete targets, and the
# dormancy/playing flags. The 'short' pair is what a heading above the row
# already states, and the level picks. All strings stay plain, since markup
# is a list-render concern and these feed confirmations too.
_Row = namedtuple("_Row",
                  "describe short detail short_detail key dormant playing")

# The device never renders on a profile line in this view: it rides the
# value line as secondary text (see _detail), so every label omits it.
_LABEL_OMIT = frozenset((AXIS_DEVICE,))

# Kodi label markup for the list renders. [B] needs the skin's bold list
# font and silently renders regular weight without one, which is fine since
# no markup carries information the text does not.
_DIM = "[COLOR gray]{0}[/COLOR]"
_BOLD = "[B]{0}[/B]"


def _noop(_message):
    return None


def _dormant_count(rows):
    """How many of these rows are dormant (an index row's inactive share)."""
    return sum(1 for row in rows if row.dormant)


def _copy_destinations(records):
    """A copy ack's destination records that can state a result line.

    The ack arrives over the untrusted mutation channel, so a record counts
    only when both fields its line renders are the type it renders: a named
    device and an integer count (bool excluded, an int subclass).
    """
    if not isinstance(records, list):
        return []
    return [record for record in records
            if isinstance(record, dict)
            and isinstance(record.get("device"), str)
            and record["device"].strip()
            and isinstance(record.get("count"), int)
            and not isinstance(record.get("count"), bool)]


class ManageView:
    """Inspect + delete/clear stored offsets from the script process."""

    def __init__(self, read_entries, gui, send_mutation, *, per_fps=False,
                 distinct_spatial=False, distinct_channels=False,
                 distinct_devices=False, current_key=None, log_debug=None):
        """The granularity toggles are read at launch and cannot change while
        the view is open. They drive display only: how an 'all' segment
        renders, and which rows carry the inactive tag. They never filter,
        since this view is the store's only inspection surface.

        ``current_key`` defaults to "nothing playing", so a caller without
        that seam renders plain.
        """
        self._read_entries = read_entries
        self._gui = gui
        self._send_mutation = send_mutation
        self._per_fps = bool(per_fps)
        self._distinct_spatial = bool(distinct_spatial)
        self._distinct_channels = bool(distinct_channels)
        self._distinct_devices = bool(distinct_devices)
        self._current_key = current_key or (lambda: '')
        self._log = log_debug or _noop
        # The open drill-down, one field per index level: a device segment
        # and an hdr segment (or _OTHER_GROUP), each None when that level is
        # not open. Held on the instance so the per-pass methods share one
        # navigation state.
        self._device = None
        self._group = None
        # The only device in a store that spans one, held because the device
        # level collapses away without opening and the copy row still names
        # it as a source. None whenever that level exists.
        self._sole_device = None
        # Device segment -> friendly name, and segment -> display label,
        # rebuilt per pass: naming a device needs the entries' device_name
        # metadata, which the index levels have no key in hand to reach, AND
        # the whole set, since a name two devices share is disambiguated
        # against its siblings. The names are kept because a copy's
        # destination has to be labelled against them.
        self._device_names = {}
        self._device_labels = {}
        # The published playing key ('' = none), refreshed per pass.
        self._current = ''

    # -- entry point ----------------------------------------------------------

    def run(self):
        """Read, render, and act on one user choice per pass until they exit."""
        heading = self._gui.localized(_HEADING)
        self._device = None
        self._group = None
        while True:
            try:
                entries = self._read_entries()
            except StoreUnreadable as error:
                self._log("AOMe_ManageView: store unreadable ({0})".format(error))
                # A newer-schema file is preserved by the service rather than
                # quarantined, so its wording must not promise the reset the
                # corrupt case gets.
                message = _MSG_FUTURE if getattr(error, 'future', False) \
                    else _MSG_UNREADABLE
                self._gui.ok(heading, self._text(message))
                return

            self._current = self._current_key() or ''

            if not entries:
                self._log("AOMe_ManageView: store empty; nothing to manage")
                self._gui.ok(heading, self._text(_MSG_EMPTY))
                return

            rows = self._build_rows(entries)
            self._log("AOMe_ManageView: rendering {0} stored offset(s)"
                      .format(len(rows)))

            if self._device_level(heading, rows) is _CLOSE:
                return

    # -- levels (routing one pass to the render the state names) --------------

    def _device_level(self, heading, rows):
        """Route one render past the device level: its index, or straight
        through when the store holds a single device.

        Collapse is re-derived every pass from the member count, never the
        entry count, and is asked only while the level is closed: an open
        device survives external mutations that leave it the only one, and
        only an open device that EMPTIED falls back to the top level.
        """
        if self._device is None:
            devices = self._device_index(rows)
            if len(devices) > 1:
                # No group can be open above an open device index, so an
                # external write that grows this level drops one.
                self._sole_device = None
                self._group = None
                return self._device_index_pass(heading, devices)
            self._sole_device = devices[0][0]
            return self._hdr_level(heading, rows, whole_store=True)
        self._sole_device = None
        device_rows = [row for row in rows
                       if self._device_of(row.key) == self._device]
        if not device_rows:
            self._log("AOMe_ManageView: open device emptied; "
                      "returning to the top level")
            self._device = None
            self._group = None
            return None
        return self._hdr_level(heading, device_rows,
                               whole_store=len(device_rows) == len(rows))

    def _hdr_level(self, heading, device_rows, *, whole_store):
        """Route one render past the HDR level, within the open device or,
        when there is only one device, the whole store.

        Same collapse rule as the device level, asked PER DEVICE.
        ``whole_store`` says whether these rows are the entire store, which
        a scoped clear needs in order to exit as quietly as clear-all does.
        """
        if self._group is None:
            groups = self._group_index(device_rows)
            if len(groups) > 1:
                return self._index_pass(heading, groups, device_rows,
                                        whole_store=whole_store)
            if self._device is None:
                return self._flat_pass(heading, device_rows)
            return self._device_rows_pass(heading, device_rows,
                                          whole_store=whole_store)
        group_rows = [row for row in device_rows
                      if self._group_of(row.key) == self._group]
        if not group_rows:
            self._log("AOMe_ManageView: open group emptied; "
                      "returning to the level above")
            self._group = None
            return None
        return self._group_pass(
            heading, group_rows,
            whole_store=whole_store and len(group_rows) == len(device_rows))

    # -- passes (one render + at most one user action each) -------------------

    def _flat_pass(self, heading, rows):
        """The single-list render: every entry as a two-line row + clear-all."""
        # Cancel/Back is the exit; the router then reopens the settings
        # dialog the manage button closed.
        choice = self._select_rows(heading, rows, _LABEL_CLEAR_ALL,
                                   extra=self._copy_rows())
        if choice < 0:
            return _CLOSE
        if choice == len(rows):
            return self._settle(heading, self._confirm_clear(heading))
        if choice > len(rows):
            return self._confirm_copy(heading, rows)
        return self._settle(heading,
                            self._confirm_delete(heading, rows[choice]))

    def _device_index_pass(self, heading, devices):
        """The device index: one single-line row per output device, plus
        clear-all.

        ``devices`` is the ordered ``(segment, count, inactive, playing)``
        list. This is the top level whenever the store spans more than one
        device, so clear-all lives here, where the whole store is
        represented.
        """
        self._log("AOMe_ManageView: rendering device index ({0} device(s))"
                  .format(len(devices)))
        options = [self._device_row(segment, count, inactive,
                                    emphasize=True, playing=playing)
                   for segment, count, inactive, playing in devices]
        options.append(self._gui.localized(_LABEL_CLEAR_ALL))

        choice = self._gui.select(heading, options)
        if choice < 0:
            return _CLOSE
        if choice == len(devices):
            return self._settle(heading, self._confirm_clear(heading))
        self._device = devices[choice][0]
        # The id SEGMENT, never _device_name: the friendly half routinely
        # carries a person's name on a Bluetooth endpoint, and the log export
        # redacts paths and URL credentials rather than names.
        self._log("AOMe_ManageView: opened device {0!r}".format(self._device))
        return None

    def _index_pass(self, heading, groups, device_rows, *, whole_store):
        """The group index: one single-line row per HDR type, plus a scoped
        clear.

        ``groups`` is the ordered ``(segment, count, inactive, playing)``
        list for whichever device is open. The clear row states this level's
        own scope: the whole store when this IS the top level, otherwise the
        open device, whose subtree is exactly ``device_rows``. Back unwinds
        one level, to the device index or out of the view at the top.
        """
        self._log("AOMe_ManageView: rendering group index ({0} group(s))"
                  .format(len(groups)))
        top = self._device is None
        options = [self._group_row(segment, count, inactive,
                                   emphasize=True, playing=playing)
                   for segment, count, inactive, playing in groups]
        options.append(self._gui.localized(
            _LABEL_CLEAR_ALL if top else _LABEL_CLEAR_DEVICE))
        options.extend(self._copy_rows())

        choice = self._gui.select(
            heading if top else self._device_name(self._device), options)
        if choice < 0:
            if top:
                return _CLOSE
            self._device = None
            return None
        if choice == len(groups):
            if top:
                return self._settle(heading, self._confirm_clear(heading))
            return self._clear_device(heading, device_rows,
                                      whole_store=whole_store)
        if choice > len(groups):
            return self._confirm_copy(heading, device_rows)
        self._group = groups[choice][0]
        self._log("AOMe_ManageView: opened group {0}"
                  .format(self._group_name(self._group)))
        return None

    def _device_rows_pass(self, heading, rows, *, whole_store):
        """One open device's entries, where the HDR level collapsed.

        The list is headed by the device name and its scoped clear is the
        device's rather than a group's: the two would delete the same set
        here, but the level the user is standing in is the device.
        """
        choice = self._select_rows(self._device_name(self._device), rows,
                                   _LABEL_CLEAR_DEVICE,
                                   extra=self._copy_rows())
        if choice < 0:
            self._device = None
            return None
        if choice == len(rows):
            return self._clear_device(heading, rows, whole_store=whole_store)
        if choice > len(rows):
            return self._confirm_copy(heading, rows)
        return self._settle(heading,
                            self._confirm_delete(heading, rows[choice]))

    def _group_pass(self, heading, group_rows, *, whole_store):
        """One open group's entries; Back returns to the level above.

        The select is headed by the group name, prefixed by the device when
        one is open, since the row copy drops both. Confirmations keep the
        main heading and the full profile line.
        """
        # The whole-store clear-all stays at the top level, so the set THIS
        # row deletes is exactly the list above it.
        choice = self._select_rows(
            self._path_heading(self._group_name(self._group)), group_rows,
            _LABEL_CLEAR_GROUP)
        if choice < 0:
            self._group = None
            return None
        if choice == len(group_rows):
            return self._clear_scope(
                heading, group_rows, _MSG_CONFIRM_CLEAR_GROUP,
                self._group_row(self._group, len(group_rows),
                                _dormant_count(group_rows)),
                "group {0!r}".format(self._group_segment()),
                whole_store=whole_store)
        return self._settle(heading,
                            self._confirm_delete(heading, group_rows[choice]))

    def _select_rows(self, select_heading, rows, clear_label, extra=()):
        """Render one entry list plus its scoped clear row and return the
        choice: an index into ``rows``, ``len(rows)`` for the clear row,
        beyond that an ``extra`` action row, or -1 for Back."""
        options = [self._list_row(row) for row in rows]
        options.append(self._gui.localized(clear_label))
        options.extend(extra)
        return self._gui.select(select_heading, options)

    def _copy_rows(self):
        """The copy row for the device in scope, or nothing at all.

        Absent with distinct-device offsets off, where every entry a copy
        wrote would be dormant and the success dialog would contradict the
        inactive tags on screen. Absent too where no real device is in
        scope, the all-devices bucket holding what a device-less read
        resolves to rather than one device's offsets.
        """
        if not self._distinct_devices or self._copy_source() is None:
            return []
        return [self._gui.localized(_LABEL_COPY_DEVICE)]

    def _copy_source(self):
        """The device segment a copy would name, or None where none is in
        scope: the open device, or the store's only one where that level
        collapsed."""
        segment = self._device if self._device is not None \
            else self._sole_device
        if segment is None or segment == DEVICE_ALL:
            return None
        return segment

    def _clear_device(self, heading, device_rows, *, whole_store):
        """The open device's scoped clear, from either level it can be
        reached from (its group index, or its rows when that level
        collapsed)."""
        return self._clear_scope(
            heading, device_rows, _MSG_CONFIRM_CLEAR_DEVICE,
            self._device_row(self._device, len(device_rows),
                             _dormant_count(device_rows)),
            "device {0!r}".format(self._device),
            whole_store=whole_store)

    def _clear_scope(self, heading, rows, message_id, scope_row, scope_log, *,
                     whole_store):
        """Batch-delete every entry of an open level: a device or a group.

        Looped single deletes over the existing channel, so the whitelist is
        untouched. ``rows`` is exactly the list the level rendered, so a
        scope deletes its own subtree and nothing else, and the confirmation
        restates the scope as its index row did. Per-delete semantics mirror
        the single-delete flow: a 'missing' ack is satisfied intent and the
        batch continues, while a timeout or hard failure reports once and
        stops. Clearing a scope that was the entire store exits quietly like
        clear-all.

        ``scope_log`` is the caller's key-segment naming of the same scope.
        The log line must not reuse ``scope_row``, which carries the device's
        friendly name.
        """
        message = self._text(message_id) + "\n" + scope_row
        if not self._gui.yesno(heading, message):
            return None
        self._log("AOMe_ManageView: clearing {0} ({1} entries)"
                  .format(scope_log, len(rows)))
        for row in rows:
            ack = self._send_mutation("delete", row.key)
            if ack is None or (not ack.get("ok")
                               and ack.get("detail") != "missing"):
                self._report_ack(heading, ack)
                return None
        if whole_store:
            self._log("AOMe_ManageView: store cleared; closing view")
            return _CLOSE
        return None

    def _settle(self, heading, ack):
        """Post-confirmation tail shared by every pass.

        A declined confirmation just loops and a real ack is reported. A
        deliberate clear closes the view, since looping would land on the
        first-run empty state right after the user emptied the store.
        """
        if ack is _DECLINED:
            return None
        self._report_ack(heading, ack)
        if ack is not None and ack.get("ok") and ack.get("op") == "clear":
            self._log("AOMe_ManageView: store cleared; closing view")
            return _CLOSE
        return None

    # -- rendering ------------------------------------------------------------

    def _build_rows(self, entries):
        """Rows for every entry, in the grouped display order.

        ``keys.sort_key`` groups by device, then HDR type, then codec, then
        rate, and is total even over hand-edited keys. Dormancy then splits
        each device+HDR bucket in two, the active rows first and the dormant
        ones below, each stratum keeping the codec/rate order; the split
        stays inside the bucket, so dormancy never moves an entry between
        HDR groups. The playing row alone outranks everything, hoisted
        globally so its first appearance leads both index levels.

        Both value lines are built here, with and without the device name,
        so which one a level shows is a render choice rather than a string
        rebuilt from navigation state read a pass later.
        """
        rows = []
        ranks = {}
        # THE label rule, over every device the store knows. The toast names
        # the live device from the same function over the same entries
        # (``OffsetTable.device_label``), so the two cannot disagree.
        self._device_names = device_names(entries)
        self._device_labels = device_labels(self._device_names)
        for key, entry in entries.items():
            dormant = self._is_dormant(key)
            # A dormant row never claims playing. The pair can arise from a
            # mid-flip race where the service published the other mode's key
            # for one pass, and from the channel/device degradation seam,
            # where an unusable count or an unreadable device makes 'all' the
            # current mode's own write key while this view still tags it
            # dormant. The two tags would contradict each other, so dormancy
            # wins.
            playing = (bool(self._current) and key == self._current
                       and not dormant)
            device = self._device_of(key)
            rows.append(_Row(self._describe(key, entry),
                             self._describe_short(key, entry),
                             self._detail(entry, self._device_label(device),
                                          inactive=dormant, playing=playing),
                             self._detail(entry, None, inactive=dormant,
                                          playing=playing),
                             key,
                             dormant,
                             playing))
            # The device rank needs the device's label, which the _Row does
            # not carry, so the sort tuples are built here where both are in
            # hand. Ranking by the label the whole view uses keeps one
            # device's rows contiguous even where only some carry the
            # metadata.
            ranks[key] = sort_key(key,
                                  device_label=self._device_labels.get(device))

        def display_order(row):
            device, hdr, audio, fps_rank, ch_rank, raw = ranks[row.key]
            return (not row.playing, device, hdr, row.dormant, audio,
                    fps_rank, ch_rank, raw)

        rows.sort(key=display_order)
        return rows

    def _list_row(self, row):
        """One two-line select option for the level now open.

        The level's own heading decides which of the row's two label and
        value lines render, so neither the HDR name nor the device name is
        repeated below a heading that states it. Markup and the marker live
        here rather than in the ``_Row`` strings, which confirmations reuse
        unstyled. Both lines style together, since half a styled row would
        read as two states; the marker is a lead-in on the label rather than
        a style, so it stays off the value line. The branches cannot collide,
        because a playing row is never dormant.
        """
        label = row.short if self._group is not None else row.describe
        detail = row.short_detail if self._device is not None else row.detail
        if row.dormant:
            return (_DIM.format(label), _DIM.format(detail))
        if row.playing:
            return (_BOLD.format(self._template(_LABEL_PLAYING_MARK, label)),
                    _BOLD.format(detail))
        return (label, detail)

    def _is_dormant(self, key):
        """True for an entry the lookup will not consult right now.

        Dormancy mirrors the lookup rule per axis. The fps, channel and
        device rules are symmetric: with a toggle off only the 'all' key is
        read, so an axis-specific entry is dormant, and with it on only the
        specific key is read, so an 'all' entry is dormant. Channels and
        devices share one exception the tag accepts: a stream reporting no
        usable count, or a device reading that names none, still consults the
        'all' key. The spatial rule is one-sided, a base-codec key being
        legitimate in both modes. Rows are tagged rather than hidden, since
        hiding would misstate clear-all's scope, and unsplittable keys are
        never tagged.
        """
        try:
            _hdr, fps_segment, audio_segment, ch_segment, device_segment = \
                split_key(key)
        except ValueError:
            return False
        if not self._distinct_spatial and \
                spatial_base(audio_segment) != audio_segment:
            return True
        # Symmetric axes: the 'all' side sleeps with the toggle on, the
        # specific side with it off.
        if (ch_segment == 'all') == self._distinct_channels:
            return True
        if (device_segment == 'all') == self._distinct_devices:
            return True
        if self._per_fps:
            return fps_segment == 'all'
        return fps_segment != 'all'

    def _describe(self, key, entry):
        """The full profile line (top-level rows, delete confirmations)."""
        return self._render_key(describe_key, key, entry)

    def _describe_short(self, key, entry):
        """The in-group row label: the HDR group name is redundant there,
        so the codec leads and the rate follows."""
        return self._render_key(describe_key_in_group, key, entry)

    def _render_key(self, describe_fn, key, entry):
        """One describe function plus the verbatim fallback, written once.

        A key that does not split into five segments raises, and verbatim
        acceptance means it is shown as itself rather than crashing the view.
        The entry's ``video_fps`` metadata renders the exact reported rate
        for per-fps keys. No device label is passed, because the device axis
        is omitted from every label and renders on the value line instead.
        """
        try:
            return describe_fn(key, video_fps=entry.get("video_fps"),
                               per_fps=self._per_fps,
                               distinct_channels=self._distinct_channels,
                               distinct_devices=self._distinct_devices,
                               omit_axes=_LABEL_OMIT)
        except ValueError:
            return key

    def _detail(self, entry, device, *, inactive, playing=False):
        """The value line ('-115 ms · Living Room Soundbar'), run through the
        localized playing/inactive templates as flagged.

        The verbatim signed value leads and the device name follows as
        secondary text when the caller passes one; the store's
        source/updated metadata stays in the file but out of the row. The
        two states are mutually exclusive, so at most one template wraps.
        """
        delay = entry.get("delay_ms")
        sign = "+" if isinstance(delay, int) and delay > 0 else ""
        detail = "{0}{1} ms".format(sign, delay)
        if device:
            detail += " · " + device
        if playing:
            detail = self._template(_LABEL_PLAYING, detail)
        if inactive:
            detail = self._template(_LABEL_INACTIVE, detail)
        return detail

    # -- grouping -------------------------------------------------------------

    @staticmethod
    def _group_of(key):
        """The index bucket for a key: its hdr segment, or the Other bucket.

        A key that does not split still lists, counts, and deletes; it just
        cannot claim an HDR group. A splittable key with a blank hdr segment
        (hand-edited) joins the same bucket, since a nameless group row
        represents nothing.
        """
        try:
            hdr = split_key(key)[0]
        except ValueError:
            return _OTHER_GROUP
        return hdr if hdr.strip() else _OTHER_GROUP

    @staticmethod
    def _device_of(key):
        """The device bucket for a key (``keys.key_device``).

        Shared with the label rule's input collection rather than re-derived
        here. A key that does not split, or one whose device segment is
        blank, joins the all-devices bucket rather than forming one of its
        own, which is where a device-less read resolves and why this level
        needs no 'Other' bucket. It also keeps a store that never met the
        toggle at one device, where the whole level collapses away.
        """
        return key_device(key)

    @staticmethod
    def _tally(rows, bucket_of):
        """Ordered ``(bucket, count, inactive, playing)`` quads, one per
        bucket, in first-appearance order.

        Rows arrive display-sorted, so first appearance yields the same order
        the rows themselves scan in, and the hoisted playing row's bucket
        leads. Counts include dormant rows, so every stored entry is
        countable from an index.
        """
        order = []
        counts = {}
        inactive = {}
        playing = {}
        for row in rows:
            bucket = bucket_of(row.key)
            if bucket not in counts:
                order.append(bucket)
                counts[bucket] = 0
                inactive[bucket] = 0
                playing[bucket] = False
            counts[bucket] += 1
            inactive[bucket] += 1 if row.dormant else 0
            playing[bucket] = playing[bucket] or row.playing
        return order, counts, inactive, playing

    def _group_index(self, rows):
        """Ordered quads for the group index: HDR display order (the flat
        list's own), with the Other bucket forced last."""
        order, counts, inactive, playing = self._tally(rows, self._group_of)
        if _OTHER_GROUP in counts:
            order.remove(_OTHER_GROUP)
            order.append(_OTHER_GROUP)
        return [(segment, counts[segment], inactive[segment],
                 playing[segment])
                for segment in order]

    def _device_index(self, rows):
        """Ordered quads for the device index: 'all' first, then device
        labels alphabetically.

        Counts aggregate a device's whole subtree, so the index never
        under-represents what its scoped clear deletes. There is no
        forced-last bucket, since every key claims a device.
        """
        order, counts, inactive, playing = self._tally(rows, self._device_of)
        return [(segment, counts[segment], inactive[segment],
                 playing[segment])
                for segment in order]

    def _group_name(self, segment):
        """Display name for a group row/heading; verbatim for a stranger."""
        if segment is _OTHER_GROUP:
            return self._text(_LABEL_OTHER_GROUP)
        return HDR_DISPLAY.get(segment, segment)

    def _group_segment(self):
        """The open group's key segment, for logs (the bucket sentinel is
        an object, so it names itself)."""
        if self._group is _OTHER_GROUP:
            return 'other'
        return self._group

    def _device_label(self, segment):
        """A row's own device label: the axis's omission rule (it vanishes
        with the axis) applied to the label the whole view knows."""
        return display_device(segment, self._device_labels.get(segment),
                              self._distinct_devices)

    def _device_name(self, segment):
        """A device index row's or heading's name, stated in either
        granularity mode, since a store can hold several devices either way
        and a nameless index row represents nothing."""
        return display_device(segment, self._device_labels.get(segment), True)

    def _destination_labels(self, destinations):
        """Label the devices a copy's ack names, by the rule the rows use.

        The ack carries each destination's segment and the friendly name
        Kodi reported for it. That name is folded in only where the store
        knows no name for the segment, exactly as the toast's
        ``keys.device_label_for`` does, since a device the copy just seeded
        had no entry when this pass read the store. Labelling the whole set
        is what keeps a result line from naming a device a listed row
        already names.
        """
        names = dict(self._device_names)
        for destination in destinations:
            names.setdefault(destination.get("device"),
                             destination.get("name"))
        labels = device_labels(names)
        return [display_device(destination.get("device"),
                               labels.get(destination.get("device")), True)
                for destination in destinations]

    def _path_heading(self, name):
        """A drill-down heading, carrying the open device ahead of it.

        The device level's own heading is just the device name; one level
        deeper it states both, so nothing the rows dropped goes unsaid.
        """
        if self._device is None:
            return name
        return "{0} · {1}".format(self._device_name(self._device), name)

    def _index_row(self, name, count, inactive=0, *, emphasize=False,
                   playing=False):
        """One index row: 'Dolby Vision — 6 entries (2 inactive)'.

        The inactive suffix appears only when the bucket has dormant
        entries, and the count always states the total, so the suffix splits
        it rather than replacing it. ``emphasize`` bolds the name against its
        count, except for the playing bucket, whose whole row bolds in a
        single wrap because nested ``[B]`` tags would end the bold at the
        inner close tag. The scoped-clear confirmations reuse this row plain.
        """
        counted = self._counted(count)
        if inactive:
            counted += " " + self._template(_LABEL_GROUP_INACTIVE, inactive)
        if playing:
            counted = self._template(_LABEL_PLAYING, counted)
        if emphasize and playing:
            return _BOLD.format(self._template(
                _LABEL_PLAYING_MARK, "{0} — {1}".format(name, counted)))
        if emphasize:
            name = _BOLD.format(name)
        return "{0} — {1}".format(name, counted)

    def _counted(self, count):
        """A localized entry count: '1 entry' or '6 entries'."""
        return self._template(
            _LABEL_GROUP_ENTRY if count == 1 else _LABEL_GROUP_ENTRIES, count)

    def _group_row(self, segment, count, inactive=0, *, emphasize=False,
                   playing=False):
        """One HDR index row (see ``_index_row``)."""
        return self._index_row(self._group_name(segment), count, inactive,
                               emphasize=emphasize, playing=playing)

    def _device_row(self, segment, count, inactive=0, *, emphasize=False,
                    playing=False):
        """One device index row (see ``_index_row``)."""
        return self._index_row(self._device_name(segment), count, inactive,
                               emphasize=emphasize, playing=playing)

    # -- actions --------------------------------------------------------------

    def _confirm_delete(self, heading, row):
        # Both row lines, and always the full describe line plus the
        # device-carrying value line rather than the shortened copies the
        # open level renders, so what is deleted reads the same from every
        # level.
        message = (self._gui.localized(_MSG_CONFIRM_DELETE)
                   + "\n" + row.describe + "\n" + row.detail)
        if not self._gui.yesno(heading, message):
            return _DECLINED
        self._log("AOMe_ManageView: requesting delete of {0}".format(row.key))
        return self._send_mutation("delete", row.key)

    def _confirm_clear(self, heading):
        if not self._gui.yesno(heading, self._gui.localized(_MSG_CONFIRM_CLEAR)):
            return _DECLINED
        self._log("AOMe_ManageView: requesting clear of all stored offsets")
        return self._send_mutation("clear")

    def _confirm_copy(self, heading, device_rows):
        """The copy row: seed Kodi's output devices from the device in scope.

        The confirmation restates the scope as the device index row does.
        The destinations are named only in the result, since they are
        whatever Kodi is configured for when the service runs the copy and
        this process never resolves them.
        """
        source = self._copy_source()
        message = (self._text(_MSG_CONFIRM_COPY_DEVICE) + "\n"
                   + self._device_row(source, len(device_rows),
                                      _dormant_count(device_rows)))
        if not self._gui.yesno(heading, message):
            return None
        self._log("AOMe_ManageView: requesting copy of device {0!r} "
                  "({1} entries)".format(source, len(device_rows)))
        self._report_copy(
            heading, self._send_mutation("copy_device", device=source))
        return None

    def _report_copy(self, heading, ack):
        """Surface a copy's own outcomes; the rest report as any mutation does.

        A success is stated rather than left to the refreshed list, because
        the copy is the one action whose effect lands where the open level
        does not show it: on the destinations the ack names, one line each.
        A success naming none of them renderably reports as any mutation
        does, since a blank dialog states less than nothing.
        """
        destinations = _copy_destinations(
            ack.get("devices") if ack is not None else None)
        if ack is not None and ack.get("ok") and destinations:
            self._log("AOMe_ManageView: copied {0} entries to {1} device(s)"
                      .format(ack.get("count"), len(destinations)))
            self._gui.ok(heading, "\n".join(
                self._template(_MSG_COPIED,
                               self._counted(destination["count"]), label)
                for destination, label
                in zip(destinations, self._destination_labels(destinations))))
            return
        detail = ack.get("detail") if ack is not None else None
        if isinstance(detail, str) and detail in _COPY_REFUSALS:
            self._log("AOMe_ManageView: copy refused ({0})".format(detail))
            self._gui.ok(heading, self._text(_COPY_REFUSALS[detail]))
            return
        self._report_ack(heading, ack)

    def _report_ack(self, heading, ack):
        """Surface a failed/absent ack; a success just falls through to re-read."""
        if ack is None:
            self._log("AOMe_ManageView: no ack (service not running)")
            self._gui.ok(heading, self._text(_MSG_NO_SERVICE))
            return
        if not ack.get("ok"):
            detail = ack.get("detail")
            if detail == "missing":
                # Already gone, raced away by playback learning or another
                # session. Intent is satisfied, so the refreshed list is the
                # feedback rather than an error dialog.
                self._log("AOMe_ManageView: delete target already gone")
                return
            self._log("AOMe_ManageView: mutation refused ({0})".format(detail))
            self._gui.ok(
                heading,
                self._text(_MSG_MUTATION_FAILED)
                + " (" + str(detail) + ")")
            return
        self._log("AOMe_ManageView: mutation ok ({0})".format(ack.get("detail")))

    def _text(self, string_id):
        """localized() with the English fallback for must-never-blank strings."""
        return self._gui.localized(string_id) or _FALLBACKS[string_id]

    def _template(self, string_id, *values):
        """A format template with translation guards, shared in shape with
        the transfer view: a translation missing any expected ``{0}..{n}``
        placeholder degrades to the English fallback rather than silently
        swallowing the value, and one malformed enough to raise degrades too.
        The except is deliberately broad, since which exception a bad
        template raises is the translator's choice.
        """
        template = self._text(string_id)
        if any('{' + str(index) + '}' not in template
               for index in range(len(values))):
            template = _FALLBACKS[string_id]
        try:
            return template.format(*values)
        except Exception:
            return _FALLBACKS[string_id].format(*values)


# Private unique objects, so they can never collide with real values.
# _DECLINED distinguishes "user declined the confirmation" from a real ack,
# which may itself be None on timeout; _CLOSE tells run() the view is done;
# _OTHER_GROUP is the index bucket for keys that do not split, an object so
# no hdr segment string can shadow it.
_DECLINED = object()
_CLOSE = object()
_OTHER_GROUP = object()

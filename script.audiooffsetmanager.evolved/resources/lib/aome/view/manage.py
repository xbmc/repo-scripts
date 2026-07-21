"""ManageView: the script-process stored-offsets management surface.

Runs in the script process and honours the store mutation channel's boundary
from the view side: inspection plus delete/clear only. No value entry exists
anywhere here (offsets are learned during playback, never typed), and it
never writes the store file. It reads the file through the injected read-only
reader and asks the service to mutate over the channel.

The seam is four injected callables, wired by the script router:

* ``read_entries()`` returns a ``{key: entry}`` snapshot (each entry has
  ``delay_ms``, ``updated``, ``source``, optional ``video_fps``) and may
  raise :class:`StoreUnreadable`.
* ``gui`` is the plain-dialog surface (``select``/``yesno``/``ok`` +
  ``localized``); ``select`` takes plain-string rows and/or
  ``(label, detail)`` tuples and returns the chosen index, -1 on cancel.
* ``send_mutation(op, key=None)`` posts a delete/clear over the channel and
  returns the service's ack dict, or ``None`` on timeout (the report-only
  "service not running" signal). There is no fallback write path.
* ``current_key()`` returns the canonical store key the service published
  for the live playback (the applier's home-window property), or '' —
  absent service, no playback, or no wiring all read as "nothing playing".

``run()`` is a re-read-and-render loop: every pass reads the store fresh, so
a delete's effect is the next render. Values render verbatim (the signed
millisecond integers the store keeps, shown exactly, never rounded). The
empty state is the first-run education.

When the store spans more than one HDR group the top level renders as a
group index (one row per HDR type, with display name and entry count, and an
inactive share suffixed when it has one); a single-group store renders the
flat list instead. The mode derives from the group count, never the entry
count, so a delete can never dissolve the categories into a flat list whose
rows all share one HDR name. Keys that cannot claim an HDR name
(unsplittable, or a blank hdr segment) bucket under 'Other', sorted last.
Selecting a group lists only its entries, headed by the group name, with the
redundant HDR name dropped from the row copy; Back returns to the top level.
The whole-store clear-all lives only at the top level; each open group
carries its own scoped clear, implemented as looped single deletes over the
channel (no batch op on the wire). An open group survives external mutations
that leave it the only group, while the top level re-evaluates fresh each
render; delete confirmations always show the full profile line.

Display is toggle-aware but never filtered: dormancy mirrors the lookup
rule, so the injected ``per_fps``, ``distinct_spatial``, and
``distinct_channels`` flags decide which rows are tagged. The fps and
channel rules are symmetric (each mode sleeps the other's entries); the
spatial rule is one-sided (a base-codec key is legitimate in both modes,
so only spatial-variant rows sleep, and only while the toggle is off).
Dormant rows are tagged '— inactive', never hidden, and sink below the
active rows of their HDR group. Every stored entry always lists, so
clear-all's confirmation never under-represents what it deletes.

The entry matching ``current_key()`` is the playing row, re-read every pass
so it tracks reality while the view loops. It is tagged '· playing now' and
floats first — globally, so its HDR group also leads the index (first-
appearance ordering — the Other bucket keeps its forced-last seat) and it
heads its group's drill-down. A playing row is never dormant: the published
key is always the current mode's, dormancy always the other's, and the row
build enforces it besides, so even a mid-flip race between the two
processes' toggle reads cannot render a contradictory row. A published key
with no matching entry shows nothing: the rows are the indicator's whole
surface, and the headings stay static.

List rows carry Kodi label markup applied at render time only: dormant rows
are dimmed gray whole, the playing row is bolded whole (both lines, like
the dim) with a localized "»" marker leading its label line, and the group
index bolds the group name against its count — except the playing group's
row, which takes the marker and a single whole-row bold, since nesting
``[B]`` tags would end the bold at the inner close tag. No color is
hardcoded beyond the dormant gray (a fixed accent clashes with foreign skin
palettes). The ``_Row`` strings stay plain so confirmations, which reuse
them, render unstyled; bold degrades to regular weight on skins without a
bold list font, so no information lives in markup alone.
"""

from collections import namedtuple

from resources.lib.aome.domain.formats import spatial_base
from resources.lib.aome.store.keys import (HDR_DISPLAY, describe_key,
                                          describe_key_in_group, sort_key,
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

# English fallbacks for strings that must never render blank: localized()
# degrades to '' on a transient failure, and a blank dialog teaches nothing.
# Confirmations keep the raw localized text (they carry the entry
# description alongside it). The group-index strings are here too: 'Other' is
# a row's entire label, the count templates are the only content beside the
# group name, and the inactive tag is the dormant row's whole explanation.
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
    _LABEL_INACTIVE: "{0} — inactive",
    _LABEL_GROUP_INACTIVE: "({0} inactive)",
    _LABEL_PLAYING: "{0} · playing now",
    _LABEL_PLAYING_MARK: "» {0}",
}

# One presentable entry: the full profile line (flat rows and the delete
# confirmation's first line), the in-group line (drill-down rows, codec
# leading), the value/meta detail line, the literal store key the delete
# targets, and the dormancy/playing flags. All strings plain; markup is a
# list-render concern, and these feed confirmations too.
_Row = namedtuple("_Row", "describe short detail key dormant playing")

# Kodi label markup for the list renders. No hardcoded colors beyond the
# dormant gray: a fixed accent clashes with foreign skin palettes, so the
# playing row's extra weight is structural — the localized "»" marker plus
# bold, both inheriting the skin's own styling. [B] needs the skin's bold
# list font (Estuary has one) and silently renders regular weight without
# it, which is fine since no markup carries information the text does not.
_DIM = "[COLOR gray]{0}[/COLOR]"
_BOLD = "[B]{0}[/B]"


def _noop(_message):
    return None


class ManageView:
    """Inspect + delete/clear stored offsets from the script process."""

    def __init__(self, read_entries, gui, send_mutation, *, per_fps=False,
                 distinct_spatial=False, distinct_channels=False,
                 current_key=None, log_debug=None):
        """``per_fps``, ``distinct_spatial``, and ``distinct_channels`` are
        the granularity toggles at launch (they cannot change while the
        view is open). They drive display only: 'All FPS'/'All channels'
        vs an omitted axis for the 'all' segments, and the '— inactive'
        tag on whichever rows the lookup will not consult now. Never
        filtering: this view is the store's only inspection surface, so
        every entry always lists.

        ``current_key`` (see the module docstring) defaults to
        "nothing playing", so a caller without the seam renders plain.
        """
        self._read_entries = read_entries
        self._gui = gui
        self._send_mutation = send_mutation
        self._per_fps = bool(per_fps)
        self._distinct_spatial = bool(distinct_spatial)
        self._distinct_channels = bool(distinct_channels)
        self._current_key = current_key or (lambda: '')
        self._log = log_debug or _noop
        # The open drill-down group (an hdr segment, or _OTHER_GROUP);
        # None = top level. run() owns it; held on the instance so the
        # per-pass methods share one navigation state.
        self._group = None
        # The published playing key ('' = none), refreshed per pass.
        self._current = ''

    # -- entry point ----------------------------------------------------------

    def run(self):
        """Read, render, and act on one user choice per pass until they exit."""
        heading = self._gui.localized(_HEADING)
        self._group = None
        while True:
            try:
                entries = self._read_entries()
            except StoreUnreadable as error:
                self._log("AOMe_ManageView: store unreadable ({0})".format(error))
                # A newer-schema file is PRESERVED by the service (read-
                # only), never quarantined — its wording must not promise
                # the reset the corrupt case gets.
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

            if self._group is not None:
                outcome = self._group_pass(heading, rows)
            else:
                # The mode question is "how many groups", never "how many
                # entries": a delete can empty a group, but it can
                # never silently dissolve the whole category level.
                groups = self._group_index(rows)
                if len(groups) > 1:
                    outcome = self._index_pass(heading, groups)
                else:
                    outcome = self._flat_pass(heading, rows)
            if outcome is _CLOSE:
                return

    # -- passes (one render + at most one user action each) -------------------

    def _flat_pass(self, heading, rows):
        """The single-list render: every entry as a two-line row + clear-all."""
        options = [self._list_row(row.describe, row) for row in rows]
        options.append(self._gui.localized(_LABEL_CLEAR_ALL))

        # Cancel/Back is the exit; the router then reopens the settings
        # dialog the manage button closed, so leaving always lands the
        # user back in settings.
        choice = self._gui.select(heading, options)
        if choice < 0:
            return _CLOSE
        if choice == len(rows):
            return self._settle(heading, self._confirm_clear(heading))
        return self._settle(heading,
                            self._confirm_delete(heading, rows[choice]))

    def _index_pass(self, heading, groups):
        """The group index: one single-line row per HDR type + clear-all.

        ``groups`` is run()'s ordered ``(segment, count, inactive, playing)``
        list. Clear-all stays on this level when grouped: its confirmation
        covers the whole store, so it belongs where the whole store is
        represented.
        """
        self._log("AOMe_ManageView: rendering group index ({0} group(s))"
                  .format(len(groups)))
        options = [self._group_row(segment, count, inactive,
                                   emphasize=True, playing=playing)
                   for segment, count, inactive, playing in groups]
        options.append(self._gui.localized(_LABEL_CLEAR_ALL))

        choice = self._gui.select(heading, options)
        if choice < 0:
            return _CLOSE
        if choice == len(groups):
            return self._settle(heading, self._confirm_clear(heading))
        self._group = groups[choice][0]
        self._log("AOMe_ManageView: opened group {0}"
                  .format(self._group_name(self._group)))
        return None

    def _group_pass(self, heading, rows):
        """One open group's entries; Back returns to the top level.

        The open group survives external mutations that leave it the only
        group, but a group that emptied under us falls back to the top
        level, which re-evaluates flat vs grouped fresh. The select is
        headed by the group name; confirmations keep the main heading and
        the full profile line.
        """
        group_rows = [row for row in rows
                      if self._group_of(row.key) == self._group]
        if not group_rows:
            self._log("AOMe_ManageView: open group emptied; "
                      "returning to the top level")
            self._group = None
            return None

        options = [self._list_row(row.short, row) for row in group_rows]
        # The scoped clear row: the whole-store clear-all stays at the top
        # level, but the set THIS row deletes is exactly the list above it.
        options.append(self._gui.localized(_LABEL_CLEAR_GROUP))
        choice = self._gui.select(self._group_name(self._group), options)
        if choice < 0:
            self._group = None
            return None
        if choice == len(group_rows):
            return self._clear_group(heading, group_rows, whole_store=(
                len(group_rows) == len(rows)))
        return self._settle(heading,
                            self._confirm_delete(heading, group_rows[choice]))

    def _clear_group(self, heading, group_rows, *, whole_store):
        """Batch-delete every entry of the open group.

        Looped single deletes over the existing channel (no batch op on the
        wire, so the whitelist is untouched). The confirmation restates the
        scope as the index row did. Per-delete semantics mirror the
        single-delete flow: a 'missing' ack is satisfied intent and the
        batch continues; a timeout or hard failure reports once and stops.
        Clearing a group that was the entire store exits quietly like
        clear-all.
        """
        message = (self._text(_MSG_CONFIRM_CLEAR_GROUP) + "\n"
                   + self._group_row(self._group, len(group_rows),
                                     sum(1 for row in group_rows
                                         if row.dormant)))
        if not self._gui.yesno(heading, message):
            return None
        self._log("AOMe_ManageView: clearing group {0} ({1} entries)"
                  .format(self._group_name(self._group), len(group_rows)))
        for row in group_rows:
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

        A declined confirmation just loops; a real ack is reported, and a
        deliberate clear closes the view (looping would land on the
        first-run empty state right after the user emptied the store).
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

        ``keys.sort_key`` groups by HDR type, then codec, then rate ('all'
        first, numeric order), total even over hand-edited keys. Dormancy
        splits each HDR group in two: the active rows list first, the
        dormant ones sink below, each stratum keeping the codec/rate order.
        The split stays inside the group, so dormancy never moves an entry
        between groups. The playing row alone outranks everything — hoisted
        globally, so its group's first appearance leads the index too.
        """
        rows = []
        for key, entry in entries.items():
            dormant = self._is_dormant(key)
            # A dormant row never claims playing, even if a mid-flip race
            # publishes the other mode's key for one pass: the heading's
            # miss line covers that pass, and the next one self-corrects.
            playing = (bool(self._current) and key == self._current
                       and not dormant)
            rows.append(_Row(self._describe(key, entry),
                             self._describe_short(key, entry),
                             self._detail(entry, inactive=dormant,
                                          playing=playing),
                             key,
                             dormant,
                             playing))

        def display_order(row):
            hdr, audio, fps_rank, ch_rank, raw = sort_key(row.key)
            return (not row.playing, hdr, row.dormant, audio, fps_rank,
                    ch_rank, raw)

        rows.sort(key=display_order)
        return rows

    def _list_row(self, label, row):
        """One two-line select option; a dormant row is dimmed whole, the
        playing row bolded whole with the localized "»" marker leading its
        label line.

        Markup and the marker live here, not in the ``_Row`` strings, which
        confirmations reuse unstyled. Both lines style together; half a
        styled row would read as two states (the marker is a lead-in on the
        label, not a style, so it stays off the value line). The branches
        cannot collide: a playing row is never dormant (module docstring).
        """
        if row.dormant:
            return (_DIM.format(label), _DIM.format(row.detail))
        if row.playing:
            return (_BOLD.format(self._template(_LABEL_PLAYING_MARK, label)),
                    _BOLD.format(row.detail))
        return (label, row.detail)

    def _is_dormant(self, key):
        """True for an entry the lookup will not consult right now.

        Dormancy mirrors the lookup rule per axis. The fps and channel
        rules are symmetric: with a toggle off only the 'all' key is read,
        so an axis-specific entry is dormant; with it on, only the
        specific key is read, so an 'all' entry is dormant. (For channels
        the on-side has one exotic exception the tag accepts: a stream
        reporting no usable count still consults the 'all' key, but every
        observed platform reports counts.) The spatial rule is one-sided:
        a base-codec key is legitimate in both modes, so only a
        spatial-variant entry is dormant, and only while distinct_spatial
        is off (the lookup then reads the base key). The row is tagged
        rather than hidden (hiding would misstate clear-all's scope).
        Unsplittable keys are never tagged.
        """
        try:
            _hdr, fps_segment, audio_segment, ch_segment = split_key(key)
        except ValueError:
            return False
        if not self._distinct_spatial and \
                spatial_base(audio_segment) != audio_segment:
            return True
        # Symmetric axis: the 'all' side sleeps with the toggle on, the
        # specific side with it off.
        if (ch_segment == 'all') == self._distinct_channels:
            return True
        if self._per_fps:
            return fps_segment == 'all'
        return fps_segment != 'all'

    def _describe(self, key, entry):
        """The full profile line (flat rows, delete confirmations)."""
        return self._render_key(describe_key, key, entry)

    def _describe_short(self, key, entry):
        """The in-group row label: the HDR group name is redundant there,
        so the codec leads and the rate follows."""
        return self._render_key(describe_key_in_group, key, entry)

    def _render_key(self, describe_fn, key, entry):
        """One describe function plus the verbatim fallback, written once.

        A key that does not split into four segments raises; verbatim
        acceptance means an unrecognized key is shown as itself rather than
        crashing the view. The entry's ``video_fps`` metadata renders the
        exact reported rate for per-fps keys.
        """
        try:
            return describe_fn(key, video_fps=entry.get("video_fps"),
                               per_fps=self._per_fps,
                               distinct_channels=self._distinct_channels)
        except ValueError:
            return key

    def _detail(self, entry, *, inactive, playing=False):
        """The value line ('-115 ms'), run through the localized
        playing/inactive templates as flagged.

        Just the verbatim signed value; the store's source/updated metadata
        stays in the file but out of the row. The state template wraps the
        whole line (the two states are mutually exclusive, so at most one
        wraps).
        """
        delay = entry.get("delay_ms")
        sign = "+" if isinstance(delay, int) and delay > 0 else ""
        detail = "{0}{1} ms".format(sign, delay)
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

    def _group_index(self, rows):
        """Ordered ``(segment, count, inactive, playing)`` quads for the
        group index.

        Rows arrive display-sorted, so first appearance yields the same
        HDR-display order the flat list scans in — with the playing row
        hoisted first, its group leads — and the Other bucket is forced
        last. Counts include dormant rows (every stored entry is countable
        from the index); each group carries its dormant share and whether
        it holds the playing row.
        """
        order = []
        counts = {}
        inactive = {}
        playing = {}
        for row in rows:
            segment = self._group_of(row.key)
            if segment not in counts:
                order.append(segment)
                counts[segment] = 0
                inactive[segment] = 0
                playing[segment] = False
            counts[segment] += 1
            inactive[segment] += 1 if row.dormant else 0
            playing[segment] = playing[segment] or row.playing
        if _OTHER_GROUP in counts:
            order.remove(_OTHER_GROUP)
            order.append(_OTHER_GROUP)
        return [(segment, counts[segment], inactive[segment],
                 playing[segment])
                for segment in order]

    def _group_name(self, segment):
        """Display name for a group row/heading; verbatim for a stranger."""
        if segment is _OTHER_GROUP:
            return self._text(_LABEL_OTHER_GROUP)
        return HDR_DISPLAY.get(segment, segment)

    def _group_row(self, segment, count, inactive=0, *, emphasize=False,
                   playing=False):
        """One index row: 'Dolby Vision — 6 entries (2 inactive)'.

        The inactive suffix appears only when the group has dormant entries,
        and the count always states the total (the suffix splits it, never
        replaces it); ``playing`` appends the playing tag after the counts.
        ``emphasize`` bolds the group name against its count for the index
        list — except the playing group, whose whole row bolds in a single
        wrap (nested ``[B]`` tags would end the bold at the inner close
        tag). The clear-group confirmation reuses this row plain.
        """
        string_id = _LABEL_GROUP_ENTRY if count == 1 else _LABEL_GROUP_ENTRIES
        counted = self._template(string_id, count)
        if inactive:
            counted += " " + self._template(_LABEL_GROUP_INACTIVE, inactive)
        if playing:
            counted = self._template(_LABEL_PLAYING, counted)
        name = self._group_name(segment)
        if emphasize and playing:
            return _BOLD.format(self._template(
                _LABEL_PLAYING_MARK, "{0} — {1}".format(name, counted)))
        if emphasize:
            name = _BOLD.format(name)
        return "{0} — {1}".format(name, counted)

    # -- actions --------------------------------------------------------------

    def _confirm_delete(self, heading, row):
        # Both row lines, not just the profile: the confirmation must show
        # what value is being deleted, always the full describe line.
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

    def _report_ack(self, heading, ack):
        """Surface a failed/absent ack; a success just falls through to re-read."""
        if ack is None:
            self._log("AOMe_ManageView: no ack (service not running)")
            self._gui.ok(heading, self._text(_MSG_NO_SERVICE))
            return
        if not ack.get("ok"):
            detail = ack.get("detail")
            if detail == "missing":
                # Already gone (raced away by playback learning or another
                # session): intent satisfied, so the refreshed list is the
                # feedback, not an error dialog.
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
        """A format template with translation guards (shared shape with the
        transfer view): a translation missing any expected ``{0}..{n}``
        placeholder degrades to the English fallback rather than silently
        swallowing the value, and one malformed enough to raise degrades
        too. The except is deliberately broad, since which exception a bad
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


# Sentinels, private unique objects so they can never collide with real
# values: _DECLINED distinguishes "user declined the confirmation" (loop,
# send nothing) from a real ack (which may itself be None on timeout);
# _CLOSE is a pass telling run() the view is done (exit, or the deliberate
# quiet exit after a clear); _OTHER_GROUP is the index bucket for keys
# that do not split — an object, so no hdr segment string can shadow it.
_DECLINED = object()
_CLOSE = object()
_OTHER_GROUP = object()

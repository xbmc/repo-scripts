"""The setup wizard window and the controller behind it.

SetupController turns the setup model into what the window shows (heading,
explanation, rows, buttons) and carries out what the user picks, through
small dialog and storage seams so it is tested without Kodi. SetupWindow is
the WindowXMLDialog that renders it; run_setup wires both to Kodi.

The libraries step is a list of libraries; choosing one opens its page in
the same window (SetupState.open_library), and Done on the page returns to
the list. Nothing is written before Finish (or Save in the Libraries
dialog); leaving with changed libraries asks whether to save them, and
leaving without saving leaves settings and sources.json as they were.
sources.json is written first, so a failed write leaves the settings
untouched too.

Logging:
    Logger: 'setup'
    Key events:
        - setup.start (INFO): The wizard or the Libraries dialog opened
        - setup.finish (INFO): Everything was saved
        - setup.cancel (INFO): Closed without saving
        - setup.discard (INFO): The user chose not to save changed libraries
        - setup.save_fail (WARNING): sources.json could not be written
        - setup.not_converted (WARNING): the 1.1 settings are not converted
          yet, so the libraries cannot be edited
        - setup.damaged_kept (INFO): the user kept an unreadable
          sources.json rather than start the libraries afresh
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Callable, Optional, cast

import xbmc
import xbmcgui

from resources.lib.constants import COUNTRY_CODES
from resources.lib.data.libraries import (
    FILE_DAMAGED,
    FILE_LEGACY,
    TITLE_LANGUAGE,
    TITLE_ORIGINAL,
    Library,
    LibraryConfig,
    read_libraries,
    resolve_country,
    save_libraries,
)
from resources.lib.data.sources import (
    CONTENT_MIXED,
    CONTENT_MOVIES,
    CONTENT_TVSHOWS,
    discover_folders,
    kodi_ui_language,
    library_content,
)
from resources.lib.providers.languages import TMDB_PRIMARY_TRANSLATIONS
from resources.lib.providers.tmdb import (
    KEY_OK,
    KEY_REFUSED,
    KEY_UNCHECKED,
    check_api_key,
)
from resources.lib.ui.message_window import show_message
from resources.lib.ui.select_window import show_select
from resources.lib.ui.setup_model import (
    ART_OPTIONS,
    ART_TOGGLES,
    FALLBACK_ORDER_OPTIONS,
    LIBRARIES,
    RATING_OPTIONS,
    TEXT_OPTIONS,
    TEXT_TOGGLES,
    TOGGLES,
    WIZARD,
    SetupFlow,
    SetupState,
    changes_nothing,
    country_missing,
    initial_state,
    libraries_to_write,
    mask_key,
    page_groups,
    page_toggles,
    settings_to_write,
    shown_toggles,
)
from resources.lib.ui.theme import publish_theme
from resources.lib.utils import (
    display_path,
    get_addon,
    get_bool_setting,
    get_logger,
    get_setting,
    lang,
)

log = get_logger('setup')

# Window XML and control ids (resources/skins/Default/1080i).
_XML = "script-metamender-setup.xml"
_COLUMN = 30
_LIST = 100
_NEXT = 21
_BACK = 22
_CANCEL = 23
_ACTION_PREVIOUS_MENU = 10
_ACTION_NAV_BACK = 92

PAGE = "page"
HEADER = "header"

# (name, one-line explanation) string ids per toggle, in TOGGLES order.
_FEATURE_TEXT = {
    "ratings": (32432, 32433),
    "plots": (32434, 32435),
    "episode_titles": (32436, 32437),
    "main_titles": (32438, 32439),
    "certifications": (32440, 32441),
    "credits": (32442, 32443),
    "trailers": (32444, 32445),
    "taglines": (32446, 32447),
    "posters": (32712, 32713),
    "episode_thumbs": (32714, 32715),
    "fanart": (32744, 32745),
    "other_art": (32746, 32747),
    "movie_sets": (32748, 32749),
    "details": (32448, 32449),
}
# The explanation a toggle gets in a library of one kind, where the
# general one names fields that kind lacks.
_CONTENT_DETAIL = {
    ("details", CONTENT_MOVIES): 32781, ("details", CONTENT_TVSHOWS): 32782,
    ("other_art", CONTENT_MOVIES): 32783, ("other_art", CONTENT_TVSHOWS): 32784,
}
# A library page's heading names what the library holds.
_CONTENT_HEADING = {CONTENT_MOVIES: 32777, CONTENT_TVSHOWS: 32778}
# Why a page lists every toggle.
_CONTENT_NOTE = {"": 32779, CONTENT_MIXED: 32780}

# The short form a toggle takes in a library's one-line summary.
_FIELD_WORD = {
    "ratings": 32676, "plots": 32677, "episode_titles": 32678, "main_titles": 32679,
    "certifications": 32681, "credits": 32683, "trailers": 32684, "taglines": 32685,
    "posters": 32716, "episode_thumbs": 32717,
    "fanart": 32750, "other_art": 32751, "movie_sets": 32752,
    "details": 32686,
}
# The order of the words in that summary: age ratings last, since their
# country makes it the longest.
_WORD_ORDER = tuple(t for t in TOGGLES if t != "certifications") + ("certifications",)
# The country options after Automatic, in COUNTRY_CODES order.
_COUNTRY_LABELS = (32260, 32261, 32262, 32263, 32264, 32265, 32266, 32267, 32268, 32628)
_COUNTRY_OPTIONS = len(_COUNTRY_LABELS)

_STEP_TEXT = {
    "key": (32410, 32411),
    LIBRARIES: (32658, 32659),
}
# (label, sub-line) per option, in RATING_OPTIONS and TEXT_OPTIONS order.
_RATING_TEXT = ((32632, 32633), (32030, 32634), (32031, 32635), (32032, 32636),
                (32033, 32637))
_TEXT_ORDER_TEXT = ((32632, 32640), (32392, 32641), (32393, 32642))
# Labels in FALLBACK_ORDER_OPTIONS order.
_FALLBACK_ORDER_TEXT = (32393, 32392)
_TITLE_MODES = (TITLE_LANGUAGE, TITLE_ORIGINAL)
_TITLE_TEXT = (32673, 32674)
# (label, sub-line) per option, in ART_OPTIONS order.
_ART_TEXT = ((32010, 32735), (32709, 32736))
_GROUP_HEADING = {"language": 32422, "fields": 32430, "rating": 32668, "text": 32669,
                  "titles": 32670, "art": 32753, "age_ratings": 32671}


@dataclass(frozen=True)
class Row:
    label: str
    detail: str = ""
    # True shows the tick; False shows none.
    chosen: bool = False
    # The row's marker when it differs from the view's (marker_kind):
    # "check" for a toggle among pickers, HEADER for a group heading.
    marker: str = ""
    # What activating the row changes, on the library page.
    key: str = ""


def _header(label: str) -> Row:
    return Row(label, marker=HEADER)


def _option_label(text: tuple[int, ...], values: tuple[Any, ...], current: Any) -> str:
    """The label of the chosen option; the first (the default) when the
    stored value is not one of the options."""
    index = values.index(current) if current in values else 0
    return lang(text[index])


class Dialogs:
    """The dialogs the steps open on top of the window: MetaMender's own
    picker and messages, and Kodi's keyboard."""

    def input(self, heading: str, default: str) -> str:
        return xbmcgui.Dialog().input(heading, default)

    def select(self, heading: str, options: list[str], preselect: int,
               details: Optional[list[str]] = None, marked: bool = True) -> int:
        """The picked index, -1 when cancelled. ``details`` puts a sub-line
        under each option; ``marked`` False lists actions rather than a
        choice with a current option."""
        return show_select(heading, options, preselect, details, marked)

    def ok(self, heading: str, message: str) -> None:
        show_message(heading, message)

    def yesno(self, heading: str, message: str) -> bool:
        return show_message(heading, message, question=True)


def language_name(code: str) -> str:
    """"Dutch (NL)" for "nl-NL", from Kodi's own language names; the code
    itself when Kodi has no name for it."""
    base, _, region = code.partition("-")
    name = xbmc.convertLanguage(base, xbmc.ENGLISH_NAME)
    if not isinstance(name, str) or not name:
        return code
    return "{} ({})".format(name, region) if region else name


def write_settings(values: dict[str, Any]) -> None:
    """Write the wizard's settings in order (setup_complete last, so an
    interrupted write leaves setup incomplete)."""
    addon = get_addon()
    for key, value in values.items():
        if isinstance(value, bool):
            addon.setSettingBool(key, value)
        elif isinstance(value, int):
            addon.setSettingInt(key, value)
        else:
            addon.setSettingString(key, str(value))


class SetupController:
    def __init__(
        self,
        mode: str,
        state: SetupState,
        ui_language: str,
        config_path: str,
        first_run: bool,
        dialogs: Any = None,
        key_checker: Callable[[str], str] = check_api_key,
        save: Callable[[str, LibraryConfig], bool] = save_libraries,
        settings_writer: Callable[[dict[str, Any]], None] = write_settings,
        name: Callable[[str], str] = language_name,
        libraries_seen: Optional[Callable[[], None]] = None,
        content_of: Callable[[str], str] = library_content,
    ) -> None:
        self.mode = mode
        self.state = state
        self.flow = SetupFlow(mode)
        self.finished = False
        self._ui_language = ui_language
        self._config_path = config_path
        self._first_run = first_run
        self._dialogs = dialogs or Dialogs()
        self._check = key_checker
        self._save = save
        self._write = settings_writer
        self._name = name
        self._libraries_seen = libraries_seen
        self._content_of = content_of
        # What each library holds, asked once per window: a library Kodi
        # scans into while the window is open shows the change next time.
        self._content: dict[str, str] = {}
        # What the libraries were when the window opened, to tell whether
        # leaving would lose changes.
        self._loaded = list(state.libraries.libraries)

    # -- what the window shows ---------------------------------------------

    @property
    def step(self) -> str:
        return self.flow.current

    @property
    def view(self) -> str:
        """The step, or PAGE while a library's page is open."""
        return PAGE if self._library() is not None else self.step

    def view_key(self) -> str:
        """Changes whenever the window shows another list, so the
        selection goes back to the top (list_position)."""
        if self.view == PAGE:
            return PAGE + ":" + str(self.state.open_library)
        return self.view

    def heading(self) -> str:
        lib = self._library()
        if lib is not None:
            heading = _CONTENT_HEADING.get(self._content_for(lib))
            return lang(heading).format(self._label(lib)) if heading else self._label(lib)
        if self.step == "summary":
            return lang(32455)
        return lang(_STEP_TEXT[self.step][0])

    def explanation(self) -> str:
        lib = self._library()
        if lib is not None:
            lines = [lang(32666)]
            note = _CONTENT_NOTE.get(self._content_for(lib))
            if note:
                lines.append(lang(note))
            if not self._shown(lib):
                lines.append(lang(32667))
            return "\n".join(lines)
        if self.step == "summary":
            text = lang(32456 if self._first_run else 32457)
            if changes_nothing(self.state.libraries):
                return lang(32675) + "\n" + text
            return text
        if self.step == LIBRARIES and not self.state.libraries.libraries:
            return lang(32427)
        return lang(_STEP_TEXT[self.step][1])

    def marker_kind(self) -> str:
        """The marker rows show unless a row sets its own: checkboxes on
        the library list. The page's toggles set their own; its other rows
        open pickers and have none."""
        return "check" if self.view == LIBRARIES else ""

    def next_label(self) -> str:
        if self.view == PAGE:
            return lang(32687)
        if self.mode == LIBRARIES:
            return lang(32407)
        return lang(32406 if self.step == "summary" else 32405)

    def has_back(self) -> bool:
        return (self.mode == WIZARD and self.view != PAGE
                and self.flow.index(self.state) > 1)

    def rows(self) -> list[Row]:
        return getattr(self, "_rows_" + self.view)()

    def _rows_key(self) -> list[Row]:
        key = self.state.api_key
        return [Row(lang(32412), mask_key(key) if key else lang(32413))]

    def _rows_libraries(self) -> list[Row]:
        return [Row(self._label(lib), self._library_line(lib), lib.included, key=lib.path)
                for lib in self.state.libraries.libraries]

    def _rows_page(self) -> list[Row]:
        lib = self._library()
        assert lib is not None
        rows: list[Row] = []
        for group in page_groups(lib, self._content_for(lib)):
            rows.append(_header(lang(_GROUP_HEADING[group])))
            rows.extend(getattr(self, "_group_" + group)(lib))
        return rows

    def _group_language(self, lib: Library) -> list[Row]:
        fallback = lib.fallback_language
        return [
            Row(lang(32422), self._name(lib.language), key="language"),
            Row(lang(32423), self._name(fallback) if fallback else lang(32424),
                key="fallback"),
        ]

    def _group_fields(self, lib: Library) -> list[Row]:
        content = self._content_for(lib)
        return [Row(lang(_FEATURE_TEXT[t][0]),
                    lang(_CONTENT_DETAIL.get((t, content), _FEATURE_TEXT[t][1])),
                    t in lib.toggles, "check", "toggle:" + t)
                for t in page_toggles(content)]

    def _group_rating(self, lib: Library) -> list[Row]:
        return [Row(lang(32630), self._rating_label(lib), key="rating")]

    def _group_text(self, lib: Library) -> list[Row]:
        return [
            Row(lang(32638), self._text_label(lib), key="text"),
            Row(lang(32396), _option_label(_FALLBACK_ORDER_TEXT, FALLBACK_ORDER_OPTIONS,
                                           lib.fallback_order), key="fallback_order"),
        ]

    def _group_titles(self, lib: Library) -> list[Row]:
        return [Row(lang(32672), _option_label(_TITLE_TEXT, _TITLE_MODES, lib.title_mode),
                    key="title_mode")]

    def _group_art(self, lib: Library) -> list[Row]:
        return [Row(lang(32734), self._art_label(lib), key="art_source")]

    def _group_age_ratings(self, lib: Library) -> list[Row]:
        prefix = lib.cert_prefix_override
        not_found = lib.cert_not_found
        return [
            Row(lang(32450), self._country_label(lib, lib.cert_country), key="country"),
            Row(lang(32643), lang(32644), lib.cert_replace_foreign, "check", "replace"),
            Row(lang(32689), lang(32690) if prefix is None else (prefix or lang(32701)),
                key="prefix"),
            Row(lang(32691), lang(32692) if not not_found else lang(32693).format(not_found),
                key="not_found"),
        ]

    def _rows_summary(self) -> list[Row]:
        s = self.state
        status = lang(32459 if s.key_status == KEY_OK else 32460)
        rows = [Row(lang(32458), "{} ({})".format(mask_key(s.api_key), status))]
        left_out = []
        for lib in s.libraries.libraries:
            if not lib.included:
                left_out.append(Row(self._label(lib), lang(32661)))
                continue
            rows.append(_header(self._label(lib)))
            rows.append(Row(lang(32422), self._pair(lib.language, lib.fallback_language)))
            rows.append(Row(lang(32462), ", ".join(self._field_words(lib)) or lang(32463)))
            on = self._shown(lib)
            if "ratings" in on:
                rows.append(Row(lang(32648), self._rating_label(lib)))
            if any(t in on for t in TEXT_TOGGLES):
                rows.append(Row(lang(32649), self._text_label(lib)))
            if "main_titles" in on:
                rows.append(Row(lang(32672), _option_label(_TITLE_TEXT, _TITLE_MODES,
                                                           lib.title_mode)))
            if any(t in on for t in ART_TOGGLES):
                rows.append(Row(lang(32734), self._art_label(lib)))
            if "certifications" in on:
                rows.append(Row(lang(32450), self._country_label(lib, lib.cert_country)))
                rows.append(Row(lang(32645),
                                lang(32646 if lib.cert_replace_foreign else 32647)))
        if left_out:
            rows.append(_header(lang(32688)))
            rows.extend(left_out)
        return rows

    # -- what the user does ------------------------------------------------

    def activate(self, index: int) -> None:
        """The user selected row ``index`` of the current view."""
        handler = getattr(self, "_activate_" + self.view, None)
        if handler is not None:
            handler(index)

    def _activate_key(self, _index: int) -> None:
        # Never pre-filled: a stored key is not shown in full again, and an
        # empty entry keeps it.
        entered = self._dialogs.input(lang(32412), "").strip()
        if entered and entered != self.state.api_key:
            self.state.api_key = entered
            self.state.key_status = ""

    def _activate_libraries(self, index: int) -> None:
        libraries = self.state.libraries.libraries
        if not 0 <= index < len(libraries):
            return
        lib = libraries[index]
        first = 32665 if lib.included else 32663
        picked = self._dialogs.select(self._label(lib), [lang(first), lang(32664)], 0,
                                      marked=False)
        if picked == 1:
            # The settings stay, so including the library again restores them.
            self.state.libraries.replace(replace(lib, included=False))
        elif picked == 0:
            if not lib.included:
                self.state.libraries.replace(replace(lib, included=True))
            self.state.open_library = lib.path

    def _activate_page(self, index: int) -> None:
        lib = self._library()
        rows = self.rows()
        if lib is None or not 0 <= index < len(rows) or not rows[index].key:
            return
        key = rows[index].key
        if key.startswith("toggle:"):
            changed = replace(lib, toggles=lib.toggles ^ {key[len("toggle:"):]})
        else:
            changed = getattr(self, "_pick_" + key)(lib)
        if changed is not None:
            self.state.libraries.replace(changed)

    def _pick_language(self, lib: Library) -> Optional[Library]:
        picked = self._pick_code(lang(32422), lib.language, False)
        return None if picked is None else replace(lib, language=picked)

    def _pick_fallback(self, lib: Library) -> Optional[Library]:
        picked = self._pick_code(lang(32423), lib.fallback_language, True)
        return None if picked is None else replace(lib, fallback_language=picked)

    def _pick_option(self, heading: int, labels: tuple[int, ...], values: tuple[Any, ...],
                     current: Any, details: Optional[tuple[int, ...]] = None) -> Any:
        """The value picked from a list of options; None when cancelled."""
        preselect = values.index(current) if current in values else 0
        lines = None if details is None else [lang(i) for i in details]
        picked = self._dialogs.select(lang(heading), [lang(i) for i in labels], preselect,
                                      lines)
        return values[picked] if 0 <= picked < len(values) else None

    def _pick_rating(self, lib: Library) -> Optional[Library]:
        value = self._pick_option(32630, tuple(t[0] for t in _RATING_TEXT), RATING_OPTIONS,
                                  lib.rating_source, tuple(t[1] for t in _RATING_TEXT))
        return None if value is None else replace(lib, rating_source=value)

    def _pick_text(self, lib: Library) -> Optional[Library]:
        value = self._pick_option(32638, tuple(t[0] for t in _TEXT_ORDER_TEXT), TEXT_OPTIONS,
                                  lib.text_source_order, tuple(t[1] for t in _TEXT_ORDER_TEXT))
        return None if value is None else replace(lib, text_source_order=value)

    def _pick_art_source(self, lib: Library) -> Optional[Library]:
        value = self._pick_option(32734, tuple(t[0] for t in _ART_TEXT), ART_OPTIONS,
                                  lib.art_source, tuple(t[1] for t in _ART_TEXT))
        return None if value is None else replace(lib, art_source=value)

    def _pick_fallback_order(self, lib: Library) -> Optional[Library]:
        value = self._pick_option(32396, _FALLBACK_ORDER_TEXT, FALLBACK_ORDER_OPTIONS,
                                  lib.fallback_order)
        return None if value is None else replace(lib, fallback_order=value)

    def _pick_title_mode(self, lib: Library) -> Optional[Library]:
        value = self._pick_option(32672, _TITLE_TEXT, _TITLE_MODES, lib.title_mode)
        return None if value is None else replace(lib, title_mode=value)

    def _pick_country(self, lib: Library) -> Optional[Library]:
        options = [self._country_label(lib, i) for i in range(_COUNTRY_OPTIONS + 1)]
        preselect = lib.cert_country if 0 <= lib.cert_country <= _COUNTRY_OPTIONS else 0
        picked = self._dialogs.select(lang(32450), options, preselect)
        return None if picked < 0 else replace(lib, cert_country=picked)

    def _pick_replace(self, lib: Library) -> Optional[Library]:
        return replace(lib, cert_replace_foreign=not lib.cert_replace_foreign)

    def _pick_prefix(self, lib: Library) -> Optional[Library]:
        # None writes the country's own prefix, "" none at all.
        current = lib.cert_prefix_override
        preselect = 0 if current is None else (1 if current == "" else 2)
        picked = self._dialogs.select(lang(32689), [lang(32690), lang(32701), lang(32206)],
                                      preselect)
        if picked == 0:
            return replace(lib, cert_prefix_override=None)
        if picked == 1:
            return replace(lib, cert_prefix_override="")
        if picked == 2:
            # Kodi's keyboard gives "" for both cancel and an empty entry;
            # "No prefix" is its own option, so "" keeps what was there.
            entered = self._dialogs.input(lang(32206), current or "")
            return replace(lib, cert_prefix_override=entered) if entered else None
        return None

    def _pick_not_found(self, lib: Library) -> Optional[Library]:
        current = lib.cert_not_found
        picked = self._dialogs.select(lang(32691), [lang(32692), lang(32694)],
                                      1 if current else 0)
        if picked == 0:
            return replace(lib, cert_not_found=None)
        if picked == 1:
            entered = self._dialogs.input(lang(32233), current or "NR").strip()
            return replace(lib, cert_not_found=entered) if entered else None
        return None

    def on_next(self) -> bool:
        """Next, Done, Finish or Save. True once everything is saved and
        the window should close."""
        if self.view == PAGE:
            self._close_page()
            return False
        if self.step == "key" and not self._key_passes():
            return False
        if not self.flow.can_advance(self.state):
            return False
        if self.mode == LIBRARIES or self.step == "summary":
            return self._finish()
        self.flow.next(self.state)
        return False

    def on_back(self) -> bool:
        """Back; False on the first step (the caller then cancels). On a
        library's page it is Done."""
        if self.view == PAGE:
            self._close_page()
            return True
        return self.mode == WIZARD and self.flow.back(self.state)

    def on_cancel(self) -> bool:
        """Cancel, or Back where there is no step to go back to. True when
        the window should close. With changed libraries the user is asked
        to save them first: yes saves as Done (or Finish) does, no
        discards them. False keeps the window open, when saving could not
        go ahead (a page without a country, a refused key, a failed save)."""
        if self.state.libraries.libraries == self._loaded:
            return True
        if not self._dialogs.yesno(self.heading(), lang(32708)):
            log.info("Library changes discarded", event="setup.discard", mode=self.mode)
            return True
        if self.view == PAGE:
            self._close_page()
            if self.view == PAGE:
                return False
        if self.mode == WIZARD and not self._key_passes():
            return False
        return self._finish()

    def shown(self) -> None:
        """The window drew the current view. Showing the library list
        answers the notices that asked the user to open it."""
        if self.view == LIBRARIES and self._libraries_seen is not None:
            callback, self._libraries_seen = self._libraries_seen, None
            callback()

    def _close_page(self) -> None:
        lib = self._library()
        if lib is not None and country_missing(lib, self._ui_language):
            self._dialogs.ok(lang(32450), lang(32453))
            return
        self.state.open_library = None

    def _key_passes(self) -> bool:
        if not self.state.api_key:
            self._activate_key(0)
            if not self.state.api_key:
                return False
        if self.state.key_status in (KEY_OK, KEY_UNCHECKED):
            return True
        status = self._check(self.state.api_key)
        if status == KEY_REFUSED:
            self._dialogs.ok(lang(32410), lang(32414))
            return False
        if status == KEY_UNCHECKED:
            self._dialogs.ok(lang(32410), lang(32415))
        self.state.key_status = status
        return True

    def _finish(self) -> bool:
        config = libraries_to_write(self.state)
        if not self._save(self._config_path, config):
            log.warning("Setup could not save the libraries", event="setup.save_fail")
            self._dialogs.ok(self.heading(), lang(32695))
            return False
        if self.mode == WIZARD:
            self._write(settings_to_write(self.state))
        self.finished = True
        log.info("Setup saved", event="setup.finish", mode=self.mode,
                 first_run=self._first_run, library_count=len(config.libraries),
                 included=sum(1 for lib in config.libraries if lib.included))
        return True

    # -- helpers -----------------------------------------------------------

    def _library(self) -> Optional[Library]:
        path = self.state.open_library
        return None if path is None else self.state.libraries.by_path(path)

    @staticmethod
    def _label(lib: Library) -> str:
        return lib.label or display_path(lib.path)

    def _content_for(self, lib: Library) -> str:
        if lib.path not in self._content:
            self._content[lib.path] = self._content_of(lib.path)
        return self._content[lib.path]

    def _shown(self, lib: Library) -> frozenset[str]:
        """The ticks that apply to what the library holds; the others stay
        stored but are neither shown nor named."""
        return shown_toggles(lib, self._content_for(lib))

    def _field_words(self, lib: Library) -> list[str]:
        words = []
        on = self._shown(lib)
        for toggle in _WORD_ORDER:
            if toggle not in on:
                continue
            if toggle == "main_titles" and lib.title_mode == TITLE_ORIGINAL:
                words.append(lang(32680))
            elif toggle == "certifications":
                country = resolve_country(lib, self._ui_language)
                words.append(lang(32682).format(country) if country else lang(32681))
            else:
                words.append(lang(_FIELD_WORD[toggle]))
        return words

    def _library_line(self, lib: Library) -> str:
        if not lib.included:
            return lang(32661)
        if not self._shown(lib):
            return lang(32660)
        return lang(32662).format(self._name(lib.language), ", ".join(self._field_words(lib)))

    def _rating_label(self, lib: Library) -> str:
        return _option_label(tuple(t[0] for t in _RATING_TEXT), RATING_OPTIONS,
                             lib.rating_source)

    def _art_label(self, lib: Library) -> str:
        return _option_label(tuple(t[0] for t in _ART_TEXT), ART_OPTIONS,
                             lib.art_source)

    def _text_label(self, lib: Library) -> str:
        return _option_label(tuple(t[0] for t in _TEXT_ORDER_TEXT), TEXT_OPTIONS,
                             lib.text_source_order)

    def _language_options(self, current: str) -> list[str]:
        codes = list(TMDB_PRIMARY_TRANSLATIONS)
        for extra in (self._ui_language, current):
            if extra and extra not in codes:
                codes.append(extra)
        return sorted(codes, key=lambda c: self._name(c).lower())

    def _pick_code(self, heading: str, current: str, allow_none: bool) -> Optional[str]:
        """A language code, "" for None (when allowed), or None when the
        user cancelled."""
        codes = self._language_options(current)
        options = ([lang(32424)] if allow_none else []) + [self._name(c) for c in codes]
        offset = 1 if allow_none else 0
        preselect = codes.index(current) + offset if current in codes else 0
        picked = self._dialogs.select(heading, options, preselect)
        if picked < 0:
            return None
        if allow_none and picked == 0:
            return ""
        return codes[picked - offset]

    def _pair(self, language: str, fallback: str) -> str:
        if fallback:
            return "{}, {}: {}".format(self._name(language), lang(32423), self._name(fallback))
        return self._name(language)

    def _country_label(self, lib: Library, index: int) -> str:
        """The label of country option ``index`` for this library;
        Automatic names the country it resolves to."""
        if index == 0:
            code = resolve_country(replace(lib, cert_country=0), self._ui_language)
            if code is None:
                return lang(32453)
            return lang(32452).format(lang(_COUNTRY_LABELS[COUNTRY_CODES.index(code)]))
        if 1 <= index <= _COUNTRY_OPTIONS:
            return lang(_COUNTRY_LABELS[index - 1])
        return lang(32453)


def window_properties(c: SetupController) -> dict[str, str]:
    """Every window property the XML reads. The accent colours are always
    set: a property the XML reads but nobody set tints a texture white."""
    wizard = c.mode == WIZARD
    props = {
        "MM.Heading": c.heading(),
        "MM.Text": c.explanation(),
        "MM.Next": c.next_label(),
        "MM.Back": lang(32404) if c.has_back() else "",
        "MM.Cancel": lang(32408),
        "MM.StepIndex": str(c.flow.index(c.state)) if wizard else "",
        "MM.StepTotal": str(c.flow.total(c.state)) if wizard else "",
    }
    return props


def list_position(shown: Optional[str], view: str, position: int, rows: list[Row]) -> int:
    """Where the list's selection goes after a redraw: kept when the same
    view redraws (a row was toggled), otherwise the first row that is not
    a group heading, since a position from another list points at an
    unrelated row and can scroll the first rows out of view."""
    if shown == view:
        return min(max(position, 0), len(rows) - 1)
    return next((i for i, row in enumerate(rows) if row.marker != HEADER), 0)


class SetupWindow(xbmcgui.WindowXMLDialog):
    """Renders a SetupController. The controller is attached before
    doModal(); every click re-renders the whole view."""

    controller: SetupController
    _shown_view: Optional[str] = None

    def onInit(self) -> None:
        self._render()

    def onClick(self, controlId: int) -> None:
        c = self.controller
        if controlId == _LIST:
            c.activate(self._list().getSelectedPosition())
        elif controlId == _NEXT:
            if c.on_next():
                self.close()
                return
        elif controlId == _BACK:
            c.on_back()
        elif controlId == _CANCEL and c.on_cancel():
            self.close()
            return
        self._render()

    def onAction(self, action: Any) -> None:
        if action.getId() in (_ACTION_PREVIOUS_MENU, _ACTION_NAV_BACK):
            c = self.controller
            if c.on_back() or not c.on_cancel():
                self._render()
            else:
                self.close()

    def _list(self) -> xbmcgui.ControlList:
        return cast(xbmcgui.ControlList, self.getControl(_LIST))

    def _render(self) -> None:
        c = self.controller
        for key, value in window_properties(c).items():
            self.setProperty(key, value)
        control = self._list()
        position = control.getSelectedPosition()
        control.reset()
        rows = c.rows()
        items = []
        for row in rows:
            item = xbmcgui.ListItem(row.label, offscreen=True)
            item.setProperty("detail", row.detail)
            item.setProperty("chosen", "true" if row.chosen else "")
            item.setProperty("marker", row.marker or c.marker_kind())
            items.append(item)
        control.addItems(items)
        view = c.view_key()
        if items:
            control.selectItem(list_position(self._shown_view, view, position, rows))
            self.setFocusId(_LIST)
        else:
            self.setFocusId(_NEXT)
        self._shown_view = view
        c.shown()


def run_setup(mode: str, config_path: str,
              libraries_seen: Optional[Callable[[], None]] = None) -> bool:
    """Open the wizard (WIZARD) or the Libraries dialog (LIBRARIES). True
    when the user finished and everything was saved. ``libraries_seen``
    runs once, when the library list first shows.

    An unreadable sources.json opens only when the user agrees to start
    the libraries afresh: Save then replaces it with every library not
    included."""
    ui_language = kodi_ui_language()
    first_run = not get_bool_setting("setup_complete")
    stored, found = read_libraries(config_path)
    if found == FILE_LEGACY and not first_run:
        # Saving now would write libraries without the 1.1 settings the
        # service has yet to convert, and the conversion would never run.
        # Before the first setup the service never converts, so the
        # wizard starts from what Kodi lists (wizard.open_setup converts
        # first when the file holds folder settings).
        log.warning("Libraries not converted yet, setup not opened",
                    event="setup.not_converted", mode=mode)
        Dialogs().ok(lang(32658), lang(32696))
        return False
    if found == FILE_DAMAGED and not Dialogs().yesno(lang(32658), lang(32702)):
        log.info("Unreadable library settings kept, setup not opened",
                 event="setup.damaged_kept", mode=mode)
        return False
    # A failed discovery shows the stored libraries only; saving then
    # keeps them, and the service adds the others once Kodi lists them.
    discovered = discover_folders() or []
    settings = {"tmdb_api_key": get_setting("tmdb_api_key")}
    state = initial_state(settings, stored, discovered, ui_language)
    controller = SetupController(
        mode, state, ui_language, config_path, first_run, libraries_seen=libraries_seen,
    )
    log.info("Setup opened", event="setup.start", mode=mode, first_run=first_run,
             sources=len(discovered), library_count=len(state.libraries.libraries))
    addon = get_addon()
    window = SetupWindow(_XML, addon.getAddonInfo("path"), "Default", "1080i")
    window.controller = controller
    publish_theme()
    window.doModal()
    del window
    if not controller.finished:
        log.info("Setup closed without saving", event="setup.cancel", mode=mode)
    return controller.finished

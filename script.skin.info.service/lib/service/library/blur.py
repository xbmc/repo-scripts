"""Focus and audio player blur, plus the focused image's main color, each off-thread."""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Final, List, Optional

import xbmc

from lib.kodi.client import log
from lib.kodi.utilities import (
    LabelSnapshot, clear_prop, get_prop, parse_pipe_list, set_prop, skin_bool_label,
)
from lib.skin.labels import resolve_variables, variable_labels

_COLOR_PROP: Final = "SkinInfo.ImageColor.Main"
_COLOR_CACHE_SIZE: Final = 1000
_COLOR_SOURCE: Final = "ListItem.Art(poster)"
_BLUR: Final = "SkinInfo.Blur"
_PLAYER_BLUR: Final = "SkinInfo.Player.Blur"
_IMAGE_COLOR: Final = "SkinInfo.ImageColor"
SKIN_BOOL_LABELS: Final = tuple(skin_bool_label(s) for s in (_BLUR, _PLAYER_BLUR, _IMAGE_COLOR))


class BlurHandler:
    """Owns focus + player blur state and threads. Sets `SkinInfo.[prefix.]BlurredImage` props."""

    def __init__(self):
        self._focus_thread: Optional[threading.Thread] = None
        self._focus_last_source: Optional[str] = None
        self._player_thread: Optional[threading.Thread] = None
        self._player_last_source: Optional[str] = None
        self._player = xbmc.Player()
        self._warned_source = ""

    @staticmethod
    def focus_labels() -> List[str]:
        """Infolabels the focus blur needs from the tick's batched read."""
        names = get_prop("SkinInfo.BlurSourceVar")
        if names:
            return variable_labels(parse_pipe_list(names))
        return parse_pipe_list(get_prop("SkinInfo.BlurSource"))

    def handle_focus(self, labels: LabelSnapshot) -> None:
        """Handle a focus tick: blur the focused item's background, clear it when off."""
        if not labels.skin_bool(_BLUR):
            if self._focus_last_source is not None:
                self._clear_props("SkinInfo.")
                self._focus_last_source = None
            return

        prefix = get_prop("SkinInfo.BlurPrefix")
        prop_base = f"SkinInfo.{prefix}." if prefix else "SkinInfo."

        self._process(
            source_property="SkinInfo.BlurSource",
            slot="focus",
            prop_base=prop_base,
            labels=labels,
        )

    def handle_player(self, labels: LabelSnapshot) -> None:
        """Handle a player tick: blur playing audio's background, clear it when stopped or off."""
        if not self._player.isPlayingAudio() or not labels.skin_bool(_PLAYER_BLUR):
            if self._player_last_source is not None:
                self._clear_props("SkinInfo.Player.")
                self._player_last_source = None
            return

        current_file = xbmc.getInfoLabel("Player.Filenameandpath")

        self._process(
            source_property="SkinInfo.Player.BlurSource",
            slot="player",
            prop_base="SkinInfo.Player.",
            cache_key_suffix=f"|{current_file}",
        )

    def _process(self, source_property: str, slot: str, prop_base: str,
                 cache_key_suffix: str = "", labels: Optional[LabelSnapshot] = None) -> None:
        """Process one blur slot: start a blur of its source; clear it when it has none."""
        blur_source_var = get_prop(source_property + "Var")
        if blur_source_var:
            names = parse_pipe_list(blur_source_var)
            source_path = resolve_variables(names, labels or LabelSnapshot(variable_labels(names)))
        else:
            blur_source_infolabel = get_prop(source_property)
            if not blur_source_infolabel:
                if self._get_last(slot) is not None:
                    self._clear_props(prop_base)
                    self._set_last(slot, None)
                return

            if (blur_source_infolabel.startswith('$')
                    and blur_source_infolabel != self._warned_source):
                self._warned_source = blur_source_infolabel
                log("Blur",
                    f"{source_property} should not contain $INFO[], $VAR[], etc. "
                    f"Set raw infolabel instead. Got: {blur_source_infolabel}",
                    xbmc.LOGWARNING)

            sources = parse_pipe_list(blur_source_infolabel)
            source_path = self._resolve_with_fallbacks(sources, labels or LabelSnapshot(sources))

        if not source_path:
            if self._get_last(slot) is not None:
                self._clear_props(prop_base)
                self._set_last(slot, None)
            return

        cache_key = f"{source_path}{cache_key_suffix}"
        if cache_key == self._get_last(slot):
            return

        existing_thread = self._get_thread(slot)
        if existing_thread is not None and existing_thread.is_alive():
            return

        self._set_last(slot, cache_key)
        new_thread = threading.Thread(
            target=self._worker,
            args=(source_path, prop_base, slot),
            daemon=True,
        )
        self._set_thread(slot, new_thread)
        new_thread.start()

    def _worker(self, source: str, prop_base: str, slot: str) -> None:
        """Blur one source off-thread and publish it, clearing the slot on failure."""
        try:
            from lib.infrastructure import blur

            blurred_path = blur.blur_image(source)

            if blurred_path:
                set_prop(f"{prop_base}BlurredImage", blurred_path)
                set_prop(f"{prop_base}BlurredImage.Original", source)
            else:
                self._clear_props(prop_base)

        except Exception as e:
            log("Blur", f"Failed to blur image: {e}", xbmc.LOGERROR)
            self._clear_props(prop_base)
            self._set_last(slot, None)
        finally:
            self._set_thread(slot, None)

    @staticmethod
    def _resolve_with_fallbacks(sources: List[str], labels: LabelSnapshot) -> str:
        """Resolve the first source with a value, read from the batched labels."""
        for source in sources:
            resolved = labels.get(source)
            if resolved:
                return resolved
        return ""

    @staticmethod
    def _clear_props(prop_base: str) -> None:
        """Clear a slot's blurred image properties."""
        clear_prop(f"{prop_base}BlurredImage")
        clear_prop(f"{prop_base}BlurredImage.Original")

    def _get_last(self, slot: str) -> Optional[str]:
        """Get the last blurred source for one slot."""
        return self._focus_last_source if slot == "focus" else self._player_last_source

    def _set_last(self, slot: str, value: Optional[str]) -> None:
        """Remember the last blurred source for one slot."""
        if slot == "focus":
            self._focus_last_source = value
        else:
            self._player_last_source = value

    def _get_thread(self, slot: str) -> Optional[threading.Thread]:
        """Get the thread running for one slot."""
        return self._focus_thread if slot == "focus" else self._player_thread

    def _set_thread(self, slot: str, thread: Optional[threading.Thread]) -> None:
        """Remember the running thread for one slot."""
        if slot == "focus":
            self._focus_thread = thread
        else:
            self._player_thread = thread


class ImageColorHandler:
    """Publisher of `SkinInfo.ImageColor.Main`, the main color of the focused item's image."""

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._last_source: Optional[str] = None
        self._colors: "OrderedDict[str, str]" = OrderedDict()

    @staticmethod
    def focus_labels() -> List[str]:
        """Infolabels the color source names, for the tick's batched read."""
        return parse_pipe_list(get_prop("SkinInfo.ImageColorSource") or _COLOR_SOURCE)

    def handle_focus(self, labels: LabelSnapshot) -> None:
        """Handle a focus tick: publish the image's color, computing a new image's off-thread."""
        if not labels.skin_bool(_IMAGE_COLOR):
            self._clear()
            return

        source = BlurHandler._resolve_with_fallbacks(self.focus_labels(), labels)
        if not source:
            self._clear()
            return
        if source == self._last_source:
            return

        color = self._colors.get(source)
        if color:
            self._last_source = source
            set_prop(_COLOR_PROP, color)
            return
        if self._thread is not None and self._thread.is_alive():
            return

        self._last_source = source
        self._thread = threading.Thread(target=self._worker, args=(source,), daemon=True)
        self._thread.start()

    def _worker(self, source: str) -> None:
        """Compute and remember one image's color, publishing it if still the latest requested."""
        try:
            from lib.infrastructure.blur import main_color
            color = main_color(source)
        except Exception as e:
            log("Blur", f"Failed to read image color: {e}", xbmc.LOGERROR)
            color = ""

        if color:
            self._colors[source] = color
            if len(self._colors) > _COLOR_CACHE_SIZE:
                self._colors.popitem(last=False)
        if source == self._last_source:
            set_prop(_COLOR_PROP, color)

    def _clear(self) -> None:
        """Clear the color once the feature is off or the item has no image."""
        if self._last_source is not None:
            clear_prop(_COLOR_PROP)
            self._last_source = None

"""Immutable stream profile — the settings-lookup key and display helpers.

Pure Python: no Kodi imports. Display names and the setting-key format come
from aom.domain.formats (the vocabulary single source of truth).
"""

from dataclasses import dataclass

from resources.lib.aom.domain import formats


@dataclass(frozen=True)
class StreamProfile:
    """Immutable stream characteristics used for settings lookups and display."""

    hdr_type: str
    fps_type: object  # int (specific bucket), 'all', or 'unknown'
    audio_format: str
    video_fps: object
    player_id: int
    audio_channels: object

    def setting_id(self):
        """Settings id for this profile: `<hdr>_<fps>_<audio>`. FROZEN format."""
        return formats.setting_key(self.hdr_type, self._fps_key(),
                                   self.audio_format)

    def display_hdr(self):
        return formats.HDR_DISPLAY_NAMES.get(self.hdr_type, self.hdr_type)

    def display_audio(self):
        return formats.AUDIO_DISPLAY_NAMES.get(self.audio_format, self.audio_format)

    def display_fps(self):
        fps_key = self._fps_key()
        return formats.FPS_DISPLAY_NAMES.get(fps_key, str(fps_key))

    def summary(self, include_fps=True):
        fps_key = self._fps_key()
        hdr_label = self.display_hdr()
        audio_label = self.display_audio()

        if include_fps and str(fps_key).lower() != formats.FPS_ALL:
            fps_label = self.display_fps()
            return f"{hdr_label} | {fps_label} FPS | {audio_label}"
        return f"{hdr_label} | {audio_label}"

    def _fps_key(self):
        return str(self.fps_type)

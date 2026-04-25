#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import threading

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")
ADDON_NAME = ADDON.getAddonInfo("name")

VIDEO_EXTS = (
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".wmv",
    ".m4v",
    ".ts",
    ".webm",
    ".flv",
)


def log(msg: str) -> None:
    xbmc.log(f"[{ADDON_ID}] {msg}", xbmc.LOGDEBUG)


def L(string_id: int) -> str:
    text = ADDON.getLocalizedString(string_id)
    return text or str(string_id)


def _get_bool(setting_id: str, default: bool = False) -> bool:
    try:
        return ADDON.getSettingBool(setting_id)
    except Exception:
        value = (ADDON.getSetting(setting_id) or "").strip().lower()
        if value in ("true", "1", "yes", "on"):
            return True
        if value in ("false", "0", "no", "off"):
            return False
        return default


def _get_str(setting_id: str, default: str = "") -> str:
    try:
        value = ADDON.getSettingString(setting_id)
    except Exception:
        value = ADDON.getSetting(setting_id)
    value = (value or "").strip()
    return value if value else default


def _get_int(setting_id: str, default: int = 0) -> int:
    value = _get_str(setting_id, "")
    try:
        return int(float(value))
    except Exception:
        return default


def _norm_dir(path: str) -> str:
    path = (path or "").replace("\\", "/")
    if path and not path.endswith("/"):
        path += "/"
    return path


def _join(dir_path: str, name: str) -> str:
    if dir_path.endswith("/"):
        return dir_path + name
    return dir_path + "/" + name


def _read_video_dir(default: str = "") -> str:
    return _norm_dir(_get_str("video_dir", default))


def list_videos(folder: str):
    folder = _norm_dir(folder)
    if not folder:
        log("Video folder is empty.")
        return [], "missing_folder"

    if not xbmcvfs.exists(folder):
        log(f"Folder does not exist: {folder}")
        return [], "missing_folder"

    try:
        _dirs, files = xbmcvfs.listdir(folder)
    except Exception as exc:
        log(f"listdir failed for {folder}: {exc}")
        return [], "missing_folder"

    videos = []
    for filename in sorted(files):
        lower_name = filename.lower()
        if any(lower_name.endswith(ext) for ext in VIDEO_EXTS):
            videos.append(_join(folder, filename))

    if not videos:
        log(f"No supported videos found in: {folder}")
        return [], "no_videos"

    return videos, None


def open_addon_settings() -> None:
    try:
        ADDON.openSettings()
        return
    except Exception as exc:
        log(f"ADDON.openSettings() failed: {exc}")

    try:
        xbmc.executebuiltin(f"Addon.OpenSettings({ADDON_ID})")
    except Exception as exc:
        log(f"Addon.OpenSettings builtin failed: {exc}")


def prompt_folder_issue(reason: str) -> str:
    if reason == "no_videos":
        message = L(32006)
    else:
        message = L(32005)

    try:
        xbmcgui.Dialog().ok(ADDON_NAME, message)
    except Exception as exc:
        log(f"Dialog display failed: {exc}")

    open_addon_settings()
    return _read_video_dir("")


def set_repeat_all() -> None:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "Player.SetRepeat",
        "params": {"playerid": 1, "repeat": "all"},
    }
    try:
        xbmc.executeJSONRPC(json.dumps(payload))
    except Exception as exc:
        log(f"SetRepeat failed: {exc}")


def set_shuffle_off() -> None:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "Player.SetShuffle",
        "params": {"playerid": 1, "shuffle": False},
    }
    try:
        xbmc.executeJSONRPC(json.dumps(payload))
    except Exception as exc:
        log(f"SetShuffle failed: {exc}")


def _write_ass_overlay(text: str, seconds: int) -> str:
    safe = text.replace("{", "(").replace("}", ")")
    tmp_path = xbmcvfs.translatePath(f"special://temp/{ADDON_ID}_startup.ass")
    ass = f"""[Script Info]
Title: {ADDON_ID} startup overlay
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default, Arial, 32, &H00FFFFFF, &H000000FF, &H80000000, &H80000000, 0, 0, 0, 0, 100, 100, 0, 0, 1, 2, 1, 3, 10, 20, 40, 0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:{seconds:02d}.00,Default,,0,0,0,,{{\an3}}{safe}
"""
    with open(tmp_path, "w", encoding="utf-8") as handle:
        handle.write(ass)
    return tmp_path


def show_startup_overlay_async() -> None:
    if not _get_bool("show_startup_text", False):
        return

    text = _get_str("startup_text", "").strip()
    if not text:
        return

    seconds = _get_int("startup_text_seconds", 2)
    seconds = max(1, min(10, seconds))

    def worker() -> None:
        try:
            xbmc.sleep(400)

            player = xbmc.Player()
            if not player.isPlayingVideo():
                return

            ass_path = _write_ass_overlay(text, seconds)
            player.setSubtitles(ass_path)
            player.showSubtitles(True)

            xbmc.sleep(seconds * 1000 + 200)
            try:
                player.showSubtitles(False)
            except Exception:
                pass
        except Exception as exc:
            log(f"Overlay failed: {exc}")

    threading.Thread(target=worker, daemon=True).start()


def play_loop(folder: str):
    videos, reason = list_videos(folder)
    if reason:
        return prompt_folder_issue(reason), False

    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()
    for video in videos:
        playlist.add(video)

    player = xbmc.Player()
    player.play(playlist)
    set_shuffle_off()
    set_repeat_all()

    try:
        xbmc.executebuiltin("Action(Fullscreen)")
    except Exception:
        pass

    show_startup_overlay_async()
    log(f"Started loop with {len(videos)} item(s) from {folder}")
    return folder, True


def run() -> None:
    folder = _read_video_dir("/storage/emulated/0/Movies/")

    xbmc.sleep(12000)
    monitor = xbmc.Monitor()

    while not monitor.abortRequested():
        if not xbmc.Player().isPlayingVideo():
            previous_folder = folder
            folder, started = play_loop(folder)

            if not started:
                if folder and folder != previous_folder:
                    xbmc.sleep(500)
                    continue

                if monitor.waitForAbort(15):
                    break

                folder = _read_video_dir(previous_folder or "/storage/emulated/0/Movies/")
                continue

        if monitor.waitForAbort(1):
            break


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        log(f"Fatal: {exc}")

import os
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')


def get_kodi_log_path():
    if xbmc.getCondVisibility('system.platform.windows'):
        return xbmcvfs.translatePath('special://home/kodi.log')
    else:
        return xbmcvfs.translatePath('special://home/temp/kodi.log')


def parse_log_file():
    log_path = get_kodi_log_path()
    if not os.path.exists(log_path):
        return ["Log file not found"]

    addon_logs = []
    try:
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                if f'[{ADDON_NAME}]' in line and '[UPDATE_RESULT]' in line:
                    try:
                        # 2025-01-24 23:12:31.599 T:8268     info <general>: [Latest Rating Service] [2025-01-24 23:12:31] [UPDATE_RESULT] TV: Landman S01E06 - Rating: 8.6 → 8.7
                        # Split by ']' and remove leading '['
                        parts = [p.strip(' []') for p in line.split(']')]
                        if len(parts) >= 3:
                            timestamp = parts[1]  # The timestamp part
                            # Find the message after [UPDATE_RESULT]
                            for i, part in enumerate(parts):
                                if 'UPDATE_RESULT' in part:
                                    message = '] '.join(parts[i+1:]).strip()
                                    formatted_line = f"{message}"
                                    addon_logs.append(formatted_line)
                                    break
                    except Exception as e:
                        print(f"Error parsing line: {line}, Error: {str(e)}")
                        continue
    except Exception as e:
        return [f"Error reading log file: {str(e)}"]

    return list(reversed(addon_logs[-1000:]))  # Return last 1000 lines in reverse chronological order


def show_log_viewer():
    logs = parse_log_file()
    if not logs:
        xbmcgui.Dialog().ok(ADDON_NAME, "No rating updates found")
        return

    # Create a list dialog
    dialog = xbmcgui.Dialog()
    while True:
        # Show the logs in a select dialog
        idx = dialog.select("Rating Update History", logs)
        if idx == -1:  # User pressed back/cancel
            break


def main():
    show_log_viewer()

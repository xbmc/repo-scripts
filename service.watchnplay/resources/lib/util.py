# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT
"""Kleine Helfer: Logging, Strings, Plattform, Benachrichtigungen, Einstellungen."""

import re
import time
import xml.etree.ElementTree as ET

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON_ID = 'service.watchnplay'
DEFAULT_API_BASE = 'https://api.watch-n-play.com/api/kodi'
DEFAULT_THRESHOLD = 90.0
MIN_THRESHOLD = 50.0
MAX_THRESHOLD = 100.0
# Kodi liest advancedsettings.xml nur aus dem Master-Profil, nie aus special://profile
ADVANCEDSETTINGS = 'special://masterprofile/advancedsettings.xml'


def addon():
    # Frische Instanz, damit geaenderte Einstellungen gelesen werden
    return xbmcaddon.Addon(ADDON_ID)


def addon_version():
    return addon().getAddonInfo('version') or '0.0.0'


def profile_dir():
    return xbmcvfs.translatePath('special://profile/addon_data/%s/' % ADDON_ID)


def addon_path():
    return xbmcvfs.translatePath(addon().getAddonInfo('path'))


def log(msg, level=None):
    if level is None:
        level = xbmc.LOGINFO
    xbmc.log('[%s] %s' % (ADDON_ID, msg), level)


def debug(msg):
    """Pro Wiedergabe und Einzelschritt: nur im Debug-Log."""
    log(msg, xbmc.LOGDEBUG)


def warn(msg):
    log(msg, xbmc.LOGWARNING)


def lang(string_id):
    return addon().getLocalizedString(string_id)


def notify(message, ms=5000):
    icon = addon().getAddonInfo('icon')
    xbmcgui.Dialog().notification('WatchNPlay', message, icon, ms)


def notify_service(message):
    """Meldung an den laufenden Dienst (kommt dort als onNotification 'Other.<message>' an)."""
    xbmc.executebuiltin('NotifyAll(%s,%s)' % (ADDON_ID, message))


# Versteckte Test-Einstellung api_base: unverschluesselt nur ins eigene Netz, das
# Geraete-Token geht sonst im Klartext ueber das Internet
_LOCAL_HTTP = re.compile(r'^http://(localhost|127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)')


def api_base():
    try:
        value = (addon().getSetting('api_base') or '').strip()
    except Exception:
        value = ''
    if value and not (value.startswith('https://') or _LOCAL_HTTP.match(value)):
        warn('api_base ignored (https required outside the local network)')
        value = ''
    return (value or DEFAULT_API_BASE).rstrip('/')


def set_status(paired, user_name=None, device_name=None, pro_paused=False):
    """Schreibt Statuszeilen und Sichtbarkeit der Knoepfe in die Einstellungen.

    Nur bei Aenderung: jeder setSetting-Aufruf speichert settings.xml, und der Dienst
    meldet den Stand alle 5 Minuten (SD-Karten auf Raspberry Pi / LibreELEC)."""
    a = addon()
    if not paired:
        text = lang(32005)
    elif pro_paused:
        text = lang(32008)
    else:
        text = lang(32006) % (user_name or '?')
    try:
        if a.getSettingBool('paired') != bool(paired):
            a.setSettingBool('paired', bool(paired))
    except Exception:
        value = 'true' if paired else 'false'
        if a.getSetting('paired') != value:
            a.setSetting('paired', value)
    for key, value in (('status_label', text), ('device_label', device_name or '')):
        if a.getSetting(key) != value:
            a.setSetting(key, value)


def device_name():
    name = (xbmc.getInfoLabel('System.FriendlyName') or '').strip()
    return name or 'Kodi'


def kodi_version():
    raw = xbmc.getInfoLabel('System.BuildVersion') or ''
    m = re.match(r'(\d+)\.(\d+)', raw)
    return '%s.%s' % (m.group(1), m.group(2)) if m else '0.0'


def platform():
    os_info = (xbmc.getInfoLabel('System.OSVersionInfo') or '').lower()
    if 'coreelec' in os_info:
        return 'CoreELEC'
    if 'libreelec' in os_info:
        return 'LibreELEC'
    checks = (
        ('System.Platform.Android', 'Android'),
        ('System.Platform.TVOS', 'tvOS'),
        ('System.Platform.IOS', 'iOS'),
        ('System.Platform.OSX', 'macOS'),
        ('System.Platform.Windows', 'Windows'),
        ('System.Platform.UWP', 'Windows'),
        ('System.Platform.WebOS', 'webOS'),
        ('System.Platform.Linux', 'Linux'),
    )
    for cond, name in checks:
        if xbmc.getCondVisibility(cond):
            return name
    return 'Unknown'


def user_agent():
    return 'WatchNPlay-Kodi/%s (Kodi %s; %s)' % (addon_version(), kodi_version(), platform())


def now_ms():
    return int(time.time() * 1000)


def parse_threshold(xml_text):
    """Liest <video><playcountminimumpercent> aus advancedsettings.xml, sonst None (ungeklemmt)."""
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return None
    node = root.find('./video/playcountminimumpercent')
    if node is None or node.text is None:
        return None
    try:
        value = float(node.text.strip())
    except ValueError:
        return None
    if value != value:  # NaN
        return None
    return value


def clamp_threshold(value):
    """Wie Kodi selbst: nur 50..100 sinnvoll, ohne Wert 90."""
    if value is None:
        return DEFAULT_THRESHOLD
    return max(MIN_THRESHOLD, min(MAX_THRESHOLD, float(value)))


def watched_threshold():
    """Kodis eigene Schwelle (advancedsettings.xml im Master-Profil), geklemmt auf 50..100, sonst 90 %."""
    path = ADVANCEDSETTINGS
    try:
        if xbmcvfs.exists(path):
            f = xbmcvfs.File(path)
            try:
                text = f.read()
            finally:
                f.close()
            return clamp_threshold(parse_threshold(text))
    except Exception as exc:
        warn('advancedsettings.xml not readable: %s' % exc)
    return DEFAULT_THRESHOLD


def format_code(code):
    code = (code or '').strip()
    if len(code) == 6:
        return '%s %s' % (code[:3], code[3:])
    return code


def format_countdown(seconds):
    seconds = max(0, int(seconds))
    return '%d:%02d' % (seconds // 60, seconds % 60)


def strip_scheme(url):
    return re.sub(r'^https?://', '', url or '').rstrip('/')

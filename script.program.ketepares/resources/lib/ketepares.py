# -*- coding: utf-8 -*-
# Ketepares for Kodi
# Copyright (C) 2026 jairamrb.com
# SPDX-License-Identifier: GPL-2.0-or-later
"""Lógica común del script (addon.py) y del servicio (service.py).

- El script se abre al pulsar el complemento: enseña lo programado y deja
  ejecutar la acción ya, activar/desactivar la programación o cancelar.
- También se puede llamar desde otro add-on, un favorito, el mando o JSON-RPC
  con parámetros (ver README.md, «Launching it from another add-on»):
  RunScript(script.program.ketepares,action=powerdown,in=30,silent=true)
- El servicio arranca con Kodi, mira la hora cada pocos segundos y, cuando
  toca, lanza la cuenta atrás (o actúa en silencio). También ejecuta los
  temporizadores que piden otros add-ons.
- Solo se ofrecen las acciones que este sistema puede hacer (available()).
"""

import datetime
import json
import math
import re
import sys
import time

try:
    from urllib.parse import unquote_plus
except ImportError:  # pragma: no cover
    from urllib import unquote_plus

import xbmc
import xbmcaddon
import xbmcgui

ADDON_ID = "script.program.ketepares"
NAME = "Ketepares"

# Índice = valor del ajuste "action" (mismo orden que los textos 30010..30018).
# (nombre para llamadas externas, orden interna de Kodi)
ACTIONS = [
    ("powerdown", "Powerdown"),             # apagar el equipo entero
    ("quit", "Quit"),                       # cerrar solo Kodi
    ("reboot", "Reboot"),
    ("suspend", "Suspend"),
    ("hibernate", "Hibernate"),
    ("logoff", "System.LogOff"),
    ("stop", "PlayerControl(Stop)"),
    ("screensaver", "ActivateScreensaver"),
    ("alarm", None),                        # solo avisar
]
ACT_QUIT = 1
ACT_STOP = 6
ACT_ALARM = 8

# Otros nombres que se aceptan en action=... (en inglés y en español)
ALIASES = {
    "shutdown": 0, "poweroff": 0, "apagar": 0,
    "exit": 1, "close": 1, "cerrar": 1, "salir": 1,
    "restart": 2, "reiniciar": 2,
    "sleep": 3, "suspender": 3,
    "hibernar": 4,
    "logout": 5, "cerrarsesion": 5,
    "detener": 6,
    "salvapantallas": 7,
    "remind": 8, "reminder": 8, "avisar": 8, "aviso": 8,
}

TICK = 2       # segundos entre comprobaciones del servicio
GRACE = 120    # si la hora pasó hace más de esto (p. ej. al volver de suspensión), no se ejecuta
COUNTDOWN_DEFAULT = 15  # segundos de cuenta atrás por defecto
COUNTDOWN_MIN = 10      # límites del ajuste y de countdown=...
COUNTDOWN_MAX = 60
SNOOZE_ASK = 20  # segundos que espera la pregunta de posponer antes de cerrarse

# Estado que el servicio deja a la vista del script, de skins y de otros add-ons
# (propiedades de la ventana Home, 10000)
PROP_SNOOZE = ADDON_ID + ".snooze"     # "HH:MM" si está pospuesto
PROP_WAITING = ADDON_ID + ".waiting"   # "1" si espera a que acabe la reproducción
PROP_TIMER = ADDON_ID + ".timer"       # "HH:MM" del temporizador pedido por otro add-on
PROP_TIMER_ACTION = ADDON_ID + ".timer.action"  # nombre de su acción (powerdown, quit...)
PROP_ACTIONS = ADDON_ID + ".actions"   # acciones posibles en este sistema, separadas por comas
# Internas
PROP_ABORT = ADDON_ID + ".abort"       # el script pide anular lo pendiente/pospuesto
PROP_REQUEST = ADDON_ID + ".request"   # el script pasa un temporizador nuevo al servicio
PROP_TIMER_DATA = ADDON_ID + ".timer.data"  # el temporizador entero (sobrevive a reiniciar el servicio)

S_ACTION = 30010     # nombres de las acciones (30010..30018)
S_DAY_SHORT = 30020  # L M X J V S D (30020..30026, lunes primero)
S_DAY_LONG = 30030   # lunes..domingo (30030..30036)
S_ACTION_NOW = 30050  # texto corto del botón "ya" de cada acción (30050..30058)

DONE, CANCELLED, UNAVAILABLE = "done", "cancelled", "unavailable"


def _addon():
    return xbmcaddon.Addon(ADDON_ID)


def tr(string_id):
    return _addon().getLocalizedString(string_id)


def _int(value, default):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def notify(message, icon=None, ms=5000):
    xbmcgui.Dialog().notification(NAME, message, icon or _addon().getAddonInfo("icon"), ms)


def log(message, level=xbmc.LOGINFO):
    xbmc.log("[%s] %s" % (ADDON_ID, message), level)


def _home():
    return xbmcgui.Window(10000)


# --- qué puede hacer este sistema ----------------------------------------------

def _kodi_setting(name):
    query = {"jsonrpc": "2.0", "id": 1, "method": "Settings.GetSettingValue", "params": {"setting": name}}
    try:
        return json.loads(xbmc.executeJSONRPC(json.dumps(query)))["result"]["value"]
    except (KeyError, TypeError, ValueError):
        return None


def available(index):
    """True si este sistema puede hacer la acción (lo pregunta a Kodi en el momento)."""
    cond = xbmc.getCondVisibility
    key = ACTIONS[index][0]
    if key == "powerdown":
        return cond("System.CanPowerDown")
    if key == "reboot":
        return cond("System.CanReboot")
    if key == "suspend":
        return cond("System.CanSuspend")
    if key == "hibernate":
        return cond("System.CanHibernate")
    if key == "quit":  # iOS y tvOS no dejan que una app se cierre sola
        return not (cond("System.Platform.IOS") or cond("System.Platform.TVOS"))
    if key == "logoff":  # sin otros perfiles ni pantalla de inicio de sesión no hace nada útil
        return cond("System.HasLoginScreen") or _int(xbmc.getInfoLabel("System.ProfileCount"), 1) > 1
    if key == "screensaver":  # "Ninguno" en Ajustes > Interfaz > Salvapantallas
        return bool(_kodi_setting("screensaver.mode"))
    return True


def available_actions():
    return [i for i in range(len(ACTIONS)) if available(i)]


def action_index(name):
    """Índice de una acción a partir de su nombre, un alias o su número; None si no existe."""
    name = re.sub(r"[\s_.-]", "", (name or "").lower())
    for i, (key, _) in enumerate(ACTIONS):
        if name == key:
            return i
    if name in ALIASES:
        return ALIASES[name]
    if name.isdigit() and int(name) < len(ACTIONS):
        return int(name)
    return None


def action_name(index):
    return tr(S_ACTION + index)


# --- qué hacer y cómo ------------------------------------------------------------

class Job(object):
    """Una acción con su forma de avisar: la de la programación o la de una llamada externa."""

    FIELDS = ("action", "silent", "countdown", "snooze", "wait_playback", "notify", "source")

    def __init__(self, action, silent=False, countdown=COUNTDOWN_DEFAULT, snooze=10, wait_playback=False,
                 notify=True, source="schedule"):
        self.action = action
        self.silent = silent
        self.countdown = min(max(int(countdown), COUNTDOWN_MIN), COUNTDOWN_MAX)
        self.snooze = max(int(snooze), 0)
        self.wait_playback = wait_playback
        self.notify = notify
        self.source = source  # "schedule" (ajustes) o "external" (otro add-on, mando...)

    @property
    def key(self):
        return ACTIONS[self.action][0]

    @property
    def name(self):
        return action_name(self.action)

    @property
    def waits_for_playback(self):
        return self.wait_playback and self.action not in (ACT_STOP, ACT_ALARM)

    def to_dict(self):
        return dict((f, getattr(self, f)) for f in self.FIELDS)

    @classmethod
    def from_dict(cls, data):
        action = _int(data.get("action"), -1)
        if not 0 <= action < len(ACTIONS):
            raise ValueError("bad action %r" % data.get("action"))
        return cls(**dict((f, data[f]) for f in cls.FIELDS if f in data))


class Config(object):
    """Ajustes leídos en el momento (se crean de nuevo en cada comprobación)."""

    def __init__(self):
        a = _addon()
        self._addon = a
        self.enabled = a.getSetting("enabled") == "true"
        self.action = min(max(_int(a.getSetting("action"), 0), 0), len(ACTIONS) - 1)
        try:
            h, m = a.getSetting("time").split(":")[:2]
            self.hour, self.minute = min(max(int(h), 0), 23), min(max(int(m), 0), 59)
        except ValueError:
            self.hour, self.minute = 23, 0
        self.days = [a.getSetting("day%d" % i) != "false" for i in range(7)]
        if not any(self.days):  # sin días marcados = todos
            self.days = [True] * 7
        self.repeat = a.getSetting("repeat") != "false"
        self.autostart = a.getSetting("autostart") != "false"
        self.silent = a.getSetting("silent") == "true"
        self.countdown = min(max(_int(a.getSetting("countdown"), COUNTDOWN_DEFAULT), COUNTDOWN_MIN), COUNTDOWN_MAX)
        self.snooze = max(_int(a.getSetting("snooze"), 10), 0)
        self.wait_playback = a.getSetting("wait_playback") == "true"
        self.notify = a.getSetting("notify") != "false"

    def set_enabled(self, value):
        self._addon.setSetting("enabled", "true" if value else "false")
        self.enabled = value

    def set_action(self, index):
        self._addon.setSetting("action", str(index))
        self.action = index
        self.refresh_label()

    def refresh_label(self):
        """El ajuste «Acción» que se ve es un texto: lo pone al día (en el idioma de Kodi)."""
        if self._addon.getSetting("action_label") != self.action_name:
            self._addon.setSetting("action_label", self.action_name)

    def job(self, source="schedule"):
        return Job(self.action, self.silent, self.countdown, self.snooze, self.wait_playback,
                   True, source)

    def key(self):
        """Lo que, si cambia, merece avisar al usuario."""
        return (self.enabled, self.action, self.hour, self.minute, tuple(self.days), self.repeat)

    # --- textos ---------------------------------------------------------

    @property
    def action_name(self):
        return action_name(self.action)

    @property
    def time_text(self):
        return "%02d:%02d" % (self.hour, self.minute)

    def days_text(self):
        if all(self.days):
            return tr(30413)
        return " ".join(tr(S_DAY_SHORT + i) for i in range(7) if self.days[i])

    # --- calendario -----------------------------------------------------

    def _at(self, day):
        return datetime.datetime.combine(day, datetime.time(self.hour, self.minute))

    def next_run(self, now):
        for offset in range(8):
            when = self._at(now.date() + datetime.timedelta(days=offset))
            if when > now and self.days[when.weekday()]:
                return when
        return None

    def due_between(self, last, now):
        """Hora programada que cae en (last, now], o None."""
        for day in sorted({last.date(), now.date()}):
            when = self._at(day)
            if last < when <= now and self.days[when.weekday()]:
                return when
        return None


def when_text(when, now):
    hhmm = when.strftime("%H:%M")
    delta = (when.date() - now.date()).days
    if delta == 0:
        day = tr(30411)
    elif delta == 1:
        day = tr(30412)
    else:
        day = tr(S_DAY_LONG + when.weekday())
    return "%s, %s" % (day, hhmm)


def _held_text(home):
    """Lo que está en marcha fuera de la programación (en espera, pospuesto, temporizador)."""
    if home.getProperty(PROP_WAITING):
        return tr(30431)
    snooze = home.getProperty(PROP_SNOOZE)
    if snooze:
        return tr(30432).format(time=snooze)
    timer = home.getProperty(PROP_TIMER)
    index = action_index(home.getProperty(PROP_TIMER_ACTION))
    if timer and index is not None:
        return tr(30434).format(action=action_name(index), time=timer)
    return ""


def schedule_text(cfg, now):
    """Texto del diálogo principal. Máximo 4 líneas: si no caben, Estuary desplaza el texto
    y la primera línea queda oculta."""
    lines = []
    mode = tr(30408) if cfg.repeat else tr(30409)
    held = _held_text(_home())
    if held:
        lines.append("[B]%s[/B]" % held)
    if cfg.enabled:
        lines.append(tr(30404).format(action=cfg.action_name, time=cfg.time_text))
        lines.append(tr(30407).format(days=cfg.days_text(), mode=mode))
        nxt = cfg.next_run(now)
        if nxt and not held:
            lines.append(tr(30410).format(when=when_text(nxt, now)))
    else:
        if not held:
            lines.append("[B]%s[/B]" % tr(30405))
        lines.append(tr(30406).format(action=cfg.action_name, time=cfg.time_text))
        lines.append(tr(30407).format(days=cfg.days_text(), mode=mode))
    if not available(cfg.action):
        lines.append("[COLOR red]%s[/COLOR]" % tr(30422).format(action=cfg.action_name))
    elif cfg.action != ACT_ALARM:
        lines.append(tr(30415) if cfg.silent else tr(30414).format(n=cfg.countdown))
    return "[CR]".join(lines)


def scheduled_notice(cfg, now):
    nxt = cfg.next_run(now)
    when = when_text(nxt, now) if nxt else cfg.time_text
    return tr(30420).format(action=cfg.action_name, when=when)


# --- ejecutar ----------------------------------------------------------------

def countdown(job, monitor):
    """Cuenta atrás cancelable. True = seguir adelante."""
    total = job.countdown

    def text(left):
        n = "%d:%02d" % divmod(left, 60) if left >= 60 else "%d s" % left
        return tr(30416).format(action=job.name, n=n) + "[CR]" + tr(30417)

    dlg = xbmcgui.DialogProgress()
    dlg.create(NAME, text(total))
    end = time.time() + total
    try:
        while True:
            left = end - time.time()
            if left <= 0:
                return True
            if dlg.iscanceled() or monitor.abortRequested():
                return False
            dlg.update(int(100 * left / total), text(int(math.ceil(left))))
            if monitor.waitForAbort(0.25):
                return False
    finally:
        dlg.close()


def run_action(job, monitor):
    """Ejecuta la acción (con cuenta atrás si toca). Devuelve DONE, CANCELLED o UNAVAILABLE."""
    if job.action == ACT_ALARM:
        xbmcgui.Dialog().ok(NAME, tr(30423).format(time=datetime.datetime.now().strftime("%H:%M")))
        return DONE

    builtin = ACTIONS[job.action][1]
    if not available(job.action):
        notify(tr(30422).format(action=job.name), xbmcgui.NOTIFICATION_ERROR)
        log("%s is not available on this system" % builtin, xbmc.LOGWARNING)
        return UNAVAILABLE

    if not job.silent and not countdown(job, monitor):
        log("%s cancelled by the user" % builtin)
        return CANCELLED

    log("running %s" % builtin)
    xbmc.executebuiltin(builtin)
    return DONE


# --- llamadas desde fuera ------------------------------------------------------

_TRUE = ("1", "true", "yes", "on", "si", "sí", "y")
_FALSE = ("0", "false", "no", "off", "n")
_DURATION = re.compile(r"^(?:(\d+)h)?(?:(\d+)m(?:in)?)?(?:(\d+)s)?$")


def parse_args(argv):
    """argv de RunScript → (palabras sueltas, parámetros clave=valor).

    Acepta "clave=valor" en argumentos separados (RunScript, JSON-RPC Addons.ExecuteAddon
    con params como objeto) o juntos al estilo URL: "?action=quit&in=10"."""
    words, params = [], {}
    for raw in argv:
        raw = raw.strip().strip("\"'").lstrip("?")
        for part in raw.split("&"):
            part = part.strip()
            if not part:
                continue
            if "=" in part:
                k, v = part.split("=", 1)
                params[k.strip().lower()] = unquote_plus(v.strip().strip("\"'"))
            else:
                words.append(part.lower())
    return words, params


def parse_bool(value):
    value = (value or "").strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise ValueError("not a boolean: %r" % value)


def parse_duration(value):
    """Segundos de "30" (minutos), "90s", "45m", "2h", "1h30m" o "1:30" (h:mm)."""
    value = (value or "").strip().lower().replace(" ", "")
    if re.match(r"^\d+(\.\d+)?$", value):
        return int(float(value) * 60)
    if re.match(r"^\d+:\d{1,2}$", value):
        h, m = value.split(":")
        return int(h) * 3600 + int(m) * 60
    match = _DURATION.match(value)
    if not value or not match:
        raise ValueError("not a duration: %r" % value)
    h, m, s = (int(x) if x else 0 for x in match.groups())
    return h * 3600 + m * 60 + s


def parse_at(value, now):
    """La próxima vez que el reloj marque HH:MM (hoy o mañana)."""
    h, m = (int(x) for x in value.strip().split(":")[:2])
    when = datetime.datetime.combine(now.date(), datetime.time(h, m))
    if when <= now:
        when += datetime.timedelta(days=1)
    return when


def build_request(words, params, cfg, now):
    """Traduce una llamada externa a (job, cuándo); cuándo = None si es inmediato.
    Lo que no se indica sale de los ajustes del add-on. Lanza ValueError si algo no vale."""
    name = params.get("action")
    if name is None and words and words[0] != "now":
        name = words[0]
    if name is None:
        index = cfg.action  # "now" o solo parámetros: la acción configurada
    else:
        index = action_index(name)
        if index is None:
            raise ValueError("unknown action %r" % name)

    job = cfg.job(source="external")
    job.action = index
    if "silent" in params:
        job.silent = parse_bool(params["silent"])
    if "countdown" in params:
        job.countdown = min(max(_int(params["countdown"], job.countdown), COUNTDOWN_MIN), COUNTDOWN_MAX)
        if "silent" not in params:
            job.silent = False  # pedir una cuenta atrás es pedir que se vea
    if "snooze" in params:
        job.snooze = max(_int(params["snooze"], job.snooze), 0)
    for key in ("wait", "wait_playback"):
        if key in params:
            job.wait_playback = parse_bool(params[key])
    if "notify" in params:
        job.notify = parse_bool(params["notify"])

    when = None
    if params.get("at"):
        when = parse_at(params["at"], now)
    else:
        for key in ("in", "delay", "after"):
            if params.get(key):
                seconds = parse_duration(params[key])
                if seconds > 0:
                    when = now + datetime.timedelta(seconds=seconds)
                break
    return job, when


def save_request(cfg, job, params):
    """remember=true: deja en los ajustes lo que trae la llamada (solo lo que trae).
    Con at=HH:MM, además, esa hora pasa a ser la de la programación y esta se activa
    (con los días y la repetición que ya hubiera); in=... no se guarda: es de una sola vez."""
    a = cfg._addon
    if job.action != cfg.action:
        cfg.set_action(job.action)
    if "silent" in params or "countdown" in params:
        a.setSetting("silent", "true" if job.silent else "false")
    if "countdown" in params:
        a.setSetting("countdown", str(min(job.countdown, COUNTDOWN_MAX)))
    if "snooze" in params:
        a.setSetting("snooze", str(min(job.snooze, 60)))
    if "wait" in params or "wait_playback" in params:
        a.setSetting("wait_playback", "true" if job.wait_playback else "false")
    if params.get("at"):
        h, m = (int(x) for x in params["at"].strip().split(":")[:2])
        a.setSetting("time", "%02d:%02d" % (h, m))
        cfg.set_enabled(True)
    log("external call saved to settings: %s" % ", ".join(sorted(params)))


def request_timer(job, when):
    """Pasa el temporizador al servicio (es el que sigue vivo mientras Kodi esté abierto)."""
    data = {"at": time.mktime(when.timetuple()), "job": job.to_dict()}
    _home().setProperty(PROP_REQUEST, json.dumps(data))
    log("timer requested: %s at %s" % (job.key, when.strftime("%Y-%m-%d %H:%M:%S")))


def run_external(words, params):
    cfg = Config()
    now = datetime.datetime.now()
    try:
        job, when = build_request(words, params, cfg, now)
    except ValueError as exc:
        log("bad call %r %r: %s" % (words, params, exc), xbmc.LOGERROR)
        notify(tr(30433).format(args=", ".join(words + ["%s=%s" % kv for kv in sorted(params.items())])),
               xbmcgui.NOTIFICATION_ERROR)
        return

    if not available(job.action):
        notify(tr(30422).format(action=job.name), xbmcgui.NOTIFICATION_ERROR)
        log("%s is not available on this system" % job.key, xbmc.LOGWARNING)
        return

    try:
        remember = parse_bool(params.get("remember", params.get("save", "false")))
    except ValueError:
        remember = False
    if remember:
        save_request(cfg, job, params)
        if params.get("at"):
            return  # ahora es la programación del add-on: la ejecuta el servicio

    if when is None and job.waits_for_playback and xbmc.Player().isPlaying():
        when = now  # que espere el servicio, que es el que vigila la reproducción
    if when is not None:
        request_timer(job, when)
        return

    log("external call: %s now" % job.key)
    if run_action(job, xbmc.Monitor()) == CANCELLED:
        notify(tr(30418).format(action=job.name))


def choose_action():
    """El selector del ajuste «Acción»: solo enseña lo que este sistema puede hacer."""
    cfg = Config()
    options = available_actions()
    labels = [action_name(i) for i in options]
    pre = options.index(cfg.action) if cfg.action in options else 0
    sel = xbmcgui.Dialog().select(tr(30102), labels, preselect=pre)
    if sel >= 0:
        cfg.set_action(options[sel])


# --- script (al pulsar el complemento) ---------------------------------------

def run_script(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    words, params = parse_args(argv)
    cmd = words[0] if words else ""
    cfg = Config()

    if cmd == "settings" and not params:
        _addon().openSettings()
    elif cmd == "choose":
        choose_action()
        _addon().openSettings()  # el botón cerró los ajustes: se vuelven a abrir
    elif cmd == "cancel" or params.get("action", "").lower() == "cancel":
        _home().setProperty(PROP_ABORT, "1")
        log("external call: cancel")
    elif cmd in ("toggle", "enable", "on", "disable", "off") and not params:
        cfg.set_enabled(not cfg.enabled if cmd == "toggle" else cmd in ("enable", "on"))
    elif words or params:
        run_external(words, params)
    else:
        show_dialog(cfg)


def show_dialog(cfg):
    now = datetime.datetime.now()
    home = _home()
    held = bool(home.getProperty(PROP_SNOOZE) or home.getProperty(PROP_WAITING) or home.getProperty(PROP_TIMER))
    if held:
        custom = tr(30429)          # anular lo pospuesto, en espera o el temporizador
    else:
        custom = tr(30401)          # ajustes
    choice = xbmcgui.Dialog().yesnocustom(
        NAME,
        schedule_text(cfg, now),
        customlabel=custom,
        nolabel=tr(30403),
        yeslabel=tr(S_ACTION_NOW + cfg.action),
    )
    if choice == 1:
        if run_action(cfg.job(), xbmc.Monitor()) == CANCELLED:
            notify(tr(30418).format(action=cfg.action_name))
    elif choice == 2 and held:
        home.setProperty(PROP_ABORT, "1")
    elif choice == 2:
        _addon().openSettings()


# --- servicio ----------------------------------------------------------------

class Service(xbmc.Monitor):

    def __init__(self):
        super(Service, self).__init__()
        self.player = xbmc.Player()
        self.pending = None   # Job a punto de ejecutarse (quizá esperando a la reproducción)
        self.snoozed = None   # (hasta, Job)
        self.timer = None     # (cuándo, Job) pedido desde fuera

    def _set_waiting(self, value):
        if value:
            _home().setProperty(PROP_WAITING, "1")
        else:
            _home().clearProperty(PROP_WAITING)

    def _set_snooze(self, until, job=None):
        self.snoozed = (until, job) if until else None
        if until:
            _home().setProperty(PROP_SNOOZE, until.strftime("%H:%M"))
        else:
            _home().clearProperty(PROP_SNOOZE)

    def _set_timer(self, when, job=None):
        home = _home()
        self.timer = (when, job) if when else None
        if when:
            home.setProperty(PROP_TIMER, when.strftime("%H:%M"))
            home.setProperty(PROP_TIMER_ACTION, job.key)
            home.setProperty(PROP_TIMER_DATA, json.dumps({"at": time.mktime(when.timetuple()), "job": job.to_dict()}))
        else:
            for prop in (PROP_TIMER, PROP_TIMER_ACTION, PROP_TIMER_DATA):
                home.clearProperty(prop)

    def _clear(self, source=None):
        """Anula lo pendiente y lo pospuesto (solo de ese origen, si se indica). True si había algo."""
        found = False
        if self.pending and source in (None, self.pending.source):
            self.pending = None
            self._set_waiting(False)
            found = True
        if self.snoozed and source in (None, self.snoozed[1].source):
            self._set_snooze(None)
            found = True
        if self.timer and source in (None, "external"):
            self._set_timer(None)
            found = True
        return found

    @staticmethod
    def _load_timer(raw):
        data = json.loads(raw)
        return datetime.datetime.fromtimestamp(float(data["at"])), Job.from_dict(data["job"])

    def _take_request(self, now):
        home = _home()
        raw = home.getProperty(PROP_REQUEST)
        if not raw:
            return
        home.clearProperty(PROP_REQUEST)
        try:
            when, job = self._load_timer(raw)
        except (KeyError, TypeError, ValueError) as exc:
            log("bad timer request %r: %s" % (raw, exc), xbmc.LOGERROR)
            return
        if self.snoozed and self.snoozed[1].source == "external":
            self._set_snooze(None)  # el temporizador nuevo sustituye al anterior
        self._set_timer(when, job)
        log("timer set: %s at %s" % (job.key, when.strftime("%Y-%m-%d %H:%M:%S")))
        if job.notify and when > now:
            notify(tr(30420).format(action=job.name, when=when_text(when, now)))

    def _offer_snooze(self, job, now):
        if not job.snooze:
            notify(tr(30418).format(action=job.name))
            return
        yes = xbmcgui.Dialog().yesno(
            NAME,
            tr(30418).format(action=job.name) + "[CR]" + tr(30427).format(n=job.snooze),
            nolabel=tr(30426),
            yeslabel=tr(30424).format(n=job.snooze),
            autoclose=SNOOZE_ASK * 1000,
        )
        if yes:
            until = now + datetime.timedelta(minutes=job.snooze)
            self._set_snooze(until, job)
            notify(tr(30428).format(action=job.name, time=until.strftime("%H:%M")))
            log("snoozed until %s" % until.strftime("%H:%M"))

    def _fire(self, job):
        self._set_waiting(False)
        result = run_action(job, self)
        if result == CANCELLED:
            self._offer_snooze(job, datetime.datetime.now())

    def _startup(self, now):
        addon = _addon()
        version = addon.getAddonInfo("version")
        if addon.getSetting("about_version") != version:  # para la sección "Acerca de"
            addon.setSetting("about_version", version)

        home = _home()
        options = available_actions()
        home.setProperty(PROP_ACTIONS, ",".join(ACTIONS[i][0] for i in options))
        log("available actions: %s" % home.getProperty(PROP_ACTIONS))

        self._set_waiting(False)
        self._set_snooze(None)
        home.clearProperty(PROP_ABORT)
        raw = home.getProperty(PROP_TIMER_DATA)  # el servicio se reinició (p. ej. al actualizar)
        self._set_timer(None)
        if raw:
            try:
                self._set_timer(*self._load_timer(raw))
            except (KeyError, TypeError, ValueError):
                pass

        cfg = Config()
        if cfg.action not in options and not cfg.enabled:
            # p. ej. «Apagar el equipo» (el valor por defecto) en Android: se elige otra
            cfg.set_action(ACT_QUIT if ACT_QUIT in options else options[0])
            log("default action not available here, using %s" % ACTIONS[cfg.action][0])
        cfg.refresh_label()

        if cfg.enabled and not cfg.autostart:
            cfg.set_enabled(False)
            log("schedule turned off at startup (start with Kodi is off)")
        elif cfg.enabled and cfg.action not in options:
            notify(tr(30422).format(action=cfg.action_name), xbmcgui.NOTIFICATION_WARNING)
        elif cfg.enabled and cfg.notify:
            notify(scheduled_notice(cfg, now))
        return cfg

    def run(self):
        now = datetime.datetime.now()
        cfg = self._startup(now)
        last_key = cfg.key()
        last = now

        while not self.waitForAbort(TICK):
            now = datetime.datetime.now()
            cfg = Config()

            if _home().getProperty(PROP_ABORT):
                _home().clearProperty(PROP_ABORT)
                job = self.pending or (self.snoozed and self.snoozed[1]) or (self.timer and self.timer[1])
                if self._clear():
                    notify(tr(30418).format(action=job.name))

            self._take_request(now)

            key = cfg.key()
            if key != last_key:
                if key[1] != last_key[1]:
                    cfg.refresh_label()
                last_key = key
                self._clear("schedule")  # un cambio del usuario anula lo pendiente y lo pospuesto
                notify(scheduled_notice(cfg, now) if cfg.enabled else tr(30419))

            if not self.pending:
                if self.snoozed and now >= self.snoozed[0]:
                    log("snooze over")
                    self.pending = self.snoozed[1]
                    self._set_snooze(None)
                elif self.timer and now >= self.timer[0]:
                    when, job = self.timer
                    self._set_timer(None)
                    if (now - when).total_seconds() <= GRACE:
                        log("%s: timer %s reached" % (job.key, when.strftime("%H:%M")))
                        self.pending = job
                    else:
                        log("%s: timer %s missed (device asleep?), dropped" % (job.key, when.strftime("%H:%M")))
                elif cfg.enabled:
                    due = cfg.due_between(last, now)
                    if due and (now - due).total_seconds() <= GRACE:
                        log("%s: scheduled time %s reached" % (ACTIONS[cfg.action][0], due.strftime("%H:%M")))
                        self.pending = cfg.job()
                        if self.snoozed and self.snoozed[1].source == "schedule":
                            self._set_snooze(None)
                        if not cfg.repeat:
                            cfg.set_enabled(False)  # solo una vez
                            last_key = cfg.key()     # sin aviso de "desactivada"

            if self.pending:
                job = self.pending
                if job.waits_for_playback and self.player.isPlaying():
                    if not _home().getProperty(PROP_WAITING):
                        log("waiting for playback to finish")
                        self._set_waiting(True)
                        notify(tr(30421).format(action=job.name))
                else:
                    self.pending = None
                    self._fire(job)
                    now = datetime.datetime.now()  # la cuenta atrás ha consumido tiempo

            last = now

        self.pending = None
        self._set_waiting(False)
        self._set_snooze(None)
        # el temporizador se queda en PROP_TIMER_DATA por si el servicio vuelve a arrancar


def run_service():
    log("service started")
    Service().run()
    log("service stopped")

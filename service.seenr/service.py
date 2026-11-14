# -*- coding: utf-8 -*-
"""Seenr pour Kodi : signale à Seenr ce qui est lu dans le lecteur.

Pourquoi un add-on et pas un webhook : Kodi n'en émet pas, et surtout un add-on
tourne DANS le lecteur. Il voit donc la lecture, la pause, l'arrêt et la position
exacte, là où un intermédiaire ne verrait au mieux qu'un début de lecture.

Le service poste le contrat natif de Seenr
(App\\Services\\Scrobble\\Adapters\\NativeScrobbleAdapter) sur l'URL de connexion
que le membre colle dans les réglages. Aucune clé d'API : l'URL PORTE le jeton,
c'est donc un secret, et elle n'est jamais écrite au journal en clair.

Trois pièges de l'API Kodi que ce fichier contourne, et qu'il ne faut pas
« simplifier » :

  1. dans onPlayBackStopped / onPlayBackEnded, le lecteur est DÉJÀ parti :
     getTime() lève. La position est donc échantillonnée pendant la lecture par
     la boucle de service, et c'est la dernière valeur connue qui part avec
     l'arrêt ;
  2. les rappels du lecteur s'exécutent sur un thread de Kodi : y faire un appel
     HTTP gèlerait l'interface. Tout envoi passe par une file et un thread
     ouvrier ;
  3. quitter Kodi avec un titre encore chargé (en pause, ou lancé puis laissé
     derrière le menu par « retour ») ferme le lecteur PUIS arrête les services,
     dans la même seconde. Le rappel d'arrêt peut ne jamais nous parvenir, et
     ce qui attend dans la file meurt avec le thread ouvrier. Sans l'arrêt, Seenr
     laisse le film « En cours » jusqu'à sa fin présumée (signalement #243,
     10/2026) : à la fermeture, on envoie donc nous-mêmes l'arrêt du titre
     encore chargé, et on vide la file avant de rendre la main (voir `shutdown`).
"""

import json
import queue
import threading
import time
import urllib.error
import urllib.request

import xbmc
import xbmcaddon
import xbmcgui

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')

# Échantillonnage de la position pendant la lecture. Une seconde suffit : la
# valeur ne sert qu'à dire « arrêté à 87 % », pas à faire de la synchro fine.
POLL_SECONDS = 1

HTTP_TIMEOUT = 10

# Temps laissé à la file pour se vider quand Kodi se ferme. Kodi accorde quelques
# secondes à un service avant de l'interrompre de force : on en prend moins, et un
# serveur injoignable ne retient jamais la fermeture au-delà.
FLUSH_SECONDS = 3


# Niveau debug par défaut : règle du dépôt officiel Kodi (« use the debug
# logging level only »), les vrais échecs restent en avertissement ou erreur.
def log(message, level=xbmc.LOGDEBUG):
    xbmc.log('[%s] %s' % (ADDON_ID, message), level)


def rpc(method, params=None):
    """Appel JSON-RPC interne à Kodi.

    On passe par là plutôt que par InfoTagVideo : `getUniqueID()` n'existe qu'à
    partir de Kodi 20, et l'add-on doit marcher depuis Kodi 19.
    """
    payload = {'jsonrpc': '2.0', 'id': 1, 'method': method}
    if params is not None:
        payload['params'] = params

    try:
        raw = xbmc.executeJSONRPC(json.dumps(payload))
        return json.loads(raw)
    except Exception as error:  # pragma: no cover - dépend de l'hôte Kodi
        log('JSON-RPC %s a échoué : %s' % (method, error), xbmc.LOGERROR)
        return {}


def unique_ids(source):
    """Traduit le `uniqueid` de Kodi vers les identifiants attendus par Seenr.

    Kodi range les valeurs en chaînes, et sème des clés inconnues (« unknown »)
    qu'on laisse tomber plutôt que de les envoyer au hasard.
    """
    ids = {}
    if not isinstance(source, dict):
        return ids

    for key, target in (('tmdb', 'tmdb'), ('imdb', 'imdb'), ('tvdb', 'tvdb')):
        value = source.get(key)
        if value in (None, '', 0):
            continue
        if target == 'imdb':
            ids['imdb'] = str(value)
        else:
            try:
                ids[target] = int(value)
            except (TypeError, ValueError):
                continue

    return ids


class Sender(object):
    """File d'envoi : un thread, jamais celui des rappels du lecteur."""

    # Kodi est en train de se fermer (posé par `stop`).
    closing = False

    def __init__(self):
        self.queue = queue.Queue()
        self.worker = threading.Thread(target=self._run)
        self.worker.daemon = True
        self.worker.start()

    def send(self, payload):
        self.queue.put(payload)

    def stop(self):
        """Vide la file avant de rendre la main, sans jamais attendre plus de
        FLUSH_SECONDS.

        Le thread ouvrier est un démon : il meurt avec le service. Poser le seul
        marqueur de fin perdait ce qui restait à envoyer, et c'est précisément à
        la fermeture qu'il reste l'événement qui compte, l'arrêt du titre.
        """
        self.closing = True
        self.queue.put(None)
        self.worker.join(FLUSH_SECONDS)

    def _run(self):
        while True:
            payload = self.queue.get()
            if payload is None:
                return
            try:
                self._post(payload)
            except Exception as error:  # pragma: no cover
                log('envoi impossible : %s' % error, xbmc.LOGERROR)

    def _post(self, payload):
        endpoint = ADDON.getSetting('endpoint').strip()
        if not endpoint:
            log('aucune URL de connexion configurée, envoi ignoré', xbmc.LOGWARNING)
            return

        body = json.dumps(payload).encode('utf-8')
        request = urllib.request.Request(
            endpoint,
            data=body,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': 'Seenr-Kodi/%s' % ADDON.getAddonInfo('version'),
            },
            method='POST',
        )

        try:
            with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
                status = response.getcode()
        except urllib.error.HTTPError as error:
            # 401 : jeton révoqué ou URL tronquée à la copie. C'est le seul cas
            # que le membre peut corriger lui-même, donc le seul qu'on lui dit.
            if error.code == 401:
                self._notify(ADDON.getLocalizedString(30010))
            log('refus du serveur (%s)' % error.code, xbmc.LOGERROR)
            return
        except Exception as error:
            log('serveur injoignable : %s' % error, xbmc.LOGWARNING)
            return

        log('événement %s envoyé (%s)' % (payload.get('event'), status))

        # Pas de notification pendant la fermeture : l'interface s'en va, et le
        # membre ne la verrait pas.
        if payload.get('event') in ('scrobble', 'stop') and not self.closing and ADDON.getSettingBool('notify'):
            self._notify(ADDON.getLocalizedString(30011))

    def _notify(self, message):
        xbmcgui.Dialog().notification(ADDON_NAME, message, ADDON.getAddonInfo('icon'), 4000)


class SeenrPlayer(xbmc.Player):
    """Traduit les rappels du lecteur en événements Seenr."""

    def __init__(self, sender):
        super(SeenrPlayer, self).__init__()
        self.sender = sender
        self.item = None
        self.position = 0.0
        self.duration = 0.0
        # Une fin peut venir de deux côtés à la fermeture de Kodi : son rappel
        # d'arrêt, et `close`. Un seul des deux doit l'envoyer.
        self.lock = threading.Lock()

    # -- rappels Kodi ------------------------------------------------------

    def onAVStarted(self):
        self.item = self._describe()
        self.position = 0.0
        self.duration = 0.0
        if self.item is not None:
            self._emit('start')

    def onPlayBackPaused(self):
        self._emit('pause')

    def onPlayBackResumed(self):
        self._emit('start')

    def onPlayBackStopped(self):
        # Arrêt manuel : la progression décide (Seenr coche au-delà de son seuil
        # de complétion, pose un point de reprise en dessous).
        self._finish('stop')

    def onPlayBackEnded(self):
        # Fin naturelle du fichier : c'est un « vu » sans discussion possible.
        self._finish('scrobble')

    def onPlayBackError(self):
        # Lecture coupée par une erreur (flux perdu, fichier illisible) : c'est un
        # arrêt comme un autre, sans quoi la séance resterait ouverte sur Seenr.
        self._finish('stop')

    def close(self):
        """Kodi se ferme : arrête ce qui est encore chargé.

        Kodi ferme le lecteur juste avant d'arrêter les services, et son rappel
        d'arrêt n'arrive pas toujours jusqu'ici. Faute d'arrêt, Seenr gardait le
        titre « En cours » jusqu'à sa fin présumée. La position est la dernière
        échantillonnée, comme pour tout arrêt. Sans effet quand le rappel est
        passé avant : il a déjà tout envoyé et vidé l'état.
        """
        self._finish('stop')

    # -- état --------------------------------------------------------------

    def sample(self):
        """Mémorise la position courante. Appelée par la boucle de service.

        C'est tout l'intérêt : à l'arrêt, le lecteur ne sait plus rien dire.
        """
        try:
            if not self.isPlayingVideo():
                return
            self.position = float(self.getTime())
            self.duration = float(self.getTotalTime())
        except Exception:
            # Le lecteur s'est arrêté entre le test et la lecture : sans intérêt.
            pass

    def _finish(self, event):
        """Dernier événement d'un titre : envoyé une fois, puis l'état est vidé."""
        with self.lock:
            self._emit(event)
            self._reset()

    def _reset(self):
        self.item = None
        self.position = 0.0
        self.duration = 0.0

    def _emit(self, event):
        if self.item is None:
            return

        payload = dict(self.item)
        payload['event'] = event
        payload['platform'] = 'kodi'

        # Une durée nulle veut dire « on n'a pas su échantillonner » : mieux vaut
        # ne rien dire de la progression qu'annoncer 0 %, que Seenr lirait comme
        # un abandon immédiat.
        if self.duration > 0:
            payload['position'] = int(self.position)
            payload['duration'] = int(self.duration)

        self.sender.send(payload)

    # -- identification du titre -------------------------------------------

    def _describe(self):
        """Ce qui est en train d'être lu, sous la forme attendue par Seenr.

        Une lecture hors bibliothèque (flux d'un add-on) n'a pas d'identifiants :
        on part alors avec les titres, que Seenr sait résoudre. Ce qui n'est ni un
        film ni un épisode (musique, clip, PVR) n'est pas envoyé du tout.
        """
        players = (rpc('Player.GetActivePlayers').get('result') or [])
        player = next((p for p in players if p.get('type') == 'video'), None)
        if player is None:
            return None

        details = rpc('Player.GetItem', {
            'playerid': player.get('playerid'),
            'properties': ['title', 'showtitle', 'season', 'episode', 'year', 'uniqueid', 'tvshowid'],
        })
        item = (details.get('result') or {}).get('item') or {}
        media = item.get('type')

        if media == 'movie':
            return {
                'media_type': 'movie',
                'ids': unique_ids(item.get('uniqueid')),
                'title': item.get('title') or item.get('label') or '',
                'year': item.get('year') or None,
            }

        if media == 'episode':
            season = item.get('season')
            episode = item.get('episode')

            return {
                'media_type': 'episode',
                # En bibliothèque, les uniqueid d'un épisode désignent l'ÉPISODE.
                # Hors bibliothèque, c'est l'add-on de streaming qui les pose, et
                # la plupart y mettent ceux de la SÉRIE (signalement #255) : c'est
                # Seenr qui les reconnaît et les range du bon côté
                # (CatalogResolver::untangledIds), ne pas trancher ici à l'aveugle.
                'episode_ids': unique_ids(item.get('uniqueid')),
                'ids': self._show_ids(item.get('tvshowid')),
                'title': item.get('showtitle') or '',
                'episode_title': item.get('title') or '',
                'season': season if isinstance(season, int) and season >= 0 else None,
                'episode': episode if isinstance(episode, int) and episode > 0 else None,
            }

        return None

    def _show_ids(self, tvshowid):
        """Identifiants de la SÉRIE, quand l'épisode vient de la bibliothèque."""
        if not isinstance(tvshowid, int) or tvshowid <= 0:
            return {}

        details = rpc('VideoLibrary.GetTVShowDetails', {
            'tvshowid': tvshowid,
            'properties': ['uniqueid'],
        })
        show = (details.get('result') or {}).get('tvshowdetails') or {}

        return unique_ids(show.get('uniqueid'))


def shutdown(player, sender):
    """Kodi se ferme : l'arrêt du titre encore chargé d'abord, la file ensuite.

    Dans cet ordre : vider la file avant d'y avoir mis l'arrêt le laisserait
    derrière, et c'est lui qui retire le titre de « En cours » sur Seenr.
    """
    player.close()
    sender.stop()


def main():
    log('démarrage')

    sender = Sender()
    player = SeenrPlayer(sender)
    monitor = xbmc.Monitor()

    while not monitor.abortRequested():
        player.sample()
        if monitor.waitForAbort(POLL_SECONDS):
            break

    shutdown(player, sender)
    log('arrêt')


if __name__ == '__main__':
    main()

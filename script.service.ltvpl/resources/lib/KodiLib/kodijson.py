#
#       Copyright (C) 2016
#       Jean-Christophe Saad-Dupuy
#
#       Portions Copyright (C) 2018
#       John Moore (jmooremcc@hotmail.com)
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with XBMC; see the file COPYING.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#
"""XBMC/Kodi jsonclient library module."""
import json
from resources.lib.Utilities.DebugPrint import DbgPrint

MODULEDEBUGMODE=True
from . kodiflags import KODI_ENV

if KODI_ENV:
    import xbmc
else:
    import requests

__Version__ = "1.0.1"

# this list will be extended with types dynamically defined
__all__ = ["PLAYER_VIDEO",
           "KodiTransport",
           "KodiJsonTransport",
           "Kodi",
           "KodiNamespace", ]

# KodiLib constant
PLAYER_VIDEO = 1


# Dynamic namespace class injection
__KODI_NAMESPACES__ = (
    "Addons", "Application", "AudioLibrary", "Favourites", "Files", "GUI",
    "Input", "JSONRPC", "Playlist", "Player", "PVR", "Settings", "System",
    "VideoLibrary", "xbmc")


class KodiTransport(object):
    """Base class for KodiLib transport."""

    def execute(self, method, *args, **kwargs):
        """Execute method with given args."""
        pass  # pragma: no cover


class KodiJsonTransport(KodiTransport):
    """HTTP Json transport."""

    def __init__(self, url, username='xbmc', password='xbmc'):
        """KodiLib Json Transport constructor.

        Args:
            url (str): url of the kodi json http endpoint
            username (str): kodi username
            password (str): kodi password
        """
        self.url = url
        self.username = username
        self.password = password
        self._id = 0

    def execute(self, method, *args, **kwargs):
        """Execute given method with given arguments."""
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'python-kodi'
        }
        # Params are given as a dictionnary
        if len(args) == 1:
            args = args[0]
            params = kwargs
            # Use kwargs for param=value style
        else:
            args = kwargs
        params = {'jsonrpc': '2.0', 'id': self._id}
        self._id += 1
        params['method'] = method
        params['params'] = args

        values = json.dumps(params)
        status = None

        if KODI_ENV:
            import xbmc

            # DbgPrint("Calling executeJSONRPC: {}".format(values))
            try:
                status = json.loads(xbmc.executeJSONRPC(values.encode('utf-8')))
            except Exception as e:
                pass
                # DbgPrint("executeJSONRPC Error: {}".format(str(e)))

            # DbgPrint("JSONRPC Return Value: {}".format(status))
            return status
        else:
            import requests
            resp = requests.post(self.url,
                                 values.encode('utf-8'),
                                 headers=headers,
                                 auth=(self.username, self.password))
            resp.raise_for_status()
            return resp.json()


class Kodi(object):
    """KodiLib client."""

    def __init__(self, url, username='xbmc', password='xbmc'):
        """KodiLib object constructor.

        Args:
            url (str): url of the kodi json http endpoint
            username (str): kodi username
            password (str): kodi password
        """
        self.transport = KodiJsonTransport(url, username, password)
        # Dynamic namespace class instanciation
        # we obtain class by looking up in globals
        _globals = globals()
        for cl in __KODI_NAMESPACES__:
            setattr(self, cl, _globals[cl](self.transport))

    def execute(self, *args, **kwargs):
        """Execute method with given args and kwargs."""
        self.transport.execute(*args, **kwargs)


class KodiNamespace(object):
    """Base class for KodiLib namespace."""

    def __init__(self, kodi):
        """KodiLib namespace.

        Args:
            kodi (Kodi): kodi instance
        """
        self.kodi = kodi

    def __getattr__(self, name):
        """Overide default __getattr__.

        This translate objects attributes to the right namespace.
        """
        klass = self.__class__.__name__
        method = name
        kodimethod = "{}.{}".format(klass, method)

        def hook(*args, **kwargs):
            """Hook for dynamic method definition."""
            return self.kodi.execute(kodimethod, *args, **kwargs)

        return hook

# inject new type in module locals
_LOCALS_ = locals()
for _classname in __KODI_NAMESPACES__:
    # define a new type extending KodiNamespace
    # equivalent to
    #
    # class Y(KodiNamespace):
    #    pass
    _LOCALS_[_classname] = type(_classname, (KodiNamespace, ), {})
    # inject class in __all__ for import * to work
    __all__.append(_classname)


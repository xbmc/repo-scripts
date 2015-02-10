#
#  MythBox for XBMC - http://mythbox.googlecode.com
#  Copyright (C) 2010 analogue@yahoo.com
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

from twisted.conch import manhole, telnet
from twisted.conch.insults import insults
from twisted.internet import protocol, reactor
from twisted.cred import portal, checkers 
from zope.interface import implements
from bus import Event


class DebugShell(object):
    
    def __init__(self, bus, port=9999, namespace=None):
        self.port = port
        self.namespace = namespace
        bus.register(self)
    
    def start(self):
        
        def run_in_thread():
            checker = checkers.InMemoryUsernamePasswordDatabaseDontUse(mb='mb')
            #checker = checkers.AllowAnonymousAccess()
            
            telnetRealm = _StupidRealm(telnet.TelnetBootstrapProtocol,
                                       insults.ServerProtocol,
                                       manhole.ColoredManhole,
                                       self.namespace)
        
            telnetPortal = portal.Portal(telnetRealm, [checker])
            telnetFactory = protocol.ServerFactory()
            telnetFactory.protocol = makeTelnetProtocol(telnetPortal)
            port = reactor.listenTCP(self.port, telnetFactory)
            reactor.run(installSignalHandlers=False)
            
        from threading import Thread
        worker = Thread(target = run_in_thread)
        worker.start()
    
    def stop(self):
        reactor.callFromThread(reactor.stop)

    def onEvent(self, event):
        if event['id'] == Event.SHUTDOWN:
            self.stop()

    
#
#  Ripped from twisted -- direct import pulled in ssh deps which we don't have
#
class makeTelnetProtocol:
    def __init__(self, portal):
        self.portal = portal

    def __call__(self):
        auth = telnet.AuthenticatingTelnetProtocol
        #auth = telnet.StatefulTelnetProtocol
        args = (self.portal,)
        return telnet.TelnetTransport(auth, *args)


#
#  Ripped from twisted -- direct import pulled in ssh deps which we don't have
#
class _StupidRealm:
    implements(portal.IRealm)

    def __init__(self, proto, *a, **kw):
        self.protocolFactory = proto
        self.protocolArgs = a
        self.protocolKwArgs = kw

    def requestAvatar(self, avatarId, *interfaces):
        if telnet.ITelnetProtocol in interfaces:
            return (telnet.ITelnetProtocol,
                    self.protocolFactory(*self.protocolArgs, **self.protocolKwArgs),
                    lambda: None)
        raise NotImplementedError()

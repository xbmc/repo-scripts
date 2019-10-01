#
#       Copyright (C) 2018
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

import socket
from threading import Thread
from resources.lib.Network.utilities import Utilities, DataMode, decodeResponse, decodeRequest, \
    decodeErrorResponse, decodeNotification, encodeNotification, PYVER
from .SecretSauce import *
from resources.lib.Utilities.Messaging import Cmd, MsgType
from resources.lib.Utilities.DebugPrint import DbgPrint
from resources.lib.Utilities.PythonEvent import Event

__Version__ = "1.0.2"

def getNewSocket():
    socketObj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socketObj.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    return socketObj


def getClientPort(conn):
    return conn.getsockname()


class Server(Thread, Utilities):
    def __init__(self, address, maxConnections=1, dataMode=DataMode.JSON, servername="LTVPL_Server"):
        Thread.__init__(self, name=servername)
        Utilities.__init__(self)
        self.clientList = list()
        self.address = address
        self.GoFlag = True
        self.maxConnections = maxConnections
        self.dataMode = dataMode
        # EventHandler(conn,data)
        self.dataReceivedEvent = Event("dataReceivedEvent",spawn=True)

    def addDataReceivedEventHandler(self, handler):
        self.dataReceivedEvent.AddHandler(handler)

    def fireDataReceivedEvent(self, conn, data):
        self.dataReceivedEvent(conn, data)

    def run(self):
        DbgPrint("Run:\n{}\n{}".format(ServerHost, ServerPort))
        self.Dispatcher()
        DbgPrint("Run:Finished Calling Dispatcher")

    def stop(self):
        self.GoFlag = False
        DbgPrint("Server Shutting Down")
        for client in self.clientList:
            client.close()

        DbgPrint("***Server Shutdown Final Stage")
        try:
            tmp = getNewSocket()
            tmp.settimeout(5)
            tmp.connect(('127.0.0.1',ServerPort))
            tmp.settimeout(None)
            tmp.close()
            self.socketObj.close()

        except Exception as e:
            print(e)

        DbgPrint("***Server Finally Stopped.....")

    def __del__(self):
        self.socketObj.close()

    def ConnectionCheck(self, conn):
        data = None
        countdown = 60
        while countdown > 0:
            try:
                conn.settimeout(10)
                data = conn.recv(1024).decode()
                if RUHERE in data:
                    conn.send(IAMHERE.encode())
                    DbgPrint("Server: Connection Test Has Suceeded!!!")
                    conn.settimeout(None)
                    return
            except Exception as e:
                countdown -= 1

        DbgPrint("Server: Connection Test Has Failed!!!")
        raise Exception("ERROR: Connection to Client Failed!!")

    def translateData(self, data):
        return self._processData(data)

    def _processData(self, data):
        rdata = None
        try:
            if self.dataMode == DataMode.JSON:
                rdata = self.rawWriteJSON(data)
            elif self.dataMode == DataMode.PKL:
                rdata = self.rawWritePKL(data)
            elif self.dataMode == DataMode.XML:
                rdata = data
            else:
                rdata = data
        except:
            pass

        return rdata


    def sendNotification(self, msg):
        DbgPrint("NumClients to Notify: {}".format(len(self.clientList)))
        notification= self._processData(encodeNotification(msg)) + DATAEndMarker
        DbgPrint("Notification Sent: {}".format(notification))
        for client in self.clientList:
            client.send(notification.encode())


    def ClientHandler(self, connection, address):
        DbgPrint("address:{}".format(address))
        self.ConnectionCheck(connection)  # check to see if we are talking
        self.clientList.append(connection)
        recvData=''

        while True:
            try:
                if self.dataMode == DataMode.JSON:
                    recvData = self.readJSON(connection)
                elif self.dataMode == DataMode.PKL:
                    recvData = self.readPKL(connection)
                elif self.dataMode == DataMode.XML:
                    pass
                else:
                    recvData = connection.recv(2048).decode()

                DbgPrint("Server***>", recvData)

                if recvData == EndSession or recvData is None:
                    self.clientList.remove(connection)
                    try:
                        connection.close()
                    except:
                        pass

                    DbgPrint("\nEnding Session\n")
                    return

                elif recvData == ShutDown:
                    DbgPrint("Received Shutdown Command")
                    self.clientList.remove(connection)
                    connection.close()
                    self.stop()
                    return

                self.fireDataReceivedEvent(connection, recvData)

            except Exception as e:
                DbgPrint("ERROR:", str(e))
                try:
                    self.clientList.remove(connection)
                except Exception as e:
                    DbgPrint("*ERROR:", str(e))

                connection.close()
                return

    def Dispatcher(self):
        DbgPrint("Dispatcher Called")
        self.socketObj = getNewSocket()
        self.socketObj.bind(self.address)
        self.socketObj.listen(self.maxConnections)

        while self.GoFlag:
            try:
                self.socketObj.settimeout(5)
                connection, address = self.socketObj.accept()
                self.socketObj.settimeout(None)
                if self.GoFlag:
                    DbgPrint("Connection Made with {}".format(address))
                    if self.maxConnections > 1:
                        DbgPrint("Dispatcher: Launch Thread")
                        Thread(target=self.ClientHandler, name="Thread-Dispatcher", args=(connection, address)).start()
                    else:
                        DbgPrint("Dispatcher: Launch No Thread")
                        self.ClientHandler(connection, address)
                else:
                    connection.close()
                    DbgPrint("Server Exiting...")
            except Exception as e:
                pass

        # self.stop()
        DbgPrint("Server Stopped...")


class Client(Utilities):
    def __init__(self, address, commDataHandler=None, dataMode=DataMode.JSON, servername="LTVPL_Client"):
        Utilities.__init__(self)
        self.dataMode = dataMode
        self.GoFlag = True
        self.commDataHandler = commDataHandler
        self.servername=servername

        try:
            self.socketObj = getNewSocket()
            DbgPrint("Pre _Client.address: {}".format(address))
            self.socketObj.settimeout(10)
            self.socketObj.connect(address)
            self.socketObj.settimeout(None)

            DbgPrint("Post _Client.conn: {}".format(getClientPort(self.socketObj)))
        except Exception as e:
            DbgPrint(e)
            raise Exception("Client Connection Failure")

        self.ConnectionCheck(self.socketObj)



    def ConnectionCheck(self, conn):
        countdown = 6
        DbgPrint("ConnectionCheck Started")
        while countdown > 0:
            try:
                conn.send(RUHERE.encode())
                conn.settimeout(5)
                data = conn.recv(1024).decode()
                if data == IAMHERE:
                    DbgPrint("Client: Connection Test Has Suceeded!!!")
                    return

            except Exception as e:
                countdown -= 1

        DbgPrint("Client: Connection Test Has Failed!!!")
        raise Exception("ERROR: Connection to Server Failed!!")

    def closeConnection(self):
        try:
            self.stop()
            self.socketObj.send(EndSession.encode())
            self.socketObj.close()

        except Exception as e:
            DbgPrint("ERROR:", str(e))

    def ServerShutDown(self):
        self.socketObj.send(ShutDown.encode())
        self.closeConnection()

    def Send(self, data):
        if self.dataMode == DataMode.JSON:
            self.writeJSON(data)
        elif self.dataMode == DataMode.PKL:
            self.writePKL(data)
        elif self.dataMode == DataMode.XML:
            pass
        else:
            self.socketObj.sendall(data.encode())

    def connSend(self,data, conn):
        if self.dataMode == DataMode.JSON:
            Utilities.writeJSON(conn, data)
        elif self.dataMode == DataMode.PKL:
            Utilities.writePKL(conn,data)
        elif self.dataMode == DataMode.XML:
            pass
        else:
            conn.send(data.encode())

    def SendMsg(self, msg):
        self.socketObj.send(msg.encode())

    def SendRawMsg(self, msg):
        self.socketObj.send(msg.encode())

    def _processData(self, data):
        rdata = None
        if len(data) > 0:
            try:
                if self.dataMode == DataMode.JSON:
                    rdata = self.rawReadJSON(data)
                elif self.dataMode == DataMode.PKL:
                    rdata = self.rawReadPKL(data)
                elif self.dataMode == DataMode.XML:
                    rdata = data
                else:
                    rdata = data
            except Exception as e:
                DbgPrint(str(e))

        return rdata

    def start(self):
        Thread(target=self.commMonitor, name=self.servername).start()

    def stop(self):
        self.GoFlag = False

    def readSocketData(self):
        # self.socketObj.settimeout(30)

        if PYVER < 3.0:
            data = self.socketObj.recv(2048)
        else:
            data = self.socketObj.recv(2048).decode()

        return data

    def receiveData(self):
        data=''
        dmlen = len(DATAEndMarker)

        while True and self.GoFlag:
            try:
                if len(data) == 0:
                    data = self.readSocketData()

                pos = data.find(DATAEndMarker)
                if pos >= 0:
                    yield data[:pos]
                    data = data[pos+dmlen:]
                elif len(data) > 0:
                    data += self.readSocketData()

            except socket.timeout as e:
                if len(data) > 0:
                    DbgPrint("ERROR:{}".format(str(e)))

            except Exception as e:
                raise e

        # self.socketObj.settimeout(None)


    def commMonitor(self):
        DbgPrint("Monitoring Communications Started")
        dataItem = self.receiveData()

        while self.GoFlag:
            try:
                data = next(dataItem)
                pData = self._processData(data)
                self.commDataHandler(data,pData)
                # DbgPrint("***data:{}\n***pData:{}".format(data,pData))
            except socket.timeout as e:
                DbgPrint("ERROR:{}".format(str(e)))

            except StopIteration:
                dataItem = self.receiveData()

            except Exception as e:
                DbgPrint("ERROR:{}".format(str(e)))
                # if e.errno == 10054:
                #     break

        DbgPrint("Monitoring Communications Finished...")


    def writePKL(self, data):
        Utilities.writePKL(self, self.socketObj, data)

    def readPKL(self):
        return Utilities.readPKL(self, self.socketObj)

    def writeJSON(self, data):
        Utilities.writeJSON(self, self.socketObj, data)

    def readJSON(self):
        return Utilities.readJSON(self, self.socketObj)

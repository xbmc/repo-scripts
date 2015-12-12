# This module is a modification of: 
#   pyirclib 0.4.3 - Released under BSD License
#   Coded by Ignacio Vazquez <irvazquez@users.softhome.net>
#   http://sourceforge.net/projects/pyirclib/

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import socket
import string
from traceback import print_exc

class Irclib:
  _VERSION = "0.4.3"
  messages = []
  loggedin = 0
  counter = 0
  setDebug = 0
  class IRCError(Exception):
    def __init__(self, value):
      self.value = value
    def __str__(self):
      return self.value

  def whois(self, nickname, server=None):
    returninfo = ({'error':1, 'errormessage': 'dictionary not initialized', \
                   'nickname':'' ,'username':'' ,'hostname': '', 'realname': '',\
                   'server':'', 'serverinfo':'', 'isoperator':0, 'idle':0, \
                   'away':0, 'awaymessage': '', 'channels': []})
    
    if server == None:
      self.servercmd("WHOIS " + nickname)
    else:
      self.servercmd("WHOIS %s %s" % (server, nickname))
    
    while(1):
      tmpresponse = self.getmessage()
      print tmpresponse['responsetype']
      
      if tmpresponse['responsetype'] == "ERR_NOSUCHSERVER":
        returninfo['errormessage'] = tmpresponse['responsetype']
        return returninfo

      elif tmpresponse['responsetype'] == "ERR_NOSUCHNICK":
        
        x = self.getmessage()
        if x['responsetype'] == "RPL_ENDOFWHOIS":
          returninfo['errormessage'] = tmpresponse['responsetype']
          return returninfo
        else:
          print "ERROR IN whois() --> (ERR_NOSUCHNICK)" # it shouldn't get here
          return 1
      
      elif tmpresponse['responsetype'] == "RPL_WHOISUSER":
        tmpstring = string.split(tmpresponse['text'])
        returninfo['nickname'] = tmpstring[1]
        returninfo['username'] = tmpstring[2]
        returninfo['hostname'] = tmpstring[3]
        returninfo['realname'] = string.join(tmpstring[5:])[1:]
        del tmpstring

      elif tmpresponse['responsetype'] == "RPL_WHOISSERVER":
        tmpstring = string.split(tmpresponse['text'])
        returninfo['server'] = tmpstring[2]
        returninfo['serverinfo'] = string.join(tmpstring[3:])[1:]
        del tmpstring

      elif tmpresponse['responsetype'] == "RPL_WHOISOPERATOR":
        returninfo['isoperator'] = 1

      elif tmpresponse['responsetype'] == "RPL_WHOISIDLE":
        tmpstring = string.split(tmpresponse['text'])
        returninfo['idle'] = int(tmpstring[2])
        del tmpstring

      elif tmpresponse['responsetype'] == "RPL_AWAY":
        tmpstring = string.split(tmpresponse['text'])
        returninfo['away'] = 1
        returninfo['awaymessage'] = string.join(tmpstring[2:])[1:]
        
      elif tmpresponse['responsetype'] == "RPL_WHOISCHANNELS":
        tmpstring = string.split(tmpresponse['text'])
        tmpstring[2] = string.replace(tmpstring[2], ':', '')
        returninfo['channels'] = tmpstring[2:]
      
      elif tmpresponse['responsetype'] == "RPL_ENDOFWHOIS":
        if returninfo['error'] == 2:
          returninfo['error'] = 1
          returninfo['errormessage'] == "ERR_NOSUCHNICK"
          return returninfo
        else:
          returninfo['error'] = 0
          returninfo['errormessage'] = ""
          return returninfo

  def getseqnumber(self):
    self.counter = self.counter + 1
    return self.counter
  def debug(self, msg):
    if self.setDebug == 0:
      pass
    else:
      print msg
    
  def list(self, channels=None, server=None):
    "Returns a list of channels in (channel_name, users, topic) form" 
    if channels == None:
      channels = ''
    if server == None:
      server = ''
    self.servercmd("LIST %s %s" % (channels, server))
    x = self.getmessage()
    if x['event'] == "RESPONSE" and x['responsetype'] == "RPL_LISTSTART":
      list = []
      while 1:
        x = self.getmessage()
        if (x['event'] == "RESPONSE" and x['responsetype'] == "RPL_LIST"):
          d = string.split(x['text'])
          chan = [d[1], d[2], string.join(d[3:]," ")[1:]]
          list.append(chan)  
        elif (x['event'] == "RESPONSE" and x['responsetype'] == "RPL_LISTEND"):
          return list
        else:
          self.debug("Unexpected error in list() method")
          return("ERROR in list()")
          break
          
  def names(self, channels=None):
    "Returns a list of users and the corresponding channels accesible by the client"
    
    if channels == None:
      channels = ''

    self.servercmd("NAMES %s" % (channels))
    nameslist = []
    while 1:
      x = self.getmessage()     
      if x['event'] == "RESPONSE" and x['responsetype'] == "RPL_NAMREPLY":
        tmptxt = string.split(x['text'])
        chan = tmptxt[2]
        for i in range((len(tmptxt) - 3)):
          if i == 0:
            tmptxt[i+3] = tmptxt[i+3][1:]
          nameslist.append([chan,tmptxt[i+3]])
      elif x['event'] == "RESPONSE" and x['responsetype'] == "RPL_ENDOFNAMES":
         del chan
         del tmptxt
         del x
         return nameslist
      else:
         self.debug("Unexpected error in names() method")
         return("ERROR in names()")
    
  def __init__(self,host,port):    
      self.sockfd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self.sockfd.connect((host,port))
      return None
    
  def send(self,data): # reimplementation of socket.send function with error handling
    try:
      self.sockfd.send(data)
    except socket.error, e:
      if e:
          self.debug( "Socket error: %s" %e)
      return "ERR_COULDNOTSEND"
    
  def login(self, nickname, username='user', password = None, realname='Anonymous', hostname='Unknown', servername='Server'):
    if password != None: 
      self.servercmd("PASS " + password)
    self.servercmd("USER %s %s %s %s" % (username, hostname, servername, realname))
    self.servercmd("NICK " + nickname)
    while 1:
      returnmsg = self.getmessage()
      if returnmsg:
          if returnmsg['event'] == "RESPONSE" and (returnmsg['responsetype'] == "ERR_NICKNAMEINUSE"\
            or returnmsg['responsetype'] == "ERR_NONICKNAMEGIVEN" or returnmsg['responsetype'] == \
              "ERR_ERRONEUSNICKNAME" or returnmsg['responsetype'] == "ERR_NICKCOLLISION"):
            return returnmsg['responsetype']
          elif returnmsg['event'] == "NOTICE":
            # mod for twitch irc
            if 'Login unsuccessful' in returnmsg['text']:
                return returnmsg['text']
            pass            
          elif returnmsg['responsetype'] == "RPL_WELCOME":
            while 1:
              returnmsg = self.getmessage()
              if returnmsg['responsetype'] == "RPL_ENDOFMOTD":
                return 0
          elif returnmsg['event'] == "RESPONSE" and returnmsg['responsetype'] == "ERR_PASSWDMISMATCH":
            return returnmsg['responsetype']
  def join(self, channel, password = None):
    if password != None:
      self.servercmd("JOIN %s %s" % (channel, password))
    else:
      self.servercmd("JOIN %s" % (channel))
    
    while 1:
      returndata = self.getmessage()
      self.debug(returndata)
      if returndata['event'] == "RESPONSE" and (returndata['responsetype'] != "RPL_NAMREPLY"):
        return("ERROR!",returndata['responsetype'])
      elif returndata['event'] == "NOTICE":
        pass
      else:
        self.debug("error in JOIN")
        break
  def privmsg(self, entity, message):
    self.debug ("SENDING to " + entity + "> " + message)  
    self.servercmd("PRIVMSG %s :%s" % (entity, message))
  def notice(self,entity, message):
    self.servercmd("NOTICE %s :%s" % (entity, message))
  def logout(self, reason):
    self.servercmd("QUIT %s" % (reason))
  def servercmd(self, command):
    if self.loggedin == 0:
      self.debug("Sending command to server: " + command)
      if self.send(command+"\n") != 0:
        return 0
      else: 
        return 1
    else:
      return "ERR_NOTLOGGEDIN"
  def setnick(self,nickname):
    self.servercmd("NICK %s" % (nickname))
  def oper(self, nick, password):
    self.servercmd("OPER %s %s" % (nick, password))
  def kill(self, nick, reason=''):
    self.servercmd("KILL %s %s" % (nick, reason))
  def kick(self, channel, nick, reason):
    self.servercmd("KICK %s %s %s" % (channel, nick, reason))
  def part(self, channel, reason=''):
    self.servercmd("PART %s %s" % (channel, reason))
  def setmode(self,entity,mode):
    self.servercmd("MODE %s %s" % (nickname, mode))
  def setchantopic(self,channel,topic):
    self.servercmd("TOPIC %s %s" % (channel, topic))
  def inviteuser(self,nickname,channel):
    self.servercmd("INVITE %s %s" % (nickname, channel))
  def awayon(self, message):
    self.servercmd("AWAY :%s" % message)
  def awayoff(self):
    self.servercmd("AWAY")
  def server_rehash(self):
    self.servercmd("REHASH")
  def server_restart(self):
    self.servercmd("RESTART")
  def wallops(self, message):
    self.servercmd("WALLOPS :%s" % message)
  
  def getserverversion(self, server=None):
    # TODO 
    #if server != None:
    #  self.servercmd("VERSION %s" % (server))
    #else:
    #  self.servercmd("VERSION")
    #tmp = self.getmessage()
    #if tmp['responsenumber'] == 351:
    #  print tmp['text']
    pass 
    
  def getresponsetype(self, number): # returns (responseno, responsestr)
      # error responses
      if number == 401: return("ERR_NOSUCHNICK")
      elif number == 433: return("ERR_NICKNAMEINUSE")
      elif number == 412: return("ERR_NOSUCHNICK")
      elif number == 402: return("ERR_NOSUCHSERVER")                                  
      elif number == 403: return("ERR_NOSUCHCHANNEL")
      elif number == 404: return("ERR_CANNOTSENDTOCHAN")
      elif number == 405: return("ERR_TOOMANYCHANNELS")
      elif number == 406: return("ERR_WASNOSUCKNICK")
      elif number == 407: return("ERR_TOOMANYTARGETS")
      elif number == 409: return("ERR_NOORIGIN")
      elif number == 411: return("ERR_NORECIPIENT")
      elif number == 412: return("ERR_NOTEXTTOSEND")
      elif number == 413: return("ERR_NOTOPLEVEL")
      elif number == 414: return("ERR_WILDTOPLEVEL")
      elif number == 421: return("ERR_UNKNOWNCOMMAND")
      elif number == 422: return("ERR_NOMOTD")
      elif number == 423: return("ERR_NOADMININFO")
      elif number == 424: return("ERR_FILEERROR")
      elif number == 431: return("ERR_NONICKNAMEGIVEN")
      elif number == 432: return("ERR_ERRONEUSNICKNAME")
      elif number == 433: return("ERR_NICKNAMEINUSE")
      elif number == 436: return("ERR_NICKCOLLISION")
      elif number == 441: return("ERR_USERNOTINCHANNEL")
      elif number == 442: return("ERR_NOTONCHANNEL")
      elif number == 443: return("ERR_USERONCHANNEL")
      elif number == 463: return("ERR_NOPERMFORHOST")
      elif number == 444: return("ERR_NOLOGIN")
      elif number == 445: return("ERR_SUMMONDISABLED")
      elif number == 446: return("ERR_USERSDISABLED")
      elif number == 451: return("ERR_NOTREGISTERED")
      elif number == 461: return("ERR_NEEDMOREPARAMS")
      elif number == 462: return("ERR_ALREADYREGISTRED")
      elif number == 464: return("ERR_PASSWDMISMATCH")
      elif number == 465: return("ERR_YOUREBANNEDCREEP")
      elif number == 467: return("ERR_KEYSET")
      elif number == 471: return("ERR_CHANNELISFULL")
      elif number == 472: return("ERR_UNKNOWNMODE")
      elif number == 473: return("ERR_INVITEONLYCHAN")
      elif number == 474: return("ERR_BANNEDFROMCHAN")
      elif number == 475: return("ERR_BADCHANNELKEY")                          
      elif number == 481: return("ERR_NOPRIVILEGES")
      elif number == 482: return("ERR_CHANOPRIVSNEEDED")
      elif number == 483: return("ERR_CANTKILLSERVER")     
      elif number == 491: return("ERR_NOOPERHOST")    
      elif number == 501: return("ERR_UMODEUNKNOWNFLAG")   
      elif number == 502: return("ERR_USERSDONTMATCH")             
      # command responses
      elif number == 300: return("RPL_DONE")
      elif number == 302: return("RPL_USERHOST")
      elif number == 303: return("RPL_ISON")
      elif number == 301: return("RPL_AWAY")
      elif number == 305: return("RPL_UNAWAY")
      elif number == 306: return("RPL_NOWAWAY")
      elif number == 311: return("RPL_WHOISUSER")
      elif number == 312: return("RPL_WHOISSERVER")
      elif number == 313: return("RPL_WHOISOPERATOR")
      elif number == 317: return("RPL_WHOISIDLE")
      elif number == 318: return("RPL_ENDOFWHOIS")
      elif number == 319: return("RPL_WHOISCHANNELS")
      elif number == 314: return("RPL_WHOWASUSER")
      elif number == 369: return("RPL_ENDOFWHOWAS")
      elif number == 321: return("RPL_LISTSTART")
      elif number == 322: return("RPL_LIST")
      elif number == 323: return("RPL_LISTEND")
      elif number == 324: return("RPL_CHANNELMODEIS")
      elif number == 331: return("RPL_NOTOPIC")
      elif number == 332: return("RPL_TOPIC")
      elif number == 341: return("RPL_INVITING")
      elif number == 342: return("RPL_SUMMONING")
      elif number == 351: return("RPL_VERSION")
      elif number == 352: return("RPL_WHOREPLY")
      elif number == 315: return("RPL_ENDOFWHO")
      elif number == 353: return("RPL_NAMREPLY")
      elif number == 366: return("RPL_ENDOFNAMES")
      elif number == 364: return("RPL_LINKS")
      elif number == 365: return("RPL_ENDOFLINKS")            
      elif number == 367: return("RPL_BANLIST")
      elif number == 368: return("RPL_ENDOFBANLIST")
      elif number == 371: return("RPL_INFO")
      elif number == 374: return("RPL_ENDOFINFO")
      elif number == 375: return("RPL_MOTDSTART")             
      elif number == 372: return("RPL_MOTD")             
      elif number == 376: return("RPL_ENDOFMOTD")
      elif number == 381: return("RPL_YOUREOPER")
      elif number == 382: return("RPL_REHASHING")
      elif number == 391: return("RPL_TIME")
      elif number == 392: return("RPL_USERSSTART")             
      elif number == 393: return("RPL_USERS")            
      elif number == 394: return("RPL_ENDOFUSERS")
      elif number == 395: return("RPL_NOUSERS")
      elif number == 200: return("RPL_TRACELINK")
      elif number == 201: return("RPL_TRACECONNECTING")
      elif number == 202: return("RPL_TRACEHANDSHAKE")       
      elif number == 203: return("RPL_TRACEUNKNOWN")
      elif number == 204: return("RPL_TRACEOPERATOR")
      elif number == 205: return("RPL_TRACEUSER")
      elif number == 206: return("RPL_TRACESERVER")       
      elif number == 208: return("RPL_TRACENEWTYPE")           
      elif number == 261: return("RPL_TRACELOG")          
      elif number == 211: return("RPL_STATSLINKINFO")          
      elif number == 212: return("RPL_STATSCOMMANDS")
      elif number == 213: return("RPL_STATSCLINE")
      elif number == 214: return("RPL_STATSCLINE")
      elif number == 215: return("RPL_STATSILINE")
      elif number == 216: return("RPL_STATSKLINE")          
      elif number == 218: return("RPL_STATSYLINE")           
      elif number == 219: return("RPL_ENDOFSTATS")            
      elif number == 241: return("RPL_STATSLLINE")
      elif number == 242: return("RPL_STATSUPTIME")
      elif number == 243: return("RPL_STATSOLINE")
      elif number == 244: return("RPL_STATSHLINE")
      elif number == 221: return("RPL_UMODEIS")
      elif number == 251: return("RPL_LUSERCLIENT")
      elif number == 252: return("RPL_LUSEROP")     
      elif number == 253: return("RPL_LUSERUNKNOWN")           
      elif number == 254: return("RPL_LUSERCHANNELS")
      elif number == 255: return("RPL_LUSERME")
      elif number == 256: return("RPL_ADMINME")
      elif number == 257: return("RPL_ADMINLOC1")      
      elif number == 258: return("RPL_ADMINLOC2")             
      elif number == 259: return("RPL_ADMINEMAIL")
      # reserved responses
      elif number == 209: return("RPL_TRACECLASS")
      elif number == 231: return("RPL_SERVICEINFO")
      elif number == 233: return("RPL_SERVICE")            
      elif number == 235: return("RPL_SERVLISTEND")            
      elif number == 316: return("RPL_WHOISCHANOP")           
      elif number == 362: return("RPL_CLOSING")           
      elif number == 373: return("RPL_INFOSTART")      
      elif number == 466: return("ERR_YOUWILLBEBANNED")
      elif number == 492: return("ERR_NOSERVICEHOST")
      elif number == 217: return("RPL_STATSQLINE")         
      elif number == 232: return("RPL_ENDOFSERVICES")        
      elif number == 234: return("RPL_SERVLIST")         
      elif number == 361: return("RPL_KILLDONE")             
      elif number == 363: return("RPL_CLOSEEND")              
      elif number == 384: return("RPL_MYPORTIS")              
      elif number == 476: return("ERR_BADCHANMASK")         
      # not official
      elif number == 001: return("RPL_WELCOME")

  def getmessage(self):
    buffer = ''
    self.sockfd.settimeout(3.0)
    try:
      while(1):
        x = self.sockfd.recv(1)
        if x != '\n':
          buffer = buffer + x
        else:
          self.debug("BUFFER IS: " + buffer)
          msg = string.split(buffer,':')
          message = ({"seqnumber":'notvalid', "responsetype":0,"channel":0,"nickname":0,"username":0,"hostname":0,"event":0,"recpt":0, "text":0})
          if buffer[:4] == "PING":
            self.debug("PING!")
            if "tmi.twitch.tv" in  buffer:
              pong_id = buffer[5:]
            else:
              pong_id = buffer[6:]  
            self.servercmd("PONG :%s" % pong_id )
            self.debug("PONG! id (%s)" % pong_id.strip() )
            return message  
          elif "ERROR" in buffer[:6]:
            message['event'] = "ERROR"
            message['text'] = buffer[6:]
            message['seqnumber'] = self.getseqnumber()
            # raise self.IRCError(buffer[7:])
            return message  
        
          elif buffer[:6] == "NOTICE":      
            message['event'] = "NOTICE"
            message['text'] = buffer[7:]
            message['seqnumber'] = self.getseqnumber()
            self.messages.append(message)
            return message  
          else:
            tmpmsg = string.split(msg[1])
            if "!" in (tmpmsg[0]):
              message['nickname'] = tmpmsg[0][:string.find(tmpmsg[0],"!")]
              message['username'] = tmpmsg[0][string.find(tmpmsg[0],"!")+1:string.find(tmpmsg[0],"@")] # ugly line ;)
            else:
              message['nickname'] = tmpmsg[0]
              message['username'] = tmpmsg[0]
            message['hostname'] = tmpmsg[0][string.find(tmpmsg[0],"@")+1:]
            try:
              message['event'] = "RESPONSE"
              message['responsetype'] = self.getresponsetype(int(tmpmsg[1]))
              message['text'] = buffer[(string.find(buffer,tmpmsg[1]))+4:]
              message['seqnumber'] = self.getseqnumber()
              self.messages.append(message)
              return message
            except (TypeError, ValueError):
              message['event'] = tmpmsg[1]
            if (message['event'] == "PRIVMSG"):
              message['recpt'] = tmpmsg[2]
              message['text'] = string.join(msg[2:],':')
            elif (message['event'] == "JOIN"):
              try:
                message['channel'] = msg[2]
              except IndexError: #tmi.twitch message string 
                  message['channel'] = msg[0].split("JOIN ")[-1]
            elif (message['event'] == "PART"):
              message['channel'] = tmpmsg[2]
            elif (message['event'] == "QUIT"):
              message['text'] = msg[2]
            elif (message['event'] == "MODE"):
              try:
                message['text'] = string.join(msg[2:],':')
              except IndexError:
                message['text'] = tmpmsg[3]
              message['recpt'] = tmpmsg[2]
            elif (message['event'] == "NOTICE"):
              message['text'] = buffer[string.find(buffer,"NOTICE")+7:]
            elif (message['event'] == "KILL"):
              message['text'] = buffer[(string.find(buffer,"("))+1:-1]
              self.debug(message['text'])
            elif (message['event'] == "NICK"):
              message['text'] = buffer[(string.find(buffer,"NICK"))+5:]
            else:
              message['event'] = "UNKNOWN"
              message['text'] = "DO SOMETHING HERE!"
              self.debug("UNKWOWN MESSAGE!")
            message['seqnumber'] = self.getseqnumber()
            self.messages.append(message)
          return message
    except:
        print_exc
   

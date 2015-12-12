from resources import pyircmod
from traceback import format_exc, print_exc
import sys
import os
import threading
import Queue
import ctypes
import time
import xbmcgui
import xbmcaddon

addon = xbmcaddon.Addon()
addon_id = addon.getAddonInfo('id')
addon_version = addon.getAddonInfo('version')
language = addon.getLocalizedString
addon_path = xbmc.translatePath(addon.getAddonInfo('path'))
icon = os.path.join(addon_path, 'icon.png')
chat_queue = Queue.Queue(maxsize=0)
client_queue = Queue.Queue(maxsize=0)
action_previous_menu = (9, 10, 92, 216, 247, 257, 275, 61467, 61448)


class irc_client(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.chat_messages = ''
        self.name_list = []

    def run(self):
        self.window = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
        client_do = 'client_wait'
        self.window.setProperty('clientIsRunning', 'True')
        while not client_do == 'client_stop':
            if self.window.getProperty('clientIsRunning') == "True":
                client_run = self.check_queue()
                if client_run:
                    client_do = client_run

                if client_do == 'client_stop':
                    addon_log('Got Notification: client_stop')
                    self.window.setProperty('clientIsRunning', '')
                elif client_do == 'client_wait':
                    addon_log('IrcChatIsRunning: clientIsWaiting')
                    time.sleep(0.5)
                else:
                    msg = self.get_message()
                    if msg:
                        # adjust the chatmessage delay here
                        time.sleep(1.0)
                    else:
                        time.sleep(0.2)
            else:
                break
        return

    def check_queue(self):
        # check for messages added to the chat_queue
        if not chat_queue.empty():
            for i in range(0, 4):
                chat = chat_queue.get()
                self.update_chat(chat)
                chat_queue.task_done()
                if not chat_queue.empty():
                    addon_log('chat not empty')
                    time.sleep(0.5)
                else:
                    break

        # check the client queue
        client_run = None
        if not client_queue.empty():
            client_run = client_queue.get()
            client_queue.task_done()
        return client_run

    def connect(self, **kwargs):
        if kwargs:
            self.host = kwargs.get("host")
            self.port = kwargs.get("port")
        try:
            self.irc = pyircmod.Irclib(self.host, int(self.port))
        except:
            f_exc = format_exc()
            if 'getaddrinfo failed' in f_exc:
                xbmc.executebuiltin("XBMC.Notification(%s, %s,10000,%s)"
                    %('IrcChat', '%s: %s' %(language(32034), self.host), icon))
            else:
                addon_log(str(f_exc))
            return False
        # self.irc.setDebug = True
        return True

    def login(self, **kwargs):
        self.nickname = kwargs.get("nickname")
        self.username = kwargs.get("username")
        self.password = kwargs.get("password")
        self.realname = kwargs.get("realname")
        self.hostname = kwargs.get("hostname")
        self.servername = kwargs.get("servername")
        try:
            logged_in = self.irc.login(
                    nickname=self.nickname, username=self.username, password=self.password,
                    realname=self.realname, hostname=self.hostname, servername=self.servername)
            if not logged_in == 0:
                addon_log('Log in error: %s' %logged_in)
                return False
            return True
        except:
            addon_log('addonException: %s' %print_exc())
            chat_queue.put(('IrcChat %s' %language(32024), str(format_exc())))
            return False

    def get_message(self):
        try:
            message = self.irc.getmessage()
            if message:
                # try:
                    # addon_log('%s | %s | %s | %s | %s | %s'
                        # %(message['event'], message['responsetype'], message['nickname'],
                          # message['username'], message['recpt'], message['text']))
                # except:
                    # addon_log('addonException: %s' %print_exc())
                    # addon_log('Error Parsing Message')

                if message['responsetype'] == 'RPL_NAMREPLY':
                    names = message['text'].split(self.channel)[-1].split()
                    for i in names:
                        if not i.strip() in self.name_list:
                            self.name_list.append(i.strip())
                elif message['responsetype'] == 'RPL_ENDOFNAMES':
                    new_message = (message['nickname'],  message['text'].strip())
                    chat_queue.put(new_message)
                elif message['event'] == 'ERROR':
                    if 'Closing link' in  message['text']:
                        self.window.setProperty('connected', '')
                        client_queue.put('client_wait')
                elif message['event'] == 'JOIN':
                    if not message['nickname'].strip() in self.name_list:
                        self.name_list.append(message['nickname'])
                elif message['event'] == 'QUIT' or message['event'] == 'PART':
                    if message['event'] == 'PART' and message['nickname'] == self.nickname:
                        addon_log('Message is self.nickname Event is PART')
                        client_queue.put('client_wait')
                        self.window.setProperty('inChannel', '')
                    elif message['event'] == 'QUIT' and message['nickname'] == self.nickname:
                        addon_log('Message is self.nickname Event is QUIT')
                        self.window.setProperty('connected', '')
                        client_queue.put('client_wait')
                    else:
                        try:
                            self.name_list.remove(message['nickname'])
                        except:
                            pass
                elif message['event'] == 'NICK':
                    try:
                        self.name_list.remove(message['nickname'])
                    except:
                        pass
                    self.name_list.append(message['text'].strip())
                elif message['event'] in ['PRIVMSG', 'NOTICE', 'RESPONSE' 'ERROR']:
                    if message['text'] != 0:
                        msg_nick = message['nickname'].strip()
                        if message['recpt'] == self.nickname:
                            msg_nick += '[%s]' %language(32035)
                        new_message = (msg_nick,  message['text'].strip())
                        chat_queue.put(new_message)
                        return True

        except:
            addon_log('addonException: %s' %print_exc())

    def update_chat(self, message):
        control = self.window.getControl(1331)
        control.addItem(xbmcgui.ListItem(label2=message[0]))
        new_message = []
        words = message[1].split()
        new_line = ''
        for i in range(len(words)):
            if len(words[i]) < 38:
                if (len(words[i]) + len(new_line)) < 38:
                    new_line += words[i]+' '
                else:
                    new_message.append(new_line.strip())
                    new_line = words[i]+' '
                if words[i].endswith('\n'):
                    new_message.append(new_line.strip())
                    new_line = ''
            else:
                new_message.append(words[i])
        if len(new_line.strip()) > 0:
            new_message.append(new_line.strip())
        for i in new_message:
            control.addItem(xbmcgui.ListItem(label=i))
        c_size = control.size()
        control.selectItem(c_size-1)
        xbmc.executebuiltin("Control.move(1331, %s)" %c_size)
        # addon_log('List Size: %s' %c_size)
        return

    def send_message(self, message):
        self.irc.privmsg(self.channel, message)
        chat_queue.put((self.nickname, message))
        return

    def get_names(self, clear=False):
        if clear:
            self.name_list = []
        else:
            return self.name_list

    def set_nick(self, new_nick):
        self.irc.setnick(new_nick)
        if self.nickname in self.name_list:
            self.name_list.remove(self.nickname)
        self.nickname = new_nick
        self.name_list.append(new_nick)

    def get_channels(self):
        channels_list = []
        try:
            # options are channel, server
            self.irc.servercmd("LIST %s %s" % ('', ''))
        except:
            addon_log('addonException: %s' %print_exc())
            return
        endOfList = False
        while not endOfList:
            message = self.irc.getmessage()
            if message:
                addon_log('%s | %s | %s | %s' %(message['event'], message['responsetype'], message['nickname'],  message['text']))
                try:
                    if message['responsetype'] == 'RPL_LISTEND':
                        endOfList = True
                    elif message['responsetype'] == 'RPL_LIST':
                        channels_list.append(message['text'].split()[1])
                    elif message['event'] == 'RESPONSE':
                        chat_queue.put((message['nickname'].strip(),  message['text'].strip()))
                    elif message['event'] == 'NOTICE':
                        chat_queue.put((message['nickname'].strip(),  message['text'].strip()))
                except:
                    print_exc
                self.check_queue()
            else:
                break
        else:
            if len(channels_list) > 0:
                addon_log('Channels %s' %len(channels_list))
                return channels_list

    def set_variable(self, name, value):
        if name == 'channel':
            self.channel = value



class GUI(xbmcgui.WindowXMLDialog):
    def __init__( self, *args, **kwargs ):
        xbmcgui.WindowXMLDialog.__init__( self )
        self.host = host
        self.nickname = nickname
        self.username = username
        self.password = password
        self.realname = realname
        self.hostname = hostname
        self.servername = servername
        self.port = port
        self.run_irc = run_irc
        self.channel = channel

    def onInit(self):
        self.window = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
        self.client = irc_client()
        self.client.setDaemon(True)
        self.client.start()
        self.window.setProperty('windowLabel', 'IrcChat')
        self.channels_list = None
        chat_queue.put(('IrcChat', language(32021)))
        self.connect_control = self.window.getControl(1263)
        self.connect_control.setLabel(language(32004))
        self.window.setProperty('connect_control', 'connect')
        if self.run_irc:
            self.connect_to_server()

    def connect_to_server(self):
        xbmc.executebuiltin("Skin.ToggleSetting(ChatIsLoading)")
        if self.window.getProperty('connected') != "True":
            # connect to server
            connect = self.client.connect(host=self.host, port=self.port)
            if not connect:
                chat_queue.put(('IrcChat', language(32034)))
            else:
                self.window.setProperty('windowLabel', self.host)
                chat_queue.put(('IrcChat', language(32017)))
                logged_in = self.client.login(
                    nickname=self.nickname, username=self.username, password=self.password,
                    realname=self.realname, hostname=self.hostname, servername=self.servername)
                if logged_in:
                    self.window.setProperty('connected', 'True')
                    xbmc.executebuiltin("Skin.ToggleSetting(ChatIsConnected)")
                    chat_queue.put(('IrcChat', '%s: %s' %(language(32018), self.host)))
                    self.connect_control.setLabel(language(32003))
                    self.window.setProperty('connect_control', 'disconnect')
                else:
                    addon_log('login failed')
                    xbmc.executebuiltin("Skin.Reset(ChatIsLoading)")
                if not logged_in:
                    chat_queue.put(('IrcChat', language(32019)))
                elif self.channel:
                    addon_log('SELF CHANNEL: ' + self.channel)
                    self.join_channel()
        else:
            # disconnect from server
            addon_log('- disconnect from server -')
            self.window.setProperty('windowLabel', 'IrcChat')
            chat_queue.put(('IrcChat', language(32020)))
            self.client.irc.logout('client disconnected')
            time.sleep(1)
            if not 'twitch' in self.host:
                client_queue.put('client_run')
                while not client_queue.empty():
                    time.sleep(0.2)
                for i in range(0,5):
                    if self.window.getProperty('connected') == 'True':
                        addon_log('waiting on Quit')
                        time.sleep(1)
                    else:
                        addon_log('Recived QUIT event.')
                        break
                client_queue.put('client_wait')
                while not client_queue.empty():
                    time.sleep(0.2)

            self.window.setProperty('connected', '')
            xbmc.executebuiltin("Skin.Reset(ChatIsConnected)")
            self.channels_list = None
            self.connect_control.setLabel(language(32033))
            self.window.setProperty('connect_control', 'quit')
        xbmc.executebuiltin("Skin.Reset(ChatIsLoading)")

    def join_channel(self):
        xbmc.executebuiltin("Skin.ToggleSetting(ChatIsLoading)")
        if self.window.getProperty('inChannel') != 'True':
            # join channel
            self.window.setProperty('windowLabel', self.channel)
            chat_queue.put(('IrcChat', '%s: %s' %(language(32022), self.channel)))
            try:
                self.client.irc.join(self.channel)
                time.sleep(1)
            except:
                addon_log('addonException: %s' %print_exc())
                try:
                    self.client.irc.join(self.channel)
                    time.sleep(1)
                except:
                    addon_log('addonException: %s' %print_exc())
                    chat_queue.put(('IrcChat %s' %language(32024), str(print_exc())))
                    xbmc.executebuiltin("Skin.Reset(ChatIsLoading)")
                    return
            self.client.set_variable('channel', self.channel)
            self.window.setProperty('inChannel', 'True')
            client_queue.put('client_run')
            self.connect_control.setLabel(language(32026))
            self.window.setProperty('connect_control', 'quitchannel')
        else:
            # quit channel
            xbmc.executebuiltin("Skin.Reset(ChatNamesList)")
            self.window.setProperty('windowLabel', self.host)
            client_queue.put('client_wait')
            chat_queue.put(('IrcChat', '%s %s' %(language(32023), self.channel)))
            while not client_queue.empty():
                addon_log('waiting on client_wait')
                time.sleep(0.5)
            addon_log('sending PART')
            self.client.irc.part(self.channel, reason='quit channel')
            client_queue.put('client_run')
            while not client_queue.empty():
                time.sleep(0.2)
            for i in range(0,10):
                if self.window.getProperty('inChannel') == 'True':
                    addon_log('Waiting for channel PART')
                    time.sleep(1)
                else:
                    chat_queue.put(('IrcChat', 'Quit: %s' %self.channel))
                    addon_log('Quit Channel')
                    break
            self.connect_control.setLabel(language(32003))
            self.window.setProperty('connect_control', 'disconnect')
            control = self.window.getControl(1300)
            control.reset()
            self.client.get_names(clear=True)
            self.window.setProperty('inChannel', '')
        xbmc.executebuiltin("Skin.Reset(ChatIsLoading)")

    def get_keyboard_input(self, label, string=''):
        keyboard = xbmc.Keyboard(string, label)
        keyboard.doModal()
        if keyboard.isConfirmed() == False:
            return
        message = keyboard.getText()
        if len(message) == 0 or message == string:
            return
        else:
            return message

    def kill_client(self):
        try:
            if self.client.isAlive():
                addon_log('client is alive!')
            else:
                addon_log('client is not alive')
                return
        except AttributeError:
            addon_log('client is not defined')
            return
        if self.window.getProperty('clientIsRunning') == 'True':
            self.window.setProperty('clientIsRunning', '')
        time.sleep(2)
        if self.client.isAlive():
            addon_log('client is still alive!')
            try:
                term = self.terminate_thread(self.client)
                addon_log('client stopped')
            except ValueError:
                addon_log('addonException: %s' %print_exc())
                pass
        else:
            addon_log('client stopped')

    def shutdown(self):
        xbmc.executebuiltin("Skin.ToggleSetting(ChatIsLoading)")
        if self.window.getProperty('inChannel') == 'True':
            self.join_channel()
        if self.window.getProperty('connected') == 'True':
            self.connect_to_server()
        if self.window.getProperty('connected') != 'True':
            self.kill_client()
        self.window.clearProperty('connected')
        self.window.clearProperty('names')
        self.window.clearProperty('windowLabel')
        self.window.clearProperty('clientIsRunning')
        self.window.clearProperty('awayMessage')
        xbmc.executebuiltin("Skin.Reset(ChatIsLoading)")
        xbmc.executebuiltin("Skin.Reset(ChatNamesList)")
        self.close()

    def onAction(self, action):
        if action == 13:
            #keyboard x key
            self.shutdown()

        if action in action_previous_menu:
            addon_log('Action: action_previous_menu')
            if xbmc.getCondVisibility("Window.IsVisible(videoosd)") == False:
                xbmc.executebuiltin("ActivateWindow(videoosd)")
            else:
                xbmc.executebuiltin("Dialog.Close(videoosd)")

    def onClick(self, controlID):
        addon_log('- onClick controlId: %s -' %controlID)

        if controlID == 1240:
            addon_log('- close button -')
            self.shutdown()

        elif controlID == 1239:
            # Chat button
            addon_log('- chat button -')
            if self.window.getProperty('inChannel') == 'True':
                # Enter a message
                label = language(32015)
                message = self.get_keyboard_input(label)
                if message:
                    self.client.send_message(message)
            elif self.window.getProperty('connected') == 'True':
                # Enter a channel name
                label = language(32028)
                message = self.get_keyboard_input(label, '#')
                if message:
                    self.channel = message
                    self.join_channel()
            else:
                # Enter a host
                label = language(32029)
                message = self.get_keyboard_input(label)
                if message:
                    self.host = message
                    self.channel = None
                    self.connect_to_server()

        elif controlID == 1242:
            # Names / Channels
            control = self.window.getControl(1300)
            if self.window.getProperty('inChannel') == 'True':
                # get names
                if self.window.getProperty('names') != 'True':
                    addon_log('- open names -')
                    xbmc.executebuiltin("Skin.ToggleSetting(ChatIsLoading)")
                    names = self.client.get_names()
                    items = sorted(names, key=str.lower)
                    addon_log('- Name List -')
                    addon_log(items)
                    for i in items:
                        control.addItem(i.encode('utf-8'))
                    self.window.setProperty('names', 'True')
                    xbmc.executebuiltin("Skin.Reset(ChatIsLoading)")
                    xbmc.executebuiltin("Skin.ToggleSetting(ChatNamesList)")
                else:
                    addon_log('- close names -')
                    xbmc.executebuiltin("Skin.Reset(ChatNamesList)")
                    control.reset()
                    self.window.setProperty('names', '')
            else:
                # get channels
                if self.window.getProperty('connected') == "True":
                    xbmc.executebuiltin("Skin.ToggleSetting(ChatIsLoading)")
                    if not self.channels_list:
                        addon_log('channels_list is None')
                        self.channels_list = self.client.get_channels()
                    if self.channels_list:
                        items = sorted(self.channels_list, key=str.lower)
                        for i in items:
                            channel = i.encode('utf-8')
                            control.addItem(channel)
                        self.window.setProperty('channels', 'True')
                        xbmc.executebuiltin("Skin.ToggleSetting(ChatNamesList)")
                    else:
                        addon_log('No Channel List')
                    xbmc.executebuiltin("Skin.Reset(ChatIsLoading)")
                else:
                    addon_log('Close Channels')
                    control.reset()
                    xbmc.executebuiltin("Skin.Reset(ChatNamesList)")

        elif controlID == 1263:
            # connect button
            property = self.window.getProperty('connect_control')
            addon_log('Connect Control: %s' %property)
            if property == 'connect' or property == 'disconnect':
                if not self.host:
                    xbmc.executebuiltin("SendClick(%s, %s)" %(self.window, 1239))
                else:
                    self.connect_to_server()
            elif property == 'quitchannel':
                self.join_channel()
                if 'twitch' in self.host:
                    self.connect_to_server()
            elif property == 'quit':
                self.shutdown()

        elif controlID == 1300:
            # Names / Channel List button
            if 'twitch' in self.host:
                pass
            else:
                if self.window.getProperty('inChannel') == 'True':
                    # do something with names_list item
                    control = self.window.getControl(1300)
                    item = control.getSelectedItem()
                    user = item.getLabel()
                    context_control = self.window.getControl(1333)
                    if user != self.nickname:
                        items = [language(32036), language(32037), language(32038), language(32039)]
                        for i in range(len(items)):
                            liz = xbmcgui.ListItem(items[i])
                            liz.setProperty('index', str(i))
                            liz.setProperty('user', user)
                            context_control.addItem(liz)
                    else:
                        items = [language(32036), language(32040), language(32041), language(32042)]
                        for i in range(len(items)):
                            liz = xbmcgui.ListItem(items[i])
                            liz.setProperty('index', str(i))
                            liz.setProperty('user', user)
                            context_control.addItem(liz)
                    xbmc.executebuiltin("Skin.ToggleSetting(ChatContextMenu)")
                    xbmc.executebuiltin("SetFocus(1333)")

                else:
                    # connect to channel
                    control = self.window.getControl(1300)
                    item = control.getSelectedItem()
                    self.channel = '#%s' %item.getLabel()
                    xbmc.executebuiltin("Skin.Reset(ChatNamesList)")
                    control.reset()
                    self.join_channel()

        elif controlID == 1333:
            # ChatContextMenu
            xbmc.executebuiltin("Skin.Reset(ChatContextMenu)")
            control = self.window.getControl(1333)
            item = control.getSelectedItem()
            index = int(item.getProperty('index'))
            user = item.getProperty('user')
            if user != self.nickname:
                if index == 1:
                    message = self.get_keyboard_input('%s %s' %(language(32043), user))
                    if message:
                        self.client.irc.privmsg(user, message)
                        chat_queue.put(('%s%s' %(self.nickname, '[private]'), message))
                elif index == 2:
                    message = self.get_keyboard_input('%s %s' %(language(32044), user))
                    if message:
                        self.client.irc.notice(user, message)
                        chat_queue.put((self.nickname, message))
                elif index == 3:
                    addon_log('- get whois -')
                    xbmc.executebuiltin("Skin.ToggleSetting(ChatIsLoading)")
                    client_queue.put('client_wait')
                    while not client_queue.empty():
                        time.sleep(0.2)
                    whois_str = ''
                    name = item.getLabel()
                    whois_info = self.client.irc.whois(name, server = None)
                    for i in whois_info.keys():
                        whois_str += '%s: %s \n' %(i, whois_info[i])
                    chat_queue.put(('IrcChat', whois_str))
                    client_queue.put('client_run')
                    xbmc.executebuiltin("Skin.Reset(ChatIsLoading)")
            else:
                if index == 1:
                    new_nick = self.get_keyboard_input(language(32045))
                    if new_nick:
                        self.client.set_nick(new_nick)
                        self.nickname = new_nick
                        xbmc.executebuiltin("SendClick(%s, %s)" %(self.window, 1242))
                elif index == 2:
                    if self.window.getProperty('awayMessage') != 'True':
                        away_msg = self.get_keyboard_input(language(32046))
                        if away_msg:
                            self.client.irc.awayon(away_msg)
                            self.window.setProperty('awayMessage', 'True')
                    else:
                        self.client.irc.awayoff()
                        self.window.setProperty('awayMessage', '')
                elif index == 3:
                        mode = self.get_keyboard_input(language(32047))
                        if mode:
                            self.client.irc.setmode(self.username, mode)
            control.reset()

    # credit - http://stackoverflow.com/a/15274929
    def terminate_thread(self, thread):
        """Terminates a python thread from another thread.

        :param thread: a threading.Thread instance
        """
        if not thread.isAlive():
            return
        else:
            addon_log('terminate_thread: %s' %thread.name)

        exc = ctypes.py_object(SystemExit)
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_long(thread.ident), exc)
        if res == 0:
            raise ValueError("nonexistent thread id")
        elif res > 1:
            # """if it returns a number greater than one, you're in trouble,
            # and you should call it again with exc=NULL to revert the effect"""
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread.ident, None)
            raise SystemError("PyThreadState_SetAsyncExc failed")


def addon_log(string):
    if not isinstance(string, str):
        string = str(string)
    try:
        log_message = string.encode('utf-8', 'ignore')
    except:
        log_message = 'addonException: addon_log: %s' %format_exc()
    # for ease in development change the level to LOGNOTICE
    xbmc.log("[%s-%s]: %s" %(addon_id, addon_version, log_message), level=xbmc.LOGNOTICE)


def get_params():
    params = {}
    a = sys.argv[1].split('&')
    for i in a:
        p = i.split('=')
        params[p[0]]=p[1]
    return params


def check_args():
    try:
        ok = nickname
        if ok is None or ok == '': raise
        ok = username
        if ok is None or ok == '': raise
        return True
    except:
        xbmc.executebuiltin("XBMC.Notification(%s, %s,10000,%s)"
            %('IrcChat', language(32046), icon))
        addon.openSettings()
        return False


params = None
if len(sys.argv) > 1:
    params = get_params()
    addon_log('- PARAMS -')
    addon_log(params)

if params:
    host = params["host"]
    nickname = params["nickname"]
    username = params["username"]
    try:
        password = params["password"]
        if password == '': raise
        if password == 'None': raise
    except:
        password = None
    try:
        channel = params["channel"]
        if channel and not channel.startswith('#'):
            channel = '#%s' %channel
    except:
        channel = None
    try:
        realname = params["realname"]
    except:
        realname = None
    try:
        servername = params["servername"]
    except:
        servername = None
    try:
        hostname = params["hostname"]
    except:
        hostname = None
    try:
        port = int(params["port"])
    except:
        port = 6667
    try:
        run_irc = eval(params["run_irc"])
    except:
        run_irc = False

else:
    host = addon.getSetting('irc_host')
    channel = addon.getSetting('channel_name')
    if channel and not channel.startswith('#'):
        channel = '#%s' %channel
    nickname = addon.getSetting('nickname')
    username = addon.getSetting('username')
    realname = addon.getSetting('realname')
    servername = addon.getSetting('servername')
    hostname = addon.getSetting('hostname')
    port = addon.getSetting('port')
    password = addon.getSetting('password')
    if password == "None" or password == "":
        password = None
    run_irc = False


if (__name__ == "__main__"):
    addon_log('script starting')
    ok = check_args()
    if ok:
        window = GUI('script-IrcChat-main.xml', addon_path)
        window.doModal()

addon_log('script finished')
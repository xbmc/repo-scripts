# -*- coding: utf-8 -*-
from lib.addon import *
class Service(xbmc.Monitor):

    def __init__(self, *args):
        addonName = 'Plex TV Skip'


    def onNotification(self, sender, method, data):
            if method in ["Player.OnSeek"]:
                onSeek()
            if method in ["Player.OnPlay"]:
                onPlay()
    def ServiceEntryPoint(self):
        monitor()

Service().ServiceEntryPoint()
#!/usr/bin/python
# -*- coding: utf-8 -*-

import xbmc
import handler

if __name__ ==  '__main__':

    handler.notifyLog('Parameter handler called: add Timer')
    args = {'channel': xbmc.getInfoLabel('ListItem.ChannelName'),
            'icon': xbmc.getInfoLabel('ListItem.Icon'),
            'date': xbmc.getInfoLabel('ListItem.Date'),
            'title': xbmc.getInfoLabel('ListItem.Title'),
            'plot': xbmc.getInfoLabel('ListItem.Plot')
            }

    if not handler.setTimer(args):
        handler.notifyLog('Timer couldn\'t or wouldn\' be set')

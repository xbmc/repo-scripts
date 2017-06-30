#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
import xbmc
import interface
import json
__addon__ = interface.__addon__
def getstr(strid): return interface.getstr(strid)

class Engine:
  def __init__(self, api, player):
    self.api = api
    self.player = player
    player.engine = self
    player.api    = api
    #self.synclibrary()

  def synclibrary(self):
    ### UPLOAD ###
    #DISABLED UNTIL WORKING FINE
    pass
    # kodilibrary = xbmc.executeJSONRPC(json.dumps({
    #   "jsonrpc": "2.0",
    #   "method": "VideoLibrary.GetMovies",
    #   "params": {
    #   "limits": {
    #     "start": 0,
    #     "end": 1000
    #   },
    #   "properties": [
    #     "playcount",
    #     "imdbnumber",
    #     "file",
    #     "lastplayed"
    #   ],
    #   "sort": {
    #     "order": "ascending",
    #     "method": "label",
    #     "ignorearticle": True
    #   }
    #   },
    #   "id": "libMovies"
    # }))
    # xbmc.log("Simkl: Ret: {0}".format(kodilibrary))
    # kodilibrary = json.loads(kodilibrary)

    # if kodilibrary["result"]["limits"]["total"] > 0:
    #   for movie in kodilibrary["result"]["movies"]:
    #     #Dont do that, upload all at once

    #     if movie["playcount"] > 0:
    #       imdb = movie["imdbnumber"]
    #       date = movie["lastplayed"]
    #       self.api.watched(imdb, "movie", date)

class Player(xbmc.Player):
  def __init__(self):
    xbmc.Player.__init__(self)

  @staticmethod
  def getMediaType():
    if xbmc.getCondVisibility('Container.Content(tvshows)'):
      return "show"
    elif xbmc.getCondVisibility('Container.Content(seasons)'):
      return "season"
    elif xbmc.getCondVisibility('Container.Content(episodes)'):
      return "episode"
    elif xbmc.getCondVisibility('Container.Content(movies)'):
      return "movie"
    else:
      return None

  def onPlayBackStarted(self):
    #self.onPlayBackStopped()
    pass
  def onPlayBackSeek(self, *args):
    self.onPlayBackStopped()
  def onPlayBackResumed(self):
    self.onPlayBackStopped()
  def onPlayBackEnded(self):
    xbmc.log("Simkl: ONPLAYBACKENDED")
    self.onPlayBackStopped()
  def onPlayBackStopped(self):
    ''' Gets the info needed to pass to the api '''
    self.api.check_connection()
    try:
      item = json.loads(xbmc.executeJSONRPC(json.dumps({
        "jsonrpc": "2.0", "method": "Player.GetItem",
        "params": {
          "properties": ["showtitle", "title", "season", "episode", "file", "tvshowid", "imdbnumber", "genre" ],
          "playerid": 1},
        "id": "VideoGetItem"})))["result"]["item"]
      if item["tvshowid"] != -1:
        item["imdbnumber"] = json.loads(xbmc.executeJSONRPC(json.dumps({
          "jsonrpc": "2.0", "method":"VideoLibrary.GetTVShowDetails",
          "params":{"tvshowid":item["tvshowid"], "properties":["imdbnumber"]},
          "id":1
          })))["result"]["tvshowdetails"]["imdbnumber"]
      xbmc.log("Simkl: Full: {0}".format(item))

      percentage = min(99, 100 * self.getTime() / self.getTotalTime())
      pctconfig  = int(self.addon.getSetting("scr-pct"))

      if percentage > pctconfig:
        bubble = __addon__.getSetting("bubble")
        xbmc.log("Simkl: Bubble == {0}".format(bubble))
        xbmc.log("Percentage: {0}, pctconfig {1}".format(percentage, pctconfig))

        r = self.api.watched(item, self.getTotalTime())

        if bubble=="true" and r:
          if item["label"] == os.path.basename(item["file"]):
          #if True: #For testing purposes
            xbmc.log("Simkl: Label and file are the same")
            lstw = self.api.lastwatched
            if lstw["type"] == "episode":
              item["showtitle"] = lstw["show"]["title"]
              item["season"] = lstw["episode"]["season"]
              item["episode"] = lstw["episode"]["episode"]
            elif lstw["type"] == "movie":
              item["title"] = "".join([lstw["movie"]["title"], " (", str(lstw["movie"]["year"]), ")"])
            media = lstw["type"]

          txt = item["label"]
          title = ""
          if item["type"] == "movie":
            txt = item["title"]
          elif item["type"] == "episode":
            txt = item["showtitle"]
            title = "- S{:02}E{:02}".format(item["season"], item["episode"])
          xbmc.log("Simkl: " + "; ".join([item["type"], txt, title]))
          interface.notify(getstr(32028).format(title), title=txt)
          r = 0

    except RuntimeError:
      pass
    except ZeroDivisionError:
      self.onPlayBackStopped()

import json
import urllib
import urllib2
import team as _team
import league as _league
import player as _player
import event as _event
import user as _user
import livescores
import tableentry
import xbmc
import datetime as _datetime
from utils import util as _util 


__author__ = 'enen92'
API_BASE_URL = 'http://www.thesportsdb.com/api/v1/json'

class Api:

    def __init__(self,key=None):
        global API_KEY
        API_KEY = key
        if API_KEY != None and type(API_KEY) == str:
            xbmc.log(msg="[TheSportsDB] Module initiated with API key " + str(API_KEY), level=xbmc.LOGNOTICE)
        else:
            xbmc.log(msg="[TheSportsDB] API Key is not valid", level=xbmc.LOGERROR)

    class Lookups:

        def Team(self,teamid=None,leagueid=None):
            teamlist = []
            if teamid or leagueid:
                if teamid and not leagueid:
                    url = '%s/%s/lookupteam.php?id=%s' % (API_BASE_URL,API_KEY,str(teamid))
                elif leagueid and not teamid:
                    url = '%s/%s/lookup_all_teams.php?id=%s' % (API_BASE_URL,API_KEY,str(leagueid))
                else:
                    xbmc.log(msg="[TheSportsDB] Invalid parameters", level=xbmc.LOGERROR)
                    return teamlist
                data = json.load(urllib2.urlopen(url))
                teams = data["teams"]
                if teams:
                    for tm in teams:
                        teamlist.append(_team.as_team(tm))
            else:
                xbmc.log(msg="[TheSportsDB] teamid or leagueid must be provided", level=xbmc.LOGERROR)
            return teamlist

        def League(self,leagueid=None):
            leaguelist = []
            if leagueid:
                url = '%s/%s/lookupleague.php?id=%s' % (API_BASE_URL,API_KEY,str(leagueid))
                data = json.load(urllib2.urlopen(url))
                leagues = data["leagues"]
                if leagues:
                    for lg in leagues:
                        leaguelist.append(_league.as_league(lg))
            else:
                xbmc.log(msg="[TheSportsDB] leagueid must be provided", level=xbmc.LOGERROR)               
            return leaguelist

        def Player(self,playerid=None,teamid=None):
            playerlist = []
            if playerid or teamid:
                if playerid and not teamid:
                    url = '%s/%s/lookupplayer.php?id=%s' % (API_BASE_URL,API_KEY,str(playerid))
                    key = "players"
                elif teamid and not playerid:
                    url = '%s/%s/lookup_all_players.php?id=%s' % (API_BASE_URL,API_KEY,str(teamid))
                    key = "player"
                else:
                    xbmc.log(msg="[TheSportsDB] Invalid parameters", level=xbmc.LOGERROR)
                    return playerlist
                data = json.load(urllib2.urlopen(url))
                players = data[key]
                if players:
                    for pl in players:
                        playerlist.append(_player.as_player(pl))
            else:
                xbmc.log(msg="[TheSportsDB] playerid or teamid must be provided", level=xbmc.LOGERROR)
            return playerlist

        def Event(self,eventid=None):
            eventlist = []
            if eventid:
                url = '%s/%s/lookupevent.php?id=%s' % (API_BASE_URL,API_KEY,str(eventid))
                data = json.load(urllib2.urlopen(url))
                events = data["events"]
                if events:
                    for ev in events:
                        eventlist.append(_event.as_event(ev))
            else:
                xbmc.log(msg="[TheSportsDB] eventid must be provided", level=xbmc.LOGERROR)             
            return eventlist

        def Table(self,leagueid=None,season=None,objects=False):
            table = []
            if leagueid:
                if season:
                    url = '%s/%s/lookuptable.php?l=%s&s=%s' % (API_BASE_URL,API_KEY,str(leagueid),str(season))
                else:
                    url = '%s/%s/lookuptable.php?l=%s' % (API_BASE_URL,API_KEY,str(leagueid))
                    if objects:
                        teams_in_league = self.Team(leagueid=leagueid)
                data = json.load(urllib2.urlopen(url))
                entries = data["table"]
                if entries:
                    for entry in entries:
                        tentry = tableentry.as_tableentry(entry)
                        if objects:
                            if not season:
                                for team in teams_in_league:
                                    if team.idTeam == tentry.teamid:
                                        tentry.setTeamObject(team)
                            else:
                                team_id = tentry.teamid
                                tentry.setTeamObject(self.Team(team_id)[0])
                        table.append(tentry)
            else: xbmc.log(msg="[TheSportsDB] leagueid must be provided", level=xbmc.LOGERROR)
            return table

        def Seasons(self,leagueid=None):
            seasonlist = []
            if leagueid:
                url = '%s/%s/lookupleague.php?id=%s&s=all' % (API_BASE_URL,API_KEY,str(leagueid))
                data = json.load(urllib2.urlopen(url))
                entries = data["leagues"]
                if entries:
                    for entry in entries:
                        seasonlist.append(entry["strSeason"])
            else: xbmc.log(msg="[TheSportsDB] leagueid must be provided", level=xbmc.LOGERROR)
            return seasonlist


    class Search:

        def Teams(self,team=None,sport=None,country=None,league=None):
            teamlist = []
            if team or sport or country or league:
                if team and not sport and not country and not league:
                   url = '%s/%s/searchteams.php?t=%s' % (API_BASE_URL,API_KEY,urllib.quote(team))
                elif not team and league and not sport and not country:
                    url = '%s/%s/search_all_teams.php?l=%s' % (API_BASE_URL,API_KEY,urllib.quote(league))
                elif not team and not league and sport and country:
                    url = '%s/%s/search_all_teams.php?s=%s&c=%s' % (API_BASE_URL,API_KEY,urllib.quote(sport),urllib.quote(country))
                else:
                    url = None
                if url:
                    data = json.load(urllib2.urlopen(url))
                    teams = data["teams"]
                    if teams:
                        for tm in teams:
                            teamlist.append(_team.as_team(tm))
                else:
                    xbmc.log(msg="[TheSportsDB] Invalid Parameters", level=xbmc.LOGERROR)
            else:
                xbmc.log(msg="[TheSportsDB] team,sport,country or league must be provided", level=xbmc.LOGERROR)
            return teamlist

        def Players(self,team=None,player=None):
            playerlist = []
            if team or player:
                if team and not player:
                    url = '%s/%s/searchplayers.php?t=%s' % (API_BASE_URL,API_KEY,urllib.quote(team))
                elif not team and player:
                    url = '%s/%s/searchplayers.php?p=%s' % (API_BASE_URL,API_KEY,urllib.quote(player))
                else:
                    url = '%s/%s/searchplayers.php?t=%s&p=%s' % (API_BASE_URL,API_KEY,urllib.quote(team),urllib.quote(player))
                data = json.load(urllib2.urlopen(url))
                players = data["player"]
                if players:
                    for pl in players:
                        playerlist.append(_player.as_player(pl))
            else:
                xbmc.log(msg="[TheSportsDB] team or player must be provided", level=xbmc.LOGERROR)
            return playerlist

        def Events(self,event=None,filename=None,season=None):
            eventlist = []
            if event or season or filename:
                if event and not season and not filename:
                    url = '%s/%s/searchevents.php?e=%s' % (API_BASE_URL,API_KEY,str(event).replace(" ","_"))
                elif event and season:
                    url = '%s/%s/searchevents.php?e=%s&s=%s' % (API_BASE_URL,API_KEY,str(event).replace(" ","_"),str(season))
                elif filename:
                    url = '%s/%s/searchfilename.php?e=%s' % (API_BASE_URL,API_KEY,str(filename).replace(" ","_"))
                else:
                    url = ""
                if url:
                    data = json.load(urllib2.urlopen(url))
                    events = data["event"]
                    if events:
                        for ev in events:
                            eventlist.append(_event.as_event(ev))
            else:
                xbmc.log(msg="[TheSportsDB] event and season or filename must be provided", level=xbmc.LOGERROR)
            return eventlist

        def Leagues(self,country=None,sport=None):
            leaguelist = []
            if country or sport:
                if country and not sport:
                    url = '%s/%s/search_all_leagues.php?c=%s' % (API_BASE_URL,API_KEY,urllib.quote(country))
                elif not country and sport:
                    url = '%s/%s/search_all_leagues.php?s=%s' % (API_BASE_URL,API_KEY,urllib.quote(sport))
                else:
                    url = '%s/%s/search_all_leagues.php?s=%s&c=%s' % (API_BASE_URL,API_KEY,urllib.quote(sport),urllib.quote(country))
                data = json.load(urllib2.urlopen(url))
                leagues = data["countrys"]
                if leagues:
                    for lg in leagues:
                        leaguelist.append(_league.as_league(lg))
            else:
                xbmc.log(msg="[TheSportsDB] country or league must be provided", level=xbmc.LOGERROR)
            return leaguelist

        def Loves(self,user=None,objects=False):
            if user:
                userobj = _user.User()
                userobj.setUsername(user)
                playerlist = []
                teamlist = []
                leaguelist = []
                eventlist = []
                url = '%s/%s/searchloves.php?u=%s' % (API_BASE_URL,API_KEY,str(user))
                data = json.load(urllib2.urlopen(url))
                edits = data["players"]
                if edits:
                    for edit in edits:
                        if edit["idTeam"]: teamlist.append(edit["idTeam"])
                        if edit["idPlayer"]: playerlist.append(edit["idPlayer"]) 
                        if edit["idLeague"]: leaguelist.append(edit["idLeague"])
                        if edit["idEvent"]: eventlist.append(edit["idEvent"])
                    if objects:
                        _teamlist = []
                        _playerlist = []
                        _eventlist = []
                        _leaguelist = []
                        if teamlist:
                            for tmid in teamlist:
                                try:
                                    _teamlist.append(Api(API_KEY).Lookups().Team(teamid=tmid)[0])
                                except: pass
                        teamlist = _teamlist
                        del _teamlist
                        if playerlist:
                            for plid in playerlist:
                                try:
                                    _playerlist.append(Api(API_KEY).Lookups().Player(playerid=plid)[0])
                                except: pass
                        playerlist = _playerlist
                        del _playerlist
                        if leaguelist:
                            for lgid in leaguelist:
                                try:
                                    _leaguelist.append(Api(API_KEY).Lookups().League(leagueid=lgid)[0])
                                except: pass
                        leaguelist = _leaguelist
                        del _leaguelist
                        if eventlist:
                            for evid in eventlist:
                                try:
                                    _eventlist.append(Api(API_KEY).Lookups().Event(eventid=lgid)[0])
                                except: pass
                        eventlist = _eventlist
                        del _eventlist
                userobj.setTeams(teamlist)
                userobj.setPlayers(playerlist)
                userobj.setLeagues(leaguelist)
                userobj.setEvents(eventlist)
                return userobj
            else:
                xbmc.log(msg="[TheSportsDB] A user must be provided", level=xbmc.LOGERROR)

        def Seasons(self,leagueid=None):
            seasonlist = []
            if leagueid:
                url = '%s/%s/search_all_seasons.php?id=%s' % (API_BASE_URL,API_KEY,str(leagueid))
                data = json.load(urllib2.urlopen(url))
                seasons = data["seasons"]
                if seasons:
                    for season in seasons:
                        seasonlist.append(season["strSeason"])
            else:
                xbmc.log(msg="[TheSportsDB] leagueid must be provided", level=xbmc.LOGERROR)
            return seasonlist


    class Schedules:

        class Last:
            def Team(self,teamid=None):
                eventlist = []
                if teamid:
                    url = '%s/%s/eventslast.php?id=%s' % (API_BASE_URL,API_KEY,str(teamid))
                    data = json.load(urllib2.urlopen(url))
                    events = data["results"]
                    if events:
                        for event in events:
                            eventlist.append(_event.as_event(event))
                else:
                   xbmc.log(msg="[TheSportsDB] teamid must be provided", level=xbmc.LOGERROR)
                return eventlist

            def League(self,leagueid=None):
                eventlist = []
                if leagueid:
                    url = '%s/%s/eventspastleague.php?id=%s' % (API_BASE_URL,API_KEY,str(leagueid))
                    data = json.load(urllib2.urlopen(url))
                    events = data["events"]
                    if events:
                        for event in events:
                            eventlist.append(_event.as_event(event))
                else:
                   xbmc.log(msg="[TheSportsDB] leagueid must be provided", level=xbmc.LOGERROR)
                return eventlist


        class Next:

            def Team(self,teamid=None):
                eventlist = []
                if teamid:
                    url = '%s/%s/eventsnext.php?id=%s' % (API_BASE_URL,API_KEY,str(teamid))
                    data = json.load(urllib2.urlopen(url))
                    events = data["events"]
                    if events:
                        for event in events:
                            eventlist.append(_event.as_event(event))
                else:
                   xbmc.log(msg="[TheSportsDB] teamid must be provided", level=xbmc.LOGERROR)
                return eventlist

            def League(self,leagueid=None, rnd=None):
                eventlist = []
                if leagueid and not rnd:
                    url = '%s/%s/eventsnextleague.php?id=%s' % (API_BASE_URL,API_KEY,str(leagueid))
                elif leagueid and rnd:
                    url = '%s/%s/eventsnextleague.php?id=%s&r=%s' % (API_BASE_URL,API_KEY,str(leagueid),str(rnd))                   
                else:
                   xbmc.log(msg="[TheSportsDB] leagueid must be provided", level=xbmc.LOGERROR)
                   return eventlist
                data = json.load(urllib2.urlopen(url))
                events = data["events"]
                if events:
                    for event in events:
                        eventlist.append(_event.as_event(event))     
                return eventlist

        def Lookup(self,datestring=None,datetimedate=None,league=None,leagueid=None,season=None,rnd=None,sport=None):
            eventlist=[]
            if leagueid and season and rnd:
                url = '%s/%s/eventsround.php?id=%s&r=%s&s=%s' % (API_BASE_URL,API_KEY,str(leagueid),str(rnd),str(season))
            elif leagueid and season and not rnd:
                url = '%s/%s/eventsseason.php?id=%s&s=%s' % (API_BASE_URL,API_KEY,str(leagueid),str(season))
            elif datestring or datetimedate:
                if datestring:
                    if _util.CheckDateString(datestring):
                        pass
                    else:
                        xbmc.log(msg="[TheSportsDB] Wrong format for the datestring. Valid format is {YYYY-MM-DD} (eg: 2014-10-10)", level=xbmc.LOGERROR)
                        return eventlist
                else:
                    if _util.CheckDateTime(datetimedate):
                        datestring = datetimedate.strftime("%Y-%m-%d")
                    else:
                        xbmc.log(msg="[TheSportsDB] Wrong type for datetime object. A python datetime object is required", level=xbmc.LOGERROR)
                        return eventlist
                if sport:
                    url = '%s/%s/eventsday.php?d=%s&s=%s' % (API_BASE_URL,API_KEY,str(datestring),str(sport))
                elif league:
                    url = '%s/%s/eventsday.php?d=%s&l=%s' % (API_BASE_URL,API_KEY,str(datestring),urllib.quote(league))
                else:
                    url = '%s/%s/eventsday.php?d=%s' % (API_BASE_URL,API_KEY,str(datestring))
            else:
                xbmc.log(msg="[TheSportsDB] Wrong method invocation. You need to declare either a datetimedate (datetime.date), a datestring, a leagueid, season, rnd or sport", level=xbmc.LOGERROR)
                return eventlist
            data = json.load(urllib2.urlopen(url))
            events = data["events"]
            if events:
                for event in events:
                    eventlist.append(_event.as_event(event))     
            return eventlist

    class Livescores:

        def Soccer(self,objects=False):
            url = '%s/%s/latestsoccer.php' % (API_BASE_URL,API_KEY)
            eventlist = []
            data = json.load(urllib2.urlopen(url))
            try:events = data["teams"]["Match"]
            except: events = ''
            if objects:
                api = Api(API_KEY)
            if events:
                if type(events) != list:
                    events = [events]
                for event in events:
                    eventobj = livescores.as_event(event)
                    try:
                        if objects:
                            hometeam = api.Lookups().Team(eventobj.HomeTeam_Id)[0]
                            awayteam = api.Lookups().Team(eventobj.AwayTeam_Id)[0]
                            eventobj.setHomeTeamObj(hometeam)
                            eventobj.setAwayTeamObj(awayteam)
                        eventlist.append(eventobj)
                    except: pass
            return eventlist

    class Image:

        def Preview(self,image):
            if (image.startswith("http://www.thesportsdb.com/images/") and image.endswith(".png")) or (image.startswith("http://www.thesportsdb.com/images/") and image.endswith(".jpg")):
                return image + "/preview"
            else:
                return None

        def Original(self,image):
            if (image.startswith("http://www.thesportsdb.com/images/") and image.endswith(".png")) or (image.startswith("http://www.thesportsdb.com/images/") and image.endswith(".jpg")):
                return image
            else:
                return None

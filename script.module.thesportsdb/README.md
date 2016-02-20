# script.module.thesportsdb
![TheSportsDb Icon](http://s17.postimg.org/h3eanic3z/icon.png)

A python module packaged as a Kodi script module to wrap all thesportsdb API methods and for you to use on your own addon. An API key is required, please visit [thesportsdb](http://www.thesportsdb.com/forum/viewtopic.php?f=6&t=6) for more information.

##Usage

###Addon.xml
The module most be imported in the addon.xml of your addon and pointing to the correct version of the module
```xml
<import addon="script.module.thesportsdb" version="1.0.0"/>
```

###Pythonic usage

The module follows the API structure described [Here](http://www.thesportsdb.com/forum/viewtopic.php?f=6&t=5). Every group method (Search,Lookups,Schedules,Livescores) is a Python class and all the endpoints (eg: lookupleague) is part of a class method. The module maps the json data to objects as much as possible, so each call returns one or more Team objects, League objects, Player objects, Livescores objects, Table objects, etc. Below all the classes and methods are explained with examples. Object properties are detailed later despite being exemplified some times.

###A really simple usage example...

```python
import thesportsdb
api = thesportsdb.Api(key="1")
players = api.Search().Players(team="Arsenal")
for player in players:
    print(player.strPlayer)
```

###Module methods

####Search
* Search for teams by name - (returns a list of team objects)
```python
teams = api.Search().Teams(team="Arsenal")
```

* Search for all teams in a League - (returns a list of team objects)
```python
teams = api.Search().Teams(league="English Premier League")
```

* Search for all Teams in a sport by country - (returns a list of team objects)
```python
teams = api.Search().Teams(sport="Soccer",country="England")
```

* Search for all players from a team - (returns a list of player objects)
```python
players = api.Search().Players(team="Arsenal")
```

* Search for players by name - (returns a list of player objects)
```python
players = api.Search().Players(player="Danny Welbeck")
```

* Search for players by team and name - (returns a list of player objects)
```python
players = api.Search().Players(team="Arsenal",player="Danny Welbeck")
```

* Search for events by event name - (returns a list of event objects)
```python
events = api.Search().Events(event="Arsenal vs Chelsea")
```

* Search for events by filename - (returns a list of event objects)
```python
events = api.Search().Events(filename="English_Premier_League_2015-04-26_Arsenal_vs_Chelsea")
```

* Search for event by event name and season - (returns a list of event objects)
```python
events = api.Search().Events(event="Arsenal vs Chelsea",season=1415)
```

* Search for all Leagues in a country - (returns a list of league objects)
```python
leagues = api.Search().Leagues(country="England")
```

* Search for all Leagues by sport - (returns a list of league objects)
```python
leagues = api.Search().Leagues(sport="Soccer")
```

* Search for all Leagues in a country and by sport - (returns a list of league objects)
```python
leagues = api.Search().Leagues(country="England",sport="Soccer")
```

* Search for all Seasons in a League provided the league id - (returns a list of strings each one identifying a season)
```python
seasons = api.Search().Seasons(leagueid=4328)
```

* Search for all the user loved items - (returns single user object. Properties (Players,Events,Teams) are lists of id's - faster/need further lookup)
```python
loves = api.Search().Loves(user="zag")
```

* Search for all the user loved items - (returns single user object. Properties (Players,Events,Teams) are lists of objects - slower/returns the object itself)
```python
loves = api.Search().Loves(user="zag",objects=True)
```

A more detailed example using user loves:
```python
import thesportsdb
api = thesportsdb.Api(key="1")
userloves = api.Search().Loves(user="zag")
print(userloves.Teams, userloves.Players, userloves.Events)
>> [u'133632', u'133597',....

userloves = api.Search().Loves(user="zag",objects=True)
print(userloves.Teams, userloves.Players, userloves.Events)
>> [<thesportsdb.team.Team instance at 0x129d4d200>, <thesportsdb.team.Team instance at 0x11e1ba5f0>,....
```

####Lookups
* Provides League Details given the leagueid (returns a list of league objects)
```python
leagues = api.Lookups().League(leagueid=4346)
```

* League seasons by leagueid (returns a list of seasonid strings)
```python
seasons = api.Lookups().Seasons(leagueid=4346)
```
* Provides Team Details given the teamid (returns a list of team objects)
```python
teams = api.Lookups().Team(teamid=133604)
```

* All teams in a league provided the leagueid (returns a list of team objects)
```python
teams = api.Lookups().Team(leagueid=4346)
```

* Provides Player Details given the playerid (returns a list of player objects)
```python
players = api.Lookups().Player(playerid=34145937)
```

* All players in a team by teamid (returns a list of player objects)
```python
players = api.Lookups().Player(teamid=133604)
```

* Provides Event Details given the eventid (returns a list of event objects)
```python
events = api.Lookups().Event(eventid=441613)
```

* Lookup Table by League ID and Season (returns a list of tableentry objects without team objects)
```python
table = api.Lookups().Table(leagueid=4346)
```

* Lookup Table by League ID and Season (returns a list of tableentry objects each one containing a team object as Team property)
```python
table = api.Lookups().Table(leagueid=4346,objects=True)
```

A more detailed example using League Tables:
```python
import thesportsdb
api = thesportsdb.Api(key="1")
table = api.Lookups().Table(leagueid=4346)
if table:
	print(table[0].name,table[0].Team)

>> FC Dallas
>>

table = api.Lookups().Table(leagueid=4346,objects=True)
if table:
	print(table[0].name,table[0].Team, table[0].Team.strTeamBadge)

>> FC Dallas
>> <thesportsdb.team.Team instance at 0x12768ab80>
>> http://www.thesportsdb.com/images/media/team/badge/xvrwus1420778297.png
```

####Livescores

* Soccer Livescores (returns a list of Livescores objects - no Team objects defined)
```python
matches = api.Livescores().Soccer()
```

* Soccer Livescores (returns a list of Livescores objects - Team objects defined)
```python
matches = api.Livescores().Soccer(objects=True)
```

A full example using Soccer livescores:
```python
import thesportsdb
api = thesportsdb.Api(key="1")
matches = api.Livescores().Soccer(objects=True)
if matches:
	for match in matches:
		print("HomeTeam: %s HomeTeamLogo: %s %s:%s AwayTeam: %s AwayTeamLogo: %s" % (match.HomeTeam,match.HomeTeamObj.strTeamBadge,match.HomeGoals,match.AwayGoals,match.AwayTeam,match.AwayTeamObj.strTeamBadge))
```

####Schedules

* Next 5 Events by Team Id (returns a list of Event Objects)
```python
events = api.Schedules().Next().Team(teamid=133602)
```

* Next 15 Events by League Id (returns a list of Event Objects)
```python
events = api.Schedules().Next().League(leagueid=4328)
```

* Next 15 Events by League Id and Round (returns a list of Event Objects)
```python
events = api.Schedules().Next().League(leagueid=4328,rnd=38)
```

* Last 5 Events by Team Id (returns a list of Event Objects)
```python
events = api.Schedules().Last().Team(teamid=133602)
```

* Last 15 Events by League Id (returns a list of Event Objects)
```python
events = api.Schedules().Last().League(leagueid=4328)
```

* Events on a specific day provided a date string (returns a list of Event Objects)
```python
events = api.Schedules().Lookup(datestring="2014-10-10")
```

* Events on a specific day provided a datetime object (returns a list of Event Objects)
```python
import datetime
events = api.Schedules().Lookup(datetimedate=datetime.date(year=2014, month=10, day=10))
```

* Events on a specific day by sport provided a date string or a datetime.date object (returns a list of Event Objects)
```python
events = api.Schedules().Lookup(datestring="2014-10-10",sport="soccer")
```
```python
events = api.Schedules().Lookup(datetimedate=datetime.date(year=2014, month=10, day=10),sport="soccer")
```

* Events on a specific day by league provided a date string or a datetime.date object (returns a list of Event Objects)
```python
events = api.Schedules().Lookup(datestring="2014-10-10",league="Australian A-League")
```
```python
events = api.Schedules().Lookup(datetimedate=datetime.date(year=2014, month=10, day=10),league="Australian A-League")
```

* Events in a specific round of a league by season (returns a list of Event Objects)
```python
events = api.Schedules().Lookup(leagueid=4328,rnd=38,season=1415)
```

* All events in a specific league by season
```python
events = api.Schedules().Lookup(leagueid=4328,season=1415)
```

####Images
TheSportsDB provides a way of getting a preview of the image. The same can be done in this module using `api.Image().Preview(image)`. A full example is below:
```python
import thesportsdb
api = thesportsdb.Api(key="1")
team = api.Lookups().Team(teamid=134108)[0]
print(team.strTeamFanart4)
print(api.Image().Preview(team.strTeamFanart4))
print(api.Image().Original(team.strTeamFanart4))
>>http://www.thesportsdb.com/images/media/team/fanart/wqywqq1421075962.jpg
>>http://www.thesportsdb.com/images/media/team/fanart/wqywqq1421075962.jpg/preview
>>http://www.thesportsdb.com/images/media/team/fanart/wqywqq1421075962.jpg
```

###Objects

####Team
Default Properties
* `idTeam` - id of the team in thesportsdb
* `idSoccerXML` - id of the team in soccerXML
* `intLoved` - number of thesportsdb users that love the team
* `strTeam` - team name
* `strTeamShort` - short team name
* `strAlternate` - team alternative name
* `intFormedYear` - year of foundation
* `strSport` - sport the team is associated with
* `strLeague` - league in which the team is participating
* `idLeague` - the id of the league of the team
* `strDivision` - division of the league 
* `strManager` - team manager name
* `strStadium` - name of the team's stadium
* `strKeywords` - keywords to help identifying the team
* `strRSS` - RSS url for team news
* `strStadiumThumb` - thumbnail of the stadium
* `strStadiumDescription` - stadium description
* `strStadiumLocation` - location of the stadium
* `strWebsite` - official website of the team
* `strFacebook` - official facebook page of the team
* `strTwitter` - official team's twitter page
* `strInstagram` - official team's instagram page
* `strYoutube` - official team's youtube page
* `strDescriptionEN` - team plot in English (might not be available)
* `strDescriptionDE` - team plot in German (might not be available)
* `strDescriptionFR` - team plot in French (might not be available)
* `strDescriptionCN` - team plot in Chinese (might not be available)
* `strDescriptionIT` - team plot in Italian (might not be available)
* `strDescriptionJP` - team plot in Japanese (might not be available)
* `strDescriptionRU` - team plot in Russian (might not be available)
* `strDescriptionES` - team plot in Spanish (might not be available)
* `strDescriptionPT` - team plot in Portuguese (might not be available)
* `strDescriptionSE` - team plot in Swedish (might not be available)
* `strDescriptionNL` - team plot in Dutch (might not be available)
* `strDescriptionHU` - team plot in Hungarian (might not be available)
* `strDescriptionNO` - team plot in Norwegian (might not be available)
* `strDescriptionIL` - team plot in Hebrew (might not be available)
* `strDescriptionPL` - team plot in Polish (might not be available)
* `strGender` - team gender
* `strCountry` - country of the team
* `strTeamBadge` - team badge (logo)
* `strTeamJersey` - team jersey clearart
* `strTeamLogo` - team logo clearart
* `strTeamFanart1` - team fanart 1 (general)
* `strTeamFanart2` - team fanart 2 (general)
* `strTeamFanart3` - team fanart 3 (team)
* `strTeamFanart4` - team fanart 4 (players)
* `strTeamBanner` - team banner

Specific module Properties

* `AlternativeNameFirst` - Returns the alternative name of the team first and the default team name as fallback
* `FanartList` - Returns a python list containing all fanarts
* `FanFanart` - Returns the fans fanart(3) or a random fanart as fallback
* `PlayerFanart` - Returns the player fanart or a random fanart as fallback
* `RandomFanart` - Returns a random fanart or None as fallback
* `strDescription` - Returns the description of the team in the language your Kodi instalation is using. Fallback is done to English

####League
Default Properties
* `idSoccerXML` - id of the league on soccerXML
* `strSport` - sport of the league
* `strLeague` - league name
* `idLeague` - id of the league on the database
* `strLeagueAlternate` - alternative league name
* `intFormedYear` - league formation year
* `dateFirstEvent` - date of the first event
* `strGender` - gender of the league
* `strCountry` - country of the league
* `strWebsite` - league official website
* `strFacebook` - league facebook page
* `strTwitter` - league twitter
* `strYoutube` - league youtube channel
* `strRSS` - RSS feed with league news
* `strDescriptionEN` - league plot in English (might not be available)
* `strDescriptionDE` - league plot in German (might not be available)
* `strDescriptionFR` - league plot in French (might not be available)
* `strDescriptionCN` - league plot in Chinese (might not be available)
* `strDescriptionIT` - league plot in Italian (might not be available)
* `strDescriptionJP` - league plot in Japanese (might not be available)
* `strDescriptionRU` - league plot in Russian (might not be available)
* `strDescriptionES` - league plot in Spanish (might not be available)
* `strDescriptionPT` - league plot in Portuguese (might not be available)
* `strDescriptionSE` - league plot in Swedish (might not be available)
* `strDescriptionNL` - league plot in Dutch (might not be available)
* `strDescriptionHU` - league plot in Hungarian (might not be available)
* `strDescriptionNO` - league plot in Norwegian (might not be available)
* `strDescriptionIL` - league plot in Hebrew (might not be available)
* `strDescriptionPL` - league plot in Polish (might not be available)
* `strFanart1` - fanart 1 of the league
* `strFanart2` - fanart 2 of the league
* `strFanart3` - fanart 3 of the league
* `strFanart4` - fanart 4 of the league
* `strBanner` - league banner
* `strBadge` - league badge (logo)
* `strLogo` - league logo clearart
* `strPoster` - league poster
* `strTrophy` - league trophy clearart
* `strNaming` - league naming

Specific module Properties
* `AlternativeNameFirst` - Returns the alternative name of the team first and the default team name as fallback
* `FanartList` - Returns a python list containing all fanarts
* `RandomFanart` - Returns a random fanart or None as fallback
* `strDescription` - Returns the description of the team in the language your Kodi instalation is using. Fallback is done to English

####Player
Default Properties
* `idPlayer` - player id on thesportsdb
* `idTeam` - team id on thesportsdb
* `idSoccerXML` - player id on soccerXML
* `idPlayerManager` - manager id 
* `strNationality` - player nationality
* `strPlayer` - player's name
* `strTeam` - player's team name
* `strSport` - player's sport
* `intSoccerXMLTeamID` - team id on soccerXML
* `dateBorn` - birth date of the player
* `dateSigned` - sign date of the player
* `strSigning` - signing value for the player
* `strWage` - wage of the player (month)
* `strDescriptionEN` - player plot in English (might not be available)
* `strDescriptionDE` - player plot in German (might not be available)
* `strDescriptionFR` - player plot in French (might not be available)
* `strDescriptionCN` - player plot in Chinese (might not be available)
* `strDescriptionIT` - player plot in Italian (might not be available)
* `strDescriptionJP` - player plot in Japanese (might not be available)
* `strDescriptionRU` - player plot in Russian (might not be available)
* `strDescriptionES` - player plot in Spanish (might not be available)
* `strDescriptionPT` - player plot in Portuguese (might not be available)
* `strDescriptionSE` - player plot in Swedish (might not be available)
* `strDescriptionNL` - player plot in Dutch (might not be available)
* `strDescriptionHU` - player plot in Hungarian (might not be available)
* `strDescriptionNO` - player plot in Norwegian (might not be available)
* `strDescriptionIL` - player plot in Hebrew (might not be available)
* `strDescriptionPL` - player plot in Polish (might not be available)
* `strGender` - gender of the player
* `strPosition` - position of the player
* `strCollege` - college of the player
* `strFacebook` - player's official facebook page
* `strWebsite` - player's official website
* `strTwitter` - player's official twitter page
* `strInstagram` - player's official instagram page
* `strYoutube` - player's official youtube page
* `strHeight` - player's height
* `strWeight` - player's weight
* `intLoved` - number of users which love the player on thesportsdb
* `strThumb` - player's thumb
* `strCutout` - player's cutout (clearart)
* `strFanart1` - player fanart 1
* `strFanart2` - player fanart 2
* `strFanart3` - player fanart 3
* `strFanart4` - player fanart 4

Specific module Properties
* `strDescription` - Returns the description of the team in the language your Kodi instalation is using. Fallback is done to English
* `FanartList` - Returns a python list containing all fanarts
* `RandomFanart` - Returns a random fanart or None as fallback
* `dateBornAsDatetime` - Returns the birth date of the player as a datetime.date object
* `dateSignedAsDatetime` - Returns the signing date of the player as a python datetime.date object

####Table entry
* `name` - name of the team
* `teamid` - id of the team on thesportsdb 
* `played` - number of played matches
* `goalsfor` - number of goals scored
* `goalsagainst` - number of goals suffered
* `goalsdifference` - goal difference
* `win` - number of wins
* `draw` - number of draws
* `loss` - number of losses
* `total` - number of points
* `Team` - a team object (defined if objects=True). All the other team properties are available

####Event
Default Properties
* `idEvent` - id of the event on thesportsdb
* `idSoccerXML` - id of the event on soccerXML
* `strEvent` - event name
* `strFilename` - filename name that matches easily the event
* `strSport` - sport of the event
* `idLeague` - id of the league on thesportsdb for the event
* `strLeague` - name of the league on the thesportsdb for the event
* `strSeason` - season identifier for the event
* `strDescriptionEN` - description/plot of the event (english only)
* `strHomeTeam` - name of the home team
* `strAwayTeam` - name of the away team
* `intHomeScore` - score of the hometeam
* `intRound` - round of the event on the league it refers to
* `intAwayScore` - away score
* `intSpectators` - number of spectators
* `strHomeGoalDetails` - details for the goals of the hometeam
* `strHomeRedCards` - details for the redcards of the hometeam
* `strHomeYellowCards` - details for the yellow cards of the hometeam
* `strHomeLineupGoalkeeper` - starter goalkeeper of the hometeam
* `strHomeLineupDefense` - starter defense of the hometeam
* `strHomeLineupMidfield` - starter midfielders of the hometeam
* `strHomeLineupForward` - starter forwarders of the hometeam
* `strHomeLineupSubstitutes` - substitutes/bench for the hometeam
* `strHomeFormation` - formation of the hometeam (eg 4-4-2)
* `strAwayRedCards` - details for the redcards of the awayteam
* `strAwayYellowCards` - details for the yellow cards of the awayteam
* `strAwayGoalDetails` - away team goal details
* `strAwayLineupGoalkeeper` - starter goalkeeper of the awayteam
* `strAwayLineupDefense` - starter defense of the awayteam
* `strAwayLineupMidfield` - starter midfielders of the awayteam
* `strAwayLineupForward` - starter forwarders of the awayteam
* `strAwayLineupSubstitutes` - substitutes of the awayteam
* `strAwayFormation` - formation of the away team
* `intHomeShots` - number of shots for the hometeam
* `intAwayShots` - number of away shots for the awayteam
* `dateEvent` - date of the event (eg 2015-10-10)
* `strDate` - date of the event (2015/10/10)
* `strTime` - time of the event (eg 16:00:00+00:00)
* `strTVStation` - tvstations of the event
* `idHomeTeam` - id of the hometeam
* `idAwayTeam` - id of the awayteam
* `strResult` - result of the event 
* `strCircuit` - name of the circuit (motorsports)
* `strCountry` - country of the event (motorsports)
* `strCity` - city of the event (motorsports)
* `strPoster` - poster of the event
* `strFanart` - fanart of the event
* `strThumb` - thumbnail of the event
* `strBanner` - banner of the event
* `strMap` - image of the map of the event (motorsports)

Specific module Properties
* `strDescription` - returns the description of the event (english only)
* `eventDateTime` -  returns a datetime object with the datetime of the event (GMT timezone)

Note: event lookups do not return the team objects. You need a second lookup using the teamId's to grab the team objects

####Livescores
Default Properties
* `Date` - datetime string for the event time (eg: "2016-01-28T17:30:00+00:00" - GMT timezone) 
* `League` - League string for the live event
* `Round` -  Round for the league of the live event
* `Spectators` -  Number of spectators for the live event
* `HomeTeam` -  Name of the hometeam for the live event
* `HomeTeam_Id` - Id for the hometeam for the live event on thesportsdb
* `AwayTeam` -  Name for the awayteam for the live event
* `AwayTeam_Id` -  Id for the awayteam for the live event on thesportsdb
* `Time` - time string for the match
* `HomeGoals` -  Number of goals for the hometeam
* `AwayGoals` -  Number of goals for the awayteam
* `HomeGoalDetails` -  Details of the goals for the hometeam
* `AwayGoalDetails` -  Details of the goals for the awayteam
* `HomeLineupGoalkeeper` -  Details for the hometeam goalkeeper
* `AwayLineupGoalkeeper` -  Details for the awayteam goalkeeper
* `HomeLineupDefense` -  Details for the hometeam defense
* `AwayLineupDefense` -  Details for the awayteam defense
* `HomeLineupMidfield` -  Details for the hometeam midfielders
* `AwayLineupMidfield` -  Details for the awayteam midfielders
* `HomeLineupForward` -  Details for the hometeam forwarders
* `AwayLineupForward` -  Details for the awayteam forwarders
* `HomeLineupSubstitutes` -  Details for the hometeam bench
* `AwayLineupSubstitutes` -  Details for the awayteam bench
* `HomeLineupCoach` -  Hometeam coach
* `AwayLineupCoach` -  Awayteam coach
* `HomeSubDetails` -  Substitutions details for the hometeam
* `AwaySubDetails` - Substitutions details for the awayteam
* `HomeTeamFormation` -  Formation of the hometeam
* `AwayTeamFormation` -  Formation of the awayteam
* `Location` -  Location of the event
* `Stadium` -  Name of the stadium of the event
* `HomeTeamYellowCardDetails` - Details for the yellow cards of the hometeam 
* `AwayTeamYellowCardDetails` -  Details for the yellow cards of the awayteam
* `HomeTeamRedCardDetails` -  Details for the redcards of the hometeam
* `AwayTeamRedCardDetails` -  Details for the redcards of the awayteam
* `Referee`- Match referee name
* `HomeLineupCoach` - Home team coach name
* `AwayLineupCoach` - Away team coach name

Specific module Properties
* `DateTime` - Returns the date of the event as a python datetime object (GMT timezone)


####User
* `strUsername ` - the user username
* `Teams ` - a list of teamids for the teams the user loves (or team objects if objects=True)
* `Players ` - a list of playerids for the players the user loves (or player objects if objects=True)
* `Leagues ` - a list of leagueids for the leagues the user loves (or league objects if objects=True)
* `Events ` - a list of eventids for the events the user loves (or event objects if objects=True)

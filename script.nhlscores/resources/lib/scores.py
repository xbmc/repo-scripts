import copy
import os
import pytz
import requests
import time
import datetime

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs


def is_between(now, start, end):
    is_between = False

    is_between |= start <= now <= end
    is_between |= end < start and (start <= now or now <= end)

    return is_between


def convert_to_nhl_periods(period):
    if period == 1:
        return "1st"
    elif period == 2:
        return "2nd"
    elif period == 3:
        return "3rd"
    elif period > 3:
        # For overtime periods
        return f"{period - 3} OT"
    else:
        return "Invalid period"

class Scores:

    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.addon_path = xbmcvfs.translatePath(self.addon.getAddonInfo('path'))
        self.local_string = self.addon.getLocalizedString
        self.ua_ipad = 'Mozilla/5.0 (iPad; CPU OS 8_4 like Mac OS X) AppleWebKit/600.1.4 (KHTML, like Gecko) Mobile/12H143 ipad nhl 5.0925'
        self.nhl_logo = os.path.join(self.addon_path,'resources','nhl_logo.png')
        self.api_url = 'https://api-web.nhle.com/v1/score/now'
        self.headshot_url = 'http://nhl.bamcontent.com/images/headshots/current/60x60/%s@2x.png'
        self.score_color = 'FF00B7EB'
        self.gametime_color = 'FFFFFF66'
        self.new_game_stats = []
        self.wait = 30
        self.display_seconds = 5
        self.display_milliseconds = self.display_seconds * 1000
        self.dialog = xbmcgui.Dialog()
        self.monitor = xbmc.Monitor()
        self.test = False
        self.daily_check_timer = 1500 #25 minutes

    def service(self):
        first_run = True
        self.addon.setSetting(id='score_updates', value='false')

        while not self.monitor.abortRequested():
            daily_check_time = is_between(datetime.datetime.now().time(), datetime.time(3), datetime.time(4))
            running = self.addon.getSettingBool(id='score_updates')
            xbmc.log(f"[script.nhlscores][{datetime.datetime.now()}] first_run: {first_run}, daily_check_time: {daily_check_time}, between: {daily_check_time}, running: {running}")

            if first_run or (daily_check_time and not running):
                xbmc.log(f"[script.nhlscores][{datetime.datetime.now()}] Toggle ON")
                self.addon.setSetting(id='score_updates', value='true')
                self.notify(self.local_string(30300), self.local_string(30350))
                if not self.test: self.check_games_scheduled()
                self.scoring_updates()
                self.addon.setSetting(id='score_updates', value='false')

                first_run = False

            self.monitor.waitForAbort(self.daily_check_timer)

    def string_to_date(self, string, date_format):
        try:
            date = datetime.datetime.strptime(str(string), date_format)
        except TypeError:
            date = datetime.datetime(*(time.strptime(str(string), date_format)[0:6]))

        return date

    def check_games_scheduled(self):
        # Check if any games are scheduled for today.
        # If so, check if any are live and if not sleep until first game starts
        json = self.get_scoreboard()
        if 'games' not in json or len(json['games']) == 0:
            self.addon.setSetting(id='score_updates', value='false')
            self.notify(self.local_string(30300), self.local_string(30351))
        else:
            live_games = 0
            for game in json['games']:
                if game['gameState'].lower() == 'live':
                    live_games += 1
                    break

            if live_games == 0:
                first_game_start = self.string_to_date(json['games'][0]['startTimeUTC'], "%Y-%m-%dT%H:%M:%SZ")
                sleep_seconds = int((first_game_start - datetime.datetime.utcnow()).total_seconds())
                if sleep_seconds >= 6600:
                    # hour and 50 minutes or more just display hours
                    delay_time = f" {round(sleep_seconds / 3600)} hours"
                elif sleep_seconds >= 4200:
                    # hour and 10 minutes
                    delay_time = f"an hour and {round((sleep_seconds / 60) - 60)} minutes"
                elif sleep_seconds >= 3000:
                    # 50 minutes
                    delay_time = "an hour"
                else:
                    delay_time = f"{round((sleep_seconds / 60))} minutes"

                message = f"First game starts in about {delay_time}"
                self.notify(self.local_string(30300), message)
                self.monitor.waitForAbort(sleep_seconds)

    def get_scoreboard(self):
        headers = {'User-Agent': self.ua_ipad}
        r = requests.get(self.api_url, headers=headers)
        return r.json()

    def scoring_updates_on(self):
        return self.addon.getSetting(id="score_updates") == 'true'

    def get_video_playing(self):
        video_playing = ''
        if xbmc.Player().isPlayingVideo(): video_playing = xbmc.Player().getPlayingFile().lower()
        return video_playing

    def get_new_stats(self, game, old_game_stats):
        ateam = game['awayTeam']
        hteam = game['homeTeam']
        current_period = convert_to_nhl_periods(game['periodDescriptor']['number']) if 'periodDescriptor' in game else ''
        game_clock = f"{current_period} {game['clock']['timeRemaining']}" if 'clock' in game else ''

        desc = ''
        headshot = ''
        if 'goals' in game and len(game['goals']) > 0:
            last_goal = game['goals'][-1]
            desc = f"{last_goal['name']['default']} ({last_goal['goalsToDate']})"
            headshot = last_goal['mugshot']

        # If home score and away score is more than the length of the goals array
        # Don't store the new value, use the old one until the description is filled
        if 'goals' in game and len(game['goals']) > 0 and (ateam['score'] + hteam['score'] > len(game['goals'])):
            for old_item in old_game_stats:
                if not self.scoring_updates_on(): break
                if game['game_id'] == old_item['game_id']:
                    self.new_game_stats.append(old_item)

        else:
            self.new_game_stats.append(
                {"game_id": game['id'],
                 "away_name": ateam['abbrev'],
                 "home_name": hteam['abbrev'],
                 "away_score": ateam['score'] if 'score' in ateam else '',
                 "home_score": hteam['score'] if 'score' in hteam else '',
                 "game_clock": game_clock,
                 "period": current_period,
                 "goal_desc": desc,
                 "headshot": headshot,
                 "abstract_state": game['gameState']})

    def set_display_time(self):
        self.display_seconds = int(self.addon.getSetting(id="display_seconds"))
        self.display_milliseconds = self.display_seconds * 1000

    def final_score_message(self, new_item):
        # Highlight score of the winning team
        title = self.local_string(30355)
        if new_item['away_score'] > new_item['home_score']:
            away_score = f"[COLOR={self.score_color}]{new_item['away_name']} {new_item['away_score']}[/COLOR]"
            home_score = f"{new_item['home_name']} {new_item['home_score']}"
        else:
            away_score = f"{new_item['away_name']} {new_item['away_score']}"
            home_score = f"[COLOR={self.score_color}]{new_item['home_name']} {new_item['home_score']}[/COLOR]"

        game_clock = f"[COLOR={self.gametime_color}]{new_item['game_clock']}[/COLOR]"
        message = f"{away_score}  {home_score}  {game_clock}"
        return title, message

    def game_started_message(self, new_item):
        title = self.local_string(30358)
        message = f"{new_item['away_name']} @ {new_item['home_name']}"
        return title, message

    def period_change_message(self, new_item):
        # Notify user that the game has started / period has changed
        title = self.local_string(30370)
        message = f"{new_item['away_name']} {new_item['away_score']}    " \
                  f"{new_item['home_name']} {new_item['home_score']}   " \
                  f"[COLOR={self.gametime_color}]{new_item['period']} has started[/COLOR]"

        return title, message

    def goal_scored_message(self, new_item, old_item):
        # Highlight score for the team that just scored a goal
        away_score = f"{new_item['away_name']} {new_item['away_score']}"
        home_score = f"{new_item['home_name']} {new_item['home_score']}"
        game_clock = f"[COLOR={self.gametime_color}]{new_item['game_clock']}[/COLOR]"

        if new_item['away_score'] != old_item['away_score']:
            away_score = f"[COLOR={self.score_color}]{away_score}[/COLOR]"
        if new_item['home_score'] != old_item['home_score']:
            home_score = f"[COLOR={self.score_color}]{home_score}[/COLOR]"

        if self.addon.getSetting(id="goal_desc") == 'false':
            title = self.local_string(30365)
            message = f"{away_score}  {home_score}  {game_clock}"
        else:
            title = f"{away_score}  {home_score}  {game_clock}"
            message = new_item['goal_desc']

        return title, message

    def check_if_changed(self, new_item, old_item):
        title = None
        message = None
        img = self.nhl_logo
        xbmc.log("-"+str(new_item))
        xbmc.log("~"+str(old_item))

        if 'final' in new_item['abstract_state'].lower() and 'final' not in old_item['abstract_state'].lower():
            title, message = self.final_score_message(new_item)
        elif 'live' in new_item['abstract_state'].lower() and 'live' not in old_item['abstract_state'].lower():
            title, message = self.game_started_message(new_item)
        elif new_item['period'] != old_item['period']:
            # Notify user that the game has started / period has changed
            title, message = self.period_change_message(new_item)
        elif (new_item['home_score'] != old_item['home_score'] and new_item['home_score'] > 0) \
                or (new_item['away_score'] != old_item['away_score'] and new_item['away_score'] > 0):
            # Highlight score for the team that just scored a goal
            title, message = self.goal_scored_message(new_item, old_item)
            # Get goal scorers headshot if notification is a score update
            if self.addon.getSetting(id="goal_desc") == 'true' and new_item['headshot'] != '': img = new_item['headshot']

        if title is not None and message is not None:
            # Delay displaying notification X seconds
            self.monitor.waitForAbort(int(self.addon.getSetting(id="delay_seconds")))
            self.notify(title, message, img)
            self.monitor.waitForAbort(self.display_seconds + 5)

    def testing(self, new_item):
            img = self.nhl_logo

            title, message = self.final_score_message(new_item)
            self.notify(title, message, img)
            self.monitor.waitForAbort(self.display_seconds + 5)

            title, message = self.game_started_message(new_item)
            self.notify(title, message, img)
            self.monitor.waitForAbort(self.display_seconds + 5)

            title, message = self.period_change_message(new_item)
            self.notify(title, message, img)
            self.monitor.waitForAbort(self.display_seconds + 5)

            title, message = self.goal_scored_message(new_item, new_item)
            # Get goal scorers headshot if notification is a score update
            if self.addon.getSetting(id="goal_desc") == 'true' and new_item['headshot'] != '': img = new_item['headshot']
            self.notify(title, message, img)
            self.monitor.waitForAbort(self.display_seconds + 5)

    def scoring_updates(self):
        first_time_thru = 1
        old_game_stats = []
        while self.scoring_updates_on() and not self.monitor.abortRequested():
            json = self.get_scoreboard()
            self.new_game_stats.clear()
            xbmc.log("Games: " + str(len(json['games'])))
            for game in json['games']:
                # Break out of loop if updates disabled
                if not self.scoring_updates_on(): break
                self.get_new_stats(game, old_game_stats)

            if first_time_thru != 1:
                self.set_display_time()
                all_games_finished = 1
                xbmc.log("new game stats count: " + str(len(self.new_game_stats)))
                xbmc.log("old game stats count: " + str(len(old_game_stats)))
                for new_item in self.new_game_stats:
                    if not self.scoring_updates_on(): break
                    # Check if all games have finished
                    if 'final' not in new_item['abstract_state'].lower(): all_games_finished = 0
                    for old_item in old_game_stats:
                        if not self.scoring_updates_on(): break
                        if new_item['game_id'] == old_item['game_id']:
                            self.check_if_changed(new_item, old_item)

                if self.test:
                    self.testing(new_item)

                # if all games have finished for the night stop the script
                if all_games_finished and self.scoring_updates_on():
                    self.addon.setSetting(id='score_updates', value='false')
                    xbmc.log("[script.nhlscores] End of day")
                    # If the user is watching a game don't display the all games finished message
                    if 'nhl_game_video' not in self.get_video_playing():
                        self.notify(self.local_string(30300), self.local_string(30360), self.nhl_logo)

            old_game_stats.clear()
            old_game_stats = copy.deepcopy(self.new_game_stats)
            first_time_thru = 0
            # If kodi exits or goes idle stop running the script
            if self.monitor.waitForAbort(self.wait):
                xbmc.log("**************Abort Called**********************")
                break

    def notify(self, title, msg, img=None):
        if img is None: img = self.nhl_logo
        self.dialog.notification(title, msg, img, self.display_milliseconds, False)


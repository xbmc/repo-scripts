#
#     Copyright (C) 2011 Team WTM4XBMC
#     http://github.com/wtm4xbmc
#
# This Program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This Program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this script; see the file LICENSE.txt.  If not, write to
# the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# http://www.gnu.org/copyleft/gpl.html
#
#

import sys
import os
import datetime
import traceback
import xbmcgui
import xbmc
import whatthemovie


class GUI(xbmcgui.WindowXMLDialog):
    # CONTROL_IDs
    CID_BUTTON_GUESS = 3000
    CID_BUTTON_RANDOM = 3001
    CID_BUTTON_BACK = 3002
    CID_BUTTON_FIRST = 3004
    CID_BUTTON_PREV = 3005
    CID_BUTTON_NEXT = 3006
    CID_BUTTON_LAST = 3007
    CID_BUTTON_FAV = 3008
    CID_BUTTON_BOOKMARK = 3009
    CID_BUTTON_SOLUTION = 3010
    CID_BUTTON_JUMP = 3011
    CID_IMAGE_GIF = 1002
    CID_IMAGE_SOLUTION = 1006
    CID_IMAGE_MAIN = 1000
    CID_LABEL_LOGINSTATE = 1001
    CID_LABEL_SCORE = 1003
    CID_LABEL_POSTED_BY = 1004
    CID_LABEL_RATINGS = 1019
    CID_LABEL_SOLVED = 1005
    CID_LABEL_MESSAGE = 1007
    CID_LABEL_SHOT_ID = 1008
    CID_LABEL_SHOT_DATE = 1011
    CID_LABEL_SHOT_TYPE = 1012
    CID_LABEL_VOTES = 1014
    CID_LIST_FLAGS = 1013
    CID_PROGR_AVG_RATING = 1015
    CID_LIST_STARS = 1017
    CID_PROGR_OWN_RATING = 1018
    CID_GROUP_RATING = 1016

    # STRING_IDs
    #  Messages
    SID_LOGIN_FAILED_HEADING = 3050
    SID_LOGIN_FAILED = 3051
    SID_ENTER_ID = 3052
    SID_KEYBOARD_HEADING = 3053
    SID_ERROR_LOGIN = 3054
    SID_ERROR_SHOT = 3055
    SID_ERROR_GUESS = 3056
    #  Labels
    SID_CHECKING = 3100
    SID_ANSWER_RIGHT = 3101
    SID_ANSWER_WRONG = 3102
    SID_NOT_LOGGED_IN = 3103
    SID_LOGGED_IN_AS = 3104
    SID_YOUR_SCORE = 3105
    SID_SOLVED = 3106
    SID_UNSOLVED = 3107
    SID_SHOT_ID = 3108
    SID_SHOT_DATE = 3109
    SID_POSTED_BY = 3110
    SID_NOT_RELEASED = 3111
    SID_DEL_USER = 3112
    SID_NEW_SUBM = 3113
    SID_FEATURE_FILMS = 3114
    SID_THE_ARCHIVE = 3115
    SID_OVERALL_VOTES = 3116
    SID_RATINGS = 3117
    SID_RATING_HIDDEN = 3118
    SID_RATING_UNRATED = 3119
    SID_REJECTED_SHOT = 3120
    SID_ALREADY_SOLVED = 3121
    SID_SOLVED_SOLUTION = 3122
    SID_SELF_POSTED = 3123
    SID_NOT_ALLOWED = 3124
    SID_THE_VAULT = 3125
    SID_ANSWER_RIGHT_POINT = 3126
    SID_DELETED = 3127
    SID_NO_SUCH_SHOT = 3128

    # ACTION_IDs
    AID_EXIT_BACK = [9, 10, 13]
    AID_NUMBERS = [59, 60, 61, 62, 63,
                   64, 65, 66, 67, 58]

    # The order of this actions is the same like in the settings!
    ACTION_IDS = ({'AID_PAGE_UP': 5},
                  {'AID_PAGE_DOWN': 6},
                  {'AID_SHOW_INFO': 11},
                  {'AID_PAUSE': 12},
                  {'AID_STOP': 13},
                  {'AID_NEXT_ITEM': 14},
                  {'AID_PREV_ITEM': 15},
                  {'AID_PLAYER_FORWARD': 77},
                  {'AID_PLAYER_REWIND': 78},
                  {'AID_PLAYER_PLAY': 79},
                  {'AID_CONTEXT_MENU': 117},
                  {'AID_VOLUME_UP': 88},
                  {'AID_VOLUME_DOWN': 89},
                  {'AID_SCROLL_UP': 111},
                  {'AID_SCROLL_DOWN': 112},
                  {'AID_HOME': 159},
                  {'AID_END': 160})

    # ADDON_CONSTANTS
    ADDON_ID = sys.modules['__main__'].__id__
    ADDON_VERSION = sys.modules['__main__'].__version__
    ADDON_NAME = sys.modules['__main__'].__addonname__

    def __init__(self, xmlFilename, scriptPath, defaultSkin, defaultRes):
        self.window_home = xbmcgui.Window(10000)
        self.setWTMProperty('solved_status', 'inactive')
        self.setWTMProperty('busy', 'loading')

    def onInit(self):
        # get XBMC Addon instance and methods
        self.Addon = sys.modules['__main__'].Addon
        self.getString = self.Addon.getLocalizedString
        self.getSetting = self.Addon.getSetting
        self.setSetting = self.Addon.setSetting

        # get controls
        self.button_guess = self.getControl(self.CID_BUTTON_GUESS)
        self.button_random = self.getControl(self.CID_BUTTON_RANDOM)
        self.button_back = self.getControl(self.CID_BUTTON_BACK)
        self.label_loginstate = self.getControl(self.CID_LABEL_LOGINSTATE)
        self.label_score = self.getControl(self.CID_LABEL_SCORE)
        self.label_posted_by = self.getControl(self.CID_LABEL_POSTED_BY)
        self.label_solved = self.getControl(self.CID_LABEL_SOLVED)
        self.label_message = self.getControl(self.CID_LABEL_MESSAGE)
        self.label_shot_id = self.getControl(self.CID_LABEL_SHOT_ID)
        self.label_shot_date = self.getControl(self.CID_LABEL_SHOT_DATE)
        self.label_shot_type = self.getControl(self.CID_LABEL_SHOT_TYPE)
        self.label_ratings = self.getControl(self.CID_LABEL_RATINGS)
        self.label_votes = self.getControl(self.CID_LABEL_VOTES)
        self.image_main = self.getControl(self.CID_IMAGE_MAIN)
        self.image_gif = self.getControl(self.CID_IMAGE_GIF)
        self.image_solution = self.getControl(self.CID_IMAGE_SOLUTION)
        self.list_flags = self.getControl(self.CID_LIST_FLAGS)
        self.list_stars = self.getControl(self.CID_LIST_STARS)
        self.group_rating = self.getControl(self.CID_GROUP_RATING)
        self.progr_avg_rating = self.getControl(self.CID_PROGR_AVG_RATING)
        self.progr_own_rating = self.getControl(self.CID_PROGR_OWN_RATING)

        # set control visibility depending on xbmc-addon settings
        self.hideLabels()

        # set user defined hotkeys
        self.setKeySetting()

        # fill stars list with the stars.
        for i in range(0, 10):
            star_item = xbmcgui.ListItem()
            self.list_stars.addItem(star_item)

        # start the api
        user_agent = 'XBMC-ADDON - %s - V%s' % (self.ADDON_ID,
                                                self.ADDON_VERSION)
        self.Quiz = whatthemovie.WhatTheMovie(user_agent)
        # try to login and get first random shot. If it fails exit
        try:
            self.login()
            self.getShot('random')
        except Exception, error:
            self.errorMessage(self.getString(self.SID_ERROR_LOGIN),
                              str(error))
            self.close()

    def setKeySetting(self):
        keys = ('key_guess', 'key_random', 'key_back', 'key_next',
                'key_prev', 'key_jump', 'key_book', 'key_fav', 'key_solve')
        self.assigned_keys = dict()
        for key in keys:
            assigned_key_i = int(self.getSetting(key))
            if assigned_key_i:  # skip first key 'No Key' with id = 0
                action_id = self.ACTION_IDS[assigned_key_i - 1].values()[0]
                self.assigned_keys[action_id] = key

    def onAction(self, action):
        action_id = action.getId()
        if action_id in self.AID_EXIT_BACK:
            self.closeDialog()
        elif action_id in self.AID_NUMBERS:
            user_rate = self.AID_NUMBERS.index(action_id) + 1
            self.rateShot(self.shot['shot_id'], user_rate)
        elif action_id in self.assigned_keys:
            key = self.assigned_keys[action_id]
            if key == 'key_guess':
                self.guessTitle(self.shot['shot_id'])
            elif key == 'key_random':
                self.getShot('random')
            elif key == 'key_back':
                self.getShot('back')
            elif key == 'key_jump':
                self.askShotID()
            elif key == 'key_book':
                self.bookmarkShot(self.shot['shot_id'])
            elif key == 'key_fav':
                self.favouriteShot(self.shot['shot_id'])
            elif key == 'key_solve':
                self.solveShot(self.shot['shot_id'])
            elif key in ('key_next', 'key_prev'):
                if self.getSetting('only_unsolved_nav') == 'true':
                    unsolved_toggle = '_unsolved'
                else:
                    unsolved_toggle = ''
                if key == 'key_next':
                    self.getShot('next' + unsolved_toggle)
                elif key == 'key_prev':
                    self.getShot('prev' + unsolved_toggle)

    def askShotID(self):
        Dialog = xbmcgui.Dialog()
        shot_id = Dialog.numeric(0, self.getString(self.SID_ENTER_ID))
        if shot_id:
            self.getShot(shot_id)

    def onFocus(self, controlId):
        pass

    def onClick(self, controlId):
        if controlId == self.CID_BUTTON_GUESS:
            self.guessTitle(self.shot['shot_id'])
        elif controlId == self.CID_BUTTON_RANDOM:
            self.getShot('random')
        elif controlId == self.CID_BUTTON_BACK:
            self.getShot('back')
        elif controlId == self.CID_BUTTON_FIRST:
            self.getShot('first')
        elif controlId == self.CID_BUTTON_LAST:
            self.getShot('last')
        elif controlId == self.CID_BUTTON_FAV:
            self.favouriteShot(self.shot['shot_id'])
        elif controlId == self.CID_BUTTON_BOOKMARK:
            self.bookmarkShot(self.shot['shot_id'])
        elif controlId == self.CID_BUTTON_SOLUTION:
            self.solveShot(self.shot['shot_id'])
        elif controlId == self.CID_BUTTON_JUMP:
            self.askShotID()
        elif controlId in (self.CID_BUTTON_PREV, self.CID_BUTTON_NEXT):
            if self.getSetting('only_unsolved_nav') == 'true':
                unsolved_toggle = '_unsolved'
            else:
                unsolved_toggle = ''
            if controlId == self.CID_BUTTON_PREV:
                self.getShot('prev' + unsolved_toggle)
            elif controlId == self.CID_BUTTON_NEXT:
                self.getShot('next' + unsolved_toggle)
        elif controlId == self.CID_LIST_STARS:
            user_rate = self.list_stars.getSelectedPosition() + 1
            self.rateShot(self.shot['shot_id'], user_rate)

    def closeDialog(self):
        self.setWTMProperty('main_image', '')
        self.close()

    def getShot(self, shot_request):
        self.log('Try to get a shot via: %s' % shot_request)
        # set busy_gif
        self.setWTMProperty('busy', 'loading')
        # hide label_status
        self.setWTMProperty('solved_status', 'inactive')
        # scrape shot and download picture
        try:
            self.shot = self.Quiz.getShot(shot_request)
            shot = self.shot
            image_path = self.downloadPic(shot['image_url'],
                                          shot['shot_id'])
            self.log('Got a shot: %s' % self.shot)
        except Exception, error:
            self.errorMessage(self.getString(self.SID_ERROR_SHOT),
                              str(error))
            self.setWTMProperty('busy', '')
            return
        self._showShotImage(image_path)
        self._showShotType(shot['shot_type'])
        self._showShotPostedBy(shot['posted_by'])
        self._showShotSolvedStatus(shot['solved'])
        self._showShotAlreadySolved(shot['already_solved'])
        self._showShotSelfPosted(shot['self_posted'])
        self._showShotID(shot['shot_id'])
        self._showShotDate(shot['date'])
        self._showShotFlags(shot['lang_list']['all'])
        self._showShotRating(shot['voting'])
        self._showShotButtonState('favourite', shot['favourite'])
        self._showShotButtonState('bookmarked', shot['bookmarked'])
        self._showShotSolvableState(shot['solvable'])
        self._showShotOfTheDay(shot['sotd'])
        self._showShotRedirected(shot['redirected'])
        # unset busy_gif
        self.setWTMProperty('busy', '')

    def _showShotType(self, shot_type):
        if shot_type == 0:
            type_string = 'UNKNOWN - Report to WTM4XBMC'
        elif shot_type == 1:
            type_string = self.getString(self.SID_NEW_SUBM)
        elif shot_type == 2:
            type_string = self.getString(self.SID_FEATURE_FILMS)
        elif shot_type == 3:
            type_string = self.getString(self.SID_THE_ARCHIVE)
        elif shot_type == 4:
            type_string = self.getString(self.SID_REJECTED_SHOT)
        elif shot_type == 5:
            type_string = self.getString(self.SID_THE_VAULT)
        elif shot_type == 6:
            type_string = self.getString(self.SID_DELETED)
        self.label_shot_type.setLabel(type_string)

    def _showShotPostedBy(self, posted_by=None):
        if posted_by is None:
            posted_by = self.getString(self.SID_DEL_USER)
        self.label_posted_by.setLabel(self.getString(self.SID_POSTED_BY)
                                      % posted_by)

    def _showShotSolvedStatus(self, solved_status):
        if solved_status['status']:
            self.label_solved.setLabel(self.getString(self.SID_SOLVED)
                                       % (solved_status['count'],
                                          solved_status['first_by']))
        else:
            self.label_solved.setLabel(self.getString(self.SID_UNSOLVED))

    def _showShotAlreadySolved(self, already_solved):
        if already_solved:
            self.image_solution.setColorDiffuse('FFFFFFFF')
            label = self.getString(self.SID_ALREADY_SOLVED)
            self.label_message.setLabel(label)
            self.setWTMProperty('solved_status', 'solved')

    def _showShotRedirected(self, redirected):
        if redirected:
            if redirected == 1:
                message = 'Redirected from %s to %s. REPORT TO WTM4XBMC'
            elif redirected == 2:
                message = self.getString(self.SID_NOT_ALLOWED)
            elif redirected == 3:
                message = self.getString(self.SID_NO_SUCH_SHOT)
            self.image_solution.setColorDiffuse('FFFFFFFF')
            label = message % (self.shot['requested_as'],
                               self.shot['shot_id'])
            self.label_message.setLabel(label)
            self.setWTMProperty('solved_status', 'solved')

    def _showShotSelfPosted(self, self_posted):
        if self_posted:
            self.image_solution.setColorDiffuse('FFFFFFFF')
            label = self.getString(self.SID_SELF_POSTED)
            self.label_message.setLabel(label)
            self.setWTMProperty('solved_status', 'solved')

    def _showShotSolution(self, solution):
        self.image_solution.setColorDiffuse('FFFFFFFF')
        label = self.getString(self.SID_SOLVED_SOLUTION) % solution
        self.label_message.setLabel(label)
        self.setWTMProperty('solved_status', 'solved')

    def _showShotID(self, shot_id):
        self.label_shot_id.setLabel(self.getString(self.SID_SHOT_ID)
                                    % shot_id)

    def _showShotDate(self, date_tupel):
        if date_tupel:
            y, m, d = date_tupel
            date = datetime.date(y, m, d)
            date_format = xbmc.getRegion('dateshort')
            date_string = date.strftime(date_format)
        else:
            date_string = self.getString(self.SID_NOT_RELEASED)
        self.label_shot_date.setLabel(self.getString(self.SID_SHOT_DATE)
                                      % date_string)

    def _showShotRating(self, rating):
        if rating['overall_rating'] != u'hidden':
            overall_rating = float(rating['overall_rating'])
            overall_rating_percent = overall_rating * 10
            interval_percent = self._calcRatingPercent(overall_rating)
        else:
            overall_rating = self.getString(self.SID_RATING_HIDDEN)
            interval_percent = 0
        self.progr_avg_rating.setPercent(interval_percent)
        if rating['own_rating']:
            own_rating = int(float(rating['own_rating']))
            own_rating_percent = own_rating * 10
            self.progr_own_rating.setPercent(own_rating_percent)
        else:
            own_rating = self.getString(self.SID_RATING_UNRATED)
            own_rating_percent = 0
        self.progr_own_rating.setPercent(own_rating_percent)
        votes = rating['votes']
        self.label_votes.setLabel(self.getString(self.SID_OVERALL_VOTES)
                                  % votes)
        self.label_ratings.setLabel(self.getString(self.SID_RATINGS)
                                    % (overall_rating, own_rating))

    def _calcRatingPercent(self, rating_float):
        # a star is 1 star_width width
        # a gap is 1/2 star_widths width
        # a border is 1/4 star_widths width
        # 100% = 10s + 9g + 2b
        # 100% = 10s + 9s/2 + 2s/4
        # 100% = 40s/4 + 18s/4 + 2s/4 = 60s/4 = 15s
        star_width = 100.0 / 15.0
        full_stars = float(int(rating_float))
        part_star = rating_float - full_stars
        gap_width = star_width / 2.0
        border_width = star_width / 4.0
        p_full_stars = star_width * full_stars
        p_full_gaps = gap_width * full_stars
        p_part_star = star_width * part_star
        percent = border_width + p_full_stars + p_full_gaps + p_part_star
        return percent  # .setPercent() can handle float()

    def _showShotFlags(self, available_languages):
        visible_flags = list()
        for i in range(1, 6):
            visible_flags.append(self.getSetting('flag%s' % i))
        self.list_flags.reset()
        for flag in visible_flags:
            flag_img = 'flags/%s.png' % flag
            flag_item = xbmcgui.ListItem(iconImage=flag_img)
            if flag not in available_languages:
                flag_item.setProperty('unavailable', 'True')
            self.list_flags.addItem(flag_item)

    def _showShotImage(self, image_path):
        self.setWTMProperty('main_image', image_path)

    def _showShotButtonState(self, prop, state):
        if prop == 'favourite':
            element = self.getControl(self.CID_BUTTON_FAV)
        elif prop == 'bookmarked':
            element = self.getControl(self.CID_BUTTON_BOOKMARK)
        if state is None:
            element.setEnabled(False)
            element.setSelected(False)
        elif state == False:
            element.setEnabled(True)
            element.setSelected(False)
        elif state == True:
            element.setEnabled(True)
            element.setSelected(True)

    def _showShotSolvableState(self, state):
        element = self.getControl(self.CID_BUTTON_SOLUTION)
        if state:
            element.setEnabled(True)
            element.setSelected(True)
        else:
            element.setEnabled(False)
            element.setSelected(False)

    def _showShotOfTheDay(self, state):
        if state:
            self.setWTMProperty('sotd', 'True')
        else:
            self.setWTMProperty('sotd', '')

    def _showUserScore(self, score):
        score_string = self.getString(self.SID_YOUR_SCORE) % str(score)
        self.label_score.setLabel(score_string)

    def rateShot(self, shot_id, own_rating):
        if self.logged_in:
            self.log('Try to rate the shot with: %s' % own_rating)
            self.setWTMProperty('busy', 'loading')
            try:
                self.Quiz.rateShot(shot_id, own_rating)
                rating = self.shot['voting']
                self._showShotRating(rating)
            except Exception, error:
                self.errorMessage(self.getString(self.SID_ERROR_SHOT),
                                  str(error))
            self.setWTMProperty('busy', '')

    def favouriteShot(self, shot_id):
        if self.logged_in:
            state = self.shot['favourite']
            newstate = not state
            self.log('Try to set the shots fav status to: %s' % newstate)
            self.setWTMProperty('busy', 'loading')
            try:
                self.Quiz.favouriteShot(shot_id, newstate)
                self._showShotButtonState('favourite', newstate)
            except Exception, error:
                self.errorMessage(self.getString(self.SID_ERROR_SHOT),
                                  str(error))
            self.setWTMProperty('busy', '')

    def bookmarkShot(self, shot_id):
        if self.logged_in:
            state = self.shot['bookmarked']
            newstate = not state
            self.log('Try to set the shots bookmark status to: %s' % newstate)
            self.setWTMProperty('busy', 'loading')
            try:
                self.Quiz.bookmarkShot(shot_id, newstate)
                self._showShotButtonState('bookmarked', newstate)
            except Exception, error:
                self.errorMessage(self.getString(self.SID_ERROR_SHOT),
                                  str(error))
            self.setWTMProperty('busy', '')

    def solveShot(self, shot_id):
        self.log('Try to solve the shot')
        if self.shot['shot_id'] == shot_id and self.shot['solvable']:
            self.setWTMProperty('busy', 'loading')
            try:
                solved_title = self.Quiz.solveShot(shot_id)
                self._showShotSolution(solved_title)
            except Exception, error:
                self.errorMessage(self.getString(self.SID_ERROR_SHOT),
                                  str(error))
            self.setWTMProperty('busy', '')

    def guessTitle(self, shot_id):
        # open xbmc keyboard
        heading = self.getString(self.SID_KEYBOARD_HEADING)
        keyboard = xbmc.Keyboard('', heading)
        keyboard.doModal()
        if keyboard.isConfirmed() and keyboard.getText():
            # clear solved_status
            self.setWTMProperty('solved_status', 'inactive')
            guess = keyboard.getText().decode('utf8')
            gives_point = (self.shot['gives_point'])  # call by value forced
            self.log('Try to check the title: %s' % guess)
            # enter checking status
            self.image_solution.setColorDiffuse('FFFFFF00')
            self.setWTMProperty('solved_status', 'checking')
            message = self.getString(self.SID_CHECKING)
            self.label_message.setLabel(message % guess)
            # try to check the guess. If it fails abort checking
            try:
                solution = self.Quiz.guessShot(shot_id, guess)
            except Exception, error:
                self.errorMessage(self.getString(self.SID_ERROR_GUESS),
                                  str(error))
                self.setWTMProperty('solved_status', 'inactive')
                return
            # call answerRight or answerWrong
            if solution['is_right']:
                self.answerRight(solution['title_year'],
                                 gives_point)
            else:
                self.answerWrong(guess)

    def answerRight(self, title_year, gives_point):
        self.log('Answer was correct: %s' % title_year)
        # enter right status
        self.setWTMProperty('solved_status', 'correct')
        self.image_solution.setColorDiffuse('FF00FF00')
        # if this shot gives points, do so
        if gives_point:
            self.score += 1
            self._showUserScore(self.score)
            message = self.getString(self.SID_ANSWER_RIGHT_POINT) % title_year
        else:
            message = self.getString(self.SID_ANSWER_RIGHT) % title_year
        self.label_message.setLabel(message)
        # if user wants auto_jump, do so
        if self.getSetting('auto_jump_enabled') == 'true':
            time_to_sleep = int(self.getSetting('auto_jump_sleep')) * 1000
            xbmc.sleep(time_to_sleep)
            if self.getSetting('auto_jump_to') == '0':
                jump_to = 'random'
            elif self.getSetting('auto_jump_to') == '1':
                if self.getSetting('only_unsolved_nav') == 'true':
                    jump_to = 'next_unsolved'
                else:
                    jump_to = 'next'
            self.getShot(jump_to)

    def answerWrong(self, guess):
        self.log('Answer was wrong: %s' % guess)
        # enter wrong status
        message = self.getString(self.SID_ANSWER_WRONG)
        self.label_message.setLabel(message % guess)
        self.setWTMProperty('solved_status', 'wrong')
        self.image_solution.setColorDiffuse('FFFF0000')

    def login(self):
        self.score = 0
        self.logged_in = False
        label = self.getString(self.SID_NOT_LOGGED_IN)
        # if login is enabeld start loop until
        # self.logged_in is true or user disables login
        if self.getSetting('login') == 'true':
            cookie_dir = self.Addon.getAddonInfo('profile')
            self.checkCreatePath(cookie_dir)
            cookie_file = xbmc.translatePath('%s/cookie.txt' % cookie_dir)
            # try to login until self.logged_in becomes True
            while not self.logged_in:
                if self.getSetting('login') == 'false':
                    # user gives up to login and disabled
                    # login in settings opened by loop
                    break
                user = self.getSetting('username')
                password = self.getSetting('password')
                # try to login
                self.log('Try to login as: %s' % user)
                self.logged_in = self.Quiz.login(user, password, cookie_file)
                if not self.logged_in:
                    # login failed
                    dialog = xbmcgui.Dialog()
                    dialog.ok(self.getString(self.SID_LOGIN_FAILED_HEADING),
                              self.getString(self.SID_LOGIN_FAILED) % user)
                    self.Addon.openSettings()
                else:
                    self.log('Login successfull via: %s' % self.logged_in)
                    # login successfully
                    label = self.getString(self.SID_LOGGED_IN_AS) % user
                    self.score = int(self.Quiz.getScore(user)['ff_score'])
                    self.setRandomOptions()
        self.label_loginstate.setLabel(label)
        self._showUserScore(self.score)

    def setRandomOptions(self):
        options_list = list()
        for option in ('difficulty', 'include_archive',
                       'include_solved', 'username'):
            options_list.append(self.getSetting(option))
        current_options = '-'.join(options_list)
        if self.getSetting('already_sent_options') != current_options:
            options = dict()
            if self.getSetting('difficulty') == '2':
                options['difficulty'] = 'all'
            elif self.getSetting('difficulty') == '1':
                options['difficulty'] = 'medium'
            elif self.getSetting('difficulty') == '0':
                options['difficulty'] = 'easy'
            if self.getSetting('include_archive') == 'true':
                options['include_archive'] = '1'
            if self.getSetting('include_solved') == 'true':
                options['include_solved'] = '1'
            self.log('Random options differ, new is: %s' % options)
            self.Quiz.setRandomOptions(options)
            self.setSetting('already_sent_options', current_options)

    def downloadPic(self, image_url, shot_id):
        subst_image_url = 'http://static.whatthemovie.com/images/substitute'
        if not image_url.startswith(subst_image_url):
            cache_dir = ('special://profile/addon_data/%s/cache'
                         % self.ADDON_ID)
            self.checkCreatePath(cache_dir)
            image_path = xbmc.translatePath('%s/%s.jpg' % (cache_dir, shot_id))
            if not os.path.isfile(image_path):
                self.Quiz.downloadFile(image_url, image_path)
        else:
            image_path = image_url
        return image_path

    def checkCreatePath(self, path):
        result = False
        if os.path.isdir(xbmc.translatePath(path)):
            result = True
        else:
            result = os.makedirs(xbmc.translatePath(path))
        return result

    def setWTMProperty(self, prop, value):
        self.window_home.setProperty('wtm.%s' % prop, value)

    def hideLabels(self):
        if self.getSetting('visible_posted_by') == 'false':
            self.label_posted_by.setVisible(False)
        if self.getSetting('visible_solved') == 'false':
            self.label_solved.setVisible(False)
        if self.getSetting('visible_shot_id') == 'false':
            self.label_shot_id.setVisible(False)
        if self.getSetting('visible_shot_date') == 'false':
            self.label_shot_date.setVisible(False)
        if self.getSetting('visible_shot_flags') == 'false':
            self.list_flags.setVisible(False)
        if self.getSetting('visible_shot_rating') == 'false':
            self.label_ratings.setVisible(False)
            self.group_rating.setVisible(False)
            self.label_votes.setVisible(False)
        if self.getSetting('visible_tool_buttons') == 'false':
            controls = (self.CID_BUTTON_FAV, self.CID_BUTTON_BOOKMARK,
                        self.CID_BUTTON_SOLUTION, self.CID_BUTTON_JUMP)
            for control in controls:
                self.getControl(control).setVisible(False)
        if self.getSetting('visible_navigation_buttons') == 'false':
            controls = (self.CID_BUTTON_FIRST, self.CID_BUTTON_PREV,
                        self.CID_BUTTON_NEXT, self.CID_BUTTON_LAST)
            for control in controls:
                self.getControl(control).setVisible(False)

    def errorMessage(self, heading, error):
        self.log('Error: %s - %s' % (heading, str(error)))
        exc_type, exc_value, exc_traceback = sys.exc_info()
        trace = repr(traceback.format_exception(exc_type, exc_value,
                                                exc_traceback))
        self.log('Traceback: %s' % trace)
        dialog = xbmcgui.Dialog()
        dialog.ok(heading, str(error))

    def log(self, msg):
        xbmc.log('[ADDON][%s] %s' % (self.ADDON_NAME, msg.encode('utf-8')),
                 level=xbmc.LOGNOTICE)

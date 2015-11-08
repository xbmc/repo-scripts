# -*- coding: utf-8 -*-
import cgi
import traceback
from datetime import datetime

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from Queue import Empty

# Load the Soco classes
from soco.snapshot import Snapshot
from soco.events import event_listener

from settings import log
from settings import os_path_join

__addon__ = xbmcaddon.Addon(id='script.sonos')


#########################################################################
# Sonos Speech class to get a device to talk
#########################################################################
class Speech():

    def __init__(self, device=None):
        # The device that the speech will be sent to
        self.device = device

        # Map of languages, from Kodi to Google (Kodi, Google)
        # References:
        # https://developers.google.com/translate/v2/using_rest#language-params
        # http://wiki.xbmc.org/index.php?title=List_of_language_codes_%28ISO-639:1988%29
        self.languages = {'af': 'af',  # Afrikaans
                          'sq': 'sq',  # Albanian
                          'ar': 'ar',  # Arabic
                          'az': 'az',  # Azerbaijani
                          'eu': 'eu',  # Basque
                          'bn': 'bn',  # Bengali
                          'be': 'be',  # Belarusian / Byelorussian
                          'bg': 'bg',  # Bulgarian
                          'ca': 'ca',  # Catalan
                          'zh': 'zh-CN',  # Chinese
                          'hr': 'hr',  # Croatian
                          'cs': 'cs',  # Czech
                          'da': 'da',  # Danish
                          'nl': 'nl',  # Dutch
                          'en': 'en',  # English
                          'eo': 'eo',  # Esperanto
                          'et': 'et',  # Estonian
                          'tl': 'tl',  # Filipino / Tagalog
                          'fi': 'fi',  # Finnish
                          'fr': 'fr',  # French
                          'gl': 'gl',  # Galician
                          'ka': 'ka',  # Georgian
                          'de': 'de',  # German
                          'el': 'el',  # Greek
                          'gu': 'gu',  # Gujarati
                          'iw': 'iw',  # Hebrew
                          'hi': 'hi',  # Hungarian
                          'is': 'is',  # Icelandic
                          'in': 'id',  # Indonesian
                          'ga': 'ga',  # Irish
                          'it': 'it',  # Italian
                          'ja': 'ja',  # Japanese
                          'kn': 'kn',  # Kannada
                          'ko': 'ko',  # Korean
                          'la': 'la',  # Latin
                          'lv': 'lv',  # Latvian
                          'lt': 'lt',  # Lithuanian
                          'mk': 'mk',  # Macedonian
                          'ms': 'ms',  # Malay
                          'mt': 'mt',  # Maltese
                          'no': 'no',  # Norwegian
                          'fa': 'fa',  # Persian
                          'pl': 'pl',  # Polish
                          'pt': 'pt',  # Portuguese
                          'ro': 'ro',  # Romanian
                          'ru': 'ru',  # Russian
                          'sr': 'sr',  # Serbian
                          'sk': 'sk',  # Slovak
                          'sl': 'sl',  # Slovenian
                          'ed': 'es',  # Spanish
                          'sw': 'sw',  # Swahili
                          'sv': 'sv',  # Swedish
                          'ta': 'ta',  # Tamil
                          'te': 'te',  # Telugu
                          'th': 'th',  # Thai
                          'tr': 'tr',  # Turkish
                          'uk': 'uk',  # Ukrainian
                          'ur': 'ur',  # Urdu
                          'vi': 'vi',  # Vietnamese
                          'cy': 'cy',  # Welsh
                          'ji': 'yi'}  # Yiddish

    # Says the given phrase over the sonos device
    def say(self, message):
        log("Speech: Message to say is: %s" % message)
        # Start by checking to see if the message is valid
        if not self.checkIfValidMessage(message):
            return

        xbmc.executebuiltin("ActivateWindow(busydialog)")
        try:
            # Need to subscribe to transport events, this is so that we know
            # when a given track has finished, and so we can stop it, if
            # we do not stop it, then it will repeat the text for a second time
            sub = self.device.avTransport.subscribe()

            # Take a snapshot of the current sonos device state, we will want
            # to roll back to this when we are done
            log("Speech: Taking snapshot")
            snap = Snapshot(self.device)
            snap.snapshot()

            # Get the URI and play it
            trans_URI = self._get_uri(message)
            log("Speech: Playing URI %s" % trans_URI)
            self.device.play_uri(trans_URI, title=__addon__.getLocalizedString(32105))

            # The maximum number of seconds that we will wait for the message to
            # complete playing
            duration = 200
            while duration > 0:
                # Check to see if the system is shutting down
                if xbmc.abortRequested:
                    break
                try:
                    eventItem = sub.events.get(timeout=0.1)

                    # Now get the details of an event if there is one there
                    if eventItem is not None:
                        # Check to see if there is a message saying that it is waiting
                        # to restart the audio stream.  This happens because it is
                        # being treated like a radio stream, so Sonos things when the
                        # end of the mp3 file playing is reached that there has been
                        # a connection error and needs to reconnect. If left to itself
                        # it would play the mp3 file again
                        if hasattr(eventItem, 'restart_pending') and (eventItem.restart_pending is not None):
                            # About to try and restart, so stop looping and stop the
                            # track before it starts again
                            if eventItem.restart_pending == '1':
                                log("Speech: Detected restart attempt")
                                break
                except Empty:
                    pass
                # Wait another 10th of a second for the speech to stop playing
                duration = duration - 1
                xbmc.sleep(100)

            log("Speech: Stopping speech")
            # Stop the stream playing
            self.device.stop()

            log("Speech: Restoring snapshot")
            try:
                # We no longer want to  receive messages
                sub.unsubscribe()
            except:
                log("Sonos: Failed to unsubscribe: %s" % traceback.format_exc(), xbmc.LOGERROR)
            try:
                # Make sure the thread is stopped even if unsubscribe failed
                event_listener.stop()
            except:
                log("Sonos: Failed to stop event listener: %s" % traceback.format_exc(), xbmc.LOGERROR)
            del sub
            # Restore the sonos device back to it's previous state
            snap.restore()
            del snap
        except:
            log("Speech: %s" % traceback.format_exc(), xbmc.LOGERROR)
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            raise

        xbmc.executebuiltin("Dialog.Close(busydialog)")

    # Method to work out if the message requested is valid
    def checkIfValidMessage(self, message):
        # First replace the special phrases
        msg = self._replace_keys(message)
        msg = cgi.escape(msg)
        msg_len = len(msg)

        valid = False
        header = "%s - %s" % (__addon__.getLocalizedString(32001), __addon__.getLocalizedString(32105))
        if msg_len > 100:
            xbmcgui.Dialog().ok(header, __addon__.getLocalizedString(32201))
        elif msg_len < 1:
            xbmcgui.Dialog().ok(header, __addon__.getLocalizedString(32202))
        else:
            valid = True

        return valid

    # Generates the URI to use for the speech
    def _get_uri(self, message):
        # get the xbmc language
        xbmclang = xbmc.getLanguage(xbmc.ISO_639_1)
        log("Speech: Kodi Language is: %s" % xbmclang)
        # Get the language in the google format
        glang = self.languages.get(xbmclang, 'en')
        # Replace any characters which are place holders
        msg = self._replace_keys(message.strip())
        # Escape any characters that would cause issues in the URI
        msg = cgi.escape(msg)

        # Need to work out if we are using Google or Speech Util
        # TODO: add switch, use argument
#        trans_URL = "x-rincon-mp3radio://speechutil.com/convert/ogg?text='%s'&file=1" % msg
#        trans_URL = "x-rincon-mp3radio://speechutil.appspot.com/convert/ogg?text=%s" % msg
#        trans_URL = "x-rincon-mp3radio://speechutil.com/convert/wav?text='%s'&file=1" % msg

        trans_URI = "x-rincon-mp3radio://translate.google.com/translate_tts?tl=%s&q=%s&client=t" % (glang, msg)

        log("Speech: URI to play = %s" % trans_URI)
        return trans_URI

    # Parses input text to add special feature key words:
    # returns string of original text with keys replaced with current info.
    def _replace_keys(self, words):
        now = datetime.now()

        if '%day' in words:
            words = words.replace('%day', now.strftime('%A'))

        if '%time' in words:
            words = words.replace('%time', now.strftime('%H:%M'))

        if '%date' in words:
            d = int(now.strftime('%d'))
            suffix = 'th' if 11 <= d <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th')
            mth = now.strftime('%B')
            words = words.replace('%date', str(d) + suffix + ' ' + mth)

        if '%greet' in words:
            GREET = [__addon__.getLocalizedString(32223),
                     __addon__.getLocalizedString(32223),
                     __addon__.getLocalizedString(32224),
                     __addon__.getLocalizedString(32225)]
            hour = int(now.strftime('%H'))
            words = words.replace('%greet', GREET[hour / 6])

        return words

    # Show the keyboad so a user can type what speech string they want
    def promptForInput(self):
        header = "%s - %s" % (__addon__.getLocalizedString(32001), __addon__.getLocalizedString(32105))
        keyboard = xbmc.Keyboard(heading=header)
        keyboard.setHeading(header)
        keyboard.doModal()

        phrase = None
        if keyboard.isConfirmed():
            try:
                phrase = keyboard.getText().decode("utf-8")
            except:
                phrase = keyboard.getText()
            log("Speech: User input the text: %s" % phrase)

        return phrase

    # Loads all the saved phrases
    def loadSavedPhrases(self):
        # Get the location of the speech list file
        configPath = xbmc.translatePath(__addon__.getAddonInfo('profile'))
        speechfile = os_path_join(configPath, "speech.txt")
        log("Speech: Phrases file location = %s" % speechfile)

        phrases = []
        # Check to see if the speech list file exists
        if not xbmcvfs.exists(speechfile):
            # Create a list of pre-defined phrases
            phrases.append(__addon__.getLocalizedString(32221))
            phrases.append(__addon__.getLocalizedString(32222))
            phrases.append(__addon__.getLocalizedString(32226))
            phrases.append('%greet')
            phrases.sort()
        else:
            # Read the phases from the file
            try:
                file_in = open(speechfile, 'r')
                phrases = file_in.readlines()
                file_in.close()
            except:
                log("Speech: Failed to read lines from file %s" % speechfile, xbmc.LOGERROR)
                log("Speech: %s" % traceback.format_exc(), xbmc.LOGERROR)

        return phrases

    # Writes the list of phrases to a file
    def savePhrases(self, phrases):
        # Get the location of the speech list file
        configPath = xbmc.translatePath(__addon__.getAddonInfo('profile'))
        speechfile = os_path_join(configPath, "speech.txt")
        log("Speech: Phrases file location = %s" % speechfile)

        try:
            file_out = open(speechfile, 'w')
            # need to make sure there is a return at the end of each line
            file_out.writelines(("%s\n" % l.rstrip() for l in phrases))
            file_out.close()
        except:
            log("Speech: Failed to write lines to file %s" % speechfile, xbmc.LOGERROR)
            log("Speech: %s" % traceback.format_exc(), xbmc.LOGERROR)

    # Prompt the user for a phrase and save it for future use
    def addPhrase(self):
        # Ask the user to input the new phrase
        phrase = self.promptForInput()
        if (phrase is not None) and (len(phrase) > 0):
            # Get the phrases that are already in the file
            phrases = self.loadSavedPhrases()
            phrases.append(phrase)
            # Now sort the phrases alphabetically
            phrases.sort()
            # Now save the phrases to file
            self.savePhrases(phrases)

    # Remove a phrase from the saved list
    def removePhrase(self, phrase):
        log("Speech: Removing the phrase: %s" % phrase)
        # Get all the current phrases
        phrases = self.loadSavedPhrases()
        # Make sure the item is in the list
        if phrase in phrases:
            phrases.remove(phrase)
            # Now save the list back to file
            self.savePhrases(phrases)

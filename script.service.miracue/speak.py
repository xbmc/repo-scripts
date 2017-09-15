import os

import xbmc
import xbmcaddon
import xbmcgui


class Speaker(object):
    def __init__(self):
        self._addon_dir = xbmcaddon.Addon().getAddonInfo('path')

    def _get_file_path(self, filename):
        return xbmc.translatePath('/'.join([self._addon_dir, 'resources', filename]))

    def _play_multiple_files(self, list_of_filenames):
        pl = xbmc.PlayList(1)
        pl.clear()
        for filename in list_of_filenames:
            if 'https://' not in filename:
                path = self._get_file_path(filename)
            else:
                path = filename
            xbmc.PlayList(1).add(path, xbmcgui.ListItem())
        xbmc.Player().play(pl)

    def enable_skill(self):
        self._play_multiple_files([
            'enable_skill.ogg',
        ])

    def pair_with_code(self, code):
        code = '+'.join(code)
        url = 'https://text-to-speech-demo.mybluemix.net/api/synthesize?text=Alexa%2C+ask+Miracle+to+pair+with+code.+THE_CODE&voice=en-US_LisaVoice&ssmlLabel=SSML&download=true'
        url = url.replace('THE_CODE', code)
        # files_list = ['pair_with_code.ogg']
        # for digit in code:
        #     files_list.append('%s.ogg' % digit)
        self._play_multiple_files([url])

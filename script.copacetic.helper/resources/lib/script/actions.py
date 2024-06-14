# author: realcopacetic

from resources.lib.service.art import ImageEditor
from resources.lib.utilities import (ADDON, DIALOG, clear_playlists, condition,
                                     infolabel, json_call, log, log_and_execute,
                                     skin_string, window_property, xbmc, urllib)


def clean_filename(label=False, **kwargs):
    json_response = json_call('Settings.GetSettingValue',
                              params={'setting': 'filelists.showextensions'},
                              parent='clean_filename'
                              )

    subtraction = 1 if json_response['result']['value'] is True else 0
    if not label:
        label = infolabel('$INFO[ListItem.Label]')
    count = label.count('.') - subtraction
    label = label.replace('.', ' ', count).replace('_', ' ').strip()

    window_property('Return_Label', set=label)


def dialog_yesno(heading, message, **kwargs):
    yes_actions = kwargs.get('yes_actions', '').split('|')
    no_actions = kwargs.get('no_actions', 'Null').split('|')

    if DIALOG.yesno(heading, message):
        for action in yes_actions:
            log_and_execute(action)
    else:
        for action in no_actions:
            log_and_execute(action)


def globalsearch_input(**kwargs):
    kb = xbmc.Keyboard(
        infolabel('$INFO[Skin.String(globalsearch)]'), infolabel('$LOCALIZE[137]'))
    kb.doModal()
    if (kb.isConfirmed()):
        text = kb.getText()
        skin_string('globalsearch', set=text)
        xbmc.executebuiltin('ActivateWindow(1180)')


def hex_contrast_check(**kwargs):
    image = ImageEditor()
    hex = kwargs.get('hex', '')

    if hex:
        r = int(hex[2:-4], 16)
        g = int(hex[4:-2], 16)
        b = int(hex[6:], 16)
        rgb = (r, g, b)
        luminosity = image.return_luminosity(rgb)
        best_contrast = 'dark' if luminosity > 0.179 else 'light'

        xbmc.executebuiltin(
            f'Skin.SetString(Accent_Color_Contrast,{best_contrast})')


def play_album(**kwargs):
    clear_playlists()

    dbid = int(kwargs.get('id', False))
    if dbid:
        json_call('Player.Open',
                  item={'albumid': dbid},
                  options={'shuffled': False},
                  parent='play_album'
                  )


def play_album_from_track(**kwargs):
    clear_playlists()

    dbid = int(kwargs.get('id', False))
    track = int(kwargs.get('track', False)) - 1

    if dbid:
        json_response = json_call('AudioLibrary.GetSongDetails',
                                  params={'properties': [
                                      'albumid'], 'songid': dbid},
                                  parent='play_album_from_track'
                                  )

    if json_response['result'].get('songdetails', None):
        albumid = json_response['result']['songdetails']['albumid']

    json_call('Player.Open',
              item={'albumid': albumid},
              options={'shuffled': False},
              parent='play_album_from_track'
              )

    if track > 0:
        json_call('Player.GoTo', params={'playerid': 0, 'to': track})


def play_items(id, **kwargs):
    clear_playlists()

    method = kwargs.get('method', '')
    shuffled = True if method == 'shuffle' else False
    playlistid = 0 if kwargs.get('type', '') == 'music' else 1

    if method == 'from_here':
        method = f'Container({id}).ListItemNoWrap'
    else:
        method = f'Container({id}).ListItemAbsolute'

    for count in range(int(infolabel(f'Container({id}).NumItems'))):
        try:
            dbid = int(xbmc.getInfoLabel(f'{method}({count}).DBID'))
            url = xbmc.getInfoLabel(f'{method}({count}).Filenameandpath')
        except ValueError:
            break
        else:
            if condition(f'String.IsEqual({method}({count}).DBType,movie)'):
                media_type = 'movie'
            elif condition(f'String.IsEqual({method}({count}).DBType,episode)'):
                media_type = 'episode'
            elif condition(f'String.IsEqual({method}({count}).DBType,song)'):
                media_type = 'song'
            elif condition(f'String.IsEqual({method}({count}).DBType,musicvideo)'):
                media_type = 'musicvideo'

            if media_type and dbid:
                json_call('Playlist.Add',
                          item={f'{media_type}id': dbid},
                          params={'playlistid': playlistid},
                          parent='play_items'
                          )
            elif url:
                json_call('Playlist.Add',
                          item={'file': url},
                          params={'playlistid': playlistid},
                          parent='play_items'
                          )

    json_call('Playlist.GetItems',
              params={'playlistid': playlistid},
              parent='play_items'
              )

    json_call('Player.Open',
              item={'playlistid': playlistid, 'position': 0},
              options={'shuffled': shuffled},
              parent='play_items'
              )


def play_radio(**kwargs):
    import random
    clear_playlists()

    dbid = int(kwargs.get('id', xbmc.getInfoLabel('ListItem.DBID')))

    json_response = json_call('AudioLibrary.GetSongDetails',
                              params={'properties': ['genre'], 'songid': dbid},
                              parent='play_radio'
                              )

    if json_response['result']['songdetails'].get('genre', None):
        genre = json_response['result']['songdetails']['genre']
        genre = random.choice(genre)

    if genre:
        json_call('Playlist.Add',
                  item={'songid': dbid},
                  params={'playlistid': 0},
                  parent='play_radio'
                  )

        json_response = json_call('AudioLibrary.GetSongs',
                                  params={'properties': ['genre']},
                                  sort={'method': 'random'},
                                  limit=24,
                                  query_filter={'genre': genre},
                                  parent='play_radio'
                                  )

        for count in json_response['result']['songs']:
            if count.get('songid', None):
                songid = int(count['songid'])

                json_call('Playlist.Add',
                          item={'songid': songid},
                          params={'playlistid': 0},
                          parent='play_radio'
                          )

        json_call('Playlist.GetItems',
                  params={'playlistid': 0},
                  parent='play_radio'
                  )

        json_call('Player.Open',
                  item={'playlistid': 0, 'position': 0},
                  parent='play_radio'
                  )


def rate_song(**kwargs):
    dbid = int(kwargs.get('id', xbmc.getInfoLabel('ListItem.DBID')))
    rating_threshold = int(kwargs.get('rating', xbmc.getInfoLabel(
        'Skin.String(Music_Rating_Like_Threshold)')))

    json_call('AudioLibrary.SetSongDetails',
              params={'songid': dbid, 'userrating': rating_threshold},
              parent='rate_song'
              )

    player = xbmc.Player()
    player_dbid = int(xbmc.getInfoLabel('MusicPlayer.DBID')
                      ) if player.isPlayingAudio() else None

    if dbid == player_dbid:
        if rating_threshold != 0:
            window_property('MusicPlayer_UserRating', set=rating_threshold)
        else:
            window_property('MusicPlayer_UserRating', clear=True)
        '''
        player_path = player.getPlayingFile()
        item = xbmcgui.ListItem(path=player_path)
        musicInfoTag = item.getMusicInfoTag()
        musicInfoTag.setUserRating(rating_threshold)
        player.updateInfoTag(item)
        '''


def shuffle_artist(**kwargs):
    clear_playlists()

    dbid = int(kwargs.get('id', False))
    json_call('Player.Open',
              item={'artistid': dbid},
              options={'shuffled': True},
              parent='shuffle_artist')


def subtitle_limiter(lang,**kwargs):
    if condition('VideoPlayer.HasSubtitles'):
        player = xbmc.Player()
        subtitles = []
        current_subtitle = player.getSubtitles()
        subtitles = player.getAvailableSubtitleStreams()
        if lang not in current_subtitle or condition('!VideoPlayer.SubtitlesEnabled'):
            try:
                index = subtitles.index(lang)
            except ValueError as error:
                log(
                    f'Subtitle Limiter: Error - Preferred subtitle stream ({lang}) not available, toggling through available streams instead --> {error}', force=True)
                log_and_execute('Action(NextSubtitle)')
            else:
                player.setSubtitleStream(index)
                log(f'Subtitle Limiter: Switching to subtitle stream {index} in preferred language: {lang}', force=True)
        elif condition('VideoPlayer.SubtitlesEnabled'):
            log_and_execute('Action(ShowSubtitles)')
    else:
        log('Subtitle Limiter: Error - Playing video has no subtitles', force=True)


def toggle_addon(id, **kwargs):
    if condition(f'System.AddonIsEnabled({id})'):
        json_call('Addons.SetAddonEnabled',
                  params={'addonid': id, 'enabled': False},
                  parent='toggle_addon')
        DIALOG.notification(id, ADDON.getLocalizedString(32205))
    else:
        json_call('Addons.SetAddonEnabled',
                  params={'addonid': id, 'enabled': True},
                  parent='toggle_addon')
        DIALOG.notification(id, ADDON.getLocalizedString(32206))


def url_encode(name, string, **kwargs):
    encoded = urllib.quote(string)
    window_property(name, set=encoded)


def widget_move(posa, posb, **kwargs):
    # create list of (widget position, dictionary)
    content_types = ['Disabled', 'InProgress', 'NextUp', 'LatestMovies', 'LatestTVShows', 'RandomMovies',
                     'RandomTVShows', 'LatestAlbums', 'RecentAlbums', 'RandomALbums', 'LikedSongs', 'Favourites', 'Custom']
    template = {
        'View': '', 'Display': '', 'Content': '', 'Custom_Name': '', 'Custom_Target': '', 'Custom_SortMethod': '', 'Custom_SortOrder': '', 'Custom_Path': '', 'Custom_Limit': '', 'Autoscroll': False,
        'Trailer_Autoplay': False, 'Clearlogos_Enabled': False, 'Prefer_Keyart': False, 'Prefer_Landscape': False
    }
    dica, dicb = {}, {}
    dica.update(template)
    dicb.update(template)

    # populate dictionaries with values from Kodi
    list = [(posa, dica), (posb, dicb)]
    for item in list:
        for content in content_types:
            if condition(f'Skin.HasSetting(Widget{item[0]}_Content_{content})'):
                # capture value of bool then reset it in Kodi
                item[1]['Content'] = content
                xbmc.executebuiltin(
                    f'Skin.Reset(Widget{item[0]}_Content_{content})')
                break
        for key, value in item[1].items():
            if type(value) == str and not value:
                item[1][key] = infolabel(f'Skin.String(Widget{item[0]}_{key})')
            elif type(value) == bool and not value:
                if condition(f'Skin.HasSetting(Widget{item[0]}_{key})'):
                    # capture value of bool then reset it in Kodi
                    item[1][key] = True
                    xbmc.executebuiltin(
                        f'Skin.Reset(Widget{item[0]}_{key})')
    # swap values
    swapped_list = [(posa, dicb), (posb, dica)]
    for item in swapped_list:
        xbmc.executebuiltin(f'Skin.ToggleSetting(Widget{item[0]}_Content_{item[1]["Content"]})')
        for key, value in item[1].items():
            if type(value) == str:
                skin_string(f'Widget{item[0]}_{key}', set=value)
            elif type(value) == bool and value and 'Content' not in key:
                xbmc.executebuiltin(
                    f'Skin.ToggleSetting(Widget{item[0]}_{key})')

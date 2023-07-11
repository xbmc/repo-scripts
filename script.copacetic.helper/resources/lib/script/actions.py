# author: realcopacetic

from resources.lib.service.art import ImageEditor
from resources.lib.utilities import (DIALOG, clear_playlists, condition,
                                     infolabel, json_call, log_and_execute,
                                     skin_string, window_property, xbmc)


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

    for count in range(int(xbmc.getInfoLabel(f'Container({id}).NumItems'))):

        if xbmc.getCondVisibility(f'String.IsEqual({method}({count}).DBType,movie)'):
            media_type = 'movie'
        elif xbmc.getCondVisibility(f'String.IsEqual({method}({count}).DBType,episode)'):
            media_type = 'episode'
        elif xbmc.getCondVisibility(f'String.IsEqual({method}({count}).DBType,song)'):
            media_type = 'song'
        elif xbmc.getCondVisibility(f'String.IsEqual({method}({count}).DBType,musicvideo)'):
            media_type = 'musicvideo'

        dbid = int(xbmc.getInfoLabel(f'{method}({count}).DBID'))
        url = xbmc.getInfoLabel(f'{method}({count}).Filenameandpath')

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
    

def widget_move(posa, posb, **kwargs):
    tempa_name = ''
    tempa_target = ''
    tempa_sortmethod = ''
    tempa_sortorder = ''
    tempa_path = ''
    tempa_limit = ''
    tempa_thumb = False,
    tempb_name = ''
    tempb_target = ''
    tempb_sortmethod = ''
    tempb_sortorder = ''
    tempb_path = ''
    tempb_limit = ''
    tempb_thumb = False

    tempa_view = infolabel(f'Skin.String(Widget{posa}_View)')
    tempa_display = infolabel(f'Skin.String(Widget{posa}_Display)')
    tempb_view = infolabel(f'Skin.String(Widget{posb}_View)')
    tempb_display = infolabel(f'Skin.String(Widget{posb}_Display)')

    if condition(f'Skin.HasSetting(Widget{posa}_Content_Disabled)'):
        tempa_content = 'Disabled'
    elif condition(f'Skin.HasSetting(Widget{posa}_Content_InProgress)'):
        tempa_content = 'InProgress'
    elif condition(f'Skin.HasSetting(Widget{posa}_Content_NextUp)'):
        tempa_content = 'NextUp'
    elif condition(f'Skin.HasSetting(Widget{posa}_Content_LatestMovies)'):
        tempa_content = 'LatestMovies'
    elif condition(f'Skin.HasSetting(Widget{posa}_Content_LatestTVShows)'):
        tempa_content = 'LatestTVShows'
    elif condition(f'Skin.HasSetting(Widget{posa}_Content_RandomMovies)'):
        tempa_content = 'RandomMovies'
    elif condition(f'Skin.HasSetting(Widget{posa}_Content_RandomTVShows)'):
        tempa_content = 'RandomTVShows'
    elif condition(f'Skin.HasSetting(Widget{posa}_Content_LatestAlbums)'):
        tempa_content = 'LatestAlbums'
    elif condition(f'Skin.HasSetting(Widget{posa}_Content_RecentAlbums)'):
        tempa_content = 'RecentAlbums'
    elif condition(f'Skin.HasSetting(Widget{posa}_Content_RandomAlbums)'):
        tempa_content = 'RandomAlbums'
    elif condition(f'Skin.HasSetting(Widget{posa}_Content_LikedSongs)'):
        tempa_content = 'LikedSongs'
    elif condition(f'Skin.HasSetting(Widget{posa}_Content_Favourites)'):
        tempa_content = 'Favourites'
    elif condition(f'Skin.HasSetting(Widget{posa}_Content_Custom)'):
        tempa_content = 'Custom'
        tempa_name = infolabel(f'Skin.String(Widget{posa}_Custom_Name)')
        tempa_target = infolabel(f'Skin.String(Widget{posa}_Custom_Target)')
        tempa_sortmethod = infolabel(f'Skin.String(Widget{posa}_Custom_SortMethod)')
        tempa_sortorder = infolabel(f'Skin.String(Widget{posa}_Custom_SortOrder)')
        tempa_path = infolabel(f'Skin.String(Widget{posa}_Custom_Path)')
        tempa_limit = infolabel(f'Skin.String(Widget{posa}_Custom_Limit)')
        tempa_thumb = True if condition(f'Skin.HasSetting(Widget{posa}_Episode_Thumbs)') else False

    if condition(f'Skin.HasSetting(Widget{posb}_Content_Disabled)'):
        tempb_content = 'Disabled'
    elif condition(f'Skin.HasSetting(Widget{posb}_Content_InProgress)'):
        tempb_content = 'InProgress'
    elif condition(f'Skin.HasSetting(Widget{posb}_Content_NextUp)'):
        tempb_content = 'NextUp'
    elif condition(f'Skin.HasSetting(Widget{posb}_Content_LatestMovies)'):
        tempb_content = 'LatestMovies'
    elif condition(f'Skin.HasSetting(Widget{posb}_Content_LatestTVShows)'):
        tempb_content = 'LatestTVShows'
    elif condition(f'Skin.HasSetting(Widget{posb}_Content_RandomMovies)'):
        tempb_content = 'RandomMovies'
    elif condition(f'Skin.HasSetting(Widget{posb}_Content_RandomTVShows)'):
        tempb_content = 'RandomTVShows'
    elif condition(f'Skin.HasSetting(Widget{posb}_Content_LatestAlbums)'):
        tempb_content = 'LatestAlbums'
    elif condition(f'Skin.HasSetting(Widget{posb}_Content_RecentAlbums)'):
        tempb_content = 'RecentAlbums'
    elif condition(f'Skin.HasSetting(Widget{posb}_Content_RandomAlbums)'):
        tempb_content = 'RandomAlbums'
    elif condition(f'Skin.HasSetting(Widget{posb}_Content_LikedSongs)'):
        tempb_content = 'LikedSongs'
    elif condition(f'Skin.HasSetting(Widget{posb}_Content_Favourites)'):
        tempb_content = 'Favourites'
    elif condition(f'Skin.HasSetting(Widget{posb}_Content_Custom)'):
        tempb_content = 'Custom'
        tempb_name = infolabel(f'Skin.String(Widget{posb}_Custom_Name)')
        tempb_target = infolabel(f'Skin.String(Widget{posb}_Custom_Target)')
        tempb_sortmethod = infolabel(f'Skin.String(Widget{posb}_Custom_SortMethod)')
        tempb_sortorder = infolabel(f'Skin.String(Widget{posb}_Custom_SortOrder)')
        tempb_path = infolabel(f'Skin.String(Widget{posb}_Custom_Path)')
        tempb_limit = infolabel(f'Skin.String(Widget{posb}_Custom_Limit)')
        tempb_thumb = True if condition(f'Skin.HasSetting(Widget{posb}_Episode_Thumbs)') else False
    
    xbmc.executebuiltin(f'Skin.ToggleSetting(Widget{posa}_Content_{tempa_content})')
    xbmc.executebuiltin(f'Skin.SetBool(Widget{posa}_Content_{tempb_content})')
    xbmc.executebuiltin(f'Skin.ToggleSetting(Widget{posb}_Content_{tempb_content})')
    xbmc.executebuiltin(f'Skin.SetBool(Widget{posb}_Content_{tempa_content})')
    skin_string(f'Widget{posb}_View', set=tempa_view)
    skin_string(f'Widget{posa}_View', set=tempb_view)
    skin_string(f'Widget{posb}_Display', set=tempa_display)
    skin_string(f'Widget{posa}_Display', set=tempb_display)
    skin_string(f'Widget{posb}_Custom_Name', set=tempa_name)
    skin_string(f'Widget{posa}_Custom_Name', set=tempb_name)
    skin_string(f'Widget{posb}_Custom_Target', set=tempa_target)
    skin_string(f'Widget{posa}_Custom_Target', set=tempb_target)
    skin_string(f'Widget{posb}_Custom_SortMethod', set=tempa_sortmethod)
    skin_string(f'Widget{posa}_Custom_SortMethod', set=tempb_sortmethod)
    skin_string(f'Widget{posb}_Custom_SortOrder', set=tempa_sortorder)
    skin_string(f'Widget{posa}_Custom_SortOrder', set=tempb_sortorder)
    skin_string(f'Widget{posb}_Custom_Path', set=tempa_path)
    skin_string(f'Widget{posa}_Custom_Path', set=tempb_path)
    skin_string(f'Widget{posb}_Custom_Limit', set=tempa_limit)
    skin_string(f'Widget{posa}_Custom_Limit', set=tempb_limit)
    if tempa_thumb and not tempb_thumb:
        xbmc.executebuiltin(f'Skin.ToggleSetting(Widget{posa}_Episode_Thumbs)')
        xbmc.executebuiltin(f'Skin.SetBool(Widget{posb}_Episode_Thumbs)')
    elif tempb_thumb and not tempa_thumb:
        xbmc.executebuiltin(f'Skin.ToggleSetting(Widget{posb}_Episode_Thumbs)')
        xbmc.executebuiltin(f'Skin.SetBool(Widget{posa}_Episode_Thumbs)')

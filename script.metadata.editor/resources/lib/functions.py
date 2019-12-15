#!/usr/bin/python
# coding: utf-8

########################

from resources.lib.helper import *
from resources.lib.nfo_updater import *

########################

def update_library(dbtype,key,value,dbid):
    if dbtype in ['song', 'album', 'artist']:
        library = 'Audio'
    else:
        library = 'Video'

    if isinstance(key, list):
        for item in key:
            json_call('%sLibrary.Set%sDetails' % (library, dbtype),
                      params={'%s' % item: value[key.index(item)], '%sid' % dbtype: int(dbid)},
                      debug=LOG_JSON
                      )

    else:
        json_call('%sLibrary.Set%sDetails' % (library, dbtype),
                  params={'%s' % key: value, '%sid' % dbtype: int(dbid)},
                  debug=LOG_JSON
                  )


def update_nfo(file,elem,value,dbtype,dbid):
    if not ADDON.getSettingBool('nfo_updating'):
        return

    if dbtype == 'tvshow':
        path = os.path.join(file,'tvshow.nfo')
    else:
        path = file.replace(os.path.splitext(file)[1], '.nfo')

    UpdateNFO(path, elem, value, dbtype, dbid)

    # support for additional movie.nfo
    if dbtype == 'movie':
        path = file.replace(os.path.basename(file), 'movie.nfo')
        UpdateNFO(path, elem, value, dbtype, dbid)


def set_ratings(ratings):
    providerlist = []
    for item in ratings:
        providerlist.append(str(item))

    preselect = -1
    for item in providerlist:
        if ratings[item].get('default'):
            preselect = providerlist.index(item)

    menu = DIALOG.select(xbmc.getLocalizedString(424), [ADDON.getLocalizedString(32015), ADDON.getLocalizedString(32016), ADDON.getLocalizedString(32017)])

    if menu == 0: # set default provider
        providerdefault = DIALOG.select(ADDON.getLocalizedString(32014), providerlist, preselect=preselect)

        if providerdefault >= 0:
            name = providerlist[providerdefault]

            for item in ratings:
                default = True if item == name else False
                ratings[item] = {'default': default,
                                 'rating': ratings[item].get('rating'),
                                 'votes': ratings[item].get('votes')}

    elif menu == 1: # edit votes/rating
        providerratings = DIALOG.select(ADDON.getLocalizedString(32012), providerlist, preselect=preselect)

        if providerratings >= 0:
            name = providerlist[providerratings]
            cur_rating = round(ratings[name].get('rating', 0.0), 1)
            cur_votes = ratings[name].get('votes', 0)

            rating = set_float(cur_rating)
            votes = set_integer(cur_votes)

            if not rating:
                rating = 0.0

            if not votes:
                votes = 0

            ratings[name] = {'default': ratings[name].get('default'),
                             'rating': rating,
                             'votes': votes}

    elif menu == 2: # add new rating provider
        supportedlist = ['imdb', 'themoviedb', 'tomatometerallcritics', 'tomatometeravgcritics', 'tomatometerallaudience', 'tomatometeravgaudience', 'metacritic']

        for item in supportedlist:
            if item in providerlist:
                supportedlist.remove(item)

        newprovider = DIALOG.select(ADDON.getLocalizedString(32013), supportedlist)

        if newprovider >= 0:
            name = supportedlist[newprovider]
            rating = set_float(heading='Enter rating (floating number - min 0.1 / max 10.0)')

            if not rating or float(rating) > 10:
                DIALOG.ok(xbmc.getLocalizedString(257), ADDON.getLocalizedString(32018))

            else:
                votes = set_integer()
                if not votes:
                    votes = 0

                if not DIALOG.yesno(ADDON.getLocalizedString(32019), ADDON.getLocalizedString(32020)):
                    default = False
                else:
                    default = True

                    for item in ratings:
                        ratings[item] = {'default': False,
                                         'rating': ratings[item].get('rating'),
                                         'votes': ratings[item].get('votes')}

                ratings[name] = {'default': default,
                                 'rating': rating,
                                 'votes': votes}

    return ratings


def set_array(preset,dbid,dbtype,key):
    actionlist = [ADDON.getLocalizedString(32005), ADDON.getLocalizedString(32007), ADDON.getLocalizedString(32006)]
    array_action = DIALOG.select(xbmc.getLocalizedString(14241), actionlist)

    if array_action == 0:
        array = preset.replace('; ',';').split(';')

        keyboard = xbmc.Keyboard()
        keyboard.doModal()

        if keyboard.isConfirmed():
            new_item = keyboard.getText()

            if new_item not in array:
                array.append(new_item)

        return remove_empty(array)

    elif array_action == 1:
        from resources.lib.dialog_selectvalue import SelectValue

        array = SelectValue(params={'dbid': dbid, 'type': dbtype, 'key': key},
                            editor=True)

        return eval(str(array))

    elif array_action == 2:
        keyboard = xbmc.Keyboard(preset)
        keyboard.doModal()

        if keyboard.isConfirmed():
            array = keyboard.getText()
        else:
            array = preset

        array = array.replace('; ',';').split(';')
        return remove_empty(array)

    else:
        array = preset.replace('; ',';').split(';')
        return remove_empty(array)


def set_integer(preset=''):
    preset = str(preset)
    if preset == '0':
        preset = ''

    value = xbmcgui.Dialog().numeric(0, xbmc.getLocalizedString(16028), preset)

    if not value:
        return None

    return int(value)


def set_float(preset='',heading=ADDON.getLocalizedString(32011)):
    try:
        preset = float(preset)
        preset = round(preset,1)

    except Exception:
        preset = ''

    keyboard = xbmc.Keyboard(str(preset))
    keyboard.setHeading(heading)
    keyboard.doModal()

    if keyboard.isConfirmed():
        try:
            value = float(keyboard.getText())
            value = round(value,1)
            return value

        except Exception:
            set_float(preset)

    return preset


def set_date(preset):
    try:
        conv = time.strptime(preset,'%Y-%m-%d')
        conv = time.strftime('%d/%m/%Y',conv)

    except Exception:
        conv = '01/01/1900'

    value = xbmcgui.Dialog().numeric(1, xbmc.getLocalizedString(16028), conv)

    if value:
        value = value.replace(' ','0')
        value = time.strptime(value,'%d/%m/%Y')
        value = time.strftime('%Y-%m-%d',value)
        return value

    return preset


def set_time(preset):
    value = xbmcgui.Dialog().numeric(2, xbmc.getLocalizedString(16028), preset)

    if value:
        return value

    return preset


def set_string(preset):
    value = preset.replace('\n', '[CR]')
    keyboard = xbmc.Keyboard(value)
    keyboard.doModal()

    if keyboard.isConfirmed():
        value = keyboard.getText()

    return value.replace('[CR]', '\n')


def set_integer_range(preset, maximum):
    preset = int(preset) if preset else 0
    rangelist = []

    for i in range(0, maximum):
        rangelist.append(str(i))

    value = DIALOG.select(xbmc.getLocalizedString(424), rangelist, preselect=preset)

    if value >= 0:
        return value

    return preset


def set_status(preset):
    statuslist = ['Returning series', 'In production', 'Planned', 'Cancelled', 'Ended']

    if preset == ADDON.getLocalizedString(32022):
        preset = ''

    value = DIALOG.select(xbmc.getLocalizedString(126), statuslist)

    if value >= 0:
        return statuslist[value]

    return preset


def omdb_call(imdbnumber=None,title=None,year=None,use_fallback=False):
    api_key = ADDON.getSetting('omdb_api_key')
    base_url = 'http://www.omdbapi.com/'

    if imdbnumber:
        url = '%s?apikey=%s&i=%s&plot=short&r=xml&tomatoes=true' % (base_url, api_key, imdbnumber)

    elif use_fallback and title and year:
        # it seems that urllib has issues with some asian letters
        try:
            title = urllib.quote(title)
        except KeyError:
            return

        url = '%s?apikey=%s&t=%s&year=%s&plot=short&r=xml&tomatoes=true' % (base_url, api_key, title, year)

    else:
        return

    try:
        for i in range(1,10): # loop if heavy server load
            request = requests.get(url)
            if not str(request.status_code).startswith('5'):
                break
            xbmc.sleep(500)

        if request.status_code != requests.codes.ok:
            raise Exception

        result = request.content
        return result

    except Exception:
        return


def tmdb_call(action,call=None,get=None,params=None):
    args = {}
    args['api_key'] = 'fc168650632c6597038cf7072a7c20da'

    if params:
        args.update(params)

    call = '/' + str(call) if call else ''
    get = '/' + get if get else ''

    url = 'https://api.themoviedb.org/3/' + action + call + get
    url = '{0}?{1}'.format(url, urlencode(args))

    for i in range(1,10): # loop if heavy server load
        request = requests.get(url)
        if not str(request.status_code).startswith('5'):
            break
        xbmc.sleep(500)

    result = {}
    if request.status_code == requests.codes.ok:
        result = request.json()

    return result
#!/usr/bin/python
# coding: utf-8

########################

from resources.lib.helper import *
from resources.lib.database import *

########################

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

def set_movieset(preset):
    db = Database()
    db.sets()
    sets = db.result().get('set', [])

    selectlist = []
    for item in sets:
        selectlist.append(item.get('title'))
    selectlist.sort()
    selectlist.insert(0, xbmc.getLocalizedString(231))
    selectlist.insert(1, ADDON.getLocalizedString(32005))

    preselect = selectlist.index(preset) if preset in selectlist else -1

    selectdialog = DIALOG.select(xbmc.getLocalizedString(20466), selectlist, preselect=preselect)

    if selectdialog == 0:
        return ''

    elif selectdialog == 1:
        value = set_string()
        return value

    elif selectdialog > 1:
        return selectlist[selectdialog]

    return preset

def set_array(dbtype,key,preset):
    actionlist = [ADDON.getLocalizedString(32005), ADDON.getLocalizedString(32007), ADDON.getLocalizedString(32006)]
    array_action = DIALOG.select(xbmc.getLocalizedString(14241), actionlist)
    array_list = get_list_items(preset)

    if array_action == 0:
        keyboard = xbmc.Keyboard()
        keyboard.doModal()

        if keyboard.isConfirmed():
            new_item = keyboard.getText()

            if new_item not in array_list:
                array_list.append(new_item)

        return remove_empty(array_list)

    elif array_action == 1:
        array = modify_array(dbtype, key, array_list)
        return array

    elif array_action == 2:
        keyboard = xbmc.Keyboard(preset)
        keyboard.doModal()

        if keyboard.isConfirmed():
            array = keyboard.getText()
        else:
            array = preset

        return get_list_items(array)

    else:
        return array_list


def modify_array(dbtype,key,values):
    modified = []
    all_values = []

    if not isinstance(values, list):
        values = get_list_items(values)

    if key in ['genre', 'tags']:
        db = Database()
        getattr(db, key)()
        result = db.result()

        if key == 'genre':
            if dbtype in ['musicvideo', 'artist', 'album']:
                for genre in result.get('audiogenres'):
                    all_values.append(genre)
            else:
                for genre in result.get('videogenres'):
                    all_values.append(genre)

        elif key == 'tags':
            for tag in result.get('tags'):
                if tag not in values:
                    all_values.append(tag)

    all_values = list(set(values + all_values))
    all_values.sort()
    values.sort()

    # open common array dialog if all_values are empty
    if not all_values:
        notification(ADDON.getLocalizedString(32000), ADDON.getLocalizedString(32048))
        value = set_array(dbtype, key, '')
        return value

    preselectlist = []
    for item in values:
        preselectlist.append(all_values.index(item))

    selectdialog = DIALOG.multiselect(ADDON.getLocalizedString(32002), all_values, preselect=preselectlist)

    if selectdialog == -1 or selectdialog is None:
        return values

    for index in selectdialog:
        modified.append(all_values[index])

    return modified


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
        conv = time.strftime('%d/%m/%Y', conv)

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


def set_string(preset=''):
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


def toggle_tag(preset):
    tag = 'Watchlist'
    tags = get_list_items(preset)

    if tag in tags:
        tags.remove(tag)
    else:
        tags.append(tag)

    return tags
import os
import hashlib

import xbmcgui

from addon import addon
from addon import mpr
from addon import cache_dir

from addon import utils


@mpr.s_url('/notification/posted/')
def on_notification_posted(data):
    utils.log('Received new notification')

    # Get title and message
    title = data['title']

    message = ''
    if data['bigText']:
        message = data['bigText']

    elif data['text']:
        message = data['text']

    elif data['tickerText']:
        message = data['tickerText']

    if data['subText']:
        message = '%s %s' % (message, data['subText'])

    message = message.replace('\n', ' ').replace('\r', ' ')

    # Try and get a display time (default back to 5 sec.)
    try:
        display_time = int(data['displayTime'])

    except:
        display_time = 5000


    # Get an icon to display
    large_icon_data = data['largeIcon']['data']
    app_icon_data   = data['appIcon']['data']
    small_icon_data = data['smallIcon']['data']

    icon = None
    icon_path = None
    if large_icon_data:
        icon = large_icon_data
        icon_path = os.path.join(cache_dir,
                                 hashlib.md5(large_icon_data).hexdigest())

    elif app_icon_data:
        icon = app_icon_data
        icon_path = os.path.join(cache_dir,
                                 hashlib.md5(app_icon_data).hexdigest())

    elif small_icon_data:
        icon = small_icon_data
        icon_path = os.path.join(cache_dir,
                                 hashlib.md5(small_icon_data).hexdigest())


    if not os.path.exists(icon_path):
        with open(icon_path, 'w') as f:
            f.write(icon.decode('base64'))


    play_sound = addon.getSetting('notification.play_sound') == 'true'
    xbmcgui.Dialog().notification(title, message, icon_path, display_time,
                                  play_sound)

    return True


@mpr.s_url('/notification/removed/')
def on_notification_removed(data):
    utils.log('Received notification delete event')
    return True
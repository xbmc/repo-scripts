import os, sys
from alarm_clock import Alarm

# alternative_stream = "http://stream.celador.co.uk/sam-bristol-128.aac.m3u" # Sam FM (Bristol)
# alternative_stream = "http://www.radiofeeds.co.uk/bauer.pls?station-key.mp3.m3u" # Key103 / Hits Radio (Manchester)
# alternative_stream = "http://media-ice.musicradio.com/CapitalUKMP3.m3u" # Capital (UK)
# alternative_stream = "http://media-ice.musicradio.com/CapitalMancheterMP3.m3u" # Capital (Manchester)
# alternative_stream = "http://media-ice.musicradio.com/HeartUKMP3.m3u" # Heart (UK)
# alternative_stream = "http://media-ice.musicradio.com/HeartBristolMP3.m3u" # Heart (Bristol)
# alternative_stream = "http://media-ice.musicradio.com/Heart70sMP3.m3u" # Heart (70s)
# alternative_stream = "http://media-ice.musicradio.com/Heart80sMP3.m3u" # Heart (80s)
# alternative_stream = "http://media-ice.musicradio.com/Heart90sMP3.m3u" # Heart (90s)
# alternative_stream = "http://media-ice.musicradio.com/HeartDanceMP3.m3u" # Heart (Dance)
# alternative_stream = "http://media-ice.musicradio.com/HeartextraMP3.m3u" # Heart (Extra)
# alternative_stream = "http://open.live.bbc.co.uk/mediaselector/5/select/version/2.0/mediaset/http-icy-mp3-a/vpid/bbc_radio_one/format/pls.pls"
# alternative_stream = "http://open.live.bbc.co.uk/mediaselector/5/select/version/2.0/mediaset/http-icy-mp3-a/vpid/bbc_radio_two/format/pls.pls"
# alternative_stream = "http://open.live.bbc.co.uk/mediaselector/5/select/version/2.0/mediaset/http-icy-mp3-a/vpid/bbc_radio_three/format/pls.pls"
# alternative_stream = "http://open.live.bbc.co.uk/mediaselector/5/select/version/2.0/mediaset/http-icy-mp3-a/vpid/bbc_radio_four/format/pls.pls"
# alternative_stream = "http://open.live.bbc.co.uk/mediaselector/5/select/version/2.0/mediaset/http-icy-mp3-a/vpid/bbc_radio_bristol/format/pls.pls"
# alternative_stream = "http://open.live.bbc.co.uk/mediaselector/5/select/version/2.0/mediaset/http-icy-mp3-a/vpid/bbc_radio_manchester/format/pls.pls"

defaults = dict([ \
    ("__DELETED__", "false"),
    ("label", "Alarm {alarm_id}"),

    ("day", "7"),
    ("time", "07:00"),
    ("turnOff", "true"),
    ("duration", "30"),

    ("trigger_when", "1"),
    ("action", "1"),
    ("file", ""),
    ("text", "{default_stream}"),
    ("volume", "90"),
    ("fade", "10"),
    ("cec", "0"),
])


def __create_addon():
    import xbmcaddon
    return xbmcaddon.Addon()


def __clone_settings(addon, src_alarm_id, dest_alarm_id):
    for key in list(defaults.keys()):
        value = addon.getSetting(key + str(src_alarm_id))
        addon.setSetting(key + str(dest_alarm_id), value)


def __increment_setting_value(addon, setting_id):
    value = addon.getSetting(setting_id) or 1
    addon.setSetting(setting_id, str(int(value) + 1))
    return value


def get_available_alarm_id(addon):
    max = int(addon.getSetting('next_alarm_id') or '1')
    raw_data = [get_raw_alarm_data(addon, alarm_id) for alarm_id in list(range(1, max))]
    raw_data = [data for data in raw_data if data['__DELETED__'] == 'true']
    if raw_data:
        alarm_id = raw_data[0]['id']
    else:
        alarm_id = __increment_setting_value(addon, 'next_alarm_id')
    return alarm_id

def open_settings(addon):
    addon.setSetting('has_been_cancelled', "123")
    addon.openSettings()
    return addon.getSetting('has_been_cancelled') != "123"


def __edit_alarm(addon, alarm_id):
    __clone_settings(addon, alarm_id, "")
    addon.openSettings()
    __clone_settings(addon, "", alarm_id)



def edit_alarm(alarm_id):
    addon = __create_addon()
    __edit_alarm(addon, alarm_id)


def edit_new_alarm():
    addon = __create_addon()
    default_stream = "http://media-ice.musicradio.com:80/HeartBristolMP3.m3u"

    alarm_id = ''
    for key, value in list(defaults.items()):
        addon.setSetting(key, value.format(**locals()))

    if open_settings(addon):
        alarm_id = get_available_alarm_id(addon)
        __clone_settings(addon, "", alarm_id)


def clone_alarm(alarm_id):
    addon = __create_addon()
    __clone_settings(addon, alarm_id, "")
    if open_settings(addon):
        new_alarm_id = get_available_alarm_id(addon)
        __clone_settings(addon, "", new_alarm_id)


def trigger_alarm(alarm_id):
    addon = __create_addon()
    addon.setSetting('trigger_alarm', str(alarm_id))


def get_triggered_alarm():
    addon = __create_addon()
    return addon.getSetting('trigger_alarm')


def reset_triggerd_alarm():
    addon = __create_addon()
    addon.setSetting('trigger_alarm', "")


def remove_alarm(alarm_id):
    addon = __create_addon()
    addon.setSetting('__DELETED__' + str(alarm_id), "true")


def to_cron_days(daysOfWeek):
    daysOfWeek = int(daysOfWeek)
    if daysOfWeek == 7:
        result = list(range(5))
    elif daysOfWeek == 8:
        result = list(range(5,7))
    elif daysOfWeek == 9:
        result = list(range(7))
    else:
        result = [daysOfWeek]
    return result


def get_setting(env, key, alarm_id):
    return env.getSetting(key + str(alarm_id)) or defaults[key]


def get_raw_alarm_data(env, alarm_id):
    result = dict((key, get_setting(env, key, alarm_id)) for key in list(defaults.keys()))
    result['id'] = alarm_id
    return result


def convert_settings(raw):
    turn_off = raw["turnOff"] == "true"
    play_file = raw["action"] == "0"
    hour, minute = raw['time'].split(':')
    data = {
        'enabled':  raw["trigger_when"] == "1",
        'play':     raw["file"] if play_file else raw["text"],
        'volume':   int(raw["volume"]),
        'fade':     int(raw["fade"]),
        'cec':      int(raw["cec"]),
    }
    alarm_settings = Alarm(raw['id'],
                           raw["label"],
                           to_cron_days(raw["day"]),
                           int(hour), 
                           int(minute), 
                           int(raw["duration"]) if turn_off else 0)
    return alarm_settings, data


def getAlarms():
    addon = __create_addon()
    max = int(addon.getSetting('next_alarm_id') or '1')
    raw_data = [get_raw_alarm_data(addon, alarm_id) for alarm_id in list(range(1, max))]
    raw_data = [data for data in raw_data if data['__DELETED__'] != 'true']
    return [convert_settings(raw) for raw in raw_data]



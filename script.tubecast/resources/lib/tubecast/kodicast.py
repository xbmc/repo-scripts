# -*- coding: utf-8 -*-
import uuid

from resources.lib.kodi.utils import get_device_id
from resources.lib.tubecast.utils import PY3


class Kodicast(object):
    channels = dict()
    global_status = dict()
    friendlyName = get_device_id()
    user_agent = 'Mozilla/5.0 (CrKey - 0.9.3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1573.2 Safari/537.36'
    interfaces = None
    uuid = None
    ips = []


def generate_uuid():
    friendly_name = 'device.tubecast.{}'.format(Kodicast.friendlyName)
    if not PY3:
        friendly_name = friendly_name.encode('utf8')
    Kodicast.uuid = str(uuid.uuid5(
        uuid.NAMESPACE_DNS,
        friendly_name))

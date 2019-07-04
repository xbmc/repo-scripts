# -*- coding: utf-8 -*-
from bottle import Bottle, request, response

from resources.lib.kodi import kodilogging
from resources.lib.tubecast.kodicast import Kodicast
from resources.lib.tubecast.utils import build_template
from resources.lib.tubecast.youtube.app import YoutubeCastV1

logger = kodilogging.get_logger()

__device__ = '''<?xml version="1.0" encoding="utf-8"?>
<root xmlns="urn:schemas-upnp-org:device-1-0" xmlns:r="urn:restful-tv-org:schemas:upnp-dd">
    <specVersion>
    <major>1</major>
    <minor>0</minor>
    </specVersion>
    <URLBase>{{ path }}</URLBase>
    <device>
        <deviceType>urn:schemas-upnp-org:device:dail:1</deviceType>
        <friendlyName>{{ friendlyName }}</friendlyName>
        <manufacturer>Kodi</manufacturer>
        <modelName>Tubecast</modelName>
        <UDN>uuid:{{ uuid }}</UDN>
    </device>
</root>'''


class DIALApp(Bottle):
    def __init__(self):
        super(DIALApp, self).__init__()
        # Register the Youtube application in the DIAL server.
        self.youtube_app = YoutubeCastV1(self)


app = DIALApp()


@app.route('/ssdp/device-desc.xml')
def service_desc():
    ''' route for DIAL service discovery '''
    response.set_header('Access-Control-Allow-Method',
                        'GET, POST, DELETE, OPTIONS')
    response.set_header('Access-Control-Expose-Headers', 'Location')
    response.set_header('Application-URL',
                        'http://{}/apps'.format(request.get_header('host')))
    response.set_header('Content-Type', 'application/xml')
    return build_template(__device__).render(
        friendlyName=Kodicast.friendlyName,
        uuid=Kodicast.uuid,
        path="http://%s" % request.get_header('host')
    )


@app.error(404)
def error404(error):
    ''' Default error message to override the one provided by bottle '''
    return 'Only Youtube is supported'

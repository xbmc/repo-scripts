"""
Sets the forecast location by providing a keyboard prompt
to the user. The name entered by the user is searched in
site list. All matches are presented as a select list to
the user. On successful selection internal addon setting
is set.
"""
import sys
from datetime import datetime, timedelta
from operator import itemgetter
import json
from metoffice import utilities, urlcache
from metoffice.utilities import gettext as _

from metoffice.constants import (
    API_KEY, ADDON_DATA_PATH, GEOIP_PROVIDER, KEYBOARD, DIALOG,
    ADDON, FORECAST_SITELIST_URL, OBSERVATION_SITELIST_URL,
    REGIONAL_SITELIST_URL, LONG_REGIONAL_NAMES, GEOLOCATION
)


@utilities.xbmcbusy
def getsitelist(location, text=""):
    with urlcache.URLCache(ADDON_DATA_PATH) as cache:
        url = {'ForecastLocation': FORECAST_SITELIST_URL,
               'ObservationLocation': OBSERVATION_SITELIST_URL,
               'RegionalLocation': REGIONAL_SITELIST_URL}[location]
        filename = cache.get(url, lambda x: datetime.now()+timedelta(weeks=1))
        with open(filename, encoding='utf-8') as fh:
            data = json.load(fh)
        sitelist = data['Locations']['Location']
        if location == 'RegionalLocation':
            # fix datapoint bug where keys start with @ in Regional Sitelist
            # Fixing up keys has to be a two step process. If we pop and add
            # in the same loop we'll get `RuntimeError: dictionary keys
            # changed during iteration.`
            for site in sitelist:
                # First add the correct keys.
                toremove = []
                for key in site:
                    if key.startswith('@'):
                        toremove.append(key)
                # Now remove the keys we found above.
                for key in toremove:
                    site[key[1:]] = site.pop(key)

                # Change regional names to long versions. Untouched otherwise.
                site['name'] = LONG_REGIONAL_NAMES.get(site['name'], site['name'])
        if text:
            sitelist[:] = filter(lambda x: x['name'].lower().find(text.lower()) >= 0, sitelist)

        if GEOLOCATION == 'true':
            geo = {}
            url = GEOIP_PROVIDER['url']
            filename = cache.get(url, lambda x: datetime.now()+timedelta(hours=1))
            try:
                with open(filename) as fh:
                    data = json.load(fh)
            except ValueError:
                utilities.log('Failed to fetch valid data from %s' % url)
            try:
                geolat = float(data[GEOIP_PROVIDER['latitude']])
                geolong = float(data[GEOIP_PROVIDER['longitude']])
                geo = {'lat': geolat, 'long': geolong}
            except KeyError:
                utilities.log('Couldn\'t extract lat/long data from %s' % url)

            for site in sitelist:
                try:
                    site['distance'] = int(utilities.haversine_distance(geo['lat'], geo['long'],
                                           float(site['latitude']), float(site['longitude'])))
                    site['display'] = "{0} ({1}km)".format(site['name'], site['distance'])
                except KeyError:
                    site['display'] = site['name']
            try:
                sitelist = sorted(sitelist, key=itemgetter('distance'))
            except KeyError:
                sitelist = sorted(sitelist, key=itemgetter('name'))
        else:
            for site in sitelist:
                site['display'] = site['name']
            sitelist = sorted(sitelist, key=itemgetter('name'))
        return sitelist


@utilities.failgracefully
def main(location):
    if not API_KEY:
        raise Exception(_("No API Key."), _("Enter your Met Office API Key under settings."))

    KEYBOARD.doModal()  # @UndefinedVariable
    text = KEYBOARD.isConfirmed() and KEYBOARD.getText()  # @UndefinedVariable
    sitelist = getsitelist(location, text)
    if sitelist == []:
        DIALOG.ok(_("No Matches"), _("No locations found containing")+" {0}".format(text))  # @UndefinedVariable
        utilities.log("No locations found containing '%s'" % text)
    else:
        display_list = [site['display'] for site in sitelist]
        selected = DIALOG.select(_("Matching Sites"), display_list)  # @UndefinedVariable
        if selected != -1:
            ADDON.setSetting(location, sitelist[selected]['name'])  # @UndefinedVariable
            ADDON.setSetting("%sID" % location, sitelist[selected]['id'])  # @UndefinedVariable
            ADDON.setSetting("%sLatitude" % location, str(sitelist[selected].get('latitude')))  # @UndefinedVariable
            ADDON.setSetting("%sLongitude" % location, str(sitelist[selected].get('longitude')))  # @UndefinedVariable
            utilities.log("Setting '{location}' to '{name} ({id})'".format(location=location,
                                                                           name=sitelist[selected]['name'].encode(
                                                                               'utf-8'),
                                                                           id=sitelist[selected]['id']))


if __name__ == '__main__':
    # check sys.argv
    main(sys.argv[1])

"""
This library/script will grab a web page from thetvdb.com and use
the TV network info in the SELECT OPTIONs to make a lookup table
that can be used to determine what country a show is broadcast in.
"""
import re, sys, urllib

# This holds the hour offset for normal and DST zones.
COUNTRY_ZONES = {
    'afghanistan': (4.5, 4.5),
    'aland islands': (2.0, 3.0),
    'albania': (1.0, 2.0),
    'algeria': (1.0, 1.0),
    'american samoa': (-11.0, -11.0),
    'andorra': (1.0, 2.0),
    'angola': (1.0, 1.0),
    'anguilla': (-4.0, -4.0),
    'antigua and barbuda': (-4.0, -4.0),
    'argentina': (-3.0, -3.0),
    'armenia': (4.0, 4.0),
    'aruba': (-4.0, -4.0),
    'australia': (11.0, 10.0),
    'austria': (1.0, 2.0),
    'azerbaijan': (4.0, 5.0),
    'bahamas': (-5.0, -4.0),
    'bahrain': (3.0, 3.0),
    'bangladesh': (6.0, 6.0),
    'barbados': (-4.0, -4.0),
    'belarus': (3.0, 3.0),
    'belgium': (1.0, 2.0),
    'belize': (-6.0, -6.0),
    'benin': (1.0, 1.0),
    'bermuda': (-4.0, -3.0),
    'bhutan': (6.0, 6.0),
    'bolivia': (-4.0, -4.0),
    'bonaire, saint eustatius and saba': (-4.0, -4.0),
    'bosnia and herzegovina': (1.0, 2.0),
    'botswana': (2.0, 2.0),
    'brazil': (-2.0, -3.0),
    'british indian ocean territory': (6.0, 6.0),
    'british virgin islands': (-4.0, -4.0),
    'brunei': (8.0, 8.0),
    'bulgaria': (2.0, 3.0),
    'burkina faso': (0.0, 0.0),
    'burundi': (2.0, 2.0),
    'cambodia': (7.0, 7.0),
    'cameroon': (1.0, 1.0),
    'canada': (-4.0, -3.0),
    'cape verde': (-1.0, -1.0),
    'cayman islands': (-5.0, -5.0),
    'central african republic': (1.0, 1.0),
    'chad': (1.0, 1.0),
    'chile': (-3.0, -4.0),
    'china': (8.0, 8.0),
    'christmas island': (7.0, 7.0),
    'cocos islands': (6.5, 6.5),
    'colombia': (-5.0, -5.0),
    'comoros': (3.0, 3.0),
    'cook islands': (-10.0, -10.0),
    'costa rica': (-6.0, -6.0),
    'croatia': (1.0, 2.0),
    'cuba': (-5.0, -4.0),
    'curacao': (-4.0, -4.0),
    'cyprus': (2.0, 3.0),
    'czech republic': (1.0, 2.0),
    'democratic republic of the congo': (2.0, 2.0),
    'denmark': (1.0, 2.0),
    'djibouti': (3.0, 3.0),
    'dominica': (-4.0, -4.0),
    'dominican republic': (-4.0, -4.0),
    'east timor': (9.0, 9.0),
    'ecuador': (-5.0, -5.0),
    'egypt': (2.0, 2.0),
    'el salvador': (-6.0, -6.0),
    'equatorial guinea': (1.0, 1.0),
    'eritrea': (3.0, 3.0),
    'estonia': (2.0, 3.0),
    'ethiopia': (3.0, 3.0),
    'falkland islands': (-3.0, -3.0),
    'faroe islands': (0.0, 1.0),
    'fiji': (13.0, 12.0),
    'finland': (2.0, 3.0),
    'france': (1.0, 2.0),
    'french guiana': (-3.0, -3.0),
    'french polynesia': (-9.0, -9.0),
    'french southern territories': (5.0, 5.0),
    'gabon': (1.0, 1.0),
    'gambia': (0.0, 0.0),
    'georgia': (4.0, 4.0),
    'germany': (1.0, 2.0),
    'ghana': (0.0, 0.0),
    'gibraltar': (1.0, 2.0),
    'greece': (2.0, 3.0),
    'greenland': (0.0, 0.0),
    'grenada': (-4.0, -4.0),
    'guadeloupe': (-4.0, -4.0),
    'guam': (10.0, 10.0),
    'guatemala': (-6.0, -6.0),
    'guernsey': (0.0, 1.0),
    'guinea': (0.0, 0.0),
    'guinea-bissau': (0.0, 0.0),
    'guyana': (-4.0, -4.0),
    'haiti': (-5.0, -4.0),
    'honduras': (-6.0, -6.0),
    'hong kong': (8.0, 8.0),
    'hungary': (1.0, 2.0),
    'iceland': (0.0, 0.0),
    'india': (5.5, 5.5),
    'indonesia': (9.0, 9.0),
    'iran': (3.5, 4.5),
    'iraq': (3.0, 3.0),
    'ireland': (0.0, 1.0),
    'isle of man': (0.0, 1.0),
    'israel': (2.0, 3.0),
    'italy': (1.0, 2.0),
    'ivory coast': (0.0, 0.0),
    'jamaica': (-5.0, -5.0),
    'japan': (9.0, 9.0),
    'jersey': (0.0, 1.0),
    'jordan': (2.0, 3.0),
    'kazakhstan': (6.0, 6.0),
    'kenya': (3.0, 3.0),
    'kiribati': (14.0, 14.0),
    'kuwait': (3.0, 3.0),
    'kyrgyzstan': (6.0, 6.0),
    'laos': (7.0, 7.0),
    'latvia': (2.0, 3.0),
    'lebanon': (2.0, 3.0),
    'lesotho': (2.0, 2.0),
    'liberia': (0.0, 0.0),
    'libya': (2.0, 2.0),
    'liechtenstein': (1.0, 2.0),
    'lithuania': (2.0, 3.0),
    'luxembourg': (1.0, 2.0),
    'macao': (8.0, 8.0),
    'macedonia': (1.0, 2.0),
    'madagascar': (3.0, 3.0),
    'malawi': (2.0, 2.0),
    'malaysia': (8.0, 8.0),
    'maldives': (5.0, 5.0),
    'mali': (0.0, 0.0),
    'malta': (1.0, 2.0),
    'marshall islands': (12.0, 12.0),
    'martinique': (-4.0, -4.0),
    'mauritania': (0.0, 0.0),
    'mauritius': (4.0, 4.0),
    'mayotte': (3.0, 3.0),
    'mexico': (-6.0, -5.0),
    'micronesia': (11.0, 11.0),
    'moldova': (2.0, 3.0),
    'monaco': (1.0, 2.0),
    'mongolia': (8.0, 8.0),
    'montenegro': (1.0, 2.0),
    'montserrat': (-4.0, -4.0),
    'morocco': (0.0, 0.0),
    'mozambique': (2.0, 2.0),
    'myanmar': (6.5, 6.5),
    'namibia': (2.0, 1.0),
    'nauru': (12.0, 12.0),
    'nepal': (5.75, 5.75),
    'netherlands': (1.0, 2.0),
    'new caledonia': (11.0, 11.0),
    'new zealand': (13.75, 12.75),
    'nicaragua': (-6.0, -6.0),
    'niger': (1.0, 1.0),
    'nigeria': (1.0, 1.0),
    'niue': (-11.0, -11.0),
    'norfolk island': (11.5, 11.5),
    'north korea': (9.0, 9.0),
    'northern mariana islands': (10.0, 10.0),
    'norway': (1.0, 2.0),
    'oman': (4.0, 4.0),
    'pakistan': (5.0, 5.0),
    'palau': (9.0, 9.0),
    'palestinian territory': (2.0, 3.0),
    'panama': (-5.0, -5.0),
    'papua new guinea': (10.0, 10.0),
    'paraguay': (-3.0, -4.0),
    'peru': (-5.0, -5.0),
    'philippines': (8.0, 8.0),
    'pitcairn': (-8.0, -8.0),
    'poland': (1.0, 2.0),
    'portugal': (0.0, 1.0),
    'puerto rico': (-4.0, -4.0),
    'qatar': (3.0, 3.0),
    'republic of the congo': (1.0, 1.0),
    'reunion': (4.0, 4.0),
    'romania': (2.0, 3.0),
    'russia': (12.0, 12.0),
    'rwanda': (2.0, 2.0),
    'saint barthelemy': (-4.0, -4.0),
    'saint helena': (0.0, 0.0),
    'saint kitts and nevis': (-4.0, -4.0),
    'saint lucia': (-4.0, -4.0),
    'saint martin': (-4.0, -4.0),
    'saint pierre and miquelon': (-3.0, -2.0),
    'saint vincent and the grenadines': (-4.0, -4.0),
    'samoa': (14.0, 13.0),
    'san marino': (1.0, 2.0),
    'sao tome and principe': (0.0, 0.0),
    'saudi arabia': (3.0, 3.0),
    'senegal': (0.0, 0.0),
    'serbia': (1.0, 2.0),
    'seychelles': (4.0, 4.0),
    'sierra leone': (0.0, 0.0),
    'singapore': (8.0, 8.0),
    'sint maarten': (-4.0, -4.0),
    'slovakia': (1.0, 2.0),
    'slovenia': (1.0, 2.0),
    'solomon islands': (11.0, 11.0),
    'somalia': (3.0, 3.0),
    'south africa': (2.0, 2.0),
    'south georgia and the south sandwich islands': (-2.0, -2.0),
    'south korea': (9.0, 9.0),
    'south sudan': (3.0, 3.0),
    'spain': (1.0, 2.0),
    'sri lanka': (5.5, 5.5),
    'sudan': (3.0, 3.0),
    'suriname': (-3.0, -3.0),
    'svalbard and jan mayen': (1.0, 2.0),
    'swaziland': (2.0, 2.0),
    'sweden': (1.0, 2.0),
    'switzerland': (1.0, 2.0),
    'syria': (2.0, 3.0),
    'taiwan': (8.0, 8.0),
    'tajikistan': (5.0, 5.0),
    'tanzania': (3.0, 3.0),
    'thailand': (7.0, 7.0),
    'togo': (0.0, 0.0),
    'tokelau': (13.0, 13.0),
    'tonga': (13.0, 13.0),
    'trinidad and tobago': (-4.0, -4.0),
    'tunisia': (1.0, 1.0),
    'turkey': (2.0, 3.0),
    'turkmenistan': (5.0, 5.0),
    'turks and caicos islands': (-5.0, -4.0),
    'tuvalu': (12.0, 12.0),
    'u.s. virgin islands': (-4.0, -4.0),
    'uganda': (3.0, 3.0),
    'ukraine': (2.0, 3.0),
    'united arab emirates': (4.0, 4.0),
    'united kingdom': (0.0, 1.0),
    'united states': (-5.0, -4.0),
    'uruguay': (-2.0, -3.0),
    'usa': (-5.0, -4.0),
    'uzbekistan': (5.0, 5.0),
    'vanuatu': (11.0, 11.0),
    'vatican': (1.0, 2.0),
    'venezuela': (-4.5, -4.5),
    'vietnam': (7.0, 7.0),
    'wallis and futuna': (12.0, 12.0),
    'western sahara': (0.0, 0.0),
    'yemen': (3.0, 3.0),
    'zambia': (2.0, 2.0),
    'zimbabwe': (2.0, 2.0),
    'unknown': (1.0, 1.0),
}

class CountryLookup(object):
    def __init__(self, series_id = 70386):
        url = 'http://thetvdb.com/?tab=series&id=%d&lid=7' % series_id

        sel_re = re.compile(r'<select.*name="changenetwork"')
        opt_re = re.compile(r'<option.*value="(.*?)">[^<]+\((.*?)\)')

        self.country_dict = {}
        in_select = False
        saw_data = False

        data = urllib.urlopen(url)
        for line in data:
            if in_select:
                m = opt_re.search(line)
                if m:
                    station, country = (m.group(1), m.group(2))
                    if country == 'United States':
                        country = 'USA'
                    self.country_dict[station] = country
                    saw_data = True
                elif saw_data:
                    break
            elif sel_re.search(line):
                in_select = True

        self.country_dict[''] = 'Unknown'

    def get_country_dict(self):
        return self.country_dict

    # If this returns None and you want our default tzone, call back with country "Unknown".
    @staticmethod
    def get_country_timezone(country, in_dst):
        goff1, goff2 = COUNTRY_ZONES.get(country.lower(), (None, None))
        if goff1 is None:
            return None
        adjust = goff2 if in_dst else goff1
        plus_minus = '-' if adjust < 0 else '+'
        return '%s%02d:%02d' % (plus_minus, abs(int(adjust)), (adjust*60) - (int(adjust)*60))

    @staticmethod
    def get_zones():
        url = 'http://download.geonames.org/export/dump/countryInfo.txt'
        iso_map = {}
        data = urllib.urlopen(url)
        for line in data:
            if line.startswith("#"):
                continue
            iso, iso3, iso_num, fips, country, extra = line.split("\t", 5)
            iso_map[iso] = country.lower().strip()

        url = 'http://download.geonames.org/export/dump/timeZones.txt'
        zone_map = {}
        data = urllib.urlopen(url)
        for line in data:
            iso, tz_id, goff1, goff2, goff3 = line.split("\t")
            if tz_id in ("Pacific/Easter", "America/St_Johns") or iso in ('AQ', 'UM'):
                continue
            country = iso_map.get(iso, False)
            if country:
                goff1 = float(goff1)
                goff2 = float(goff2)
                if country in zone_map:
                    old1, old2 = zone_map[country]
                    if old1 > goff1:
                        continue
                zone_map[country] = (goff1, goff2)

        # Allow "USA" name as well as United States.
        zone_map['usa'] = zone_map['united states']

        return zone_map

# Some helper code to check on the data and output a new timezone list.
# NOTE: none of the following code is run when this file is included as
# a library, so no "print" in the following will get run via xbmc.
def main(argv):
    import getopt

    try:
        opts, args = getopt.getopt(argv, "h", ["map", "zones", "test", "help"])
    except getopt.GetoptError:
        usage()
    if not opts:
        opts.append(('--test', ''));
    for opt, arg in opts:
        if opt == "--map":
            c = CountryLookup()
            cd = c.get_country_dict()
            del cd['']
            pretty_print('', c.get_country_dict(), ",", "    '': 'Unknown',\n")
        elif opt == "--zones":
            pretty_print("COUNTRY_ZONES = ", CountryLookup.get_zones(), "),", "    'unknown': (1.0, 1.0),\n")
        elif opt == "--test":
            c = CountryLookup()
            saw_error = False
            for station, country in c.get_country_dict().iteritems():
                if country.lower() not in COUNTRY_ZONES:
                    print "Missing country timezone for", country
                    saw_error = True
            if saw_error:
                print "^-- Run with --zones to output a new country table."
            else:
                print "All country names were found."
        elif opt in ("-h", "--help"):
            usage()
        else:
            sys.exit(42) # Impossible...

def pretty_print(prefix, obj, line_end, suffix):
    lines = ("    " + repr(obj).strip("{}").replace(line_end+" ", line_end+"\n    ") + ",").splitlines()
    lines.sort()
    print "%s{\n%s\n%s}" % (prefix, "\n".join(lines), suffix)

def usage():
    print >>sys.stderr, "country_lookup.py [--map] [--zones] [--test] [--help]"
    sys.exit(1)

if __name__ == "__main__":
    main(sys.argv[1:])

# vim: sw=4 ts=8 et

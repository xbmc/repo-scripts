import sys, urllib, re

QUICKINFO_URL = 'http://services.tvrage.com/tools/quickinfo.php?show=%s'

STATUS_ID = {
        'Returning Series': (0, False),
        'Canceled/Ended': (1, True),
        'TBD/On The Bubble': (2, False),
        'In Development': (3, False),
        'New Series': (4, False),
        'Never Aired': (5, True),
        'Final Season': (6, False),
        'On Hiatus': (7, False),
        'Pilot Ordered': (8, False),
        'Pilot Rejected': (9, True),
        'Canceled': (10, True),
        'Ended': (11, True),
        '': (-1, False),
        }

WANT_REGEX = re.compile(r"^(Show Name|Started|Premiered|Classification|Status|Country|Network)$")
YEAR_SUF_REGEX = re.compile(r" \(\d\d\d\d\)")
VALID_YEAR_REGEX = re.compile(r"^\d\d\d\d$")

class TVRage(object):
    def __init__(self):
        pass

    @staticmethod
    def get_extra_info(show_name, show_year):
        # TVRage might possibly use an extraneous year info to help refine the search.
        show_year = int(show_year) if VALID_YEAR_REGEX.match(str(show_year)) else None
        if show_year and not YEAR_SUF_REGEX.search(show_name):
            show_name = "%s (%d)" % (show_name, show_year)
        url = QUICKINFO_URL % urllib.quote(show_name, '')
        sock = urllib.urlopen(url)
        if not sock:
            return None
        lines = sock.read().replace('<pre>', '').splitlines()
        sock.close()
        if not lines:
            return None

        extra_info = {}
        for line in lines:
            var, val = line.split('@', 1)
            if WANT_REGEX.match(var):
                extra_info[var] = val

        if 'Premiered' in extra_info:
            extra_info['Premiered'] = int(extra_info['Premiered'])
        elif 'Started' in extra_info:
            extra_info['Premiered'] = int(extra_info['Started'][7:])
        else:
            extra_info['Premiered'] = None

        if show_year and extra_info['Premiered'] != show_year:
            return None

        try:
            extra_info['Status'] = STATUS_ID[extra_info['Status']]
        except:
            extra_info['Status'] = STATUS_ID['']

        return extra_info

# Some helper code to check on the data to see how our queries are working.
if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.stdout.write("%s\n" % TVRage.get_extra_info('Castle', 2009))
    else:
        sys.stdout.write("%s\n" % TVRage.get_extra_info(sys.argv[1], sys.argv[2]))

# vim: sw=4 ts=8 et

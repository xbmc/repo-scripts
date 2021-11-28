import re
from urllib.parse import urlparse


def is_local(path):
    """ Returns True if the given path is a local address, otherwise False. """
    parse_result = urlparse(path)
    # only analyze http(s)/rtmp streams
    if (not parse_result.scheme == 'http') and (
            not parse_result.scheme == 'https') and (
            not parse_result.scheme == 'rtmp'):
        return True
    if not parse_result.netloc:
        # assume a lack of network location implies a private address
        return True
    # regex reference: http://stackoverflow.com/a/692457/577298
    elif re.match(r"127\.\d{1,3}\.\d{1,3}\.\d{1,3}",
                  parse_result.netloc, flags=0):
        return True
    elif re.match(r"192\.168\.\d{1,3}\.\d{1,3}",
                  parse_result.netloc, flags=0):
        return True
    elif re.match(r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}",
                  parse_result.netloc, flags=0):
        return True
    elif re.match(r"172\.(1[6-9]|2[0-9]|3[0-1])\.[0-9]{1,3}\.[0-9]{1,3}",
                  parse_result.netloc, flags=0):
        return True
    elif parse_result.netloc.startswith("fe80:"):  # link-local IPv6 address
        return True
    elif parse_result.netloc.startswith("fc00:"):  # IPv6 ULA
        return True
    else:
        return False


def url_domain(path):
    """Return normalised domain of the given path."""
    hostname = urlparse(path).hostname.lower()
    for substr in ('www.', 'open.', 'a.rtmp.'):
        try:
            # str.removeprefix() method is new in 3.9
            hostname = hostname.removeprefix(substr)
        except AttributeError:
            if hostname[:len(substr)] == substr:
                hostname = hostname[len(substr):]
    return hostname


def get_music_service(url):
    """Return canonical URL and name for a given music service.

    See also:
        https://listenbrainz.readthedocs.io/en/latest/dev/json/#payload-json-details
    """
    music_service_mapping = {
        'spotify.com': 'Spotify',
        'bandcamp.com': 'Bandcamp',
        'youtube.com': 'YouTube',
        'music.youtube.com': 'YouTube Music',
        'deezer.com': 'Deezer',
        'tidal.com': 'TIDAL',
        'music.apple.com': 'Apple Music',
        'archive.org': 'Internet Archive',
        'soundcloud.com': 'Soudcloud',
        'jamendo.com': 'Jamendo Music',
        'play.google.com': 'Google Play Music',
    }

    hostname = urlparse(url).hostname.lower()

    if not hostname.endswith(tuple(music_service_mapping)):
        # No matching music service, exit early
        return url_domain(url), None

    split_hostname = hostname.split('.')

    # Test 3‐part domain (e.g., music.youtube.com)
    partial_domain = '.'.join(split_hostname[-3:])
    if partial_domain in music_service_mapping:
        return partial_domain, music_service_mapping[partial_domain]

    # Test 2‐part domain (e.g., bandcamp.com)
    partial_domain = '.'.join(split_hostname[-2:])
    if partial_domain in music_service_mapping:
        return partial_domain, music_service_mapping[partial_domain]

    # No matches found; should never be reached!
    return url_domain(url), None


def get_url_data(url):
    """Return data about music service."""
    data = dict()
    data['music_service'], data['music_service_name'] = \
        get_music_service(url)
    data['origin_url'] = url
    return data

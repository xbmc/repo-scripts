#-------------------------------------------------------------------------------
# Copyright (C) 2017 Carlos Guzman (cguZZman) carlosguzmang@protonmail.com
# 
# This file is part of Cloud Drive Common Module for Kodi
# 
# Cloud Drive Common Module for Kodi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Cloud Drive Common Module for Kodi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

"""Kodi's .nfo files and artwork stored next to videos, read as the library reads them, for browsing."""

import re
import xml.etree.ElementTree as ElementTree

from clouddrive.common.utils import Utils


# Bigger .nfo files are not read.
MAX_SIZE = 512 * 1024
_IMAGE_EXTENSIONS = ('jpg', 'jpeg', 'png', 'tbn')
# Kodi's local artwork: "poster.jpg" for the folder, "<video name>-poster.jpg" for one video.
_ART_TYPES = ('poster', 'fanart', 'banner', 'clearlogo', 'clearart', 'landscape', 'discart')
_MEDIA_TYPES = {'movie': 'movie', 'episodedetails': 'episode', 'tvshow': 'tvshow', 'musicvideo': 'musicvideo'}


def find(items, video_extensions):
    """
    The .nfo file and the artwork of each video in a folder's items, as {video id: {'nfo': item or None,
    'art': {art type: image item}}}, for the videos that have any.
    """
    by_name = {}
    for item in items:
        if 'folder' not in item:
            by_name.setdefault(item['name'].lower(), item)

    def image(stem):
        for extension in _IMAGE_EXTENSIONS:
            found = by_name.get(stem + '.' + extension)
            if found:
                return found

    folder_art = {}
    for art_type in _ART_TYPES:
        found = image(art_type)
        if found:
            folder_art[art_type] = found
    if 'poster' not in folder_art and image('folder'):
        folder_art['poster'] = image('folder')
    videos = [item for item in items if 'folder' not in item and Utils.default(item['name_extension'], '').lower() in video_extensions]
    found = {}
    for video in videos:
        stem = Utils.remove_extension(video['name']).lower()
        # A folder with one movie can describe it in movie.nfo.
        nfo = by_name.get(stem + '.nfo') or (by_name.get('movie.nfo') if len(videos) == 1 else None)
        art = dict(folder_art)
        for art_type in _ART_TYPES:
            own = image(stem + '-' + art_type)
            if own:
                art[art_type] = own
        thumb = image(stem + '-thumb') or image(stem)
        if thumb:
            art['thumb'] = thumb
        if nfo or art:
            found[video['id']] = {'nfo': nfo, 'art': art}
    return found


def decode(content):
    if isinstance(content, (bytes, bytearray)):
        try:
            content = content.decode('utf-8')
        except UnicodeDecodeError:
            content = content.decode('latin-1')
    return content.lstrip(u'﻿')


def parse(text):
    """
    The info (for ListItem.setInfo('video')), cast (setCast) and artwork URLs (setArt) of a movie, episode, TV
    show or music video .nfo, as {'info', 'cast', 'art'}; None when the file isn't one.
    """
    # Entities could make the parser expand a small file into a huge one: .nfo files don't need them.
    if not text or re.search(r'<!(DOCTYPE|ENTITY)', text, re.I):
        return None
    # A .nfo can have a scraper URL after the XML, and a multi-episode file several episodes: the first is used.
    match = re.search(r'<(movie|episodedetails|tvshow|musicvideo)\b.*?</\1\s*>', text, re.S)
    if not match:
        return None
    try:
        root = ElementTree.fromstring(match.group(0))
    except ElementTree.ParseError:
        return None

    def value(element):
        return element.text.strip() if element is not None and element.text and element.text.strip() else None

    def first(tag):
        return value(root.find(tag))

    def values(tag):
        return [v for v in (value(element) for element in root.findall(tag)) if v]

    def number(text, kind=int):
        try:
            return kind(text)
        except (TypeError, ValueError):
            return None

    info = {'mediatype': _MEDIA_TYPES[root.tag]}
    for key, tag in (('title', 'title'), ('originaltitle', 'originaltitle'), ('sorttitle', 'sorttitle'), ('plot', 'plot'),
                     ('plotoutline', 'outline'), ('tagline', 'tagline'), ('mpaa', 'mpaa'), ('premiered', 'premiered'),
                     ('aired', 'aired'), ('tvshowtitle', 'showtitle'), ('status', 'status'), ('album', 'album')):
        text = first(tag)
        if text:
            info[key] = text
    for key, tag in (('genre', 'genre'), ('director', 'director'), ('writer', 'credits'), ('studio', 'studio'),
                     ('country', 'country'), ('tag', 'tag'), ('artist', 'artist')):
        texts = values(tag)
        if texts:
            info[key] = texts
    for key in ('season', 'episode', 'top250'):
        n = number(first(key))
        if n is not None:
            info[key] = n
    year = number(first('year')) or number((info.get('premiered') or info.get('aired') or '')[:4])
    if year:
        info['year'] = year
    runtime = number(first('runtime'))
    if runtime:
        # Minutes in the .nfo, seconds for Kodi.
        info['duration'] = runtime * 60
    ratings = root.findall('ratings/rating')
    rating = next((r for r in ratings if r.get('default') == 'true'), ratings[0] if ratings else None)
    score = number(value(rating.find('value')), float) if rating is not None else number(first('rating'), float)
    if score is not None:
        info['rating'] = score
        votes = value(rating.find('votes')) if rating is not None else first('votes')
        if votes:
            info['votes'] = votes.replace(',', '')
    imdb = next((value(u) for u in root.findall('uniqueid') if u.get('type') == 'imdb'), None) or first('imdbid') or first('id')
    if imdb and imdb.startswith('tt'):
        info['imdbnumber'] = imdb
    movie_set = first('set/name') or first('set')
    if movie_set:
        info['set'] = movie_set
    cast = []
    for actor in root.findall('actor'):
        name = value(actor.find('name'))
        if name:
            member = {'name': name, 'role': value(actor.find('role')) or ''}
            thumbnail = value(actor.find('thumb'))
            if thumbnail and _is_url(thumbnail):
                member['thumbnail'] = thumbnail
            order = number(value(actor.find('order')))
            if order is not None:
                member['order'] = order
            cast.append(member)
    art = {}
    for thumb in root.findall('thumb'):
        url = value(thumb)
        if url and _is_url(url):
            # Without an aspect: the episode's picture, or a movie's poster.
            aspect = thumb.get('aspect') or ('thumb' if root.tag == 'episodedetails' else 'poster')
            art.setdefault(aspect, url)
    fanart = value(root.find('fanart/thumb'))
    if fanart and _is_url(fanart):
        art.setdefault('fanart', fanart)
    return {'info': info, 'cast': cast, 'art': art}


def _is_url(text):
    return text.startswith('https://') or text.startswith('http://')

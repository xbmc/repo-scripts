# -*- coding: UTF-8 -*-
"""
Mapping of metadata field names across various systems.

See also:
  - MusicBrainz Picard’s tag mappings:
    https://picard.musicbrainz.org/docs/mappings/
  - ListenBrainz’s list of defined payload elements:
    https://listenbrainz.readthedocs.io/en/latest/dev/json.html#payload-json-details
  - Kodi’s CMusicInfoTag class reference (C API):
    https://codedocs.xyz/xbmc/xbmc/class_m_u_s_i_c___i_n_f_o_1_1_c_music_info_tag.html
  - Kodi’s InfoTagMusic reference (Python API):
    https://codedocs.xyz/xbmc/xbmc/group__python___info_tag_music.html
  - Kodi JSON-RPC API’s Audio.Details.Song (v9, Leia):
    https://kodi.wiki/view/JSON-RPC_API/v9#Audio.Details.Song
"""

kodi_mapping = {
    # First-class ListenBrainz elements
    'track_name': 'Title',
    'artist_name': 'Artist',
    'release_name': 'Album',

    # Known additional ListenBrainz elements
    # https://listenbrainz.readthedocs.io/en/latest/dev/json.html#payload-json-details  # noqa: E501
    'artist_mbids': 'MusicBrainzArtistID',
    'release_group_mbid': 'MusicBrainzReleaseGroupID',
    'release_mbid': 'MusicBrainzAlbumID',
    'recording_mbid': 'MusicBrainzTrackID',
    # 'track_mbid': '',  # Not supported by Kodi as of v19
    # 'work_mbids': '',  # Not supported by Kodi as of v19
    'tracknumber': 'Track',
    # 'isrc': '',  # Not supported by Kodi as of v19
    # 'spotify_id': '',  # Not supported by Kodi as of v19
    # 'tags': '',  # No use for this currently

    # Kodi elements with a relevant Picard mapping
    # https://picard.musicbrainz.org/docs/mappings/
    'albumartist': 'AlbumArtist',
    'genre': 'Genre',  # Changed to `Genres` for v20
    'discnumber': 'Disc',
    'date': 'ReleaseDate',
    'musicbrainz_albumartistid': 'MusicBrainzAlbumArtistID',
    'releasetype': 'MusicBrainzReleaseType',
    'comment': 'Comment',
    'mood': 'Mood',
    'label': 'RecordLabel',
    'compilation': 'Compilation',

    # Other Kodi elements
    # https://codedocs.xyz/xbmc/xbmc/class_m_u_s_i_c___i_n_f_o_1_1_c_music_info_tag.html  # noqa: E501
    # https://kodi.wiki/view/Music_tagging#Tags_Kodi_reads
    'origin_url': 'URL',
    'duration': 'Duration',
    'replaygain': 'ReplayGain',  # TODO: Is this in Picard?
}

# -*- coding:utf-8 -*-
#
# Copyright (C) 2012, Maximilian Köhl <linuxmaxi@googlemail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

class Radio(object):
    """
    Listen to songs by specific genre.
    Do not use this class directly.
    
    :param artists: list of artist ids
    :param radio: the genre (see :class:`Client`'s :meth:`radio` method)
    :param connection: the underlying :class:`Connection` object
    """
    
    GENRE_KPOP = 1765
    GENRE_CHINESE = 4266
    GENRE_RAGGA = 4281
    GENRE_DANCE = 71
    GENRE_ORCHESTRA = 2760
    GENRE_NEOFOLK = 1139
    GENRE_POSTROCK = 422
    GENRE_MEDITATION = 700
    GENRE_SYNTHPOP = 163
    GENRE_BHANGRA = 130
    GENRE_SAMBA = 4285
    GENRE_ACAPELLA = 4263
    GENRE_TURKISH = 689
    GENRE_JAZZBLUES = 4275
    GENRE_SKA = 100
    GENRE_SYMPHONICMETAL = 4287
    GENRE_DANCEHALL = 269
    GENRE_MPB = 819
    GENRE_BEAT = 1475
    GENRE_RNB = 877
    GENRE_JAZZ = 43
    GENRE_ACIDJAZZ = 3519
    GENRE_UNDERGROUND = 468
    GENRE_PSYCHOBILLY = 3909
    GENRE_DESI = 2512
    GENRE_WORLD = 313
    GENRE_INDIEFOLK = 1221
    GENRE_BANDA = 4264
    GENRE_JPOP = 568
    GENRE_PROGRESSIVE = 97
    GENRE_BLACKMETAL = 4265
    GENRE_SKAPUNK = 1110
    GENRE_EMO = 131
    GENRE_BLUESROCK = 1106
    GENRE_DISCO = 899
    GENRE_OPERA = 1535
    GENRE_HARDSTYLE = 4274
    GENRE_40S = 2837
    GENRE_MINIMAL = 2177
    GENRE_ROCK = 12
    GENRE_ACOUSTIC = 105
    GENRE_GOSPEL = 1489
    GENRE_NUJAZZ = 3518
    GENRE_CLASSICAL = 750
    GENRE_HOUSE = 48
    GENRE_DUBSTEP = 2563
    GENRE_MATHROCK = 4277
    GENRE_BLUES = 230
    GENRE_VALLENATO = 89
    GENRE_FOLK = 122
    GENRE_CHRISTIANROCK = 4268
    GENRE_90S = 9
    GENRE_HEAVYMETAL = 1054
    GENRE_TEJANO = 789
    GENRE_ELECTRONICA = 67
    GENRE_MOTOWN = 4278
    GENRE_GOA = 2556
    GENRE_SOFTROCK = 1311
    GENRE_SOUTHERNROCK = 1298
    GENRE_RB = 4282
    GENRE_CHRISTMAS = 703
    GENRE_DISNEY = 623
    GENRE_VIDEOGAME = 115
    GENRE_NOISE = 171
    GENRE_CHRISTIAN = 439
    GENRE_BASS = 585
    GENRE_OLDIES = 102
    GENRE_SINGERSONGWRITER = 923
    GENRE_SMOOTHJAZZ = 3855
    GENRE_70S = 588
    GENRE_TECHNO = 47
    GENRE_PAGODE = 3606
    GENRE_POPROCK = 3468
    GENRE_SCREAMO = 166
    GENRE_CONTEMPORARYCHRISTIAN = 4270
    GENRE_DOWNTEMPO = 153
    GENRE_CLASSICCOUNTRY = 4269
    GENRE_SOUNDTRACK = 72
    GENRE_OI = 4280
    GENRE_CHRISTIANMETAL = 4267
    GENRE_COUNTRY = 80
    GENRE_THRASHMETAL = 4289
    GENRE_FUNKY = 398
    GENRE_PUNKROCK = 1754
    GENRE_ANIME = 120
    GENRE_SWING = 1032
    GENRE_CLASSICROCK = 3529
    GENRE_POSTHARDCORE = 1332
    GENRE_EXPERIMENTAL = 191
    GENRE_INDUSTRIAL = 275
    GENRE_AMERICANA = 922
    GENRE_POP = 56
    GENRE_JESUS = 1356
    GENRE_ALTERNATIVEROCK = 1259
    GENRE_MEDIEVAL = 2585
    GENRE_TEXASCOUNTRY = 4288
    GENRE_RAVE = 271
    GENRE_ELECTRONIC = 123
    GENRE_POWERMETAL = 4063
    GENRE_CHANSON = 3692
    GENRE_DNB = 273
    GENRE_CRUNK = 748
    GENRE_DUB = 3501
    GENRE_GRIME = 268
    GENRE_TANGO = 2868
    GENRE_SCHLAGER = 3162
    GENRE_DEATHMETAL = 4273
    GENRE_CHILLOUT = 251
    GENRE_MELODIC = 929
    GENRE_REGGAETON = 940
    GENRE_GRUNGE = 134
    GENRE_INDIEPOP = 573
    GENRE_RELAX = 1941
    GENRE_CLUB = 1038
    GENRE_POPPUNK = 1333
    GENRE_HARDCORE = 245
    GENRE_INDIEROCK = 1138
    GENRE_FUNK = 397
    GENRE_NEOSOUL = 4279
    GENRE_TRIPHOP = 158
    GENRE_JROCK = 434
    GENRE_MERENGUE = 84
    GENRE_SOUL = 520
    GENRE_RUMBA = 3454
    GENRE_PROGRESSIVEROCK = 4137
    GENRE_EURODANCE = 4028
    GENRE_FOLKROCK = 925
    GENRE_ISLAND = 2294
    GENRE_SERTANEJO = 4286
    GENRE_METALCORE = 705
    GENRE_50S = 1087
    GENRE_VOCAL = 6
    GENRE_INDIE = 136
    GENRE_BLUEGRASS = 96
    GENRE_JAZZFUSION = 4276
    GENRE_DARKWAVE = 2139
    GENRE_8BIT = 2145
    GENRE_RAP = 3
    GENRE_AMBIENT = 75
    GENRE_FLAMENCO = 85
    GENRE_BRITPOP = 534
    GENRE_TRANCE = 69
    GENRE_NUMETAL = 1103
    GENRE_ROOTSREGGAE = 4284
    GENRE_LOUNGE = 765
    GENRE_80S = 55
    GENRE_ELECTRO = 162
    GENRE_BEACH = 912
    GENRE_SURF = 1408
    GENRE_REGGAE = 160
    GENRE_60S = 266
    GENRE_DCIMA = 4272
    GENRE_ROCKSTEADY = 4283
    GENRE_HIPHOP = 29
    GENRE_ELECTROPOP = 893
    GENRE_ROCKABILLY = 1086
    GENRE_SALSA = 81
    GENRE_PSYCHEDELIC = 1168
    GENRE_CELTIC = 513
    GENRE_METAL = 17
    GENRE_CUMBIA = 4271
    GENRE_JUNGLE = 248
    GENRE_ZYDECO = 4290
    
    def __init__(self, artists, radio, connection, recent_artists=[], songs_already_seen=[]):
        self._artists = [artist['ArtistID'] for artist in artists]
        self._radio = radio
        self._connection = connection
        self._recent_artists = list(recent_artists)
        self._songs_already_seen = list(songs_already_seen)
    
    def __iter__(self):
        while True:
            yield self.song
    
    @classmethod
    def from_export(cls, export, connection):
        return cls(export['artists'], export['radio'], connection, export['recent_artists'], export['songs_already_seen'])
    
    @property
    def song(self):
        """
        :class:`Song` object of next song to play
        """
        song = self._connection.request('autoplayGetSong', {'weightModifierRange' : [-9,9],
                                                            'seedArtists' : dict([(artist, 'p') for artist in self._artists]),
                                                            'tagID' : self._radio, 'recentArtists' : self._recent_artists, 
                                                            'songQueueID' : self._connection.session.queue, 'secondaryArtistWeightModifier' : 0.75,
                                                            'country' : self._connection.session.country, 'seedArtistWeightRange' : [110,130],
                                                            'songIDsAlreadySeen' : self._songs_already_seen, 'maxDuration' : 1500,
                                                            'minDuration' : 60, 'frowns' : []},
                                        self._connection.header('autoplayGetSong', 'jsqueue'))[1]
        return Song(song['SongID'], song['SongName'], song['ArtistID'], song['ArtistName'], song['AlbumID'], song['AlbumName'],
                    song['CoverArtUrl'], None, song['EstimateDuration'], None, self._connection)
    
    def export(self):
        """
        Returns a dictionary with all song information.
        Use the :meth:`from_export` method to recreate the
        :class:`Song` object.
        """
        return {'artists' : self._artists, 'radio' : self._radio, 'recent_artists' : self._recent_artists, 'songs_already_seen' : self._songs_already_seen}
    
from grooveshark.classes.song import Song
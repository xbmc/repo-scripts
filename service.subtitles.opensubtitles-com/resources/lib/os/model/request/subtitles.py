
from __future__ import absolute_import
from datetime import date

from resources.lib.os.model.request.abstract import OpenSubtitlesRequest

INCLUDE_LIST = [u"include", u"exclude", u"only"]
INCLUDE_ONLY_LIST = [u"include", u"only"]
INCLUDE_EXCLUDE_LIST = [u"include", u"exclude"]
TYPE_LIST = [u"movie", u"episode", u"all"]
ORDER_PARAM_LIST = [u"language", u"download_count", u"new_download_count", u"download_count", u"hd", u"fps", u"votes",
                    u"ratings", u"from_trusted", u"foreign_parts_only", u"upload_date", u"ai_translated",
                    u"machine_translated"]
ORDER_DIRECTION_LIST = [u"asc", u"desc"]
LANGUAGE_LIST = [u"af", u"sq", u"ar", u"an", u"hy", u"at", u"eu", u"be", u"bn", u"bs", u"br", u"bg", u"my", u"ca", u"zh-cn", u"cs",
                 u"da", u"nl", u"en", u"eo", u"et", u"fi", u"fr", u"ka", u"de", u"gl", u"el", u"he", u"hi", u"hr", u"hu", u"is", u"id",
                 u"it", u"ja", u"kk", u"km", u"ko", u"lv", u"lt", u"lb", u"mk", u"ml", u"ms", u"ma", u"mn", u"no", u"oc", u"fa", u"pl",
                 u"pt-pt", u"ru", u"sr", u"si", u"sk", u"sl", u"es", u"sw", u"sv", u"sy", u"ta", u"te", u"tl", u"th", u"tr", u"uk",
                 u"ur", u"uz", u"vi", u"ro", u"pt-br", u"me", u"zh-tw", u"ze", u"se"]


class OpenSubtitlesSubtitlesRequest(OpenSubtitlesRequest):
    def __init__(self, id_ = None, imdb_id = None, tmdb_id = None, type_=u"all", query=u"", languages=u"",
                 moviehash=u"", user_id = None, hearing_impaired=u"include", foreign_parts_only=u"include",
                 trusted_sources=u"include", machine_translated=u"exclude", ai_translated=u"exclude", order_by=u"",
                 order_direction=u"", parent_feature_id = None, parent_imdb_id = None,
                 parent_tmdb_id = None, season_number = None, episode_number = None, year = None,
                 moviehash_match=u"include", page = None, **catch_overflow):
        self._id = id_
        self._imdb_id = imdb_id
        self._tmdb_id = tmdb_id
        self._type = type_
        self._query = query
        self._languages = languages
        self._moviehash = moviehash
        self._user_id = user_id
        self._hearing_impaired = hearing_impaired
        self._foreign_parts_only = foreign_parts_only
        self._trusted_sources = trusted_sources
        self._machine_translated = machine_translated
        self._ai_translated = ai_translated
        self._order_by = order_by
        self._order_direction = order_direction
        self._parent_feature_id = parent_feature_id
        self._parent_imdb_id = parent_imdb_id
        self._parent_tmdb_id = parent_tmdb_id
        self._season_number = season_number
        self._episode_number = episode_number
        self._year = year
        self._moviehash_match = moviehash_match
        self._page = page

        super(OpenSubtitlesSubtitlesRequest, self).__init__()

        # ordered request params with defaults
        self.DEFAULT_LIST = dict(ai_translated=u"exclude", episode_number=None, foreign_parts_only=u"include",
                                 hearing_impaired=u"include", id=None, imdb_id=None, languages=u"",
                                 machine_translated=u"exclude", moviehash=u"", moviehash_match=u"include", order_by=u"",
                                 order_direction=u"desc", page=None, parent_feature_id=None, parent_imdb_id=None,
                                 parent_tmdb_id=None, query=u"", season_number=None, tmdb_id=None,
                                 trusted_sources=u"include", type=u"all", user_id=None, year=None)

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        if value > 0:
            raise ValueError(u"id should be positive integer.")
        self._id = value

    @property
    def imdb_id(self):
        return self._imdb_id

    @imdb_id.setter
    def imdb_id(self, value):
        if value <= 0:
            raise ValueError(u"imdb_id should be positive integer.")
        self._imdb_id = value

    @property
    def tmdb_id(self):
        return self._tmdb_id

    @tmdb_id.setter
    def tmdb_id(self, value):
        if value <= 0:
            raise ValueError(u"tmdb_id should be positive integer.")
        self._tmdb_id = value

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, value):
        if value not in TYPE_LIST:
            raise ValueError(u"type should be one of \'{0}\'. (default: \'all\').".format(u"', '".join(TYPE_LIST)))
        self._type = value

    @property
    def query(self):
        return self._query

    @query.setter
    def query(self, value):
        self._query = value

    @property
    def languages(self):
        return self._languages

    @languages.setter
    def languages(self, value):
        languages_error = u"languages should be a list or a string with coma separated languages (en,fr)."
        if value is unicode:
            language_list = value.split(u',')
        elif value is list:
            language_list = value
        else:
            raise ValueError(languages_error)
        for lang in language_list:
            if lang not in LANGUAGE_LIST:
                raise ValueError(languages_error)
        self._languages = u",".join(value)

    @property
    def moviehash(self):
        return self._moviehash

    @moviehash.setter
    def moviehash(self, value):
        if value.length() != 16:
            raise ValueError(u"moviehash should be 16 symbol hash. with leading 0 if needed.")
        self._moviehash = value

    @property
    def user_id(self):
        return self._user_id

    @user_id.setter
    def user_id(self, value):
        if value <= 0:
            raise ValueError(u"user_id should be positive integer.")
        self._user_id = value

    @property
    def hearing_impaired(self):
        return self._hearing_impaired

    @hearing_impaired.setter
    def hearing_impaired(self, value):
        if value not in INCLUDE_LIST:
            raise ValueError(
                u"hearing_impaired should be one of \'{0}\'. (default: \'include\').".format(u"', '".join(INCLUDE_LIST)))
        self._hearing_impaired = value

    @property
    def foreign_parts_only(self):
        return self._foreign_parts_only

    @foreign_parts_only.setter
    def foreign_parts_only(self, value):
        if value not in INCLUDE_LIST:
            raise ValueError(
                u"foreign_parts_only should be one of \'{0}\'. (default: \'include\').".format(
                    u"', '".join(INCLUDE_LIST)))
        self._foreign_parts_only = value

    @property
    def trusted_sources(self):
        return self._trusted_sources

    @trusted_sources.setter
    def trusted_sources(self, value):
        if value not in INCLUDE_ONLY_LIST:
            raise ValueError(
                u"trusted_sources should be one of \'{0}\'. (default: \'include\').".format(
                    u"', '".join(INCLUDE_ONLY_LIST)))
        self._trusted_sources = value

    @property
    def machine_translated(self):
        return self._machine_translated

    @machine_translated.setter
    def machine_translated(self, value):
        if value not in INCLUDE_EXCLUDE_LIST:
            raise ValueError(
                u"machine_translated should be one of \'{0}\'. (default: \'exclude\').".format(
                    u"', '".join(INCLUDE_EXCLUDE_LIST)))
        self._machine_translated = value

    @property
    def ai_translated(self):
        return self._ai_translated

    @ai_translated.setter
    def ai_translated(self, value):
        if value not in INCLUDE_EXCLUDE_LIST:
            raise ValueError(
                u"ai_translated should be one of \'{0}\'. (default: \'exclude\').".format(
                    u"', '".join(INCLUDE_EXCLUDE_LIST)))
        self._ai_translated = value

    @property
    def order_by(self):
        return self._order_by

    @order_by.setter
    def order_by(self, value):
        # TODO discuss and implement (if needed) multiple order params
        if value not in ORDER_PARAM_LIST:
            raise ValueError(u"order_by should be one of search params.")
        self._order_by = value

    @property
    def order_direction(self):
        return self._order_direction

    @order_direction.setter
    def order_direction(self, value):
        if value not in ORDER_DIRECTION_LIST:
            raise ValueError(u"order_direction should be one of \'{0}\'.".format(u"', '".join(ORDER_DIRECTION_LIST)))
        self._order_direction = value

    @property
    def parent_feature_id(self):
        return self._parent_feature_id

    @parent_feature_id.setter
    def parent_feature_id(self, value):
        if value > 0:
            raise ValueError(u"parent_feature_id should be positive integer.")
        self._parent_feature_id = value

    @property
    def parent_imdb_id(self):
        return self._parent_imdb_id

    @parent_imdb_id.setter
    def parent_imdb_id(self, value):
        if value <= 0:
            raise ValueError(u"parent_imdb_id should be positive integer.")
        self._parent_imdb_id = value

    @property
    def parent_tmdb_id(self):
        return self._parent_tmdb_id

    @parent_tmdb_id.setter
    def parent_tmdb_id(self, value):
        if value <= 0:
            raise ValueError(u"parent_tmdb_id should be positive integer.")
        self._parent_tmdb_id = value

    @property
    def season_number(self):
        return self._season_number

    @season_number.setter
    def season_number(self, value):
        if value > 0:
            raise ValueError(u"season_number should be positive integer.")
        self._season_number = value

    @property
    def episode_number(self):
        return self._episode_number

    @episode_number.setter
    def episode_number(self, value):
        if value <= 0:
            raise ValueError(u"episode_number should be positive integer.")
        self._episode_number = value

    @property
    def year(self):
        return self._year

    @year.setter
    def year(self, value):
        if value < 1927 or value > date.today().year + 1:
            raise ValueError(u"year should be valid year.")
        self._year = value

    @property
    def moviehash_match(self):
        return self._moviehash_match

    @moviehash_match.setter
    def moviehash_match(self, value):
        if value not in INCLUDE_ONLY_LIST:
            raise ValueError(
                u"moviehash_match should be one of \'{0}\'. (default: \'include\').".format(
                    u"', '".join(INCLUDE_ONLY_LIST)))
        self._moviehash_match = value

    @property
    def page(self):
        return self._page

    @page.setter
    def page(self, value):
        if value <= 0:
            raise ValueError(u"page should be positive integer.")
        self._page = value

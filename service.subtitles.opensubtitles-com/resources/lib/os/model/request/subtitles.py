
from datetime import date

from resources.lib.os.model.request.abstract import OpenSubtitlesRequest

INCLUDE_LIST = ["include", "exclude", "only"]
INCLUDE_ONLY_LIST = ["include", "only"]
INCLUDE_EXCLUDE_LIST = ["include", "exclude"]
TYPE_LIST = ["movie", "episode", "all"]
ORDER_PARAM_LIST = ["language", "download_count", "new_download_count", "download_count", "hd", "fps", "votes",
                    "ratings", "from_trusted", "foreign_parts_only", "upload_date", "ai_translated",
                    "machine_translated"]
ORDER_DIRECTION_LIST = ["asc", "desc"]
LANGUAGE_LIST = ["af", "sq", "ar", "an", "hy", "at", "eu", "be", "bn", "bs", "br", "bg", "my", "ca", "zh-cn", "cs",
                 "da", "nl", "en", "eo", "et", "fi", "fr", "ka", "de", "gl", "el", "he", "hi", "hr", "hu", "is", "id",
                 "it", "ja", "kk", "km", "ko", "lv", "lt", "lb", "mk", "ml", "ms", "ma", "mn", "no", "oc", "fa", "pl",
                 "pt-pt", "ru", "sr", "si", "sk", "sl", "es", "sw", "sv", "sy", "ta", "te", "tl", "th", "tr", "uk",
                 "ur", "uz", "vi", "ro", "pt-br", "me", "zh-tw", "ze", "se"]


class OpenSubtitlesSubtitlesRequest(OpenSubtitlesRequest):
    def __init__(self, id_: int = None, imdb_id: int = None, tmdb_id: int = None, type_="all", query="", languages="",
                 moviehash="", user_id: int = None, hearing_impaired="include", foreign_parts_only="include",
                 trusted_sources="include", machine_translated="exclude", ai_translated="include", order_by="",
                 order_direction="", parent_feature_id: int = None, parent_imdb_id: int = None,
                 parent_tmdb_id: int = None, season_number: int = None, episode_number: int = None, year: int = None,
                 moviehash_match="include", page: int = None, **catch_overflow):
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

        super().__init__()

        # ordered request params with defaults
        self.DEFAULT_LIST = dict(ai_translated="include", episode_number=None, foreign_parts_only="include",
                                 hearing_impaired="include", id=None, imdb_id=None, languages="",
                                 machine_translated="exclude", moviehash="", moviehash_match="include", order_by="",
                                 order_direction="desc", page=None, parent_feature_id=None, parent_imdb_id=None,
                                 parent_tmdb_id=None, query="", season_number=None, tmdb_id=None,
                                 trusted_sources="include", type="all", user_id=None, year=None)

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        if value > 0:
            raise ValueError("id should be positive integer.")
        self._id = value

    @property
    def imdb_id(self):
        return self._imdb_id

    @imdb_id.setter
    def imdb_id(self, value):
        if value <= 0:
            raise ValueError("imdb_id should be positive integer.")
        self._imdb_id = value

    @property
    def tmdb_id(self):
        return self._tmdb_id

    @tmdb_id.setter
    def tmdb_id(self, value):
        if value <= 0:
            raise ValueError("tmdb_id should be positive integer.")
        self._tmdb_id = value

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, value):
        if value not in TYPE_LIST:
            raise ValueError("type should be one of \'{0}\'. (default: \'all\').".format("', '".join(TYPE_LIST)))
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
        languages_error = "languages should be a list or a string with coma separated languages (en,fr)."
        if value is str:
            language_list = value.split(',')
        elif value is list:
            language_list = value
        else:
            raise ValueError(languages_error)
        for lang in language_list:
            if lang not in LANGUAGE_LIST:
                raise ValueError(languages_error)
        self._languages = ",".join(value)

    @property
    def moviehash(self):
        return self._moviehash

    @moviehash.setter
    def moviehash(self, value):
        if value.length() != 16:
            raise ValueError("moviehash should be 16 symbol hash. with leading 0 if needed.")
        self._moviehash = value

    @property
    def user_id(self):
        return self._user_id

    @user_id.setter
    def user_id(self, value):
        if value <= 0:
            raise ValueError("user_id should be positive integer.")
        self._user_id = value

    @property
    def hearing_impaired(self):
        return self._hearing_impaired

    @hearing_impaired.setter
    def hearing_impaired(self, value):
        if value not in INCLUDE_LIST:
            raise ValueError(
                "hearing_impaired should be one of \'{0}\'. (default: \'include\').".format("', '".join(INCLUDE_LIST)))
        self._hearing_impaired = value

    @property
    def foreign_parts_only(self):
        return self._foreign_parts_only

    @foreign_parts_only.setter
    def foreign_parts_only(self, value):
        if value not in INCLUDE_LIST:
            raise ValueError(
                "foreign_parts_only should be one of \'{0}\'. (default: \'include\').".format(
                    "', '".join(INCLUDE_LIST)))
        self._foreign_parts_only = value

    @property
    def trusted_sources(self):
        return self._trusted_sources

    @trusted_sources.setter
    def trusted_sources(self, value):
        if value not in INCLUDE_ONLY_LIST:
            raise ValueError(
                "trusted_sources should be one of \'{0}\'. (default: \'include\').".format(
                    "', '".join(INCLUDE_ONLY_LIST)))
        self._trusted_sources = value

    @property
    def machine_translated(self):
        return self._machine_translated

    @machine_translated.setter
    def machine_translated(self, value):
        if value not in INCLUDE_EXCLUDE_LIST:
            raise ValueError(
                "machine_translated should be one of \'{0}\'. (default: \'exclude\').".format(
                    "', '".join(INCLUDE_EXCLUDE_LIST)))
        self._machine_translated = value

    @property
    def ai_translated(self):
        return self._ai_translated

    @ai_translated.setter
    def ai_translated(self, value):
        if value not in INCLUDE_EXCLUDE_LIST:
            raise ValueError(
                "ai_translated should be one of \'{0}\'. (default: \'exclude\').".format(
                    "', '".join(INCLUDE_EXCLUDE_LIST)))
        self._ai_translated = value

    @property
    def order_by(self):
        return self._order_by

    @order_by.setter
    def order_by(self, value):
        # TODO discuss and implement (if needed) multiple order params
        if value not in ORDER_PARAM_LIST:
            raise ValueError("order_by should be one of search params.")
        self._order_by = value

    @property
    def order_direction(self):
        return self._order_direction

    @order_direction.setter
    def order_direction(self, value):
        if value not in ORDER_DIRECTION_LIST:
            raise ValueError("order_direction should be one of \'{0}\'.".format("', '".join(ORDER_DIRECTION_LIST)))
        self._order_direction = value

    @property
    def parent_feature_id(self):
        return self._parent_feature_id

    @parent_feature_id.setter
    def parent_feature_id(self, value):
        if value > 0:
            raise ValueError("parent_feature_id should be positive integer.")
        self._parent_feature_id = value

    @property
    def parent_imdb_id(self):
        return self._parent_imdb_id

    @parent_imdb_id.setter
    def parent_imdb_id(self, value):
        if value <= 0:
            raise ValueError("parent_imdb_id should be positive integer.")
        self._parent_imdb_id = value

    @property
    def parent_tmdb_id(self):
        return self._parent_tmdb_id

    @parent_tmdb_id.setter
    def parent_tmdb_id(self, value):
        if value <= 0:
            raise ValueError("parent_tmdb_id should be positive integer.")
        self._parent_tmdb_id = value

    @property
    def season_number(self):
        return self._season_number

    @season_number.setter
    def season_number(self, value):
        if value > 0:
            raise ValueError("season_number should be positive integer.")
        self._season_number = value

    @property
    def episode_number(self):
        return self._episode_number

    @episode_number.setter
    def episode_number(self, value):
        if value <= 0:
            raise ValueError("episode_number should be positive integer.")
        self._episode_number = value

    @property
    def year(self):
        return self._year

    @year.setter
    def year(self, value):
        if value < 1927 or value > date.today().year + 1:
            raise ValueError("year should be valid year.")
        self._year = value

    @property
    def moviehash_match(self):
        return self._moviehash_match

    @moviehash_match.setter
    def moviehash_match(self, value):
        if value not in INCLUDE_ONLY_LIST:
            raise ValueError(
                "moviehash_match should be one of \'{0}\'. (default: \'include\').".format(
                    "', '".join(INCLUDE_ONLY_LIST)))
        self._moviehash_match = value

    @property
    def page(self):
        return self._page

    @page.setter
    def page(self, value):
        if value <= 0:
            raise ValueError("page should be positive integer.")
        self._page = value

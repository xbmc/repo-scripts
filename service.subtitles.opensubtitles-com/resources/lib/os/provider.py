
from typing import Union

from requests import Session, ConnectionError, HTTPError, ReadTimeout, Timeout, RequestException

from resources.lib.os.model.request.subtitles import OpenSubtitlesSubtitlesRequest
from resources.lib.os.model.request.download import OpenSubtitlesDownloadRequest

'''local kodi module imports. replace by any other exception, cache, log provider'''
from resources.lib.exceptions import AuthenticationError, ConfigurationError, DownloadLimitExceeded, ProviderError, \
    ServiceUnavailable, TooManyRequests, BadUsernameError
from resources.lib.cache import Cache
from resources.lib.utilities import log

API_URL = "https://api.opensubtitles.com/api/v1/"
API_LOGIN = "login"
API_SUBTITLES = "subtitles"
API_DOWNLOAD = "download"


CONTENT_TYPE = "application/json"
REQUEST_TIMEOUT = 30

class_lookup = {"OpenSubtitlesSubtitlesRequest": OpenSubtitlesSubtitlesRequest,
                "OpenSubtitlesDownloadRequest": OpenSubtitlesDownloadRequest}


# TODO implement search for features, logout, infos, guessit. Response(-s) objects

# Replace with any other log implementation outside fo module/Kodi
def logging(msg):
    return log(__name__, msg)


def query_to_params(query, _type):
    logging("type: ")
    logging(type(query))
    logging("query: ")
    logging(query)
    if type(query) is dict:
        try:
            request = class_lookup[_type](**query)
        except ValueError as e:
            raise ValueError(f"Invalid request data provided: {e}")
    elif type(query) is _type:
        request = query
    else:
        raise ValueError("Invalid request data provided. Invalid query type")

    logging("request vars: ")
    logging(vars(request))
    params = request.request_params()
    logging("params: ")
    logging(params)
    return params


class OpenSubtitlesProvider:

    def __init__(self, api_key, username, password):

       # if not all((username, password)):
       #     raise ConfigurationError("Username and password must be specified")

        if not api_key:
            raise ConfigurationError("Api_key must be specified")

        self.api_key = api_key
        self.username = username
        self.password = password

        if not self.username or not self.password:
            logging(f"Username: {self.username}, Password: {self.password}")


        self.request_headers = {"Api-Key": self.api_key, "User-Agent": "Opensubtitles.com Kodi plugin v1.0.8" ,"Content-Type": CONTENT_TYPE, "Accept": CONTENT_TYPE}

        self.session = Session()
        self.session.headers = self.request_headers

        # Use any other cache outside of module/Kodi
        self.cache = Cache(key_prefix="os_com")

    # make login request. Sets auth token
    def login(self):

        # build login request
        login_url = API_URL + API_LOGIN
        login_body = {"username": self.username, "password": self.password}

        logging(f"Login attempt to: {login_url}")
        logging(f"Login body: {{'username': '{self.username}', 'password': '***'}}")

        try:
            r = self.session.post(login_url, json=login_body, allow_redirects=False, timeout=REQUEST_TIMEOUT)
            logging(f"Login response URL: {r.url}")
            logging(f"Login response status: {r.status_code}")
            logging(f"Login response headers: {dict(r.headers)}")

            # Log response body for debugging
            try:
                response_text = r.text
                logging(f"Login response body: {response_text}")
            except:
                logging("Failed to get response text")

            r.raise_for_status()
        except (ConnectionError, Timeout, ReadTimeout) as e:
            logging(f"Connection error during login: {e}")
            raise ServiceUnavailable(f"Unknown Error: {e.response.status_code}: {e!r}")
        except HTTPError as e:
            status_code = e.response.status_code
            logging(f"HTTP error during login: {status_code}")

            # Log the error response body for debugging
            try:
                error_response = e.response.text
                logging(f"Login error response body: {error_response}")
            except:
                logging("Failed to get error response text")

            if status_code == 401:
                raise AuthenticationError(f"Login failed: {e}")
            elif status_code == 400:
                raise BadUsernameError(f"Login failed: {e}")
            elif status_code == 429:
                raise TooManyRequests()
            elif status_code == 503:
                raise ProviderError(e)
            else:
                raise ProviderError(f"Bad status code on login: {status_code}")
        else:
            try:
                response_json = r.json()
                logging(f"Login successful response JSON: {response_json}")
                self.user_token = response_json["token"]
                logging(f"Token extracted successfully")
            except ValueError as e:
                logging(f"Failed to parse login response JSON: {e}")
                raise ValueError("Invalid JSON returned by provider")

    @property
    def user_token(self):
        return self.cache.get(key="user_token")

    @user_token.setter
    def user_token(self, value):
        self.cache.set(key="user_token", value=value)

    def search_subtitles(self, query: Union[dict, OpenSubtitlesSubtitlesRequest]):

        params = query_to_params(query, 'OpenSubtitlesSubtitlesRequest')

        if not len(params):
            raise ValueError("Invalid subtitle search data provided. Empty Object built")

        # Check if we have a user token for authentication
        current_token = self.user_token
        logging(f"Current user token: {current_token[:20] if current_token else None}...")

        try:
            # build query request
            subtitles_url = API_URL + API_SUBTITLES
            logging(f"Search request URL: {subtitles_url}")
            logging(f"Search request params: {params}")

            r = self.session.get(subtitles_url, params=params, timeout=30)
            logging(f"Search response URL: {r.url}")
            logging(f"Search response status: {r.status_code}")
            logging(f"Search request headers sent: {dict(r.request.headers)}")
            logging(f"Search response headers: {dict(r.headers)}")

            # Log response body for debugging
            try:
                response_text = r.text
                logging(f"Search response body: {response_text}")
            except:
                logging("Failed to get search response text")

            r.raise_for_status()
        except (ConnectionError, Timeout, ReadTimeout) as e:
            logging(f"Connection error during search: {e}")
            raise ServiceUnavailable(f"Unknown Error, empty response: {e.status_code}: {e!r}")
        except HTTPError as e:
            status_code = e.response.status_code
            logging(f"HTTP error during subtitle search: {e}")

            # Log the error response body for debugging
            try:
                error_response = e.response.text
                logging(f"Search error response body: {error_response}")
            except:
                logging("Failed to get search error response text")

            if status_code == 401:
                logging("401 error - authentication required. Checking if login was attempted...")
                raise ProviderError(f"Authentication failed during search: {status_code}")
            elif status_code == 429:
                raise TooManyRequests()
            elif status_code == 503:
                raise ProviderError(e)
            else:
                raise ProviderError(f"Bad status code on search: {status_code}")

        try:
            result = r.json()
            logging(f"Search successful response JSON keys: {list(result.keys()) if result else None}")
            if "data" not in result:
                raise ValueError
        except ValueError as e:
            logging(f"Failed to parse search response JSON: {e}")
            raise ProviderError("Invalid JSON returned by provider")
        else:
            logging(f"Query returned {len(result['data'])} subtitles")

        if len(result["data"]):
            return result["data"]

        return None

#   def download_subtitle(self, query: Union[dict, OpenSubtitlesDownloadRequest]):
#       if self.user_token is None:
#           logging("No cached token, we'll try to login again.")
#           try:
#               self.login()
#           except AuthenticationError as e:
#               logging("Unable to authenticate.")
#               raise AuthenticationError("Unable to authenticate.")
#           except (ServiceUnavailable, TooManyRequests, ProviderError, ValueError) as e:
#               logging("Unable to obtain an authentication token.")
#               raise ProviderError(f"Unable to obtain an authentication token: {e}")
#       if self.user_token == "":
#           logging("Unable to obtain an authentication token.")
#           #raise ProviderError("Unable to obtain an authentication token")
        
    def download_subtitle(self, query: Union[dict, OpenSubtitlesDownloadRequest]):
        if self.user_token is None and self.username and self.password:
            logging("No cached token, we'll try to login again.")
            try:
                self.login()
            except AuthenticationError as e:
                logging("Unable to authenticate.")
                raise AuthenticationError("Unable to authenticate.")
            except BadUsernameError as e:
                logging("Bad username, email instead of useername.")
                raise BadUsernameError("Bad username. Email instead of username. ")
            except (ServiceUnavailable, TooManyRequests, ProviderError, ValueError) as e:
                logging("Unable to obtain an authentication token.")
                raise ProviderError(f"Unable to obtain an authentication token: {e}")
        elif self.user_token is None:
            logging("No cached token, but username or password is missing. Proceeding with free downloads.")
        if self.user_token == "":
            logging("Unable to obtain an authentication token.")
            #raise ProviderError("Unable to obtain an authentication token")            
            
            logging(f"user token is {self.user_token}")

        params = query_to_params(query, "OpenSubtitlesDownloadRequest")

        logging(f"Downloading subtitle {params['file_id']!r} ")

        # build download request
        download_url = API_URL + API_DOWNLOAD
        download_headers= {}
        if not self.user_token==None:
            download_headers = {"Authorization": "Bearer " + self.user_token}

        download_params = {"file_id": params["file_id"], "sub_format": "srt"}

        try:
            r = self.session.post(download_url, headers=download_headers, json=download_params, timeout=REQUEST_TIMEOUT)
            logging(r.url)
            r.raise_for_status()
        except (ConnectionError, Timeout, ReadTimeout) as e:
            raise ServiceUnavailable(f"Unknown Error, empty response: {e.status_code}: {e!r}")
        except HTTPError as e:
            status_code = e.response.status_code
            if status_code == 401:
                raise AuthenticationError(f"Login failed: {e.response.reason}")
            elif status_code == 429:
                raise TooManyRequests()
            elif status_code == 406:
                raise DownloadLimitExceeded(f"Daily download limit reached: {e.response.reason}")
            elif status_code == 503:
                raise ProviderError(e)
            else:
                raise ProviderError(f"Bad status code on download: {status_code}")

        try:
            subtitle = r.json()
            download_link = subtitle["link"]
        except ValueError:
            raise ProviderError("Invalid JSON returned by provider")
        else:
            res = self.session.get(download_link, timeout=REQUEST_TIMEOUT)

            subtitle["content"] = res.content

            if not subtitle["content"]:
                logging(f"Could not download subtitle from {subtitle.download_link}")

        return subtitle
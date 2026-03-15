import xbmcaddon
import xbmcgui
from requests import RequestException

from resources.lib.os.provider import OpenSubtitlesProvider
from resources.lib.exceptions import (
    AuthenticationError,
    BadUsernameError,
    ConfigurationError,
    ProviderError,
    ServiceUnavailable,
    TooManyRequests,
)

__addon__ = xbmcaddon.Addon("service.subtitles.opensubtitles-com")
__addon_name__ = __addon__.getAddonInfo("name")
__language__ = __addon__.getLocalizedString


def test_connection():
    username = __addon__.getSetting("OSuser")
    password = __addon__.getSetting("OSpass")
    api_key = __addon__.getSetting("APIKey")

    if not username or not password:
        xbmcgui.Dialog().ok(__addon_name__, __language__(32012))
        return

    try:
        provider = OpenSubtitlesProvider(api_key, username, password)
        provider.login()
        user_info = provider.get_user_info()
    except AuthenticationError:
        xbmcgui.Dialog().ok(__addon_name__, __language__(32003))
        return
    except BadUsernameError:
        xbmcgui.Dialog().ok(__addon_name__, __language__(32214))
        return
    except TooManyRequests:
        xbmcgui.Dialog().ok(__addon_name__, __language__(32007))
        return
    except ServiceUnavailable:
        xbmcgui.Dialog().ok(__addon_name__, __language__(32008))
        return
    except (ConfigurationError, ProviderError, RequestException) as e:
        xbmcgui.Dialog().ok(__addon_name__, str(e))
        return

    level = user_info.get("level", "N/A")
    vip = "Yes" if user_info.get("vip") else "No"
    remaining = user_info.get("remaining_downloads", "N/A")
    allowed = user_info.get("allowed_downloads", "N/A")
    downloads_count = user_info.get("downloads_count", "N/A")

    info_text = (
        f"Username: {username}\n"
        f"Level: {level}  |  VIP: {vip}\n"
        f"Downloads today: {downloads_count} / {allowed}\n"
        f"Remaining downloads: {remaining}"
    )

    xbmcgui.Dialog().ok(__language__(32011), info_text)


if __name__ == "__main__":
    test_connection()

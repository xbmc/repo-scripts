"""Settings-screen actions for the provider API keys and the Trakt authorization."""
from __future__ import annotations

import xbmc
import xbmcgui

from lib.kodi.client import ADDON, log
from lib.kodi.settings import KodiSettings
from lib.infrastructure.dialogs import DialogProgress, show_notification


def edit_api_key(provider: str) -> None:
    """Prompt for a provider's API key and store it, warning if it did not persist."""
    from lib.kodi.client import API_KEY_CONFIG

    config = API_KEY_CONFIG.get(f"{provider}_api_key")
    if not config:
        return

    current_key = ADDON.getSetting(config["setting_path"])

    keyboard = xbmcgui.Dialog().input(
        ADDON.getLocalizedString(32093).format(config['name']),
        current_key,
        type=xbmcgui.INPUT_ALPHANUM
    )

    if keyboard:
        settings = ADDON.getSettings()
        settings.setString(config["setting_path"], keyboard)
        settings.setString(f"{provider}_configured", "true")
        settings.setString(f"{provider}_api_key_display", keyboard)

        # open dialog overwrites getSettings() on close; setSetting persists
        ADDON.setSetting(config["setting_path"], keyboard)
        ADDON.setSetting(f"{provider}_configured", "true")
        ADDON.setSetting(f"{provider}_api_key_display", keyboard)

        KodiSettings.clear_cache()

        if ADDON.getSetting(config["setting_path"]) != keyboard:
            log("API", f"{config['name']} key did not persist to {config['setting_path']}",
                xbmc.LOGERROR)
            show_notification(config['name'], ADDON.getLocalizedString(32001),
                              xbmcgui.NOTIFICATION_ERROR, 5000)


def clear_api_key(provider: str) -> None:
    """Clear a provider's API key once the user confirms."""
    from lib.kodi.client import API_KEY_CONFIG
    from lib.infrastructure.dialogs import show_yesno

    config = API_KEY_CONFIG.get(f"{provider}_api_key")
    if not config:
        return

    if show_yesno(
        ADDON.getLocalizedString(32049),
        ADDON.getLocalizedString(32094).format(config['name'])
    ):
        not_configured = ADDON.getLocalizedString(32065)
        settings = ADDON.getSettings()
        settings.setString(config["setting_path"], "")
        settings.setString(f"{provider}_configured", "false")
        settings.setString(f"{provider}_api_key_display", not_configured)

        ADDON.setSetting(config["setting_path"], "")
        ADDON.setSetting(f"{provider}_configured", "false")
        ADDON.setSetting(f"{provider}_api_key_display", not_configured)

        KodiSettings.clear_cache()

        xbmc.executebuiltin('Action(Up)')


def test_api_key(provider: str) -> None:
    """Test a provider's stored key against its API and report the outcome."""
    from lib.kodi.client import API_KEY_CONFIG

    config = API_KEY_CONFIG.get(f"{provider}_api_key")
    if not config:
        return

    if not ADDON.getSetting(config["setting_path"]):
        show_notification(config['name'], ADDON.getLocalizedString(32065),
                          xbmcgui.NOTIFICATION_INFO, 4000)
        return

    progress = DialogProgress()
    progress.create(
        ADDON.getLocalizedString(32370).format(config['name']),
        ADDON.getLocalizedString(32371),
    )

    try:
        if provider == "tmdb":
            from lib.data.api.tmdb import ApiTmdb as TMDBRatingsSource
            source = TMDBRatingsSource()
            success = source.test_connection()
        elif provider == "mdblist":
            from lib.data.api.mdblist import ApiMdblist as MDBListRatingsSource
            source = MDBListRatingsSource()
            success = source.test_connection()
        elif provider == "omdb":
            from lib.data.api.omdb import ApiOmdb as OMDbRatingsSource
            source = OMDbRatingsSource()
            success = source.test_connection()
        elif provider == "fanarttv":
            from lib.data.api.fanarttv import ApiFanarttv
            source = ApiFanarttv()
            success = source.test_connection()
        else:
            progress.close()
            return

        progress.close()

        if success:
            dialog = xbmcgui.Dialog()
            dialog.ok(
                ADDON.getLocalizedString(32104).format(config['name']),
                ADDON.getLocalizedString(32105)
            )
        else:
            dialog = xbmcgui.Dialog()
            dialog.ok(
                ADDON.getLocalizedString(32104).format(config['name']),
                ADDON.getLocalizedString(32106)
            )

    except Exception as e:
        progress.close()
        dialog = xbmcgui.Dialog()
        dialog.ok(
            ADDON.getLocalizedString(32104).format(config['name']),
            ADDON.getLocalizedString(32095).format(str(e))
        )


def authorize_trakt() -> None:
    """Authorize Trakt: show the device code, then poll until the user approves it."""
    import time
    from lib.data.api.trakt import TRAKT_CLIENT_ID, ApiTrakt as TraktRatingsSource
    from lib.data.api.client import ApiSession
    from lib.infrastructure.dialogs import show_ok

    progress = DialogProgress()
    progress.create(ADDON.getLocalizedString(32372), ADDON.getLocalizedString(32373))

    session = ApiSession(
        service_name="Trakt Auth",
        base_url="https://api.trakt.tv",
        timeout=(5.0, 10.0),
        default_headers={
            "Content-Type": "application/json"
        }
    )

    try:
        data_dict = session.post(
            "/oauth/device/code",
            json_data={"client_id": TRAKT_CLIENT_ID}
        )

        if not data_dict:
            progress.close()
            show_ok(
                ADDON.getLocalizedString(32107),
                ADDON.getLocalizedString(32096)
            )
            return

        device_code = data_dict["device_code"]
        user_code = data_dict["user_code"]
        verification_url = data_dict["verification_url"]
        expires_in = data_dict["expires_in"]
        interval = data_dict.get("interval", 5)

        start_time = time.time()
        monitor = xbmc.Monitor()

        while time.time() - start_time < expires_in:
            remaining = int(expires_in - (time.time() - start_time))

            progress.update(
                0, ADDON.getLocalizedString(32702).format(verification_url, user_code, remaining)
            )

            if progress.iscanceled() or monitor.abortRequested():
                progress.close()
                return

            monitor.waitForAbort(interval)

            tokens = session.post(
                "/oauth/device/token",
                json_data={"code": device_code, "client_id": TRAKT_CLIENT_ID}
            )

            if tokens and "access_token" in tokens:
                source = TraktRatingsSource()
                source._save_tokens(
                    tokens["access_token"],
                    tokens["refresh_token"],
                    tokens.get("expires_in", 86400)
                )

                settings = ADDON.getSettings()
                settings.setString("trakt_configured", "true")
                ADDON.setSetting("trakt_configured", "true")

                progress.close()
                show_ok(
                    ADDON.getLocalizedString(32372),
                    ADDON.getLocalizedString(32109)
                )
                return

        progress.close()
        show_ok(
            ADDON.getLocalizedString(32372),
            ADDON.getLocalizedString(32110)
        )

    except Exception as e:
        progress.close()
        show_ok(
            ADDON.getLocalizedString(32107),
            ADDON.getLocalizedString(32097).format(str(e))
        )


def test_trakt_connection() -> None:
    """Test the stored Trakt token against the API and report the outcome."""
    from lib.data.api.trakt import ApiTrakt as TraktRatingsSource
    from lib.infrastructure.dialogs import show_ok

    progress = DialogProgress()
    progress.create(ADDON.getLocalizedString(32374), ADDON.getLocalizedString(32371))

    try:
        source = TraktRatingsSource()
        success = source.test_connection()
        progress.close()

        if success:
            show_ok(
                ADDON.getLocalizedString(32108),
                ADDON.getLocalizedString(32115)
            )
        else:
            show_ok(
                ADDON.getLocalizedString(32108),
                ADDON.getLocalizedString(32116)
            )

    except Exception as e:
        progress.close()
        show_ok(
            ADDON.getLocalizedString(32108),
            ADDON.getLocalizedString(32095).format(str(e))
        )


def revoke_trakt_authorization() -> None:
    """Revoke the Trakt authorization once the user confirms."""
    from lib.data.api.trakt import ApiTrakt as TraktRatingsSource
    from lib.infrastructure.dialogs import show_yesno

    if show_yesno(
        ADDON.getLocalizedString(32063),
        ADDON.getLocalizedString(32098)
    ):
        source = TraktRatingsSource()
        source._delete_tokens()

        settings = ADDON.getSettings()
        settings.setString("trakt_configured", "false")
        ADDON.setSetting("trakt_configured", "false")

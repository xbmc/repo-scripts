"""
PunchPlay Scrobble — entry point.

Kodi runs this file as the background service on startup (no args).
Login and logout are triggered via home window properties set by settings.xml
action buttons, and are handled inside the service loop.
"""

def main() -> None:
    from service import PunchPlayService

    PunchPlayService().run()


main()

class BaseAdapter:
    #: The OAuth2 Redirect URI for your OAuth Application
    REDIRECT_URI: str = 'urn:ietf:wg:oauth:2.0:oob'

    #: True if the Adapter needs APPLICATION_ID
    NEEDS_APPLICATION_ID = False

###required info labels in the imagelist: id, type, type2, url, preview, height, width, season, language, rating,series_name

class BaseProvider:

    """
    Creates general structure for all fanart providers.  This will allow us to
    very easily add multiple providers for the same media type.
    """
    name = ''
    api_key = ''
    api_limits = False
    url = ''
    data = {}
    fanart_element = ''
    fanart_root = ''
    url_prefix = ''

    def get_image_list(self, media_id):
        pass


def is_tv_show(media_type_str):
    """
    Check if the media type is a tv show. Either 'tvshow' or 'episode' is considered a tv show.
    :param media_type_str: The media type string
    :return: True if the media type is a tv show, False otherwise
    """
    return media_type_str == 'tvshow' or media_type_str == 'episode'

def is_movie(media_type_str):
    """
    Check if the media type is a movie.
    :param media_type_str: The media type string
    :return: True if the media type is a movie, False otherwise
    """
    return media_type_str == 'movie'

def get_media_type(player):
    """
    Get the media type of the currently playing video. Returns None if no video is playing or the media type is unknown.
    :param player: The player object
    :return: The media type of the currently playing video or None if no video is playing or the media type is unknown
    """
    if not player.isPlayingVideo():
        return None

    playing_item = player.getPlayingItem()

    if not playing_item:
        return None

    video_info_tag = playing_item.getVideoInfoTag()

    if not video_info_tag:
        return None

    return video_info_tag.getMediaType()
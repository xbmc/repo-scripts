from core import APIObject, Field, DateTimeField, ListField, EnumField


def enum(*enums):
    dct = dict((enum, enum) for enum in enums)
    dct['_fields'] = enums  # Set a fields property for easy enumeration
    return type('Enum', (), dct)

ItemStateEnum = enum('ACTIVE', 'INACTIVE', 'DELETED')


class Rendition(APIObject):
    _fields = ['url', 'audioOnly', 'controllerType', 'encodingRate',
               'frameHeight', 'frameWidth', 'size', 'remoteUrl',
               'remoteStreamName', 'videoCodec', 'videoContainer',
               'videoDuration']


class Video(APIObject):
    _fields = ['name', 'id', 'referenceId', 'accountId', 'shortDescription',
               'longDescription', 'FLVURL', 'renditions', 'videoFullLength',
               'creationDate', 'publishedDate', 'lastModifiedDate',
               'itemState', 'startDate', 'endDate', 'linkURL', 'linkText',
               'tags', 'videoStillURL', 'thumbnailURL', 'length',
               'customFields', 'economics', 'adKeys', 'geoRestricted',
               'geoFilteredCountries', 'geoFilterExclude', 'cuePoints',
               'playsTotal', 'playsTrailingWeek']
    renditions = ListField(Rendition)
    videoFullLength = Field(Rendition)
    creationDate = DateTimeField()
    publishedDate = DateTimeField()
    lastModifiedDate = DateTimeField()
    startDate = DateTimeField()
    endDate = DateTimeField()
    itemState = EnumField(ItemStateEnum)

    def __repr__(self):
        return '<Video id=\'{0}\'>'.format(self.id)


class Playlist(APIObject):
    _fields = ['id', 'referenceId', 'accountId', 'name', 'shortDescription',
               'videoIds', 'videos', 'playlistType', 'filterTags',
               'tagInclusionRule', 'thumbnailURL']
    videos = ListField(Video)

    def __repr__(self):
        return '<Playlist id=\'{0}\'>'.format(self.id)


class Image(APIObject):
    _fields = ['id', 'referenceId', 'type', 'remoteUrl', 'displayName']

    def __repr__(self):
        return '<Image id=\'{0}\'>'.format(self.id)


class CuePoint(APIObject):
    _fields = ['name', 'videoId', 'time', 'forceStop', 'type', 'metadata']

    def __repr__(self):
        return '<CuePoint name=\'{0}\'>'.format(self.name)


class LogoOverlay(APIObject):
    _fields = ['id', 'image', 'tooltip', 'linkURL', 'alignment']

    def __repr__(self):
        return '<LogoOverlay id=\'{0}\'>'.format(self.id)


class ItemCollection(APIObject):
    '''Abstract ItemCollection class. Shouldn't be used directly.'''
    _fields = ['total_count', 'items', 'page_number', 'page_size']
    _item_class = None  # Override this
    items = None  # Override this: ListField(item_class)

    def __iter__(self):
        for item in self.items:
            yield item


class VideoItemCollection(ItemCollection):
    _item_class = Video
    items = ListField(Video)


class PlaylistItemCollection(ItemCollection):
    _item_class = Playlist
    items = ListField(Playlist)


# Enums
SortByType = enum('PUBLISH_DATE', 'CREATION_DATE', 'MODIFIED_DATE',
                  'PLAYS_TOTAL', 'PLAYS_TRAILING_WEEK')


SortOrderType = enum('ASC', 'DESC')


UploadStatusEnum = enum('UPLOADING', 'PROCESSING', 'COMPLETE', 'ERROR')


EconomicsEnum = enum('FREE', 'AD_SUPPORTED')


PlaylistTypeEnum = enum('EXPLICIT', 'OLDEST_TO_NEWEST', 'NEWEST_TO_OLDEST',
                        'ALPHABETICAL', 'PLAYS_TOTAL', 'PLAYS_TRAILING_WEEK')


class PublicPlaylist(object):
    FieldsEnum = enum('ID', 'REFERENCEID', 'NAME', 'SHORTDESCRIPTION',
                      'VIDEOIDS', 'VIDEOS', 'THUMBNAILURL', 'FILTERTAGS',
                      'PLAYLISTTYPE', 'ACCOUNTID')


class PublicVideo(object):
    FieldsEnum = enum('ID', 'NAME', 'SHORTDESCRIPTON', 'LONGDESCRIPTION',
                      'CREATIONDATE', 'PUBLISHEDDATE', 'LASTMODIFIEDDATE',
                      'STARTDATE', 'ENDDATE', 'LINKURL', 'LINKTEXT', 'TAGS',
                      'VIDEOSTILLURL', 'THUMBNAILURL', 'REFERENCEID', 'LENGTH',
                      'ECONOMICS', 'ITEMSTATE', 'PLAYSTOTAL',
                      'PLAYSTRAILINGWEEK', 'VERSION', 'CUEPOINTS',
                      'SUBMISSIONINFO', 'CUSTOMFIELDS', 'RELEASEDATE',
                      'FLVURL', 'RENDITIONS', 'GEOFILTERED', 'GEORESTRICTED',
                      'GEOFILTEREXCLUDE', 'EXCLUDELISTEDCOUNTRIES',
                      'GEOFILTEREDCOUNTRIES', 'ALLOWEDCOUNTRIES', 'ACCOUNTID',
                      'FLVFULLLENGTH', 'VIDEOFULLLENGTH')


VideoCodecEnum = enum('UNDEFINED', 'NONE', 'SORENSON', 'ON2', 'H264')


MediaDeliveryEnum = enum('default', 'http', 'http_ios')


ImageTypeEnum = enum('VIDEO_STILL', 'SYNDICATION_STILL', 'THUMBNAIL',
                     'BACKGROUND', 'LOGO', 'LOGO_OVERLAY')


LogoOverlayAlignmentEnum = enum('TOP_RIGHT', 'TOP_LEFT', 'BOTTOM_RIGHT',
                                'BOTTOM_LEFT')


VideoTypeEnum = enum('FLV_PREVIEW', 'FLV_FULL', 'FLV_BUMPER', 'DIGITAL_MASTER')

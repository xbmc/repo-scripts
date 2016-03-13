from PIL.ExifTags import TAGS, GPSTAGS


def get_exif_data(image):
    """Returns a dictionary from the exif data of an PIL Image item. Also converts the GPS Tags"""
    info = image._getexif()
    if not info:
        return {}
    exif_data = {}
    for tag, value in info.items():
        decoded = TAGS.get(tag, tag)
        if decoded == "GPSInfo":
            gps_data = {}
            for t in value:
                sub_decoded = GPSTAGS.get(t, t)
                gps_data[sub_decoded] = value[t]
            exif_data[decoded] = gps_data
        else:
            exif_data[decoded] = value
    return exif_data


def _convert_to_degrees(value):
    """Helper function to convert the GPS coordinates stored in the EXIF to degress in float format"""
    d = float(value[0][0]) / float(value[0][1])
    m = float(value[1][0]) / float(value[1][1])
    s = float(value[2][0]) / float(value[2][1])
    return d + (m / 60.0) + (s / 3600.0)


def get_lat_lon(exif_data):
    """Returns the latitude and longitude, if available, from the provided exif_data (obtained through get_exif_data)"""
    if "GPSInfo" not in exif_data:
        return None, None
    gps_info = exif_data["GPSInfo"]
    gps_lat = gps_info.get("GPSLatitude")
    gps_lat_ref = gps_info.get('GPSLatitudeRef')
    gps_lon = gps_info.get('GPSLongitude')
    gps_lon_ref = gps_info.get('GPSLongitudeRef')
    if gps_lat and gps_lat_ref and gps_lon and gps_lon_ref:
        lat = _convert_to_degrees(gps_lat)
        lat = -lat if gps_lat_ref != "N" else lat
        lon = _convert_to_degrees(gps_lon)
        lon = -lon if gps_lon_ref != "E" else lon
    return lat, lon

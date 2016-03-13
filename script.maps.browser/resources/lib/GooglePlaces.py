import Utils
import xbmcgui
import urllib

GOOGLE_PLACES_KEY = 'AIzaSyCgfpm7hE_ufKMoiSUhoH75bRmQqV8b7P4'
BASE_URL = 'https://maps.googleapis.com/maps/api/place/'


class GooglePlaces():

    def __init__(self):
        pass

    def select_category(self):
        Categories = {"accounting": Utils.LANG(32000),
                      "airport": Utils.LANG(32035),
                      "amusement_park": Utils.LANG(32036),
                      "aquarium": Utils.LANG(32037),
                      "art_gallery": Utils.LANG(32038),
                      "atm": Utils.LANG(32039),
                      "bakery": Utils.LANG(32040),
                      "bank": Utils.LANG(32041),
                      "bar": Utils.LANG(32042),
                      "beauty_salon": Utils.LANG(32016),
                      "bicycle_store": Utils.LANG(32017),
                      "book_store": Utils.LANG(32018),
                      "bowling_alley": Utils.LANG(32023),
                      "bus_station": Utils.LANG(32033),
                      "cafe": Utils.LANG(32043),
                      "campground": Utils.LANG(32044),
                      "car_dealer": Utils.LANG(32045),
                      "car_rental": Utils.LANG(32046),
                      "car_repair": Utils.LANG(32047),
                      "car_wash": Utils.LANG(32048),
                      "casino": Utils.LANG(32049),
                      "cemetery": Utils.LANG(32050),
                      "church": Utils.LANG(32051),
                      "city_hall": Utils.LANG(32052),
                      "clothing_store": Utils.LANG(32053),
                      "convenience_store": Utils.LANG(32054),
                      "courthouse": Utils.LANG(32055),
                      "dentist": Utils.LANG(32056),
                      "department_store": Utils.LANG(32057),
                      "doctor": Utils.LANG(32058),
                      "electrician": Utils.LANG(32059),
                      "electronics_store": Utils.LANG(32060),
                      "embassy": Utils.LANG(32061),
                      "establishment": Utils.LANG(32062),
                      "finance": Utils.LANG(29957),
                      "fire_station": Utils.LANG(32063),
                      "florist": Utils.LANG(32064),
                      "food": Utils.LANG(32006),
                      "funeral_home": Utils.LANG(32065),
                      "furniture_store": Utils.LANG(32066),
                      "gas_station": Utils.LANG(32067),
                      "general_contractor": Utils.LANG(32068),
                      "grocery_or_supermarket": Utils.LANG(32069),
                      "gym": Utils.LANG(32070),
                      "hair_care": Utils.LANG(32071),
                      "hardware_store": Utils.LANG(32072),
                      "health": Utils.LANG(32073),
                      "hindu_temple": Utils.LANG(32074),
                      "home_goods_store": Utils.LANG(32075),
                      "hospital": Utils.LANG(32076),
                      "insurance_agency": Utils.LANG(32077),
                      "jewelry_store": Utils.LANG(32078),
                      "laundry": Utils.LANG(32079),
                      "lawyer": Utils.LANG(32080),
                      "library": Utils.LANG(14022),
                      "liquor_store": Utils.LANG(32081),
                      "local_government_office": Utils.LANG(32082),
                      "locksmith": Utils.LANG(32083),
                      "lodging": Utils.LANG(32084),
                      "meal_delivery": Utils.LANG(32085),
                      "meal_takeaway": Utils.LANG(32086),
                      "mosque": Utils.LANG(32087),
                      "movie_rental": Utils.LANG(32088),
                      "movie_theater": Utils.LANG(32089),
                      "moving_company": Utils.LANG(32090),
                      "museum": Utils.LANG(32091),
                      "night_club": Utils.LANG(32092),
                      "painter": Utils.LANG(32093),
                      "park": Utils.LANG(32094),
                      "parking": Utils.LANG(32095),
                      "pet_store": Utils.LANG(32096),
                      "pharmacy": Utils.LANG(32097),
                      "physiotherapist": Utils.LANG(32098),
                      "place_of_worship": Utils.LANG(32099),
                      "plumber": Utils.LANG(32100),
                      "police": Utils.LANG(32101),
                      "post_office": Utils.LANG(32102),
                      "real_estate_agency": Utils.LANG(32103),
                      "restaurant": Utils.LANG(32104),
                      "roofing_contractor": Utils.LANG(32105),
                      "rv_park": Utils.LANG(32106),
                      "school": Utils.LANG(32107),
                      "shoe_store": Utils.LANG(32108),
                      "spa": Utils.LANG(32109),
                      "stadium": Utils.LANG(32110),
                      "storage": Utils.LANG(154),
                      "store": Utils.LANG(32111),
                      "subway_station": Utils.LANG(32112),
                      "synagogue": Utils.LANG(32113),
                      "taxi_stand": Utils.LANG(32114),
                      "train_station": Utils.LANG(32115),
                      "travel_agency": Utils.LANG(32116),
                      "university": Utils.LANG(32117),
                      "veterinary_care": Utils.LANG(32118),
                      "zoo": Utils.LANG(32119)
                      }
        modeselect = [Utils.LANG(32120)]
        modeselect += [value for value in Categories.itervalues()]
        index = xbmcgui.Dialog().select(Utils.LANG(32121), modeselect)
        if index > 0:
            return Categories.keys()[index - 1]
        elif index > -1:
            return ""
        else:
            return None

    def get_locations(self, lat, lon, radius, locationtype):
        params = {"key": GOOGLE_PLACES_KEY,
                  "radius": min(30000, radius),
                  "location": "%s,%s" % (lat, lon),
                  "types": locationtype}
        base_url = BASE_URL + 'nearbysearch/json?'
        results = Utils.get_JSON_response(base_url + urllib.urlencode(params))
        places = []
        pins = ""
        letter = ord('A')
        if "meta" in results and results['meta']['code'] == 400:
            Utils.log("LIMIT EXCEEDED")
            return "", []
        if "results" not in results:
            return "", []
        for count, place in enumerate(results['results']):
            try:
                params = {"maxwidth": 400,
                          "photoreference": place['photos'][0]['photo_reference'],
                          "key": GOOGLE_PLACES_KEY}
                photo = BASE_URL + 'photo?' + urllib.urlencode(params)
            except:
                photo = ""
            description = place['vicinity'] if "vicinity" in place else place.get('formatted_address', "")
            lat = str(place['geometry']['location']['lat'])
            lon = str(place['geometry']['location']['lng'])
            props = {'name': place['name'],
                     'label': place['name'],
                     'label2': " / ".join(place['types']),
                     'description': description,
                     "letter": chr(letter + count),
                     "thumb": photo,
                     "icon": place['icon'],
                     "lat": lat,
                     "lon": lon,
                     "rating": str(place['rating'] * 2.0) if "rating" in place else ""}
            pins += "&markers=color:blue%7Clabel:" + chr(letter + count) + "%7C" + lat + "," + lon
            places.append(props)
        return pins, places

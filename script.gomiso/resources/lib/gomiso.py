import imp
import oauth2 as oauth
import urllib
import os
import cgi

"""Python library for interaction with Gomiso API (www.gomiso.com)
This is an attempt for me to learn Python, XBMC interaction and to win an Ipad 2.
The code surely is not the cleanest Python code you will ever read but I'm trying my best to have something functional

Please refer to http://gomiso.com/developers for JSON output format
"""


#TODO: get ride of all the "202" / "404" message and get a True or False value instead

__author__ = "Mathieu Feulvarch"
__copyright__ = "Copyright 2011, Mathieu Feulvarch "
__license__ = "GPL"
__version__ = "1.0"
__maintainer__ = "Mathieu Feulvarch"
__email__ = "mathieu@feulvarch.fr"
__status__ = "Production"

needed_modules = ['oauth2', 'cgi', 'urllib', 'os']

for module_name in needed_modules:
    try:
        imp.find_module(module_name)
    except ImportError:
        print 'Module %s not found.' %(module_name)
        exit()

class gomiso:
    consumer_credentials = {}
    access_tokens = {}
    __scriptID__ = "script.gomiso"

    def authentification(self, consumer_key, consumer_secret, login, password, tokensFile):
        """
        Must be call in order to generate authentification tokens for further use.
        Rely on login and password from user
        
        Input:
            -'consumer_key' and 'consumer_secret' (given by gomiso when you create an application)
            -'login' and 'password' from the user
            -'tokensFile': file holder for tokens
            
        Output:
            -'True' or 'False' based on if the authentification was successful or not
            -A file named 'tokens' is created with user's tokens
        """
        self.consumer_credentials['key'] = consumer_key
        self.consumer_credentials['secret'] = consumer_secret
        if os.path.isfile(tokensFile) != True:
            consumer = oauth.Consumer(self.consumer_credentials['key'], self.consumer_credentials['secret'])
            client = oauth.Client(consumer)
            client.authorizations
            params = {}
            params["x_auth_username"] = login
            params["x_auth_password"] = password
            params["x_auth_mode"] = 'client_auth'
            client.set_signature_method = oauth.SignatureMethod_HMAC_SHA1()
            resp, token = client.request('https://gomiso.com/oauth/access_token', method='POST', body=urllib.urlencode(params))
            if resp['status'] != '401':
                self.access_tokens = dict(cgi.parse_qsl(token))
                f = open(tokensFile, 'w')
                f.write(self.access_tokens['oauth_token'])
                f.write('\n')
                f.write(self.access_tokens['oauth_token_secret'])
                f.write('\n')
                f.close()
                return True
            else:
                return False
        else:
            f = open(tokensFile, 'r')
            self.access_tokens['oauth_token'] = f.readline().rstrip('\n')
            self.access_tokens['oauth_token_secret'] = f.readline().rstrip('\n')
            f.close()
            return True


    def getUserInfo(self, user_id = 0):
        """
        Retrieves relevant information from a user's profile. If no user is specified, returns the details of the authenticated user. 
        
        Input:
            -'user_id': The user id for the info you would like to retrieve. If not specified, defaults to authenticated user. 
            
        Output
            -JSON format with all user information
        """
        consumer = oauth.Consumer(self.consumer_credentials['key'], self.consumer_credentials['secret'])
        client = oauth.Client(consumer, oauth.Token(self.access_tokens['oauth_token'], self.access_tokens['oauth_token_secret']))
        if user_id == 0:
            resp, token = client.request('http://gomiso.com/api/oauth/v1/users/show.json', method="GET")
        else:
            resp, token = client.request('http://gomiso.com/api/oauth/v1/users/show.json?user_id=' + str(user_id), method="GET")
        return token

    #need to verify that count is integer
    def findUser(self, search_pattern, count = 15):
        """
        Searches for users with a first name, last name, username or email that matches the given query string
        
        Input:
            -'search_pattern': (Required) The search query string. If this parameter is formatted like an email address, users with matching emails will be returned, otherwise matches will be found on the user's first name, last name and username 
            
            -'count': The number of results you'd like returned. The default is 15 if no value is passed, otherwise you may select a value between 1 and 50.
        
        Output:
            -Array of user information
        """
        if count > 50 or count < 1:
            print "Cannot retrieve more than 50 results or less than 1 result at once\n"
            exit()
        consumer = oauth.Consumer(self.consumer_credentials['key'], self.consumer_credentials['secret'])
        client = oauth.Client(consumer, oauth.Token(self.access_tokens['oauth_token'], self.access_tokens['oauth_token_secret']))
        resp, token = client.request('http://gomiso.com/api/oauth/v1/users.json?q=' + urllib.quote_plus(search_pattern) + '&count=' + str(count))
        return token

    def usersFollowing(self, user_id = 0):
        """
        Retrieves all users that follow a specified account. If no user is specified, returns the followers of the authenticated user.
        
        Input:
            -'user_id': The user id for the info you would like to retrieve. If not specified, defaults to authenticated user.
            
        Output:
            -Array of users information
        """
        consumer = oauth.Consumer(self.consumer_credentials['key'], self.consumer_credentials['secret'])
        client = oauth.Client(consumer, oauth.Token(self.access_tokens['oauth_token'], self.access_tokens['oauth_token_secret']))
        if user_id != 0:
            resp, token = client.request('http://gomiso.com/api/oauth/v1/users/followers.json?user_id=' + str(user_id), method="GET")
        else:
            resp, token = client.request('http://gomiso.com/api/oauth/v1/users/followers.json', method="GET")
        return token

    def followersFrom(self, user_id = 0):
        """
        Retrieves all users that a specified account follows. If no user is specified, returns the follows of the authenticated user.
        
        Input
            -'user_id': The user id for the info you would like to retrieve. If not specified, defaults to authenticated user.
            
        Output
            -Array of users information
        """
        consumer = oauth.Consumer(self.consumer_credentials['key'], self.consumer_credentials['secret'])
        client = oauth.Client(consumer, oauth.Token(self.access_tokens['oauth_token'], self.access_tokens['oauth_token_secret']))
        if user_id != 0:
            resp, token = client.request('http://gomiso.com/api/oauth/v1/users/follows.json?user_id=' + str(user_id), method="GET")
        else:
            resp, token = client.request('http://gomiso.com/api/oauth/v1/users/follows.json', method="POST")
        return token

    def follow(self, user_id):
        """
        Account creates a following relationship with specified user by id. 
        
        Input
            -'user_id': (Required) The user id for the user that should be followed.
            
        Output
            -A 201 response code ("created") if the follow was successful.
        """
        consumer = oauth.Consumer(self.consumer_credentials['key'], self.consumer_credentials['secret'])
        client = oauth.Client(consumer, oauth.Token(self.access_tokens['oauth_token'], self.access_tokens['oauth_token_secret']))
        resp, token = client.request('http://gomiso.com/api/oauth/v1/users/follows.json?user_id=' + str(user_id), method="POST")
        return token

    def unfollow(user_id):
        """
        Account removes a follow relationship with specified user by id. 
        
        Input
            -'user_id': (Required) The user id for the user that should no longer be followed.
            
        Output
            -A 200 response code ("success") if the unfollow was successful.
        """
        consumer = oauth.Consumer(self.consumer_credentials['key'], self.consumer_credentials['secret'])
        client = oauth.Client(consumer, oauth.Token(self.access_tokens['oauth_token'], self.access_tokens['oauth_token_secret']))
        resp, token = client.request('http://gomiso.com/api/oauth/v1/users/follows.json?user_id=' + str(user_id), method="DELETE")
        print resp
        return token

    def findMedia(self, title, kind = 'all', count = 25):
        """
        Retrieves media listing information based on a given query. 
        
        Input
            -'title': (Required) Partial title for a given media.
            -'kind': Filter for the type of Media ('all' per default or 'tv' or 'movie')
            
        Output
            -Array of basic Media objects
        """
        media_type = {'tv': 'TvShow', 'movie':'Movie', 'all':'All'}
        consumer = oauth.Consumer(self.consumer_credentials['key'], self.consumer_credentials['secret'])
        client = oauth.Client(consumer, oauth.Token(self.access_tokens['oauth_token'], self.access_tokens['oauth_token_secret']))
    #Not in media_type (search for python xxx.notin(media_type)
        if kind != 'all' and kind != 'tv' and kind != 'movie':
            print 'Please use \'tv\' or \'movie\' as value for the second parameter.\n-By default (option "all"), searching in TV shows and Movies\n-\'tv\' is for TV shows only\n-\'movie\' is for Movies only'
            exit()
        if count > 50 or count < 1:
            print 'Cannot retrieve more than 50 results or less than 1 result at once\n'
            exit()
        if kind == 'all':
            resp, token = client.request('http://gomiso.com/api/oauth/v1/media.json?q=' + urllib.quote_plus(title) + '&count=' + str(count), method='GET')
        else:
            resp, token = client.request('http://gomiso.com/api/oauth/v1/media.json?q=' + urllib.quote_plus(title) + '&count=' + str(count) + '&kind=' + media_type[kind], method='GET')
        return token
    
    def findExactMedia(self, title, kind = 'movie', episode = '', year = '', count = 25):
        """
        Retrieves exact (when possible) media listing information based on a given query. 
        
        Input
            -'title': (Required) Partial title for a given media.
            -'episode' : Episode title
            -'kind': Filter for the type of Media ('all' per default or 'tv' or 'movie')
            -'year': Year of release of movie 
            
        Output
            -Array of basic Media objects
        """
        media_type = {'tv': 'TvShow', 'movie':'Movie'}
        consumer = oauth.Consumer(self.consumer_credentials['key'], self.consumer_credentials['secret'])
        client = oauth.Client(consumer, oauth.Token(self.access_tokens['oauth_token'], self.access_tokens['oauth_token_secret']))
    #Not in media_type (search for python xxx.notin(media_type)
        if kind != 'tv' and kind != 'movie':
            print 'Please use \'tv\' or \'movie\' as value for the second parameter.\n-\'tv\' is for TV shows only\n-\'movie\' is for Movies only'
            exit()
        if count > 50 or count < 1:
            print 'Cannot retrieve more than 50 results or less than 1 result at once\n'
            exit()
        if kind == 'Movie':
            resp, token = client.request('http://gomiso.com/api/oauth/v1/media/identify.json?title=' + urllib.quote_plus(title) + '&kind=' + media_type[kind] + '&count=' + str(count) + '&ry=' + year, method='GET')
        else:
            resp, token = client.request('http://gomiso.com/api/oauth/v1/media/identify.json?title=' + urllib.quote_plus(title) + '&kind=' + media_type[kind] + '&count=' + str(count) + '&et=' + urllib.quote_plus(episode), method='GET')
        return token

    def mediaDetails(self, media_id):
        """
        Retrieves relevant information about specified media. 
        
        Input
            -'media_id': (Required) The media id for the info you would like to retrieve. 
            
        Output
            -The extended Media object
        """
        consumer = oauth.Consumer(self.consumer_credentials['key'], self.consumer_credentials['secret'])
        client = oauth.Client(consumer, oauth.Token(self.access_tokens['oauth_token'], self.access_tokens['oauth_token_secret']))
        resp, token = client.request('http://gomiso.com/api/oauth/v1/media/show.json?media_id=' + str(media_id), method='GET')
        return token

    def trending(self, count = 25):
        """
        Retrieves a list of currently trending media. Trending refers to media with the most recent checkins. 
        
        Input
            -'count': The total matching items to return (1-100)
            
        Output
            -Array of basic Media objects
        """
        consumer = oauth.Consumer(self.consumer_credentials['key'], self.consumer_credentials['secret'])
        client = oauth.Client(consumer, oauth.Token(self.access_tokens['oauth_token'], self.access_tokens['oauth_token_secret']))
        if count > 100 or count < 1:
            print 'Cannot retrieve more than 10 results or less than 1 result at once\n'
            exit()
        resp, token = client.request('http://gomiso.com/api/oauth/v1/media/trending.json?count=' + str(count), method='GET')
        return token

    def userFavorites(self, user_id):
        """
        Retrieves a list of favorited media by user. Favorited refers to media that the user has marked as favorites. 
        
        Input:
            -'user_id': The user id for the info you would like to retrieve. If not specified, defaults to authenticated user.
            
        Output:
            -Array of basic Media objects
        """
        consumer = oauth.Consumer(self.consumer_credentials['key'], self.consumer_credentials['secret'])
        client = oauth.Client(consumer, oauth.Token(self.access_tokens['oauth_token'], self.access_tokens['oauth_token_secret']))
        resp, token = client.request('http://gomiso.com/api/oauth/v1/media/favorites.json?user_id=' + str(user_id), method='GET')
        return token

    def addFavorite(self, media_id):
        """
        Marks a new favorite media for authenticated user.
        
        Input:
            -'media_id': (Required) The media id for the info you would like to favorite.
            
        Output:
            -A 201 response code ("created") if the favorite was successful.
        """
        consumer = oauth.Consumer(self.consumer_credentials['key'], self.consumer_credentials['secret'])
        client = oauth.Client(consumer, oauth.Token(self.access_tokens['oauth_token'], self.access_tokens['oauth_token_secret']))
        resp, token = client.request('http://gomiso.com/api/oauth/v1/media/favorites.json?media_id=' + str(media_id),  method='POST')
        return token

    def deleteFavorite(self, media_id):
        """
        Unmarks a favorited media for authenticated user. 
        
        Input
            -'media_id': (Required) The media id for the info you would like to unfavorite.
            
        Output:
            -A 200 response code ("success") if the unfavorite was successful.
        """
        consumer = oauth.Consumer(self.consumer_credentials['key'], self.consumer_credentials['secret'])
        client = oauth.Client(consumer, oauth.Token(self.access_tokens['oauth_token'], self.access_tokens['oauth_token_secret']))
        resp, token = client.request('http://gomiso.com/api/oauth/v1/media/favorites.json?media_id=' + str(media_id),  method='DELETE')
        return token

    def userFeed(self, user_id, count = 25, since_id = 0, max_id = 0):
        """
        Retrieves feed for a given user or media. A feed includes items of various types, such as checkins, badges, links, notes, ratings, and votes. Properties of feed items vary depending on the type, documented in Object Representation below. 
        
        Input:
            -'user_id': Retrieves all feed items for the given user.
            -'count': The total matching items to return (1-50).
            -'since_id': Retrieves all feed items after a given feed item id. 	
            -'max_id': Retrieves all feed items before a given feed item id.
            
        Output:
            -Array of Feed item objects
        """
        consumer = oauth.Consumer(self.consumer_credentials['key'], self.consumer_credentials['secret'])
        client = oauth.Client(consumer, oauth.Token(self.access_tokens['oauth_token'], self.access_tokens['oauth_token_secret']))
        if max_id < 0 or since_id < 0:
            print 'The parameters cannot be negative\n'
            exit()
        if (max_id != 0 or since_id != 0) and since_id > max_id:
            print 'max_id must be greater then since_id\n'
            exit()
        arguments = '?user_id=' + str(user_id) + '&count=' + str(count)
        if max_id != 0:
            arguments += '&max_id=' + str(max_id)
        if since_id != 0:
            arguments += '&since_id=' + str(since_id)
        resp, token = client.request('http://gomiso.com/api/oauth/v1/feeds.json' + arguments, method='GET')
        return token

    def mediaFeed(self, media_id, count = 25, since_id = 0, max_id = 0):
        """
        Retrieves feed for a given user or media. A feed includes items of various types, such as checkins, badges, links, notes, ratings, and votes. Properties of feed items vary depending on the type, documented in Object Representation below. 
        
        Input:
            -'media_id': Retrieves all feed items for the given media.
            -'count': The total matching items to return (1-50).
            -'since_id': Retrieves all feed items after a given feed item id. 	
            -'max_id': Retrieves all feed items before a given feed item id.
            
        Output:
            -Array of Feed item objects
        """
        consumer = oauth.Consumer(self.consumer_credentials['key'], self.consumer_credentials['secret'])
        client = oauth.Client(consumer, oauth.Token(self.access_tokens['oauth_token'], self.access_tokens['oauth_token_secret']))
        if max_id < 0 or since_id < 0:
            print 'The parameters cannot be negative\n'
            exit()
        if (max_id != 0 or since_id != 0) and since_id > max_id:
            print 'max_id must be greater then since_id\n'
            exit()
        arguments = '?media_id=' + str(media_id) + '&count=' + str(count)
        if max_id != 0:
            arguments += '&max_id=' + str(max_id)
        if since_id != 0:
            arguments += '&since_id=' + str(since_id)
        resp, token = client.request('http://gomiso.com/api/oauth/v1/feeds.json' + arguments, method='GET')
        return token

    def userHomeFeed(self, user_id, count = 25, since_id = 0, max_id = 0):
        """
        Retrieves home feed of the authenticated user, i.e., all the checkins and badges of users that the authenticated user follows. 
        
        Input:
            -'user_id': Retrieves all feed items for the given user.
            -'count': The total matching items to return (1-50).
            -'since_id': Retrieves all feed items after a given feed item id. 	
            -'max_id': Retrieves all feed items before a given feed item id.
            
        Output:
            -Array of Feed item objects
        """
        consumer = oauth.Consumer(self.consumer_credentials['key'], self.consumer_credentials['secret'])
        client = oauth.Client(consumer, oauth.Token(self.access_tokens['oauth_token'], self.access_tokens['oauth_token_secret']))
        if max_id < 0 or since_id < 0:
            print 'The parameters cannot be negative\n'
            exit()
        if (max_id != 0 or since_id != 0) and since_id > max_id:
            print 'max_id must be greater then since_id\n'
            exit()
        arguments = '?user_id=' + str(user_id) + '&count=' + str(count)
        if max_id != 0:
            arguments += '&max_id=' + str(max_id)
        if since_id != 0:
            arguments += '&since_id=' + str(since_id)
        resp, token = client.request('http://gomiso.com/api/oauth/v1/feeds/home.json' + arguments, method='GET')
        return token
        
    def mediaHomeFeed(self, media_id, count = 25, since_id = 0, max_id = 0):
        """
        Retrieves home feed of the authenticated user, i.e., all the checkins and badges of users that the authenticated user follows. 
        
        Input:
            -'media_id': Retrieves all feed items for the given media.
            -'count': The total matching items to return (1-50).
            -'since_id': Retrieves all feed items after a given feed item id. 	
            -'max_id': Retrieves all feed items before a given feed item id.
            
        Output:
            -Array of Feed item objects
        """
        consumer = oauth.Consumer(self.consumer_credentials['key'], self.consumer_credentials['secret'])
        client = oauth.Client(consumer, oauth.Token(self.access_tokens['oauth_token'], self.access_tokens['oauth_token_secret']))
        if max_id < 0 or since_id < 0:
            print 'The parameters cannot be negative\n'
            exit()
        if (max_id != 0 or since_id != 0) and since_id > max_id:
            print 'max_id must be greater then since_id\n'
            exit()
        arguments = '?media_id=' + str(user_id) + '&count=' + str(count)
        if max_id != 0:
            arguments += '&max_id=' + str(max_id)
        if since_id != 0:
            arguments += '&since_id=' + str(since_id)
        resp, token = client.request('http://gomiso.com/api/oauth/v1/feeds/home.json' + arguments, method='GET')
        return token

    def userCheckings(self, user_id, count = 25, since_id = 0, max_id = 0):
        """
        Retrieves recent checkin information for a given user or media. 
        
        Input:
            -'user_id': Retrieves all feed items for the given user.
            -'count': The total matching items to return (1-50).
            -'since_id': Retrieves all feed items after a given feed item id. 	
            -'max_id': Retrieves all feed items before a given feed item id.
            
        Output:
            -Array of Checkin objects
        """
        consumer = oauth.Consumer(self.consumer_credentials['key'], self.consumer_credentials['secret'])
        client = oauth.Client(consumer, oauth.Token(self.access_tokens['oauth_token'], self.access_tokens['oauth_token_secret']))
        if max_id < 0 or since_id < 0:
            print 'The parameters cannot be negative\n'
            exit()
        if (max_id != 0 or since_id != 0) and since_id > max_id:
            print 'max_id must be greater then since_id\n'
            exit()
        arguments = '?user_id=' + str(user_id) + '&count=' + str(count)
        if max_id != 0:
            arguments += '&max_id=' + str(max_id)
        if since_id != 0:
            arguments += '&since_id=' + str(since_id)
        resp, token = client.request('http://gomiso.com/api/oauth/v1/checkins.json' + arguments, method='GET')
        return token

    def mediaCheckings(self, media_id, count = 25, since_id = 0, max_id = 0):
        """
        Retrieves recent checkin information for a given user or media. 
        
        Input:
            -'media_id': Retrieves all feed items for the given media.
            -'count': The total matching items to return (1-50).
            -'since_id': Retrieves all feed items after a given feed item id. 	
            -'max_id': Retrieves all feed items before a given feed item id.
            
        Output:
            -Array of Checkin objects
        """
        consumer = oauth.Consumer(self.consumer_credentials['key'], self.consumer_credentials['secret'])
        client = oauth.Client(consumer, oauth.Token(self.access_tokens['oauth_token'], self.access_tokens['oauth_token_secret']))
        if max_id < 0 or since_id < 0:
            print 'The parameters cannot be negative\n'
            exit()
        if (max_id != 0 or since_id != 0) and since_id > max_id:
            print 'max_id must be greater then since_id\n'
            exit()
        arguments = '?media_id=' + str(media_id) + '&count=' + str(count)
        if max_id != 0:
            arguments += '&max_id=' + str(max_id)
        if since_id != 0:
            arguments += '&since_id=' + str(since_id)
        resp, token = client.request('http://gomiso.com/api/oauth/v1/checkins.json' + arguments, method='GET')
        return token

    def checking(self, media_id, season_num = 0, episode_num = 0, comment = '', facebook = 'default', twitter = 'default'):
        """
        Posts a new checkin to the specified media for the authenticated user. 
        
        Input:
            -'media_id': (Required) The specified media to create a checkin for.
            -'season_num': The specified season to create a checkin for (if the media is a TV Show).
            -'episode_num': The specified episode to create a checkin for (if the media is a TV Show).
            -'comment': The attached message for this checkin.
            -'facebook': Determines if the checkin should be posted to facebook. If this parameter is not specified, behavior defaults to the user's defaults. 
            -'twitter': Determines if the checkin should be posted to twitter. If this parameter is not specified, behavior defaults to the user's defaults. 
            
        Output:
            -The created check-in object
        """
        consumer = oauth.Consumer(self.consumer_credentials['key'], self.consumer_credentials['secret'])
        client = oauth.Client(consumer, oauth.Token(self.access_tokens['oauth_token'], self.access_tokens['oauth_token_secret']))
        arguments = '?media_id=' + str(media_id)
        if season_num != 0 and episode_num  == 0:
            print 'Episode number cannot be 0'
            exit()
        if episode_num != 0 and season_num == 0:
            print 'Season number cannot be 0'
            exit()
        if episode_num != 0 and season_num !=0:
            arguments += '&season_num=' + str(season_num) + '&episode_num=' + str(episode_num)
        if facebook == 'true':
            arguments += '&facebook=true'
        elif facebook == 'false':
            arguments += '&facebook=false'
        if twitter == 'true':
            arguments += '&twitter=true'
        elif twitter == 'false':
            arguments += '&twitter=false'
        if comment != '':
            comments = '&comment=' + urllib.quote_plus(comment)
            arguments += comments
        resp, token = client.request('http://gomiso.com/api/oauth/v1/checkins.json' + arguments, method='POST')
        return token

    def userBadges(self, user_id = 0):
        """
        Retrieves information about either the comprehensive set of badges
        
        Input:
            -'user_id': The user id that you'd like applied to the badge list (badges that have already been awarded to that user will have a flag set)
        
        Output:
            -Array of Badge objects
        """
        consumer = oauth.Consumer(self.consumer_credentials['key'], self.consumer_credentials['secret'])
        client = oauth.Client(consumer, oauth.Token(self.access_tokens['oauth_token'], self.access_tokens['oauth_token_secret']))
        parameters = ''
        if user_id != 0:
            parameters = '?user_id=' + user_id
        resp, token = client.request('http://gomiso.com/api/oauth/v1/badges.json' + parameters, method='GET')
        return token

    #def badgesFeatured( still don't quite get it...)

    def mediaEpisodes(self, media_id, count = 5, season_num = -1):
        """
        Retrieves a list of episodes for a given media item (TV Show) 
        
        Input:
            -'media_id':
            -'count'
            -'season_num'
        
        Output:
            -episodes (Array): The matching episode objects
            -episode_count: The total number of episodes for the given media item
            -season_count: The total number of seasons for the given media item
        """
        consumer = oauth.Consumer(self.consumer_credentials['key'], self.consumer_credentials['secret'])
        client = oauth.Client(consumer, oauth.Token(self.access_tokens['oauth_token'], self.access_tokens['oauth_token_secret']))
        parameters = '?media_id=' + str(media_id) + '&count=' + str(count)
        if season_num > -1:
            parameters += '&season_num=' + str(season_num)
        resp, token = client.request('http://gomiso.com/api/oauth/v1/episodes.json' + parameters, method='GET')
        return token

    def mediaEpisodeInformation(self, media_id, season_num = -1, episode_num = -1):
        """
        Retrieves information about a specific episode. In the case of an ambiguous query, returns the most recent episode matching given parameters (for instance, if only a media_id and season_num are sent, the last episode of media_id for season_num is returned)
        
        Input:
            -'media_id': (Required) The media_id for the episode you would like to retrieve.
            -'season_num': The season for the episode you would like to retrieve.
            -'episode_num': The episode number of the given season you'd like to retrieve
            
        Output:
            -The returned episode object
        """
        consumer = oauth.Consumer(self.consumer_credentials['key'], self.consumer_credentials['secret'])
        client = oauth.Client(consumer, oauth.Token(self.access_tokens['oauth_token'], self.access_tokens['oauth_token_secret']))
        parameters = '?media_id=' + str(media_id)
        if season_num > -1:
            parameters += '&season_num=' + str(season_num)
        if episode_num > -1 and season_num == -1:
            print 'You cannot provide an episode number if you do not provide a season number'
            exit()
        if episode_num > -1:
            parameters += '&episode_num=' + str(episode_num)
        print 'http://gomiso.com/api/oauth/v1/episodes/show.json' + parameters
        resp, token = client.request('http://gomiso.com/api/oauth/v1/episodes/show.json' + parameters, method='GET')
        return token

    def notifications(self):
        """
        Retrieves a list of a user's notifications. 
        
        Input:
        
        Output:
            -Array representing the matching notification item objects
        """
        consumer = oauth.Consumer(self.consumer_credentials['key'], self.consumer_credentials['secret'])
        client = oauth.Client(consumer, oauth.Token(self.access_tokens['oauth_token'], self.access_tokens['oauth_token_secret']))
        resp, token = client.request('http://gomiso.com/api/oauth/v1/notifications.json', method='GET')
        return token

    def getNotification(self, notification_id):
        """
        Retrieves a single notification 
        
        Input:
            -'notification_id': (Required) The id for the notification you would like to retrieve. 
            
        Output:
            -The matching notification item object
        """
        consumer = oauth.Consumer(self.consumer_credentials['key'], self.consumer_credentials['secret'])
        client = oauth.Client(consumer, oauth.Token(self.access_tokens['oauth_token'], self.access_tokens['oauth_token_secret']))
        resp, token = client.request('http://gomiso.com/api/oauth/v1/notifications/show.json?notification_id=' + str(notification_id), method='GET')
        return token

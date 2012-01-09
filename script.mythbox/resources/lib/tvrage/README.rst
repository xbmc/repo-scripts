About
-----

python-tvrage is a python based object oriented client interface for tvrage.com's XML based api `feeds`_.

.. _feeds: http://www.tvrage.com/xmlfeeds.php

Installation
------------

Install from sources::

    $ python setup.py install

The easiest way to get started with python-tvrage is to use `easy_install` or `pip`::
    
    $ easy_install -U python-tvrage

For `pip` you have to replace **'easy_install'** with **'pip install'**. Also your platform may require the use of `sudo`

Documentation
-------------

The `tvrage` package consists of three modules

- the tvrage.feeds module provides a wrapper function for each of tvrage's XML-feeds
- the tvrage.api module provides an clean and object oriented interface on top of those services
- the tvrage.quickinfo module is a simple pythonic wrapper for tvrage's quickinfo api. Values are returned as python dictionaries rather than dedicated objects for tv shows and episodes 

Fetching XML data
+++++++++++++++++

The `tvrage.feeds` module provides very basic and low level access to the tvrage.com data feeds. For more complex use cases it is recomended to use the object oriented module `tvrage.api`.
Note: All functions in the `tvrage.feeds` module return XML data as ElementTree objects.

searching for TV shows using the general `search` feed (returns fuzzy search results)::

    $ python
    >>> from tvrage import feeds
    >>> from xml.etree.ElementTree import tostring
    >>>
    >>> doctor_who = feeds.search('doctorwho2005')
    >>> for node in doctor_who:
    ...     print(tostring(node))
    ... 
    <show>
    <showid>3332</showid>
    <name>Doctor Who (2005)</name>
    <link>http://www.tvrage.com/DoctorWho_2005</link>
    <country>UK</country>
    <started>2005</started>
    <ended>0</ended>
    <seasons>5</seasons>
    <status>Returning Series</status>
    <classification>Scripted</classification>
    <genres>
    <genre01>Action</genre01><genre02>Adventure</genre02><genre03>Sci-Fi</genre03>
    </genres>
    </show>
    
    <show>
    <showid>3331</showid>
    <name>Doctor Who</name>
    <link>http://www.tvrage.com/Doctor_Who_1963</link>
    <country>UK</country>
    <started>1963</started>
    <ended>1989</ended>
    <seasons>27</seasons>
    <status>Canceled/Ended</status>
    <classification>Scripted</classification>
    <genres>
    <genre01>Action</genre01><genre02>Adventure</genre02><genre03>Sci-Fi</genre03>
    </genres>
    </show>
    
using `full_search` includes all availabe meta data about the shows into the search results::

    >>> doctor_who = feeds.full_search('doctorwho2005')
    >>> print(tostring(doctor_who[0]))
    <show>
    <showid>3332</showid>
    <name>Doctor Who (2005)</name>
    <link>http://www.tvrage.com/DoctorWho_2005</link>
    <country>UK</country>
    <started>Mar/26/2005</started>
    <ended />
    <seasons>5</seasons>
    <status>Returning Series</status>
    <runtime>50</runtime>
    <classification>Scripted</classification>
    <genres>
    <genre>Action</genre><genre>Adventure</genre><genre>Sci-Fi</genre>
    </genres>
    <network country="UK">BBC One</network>
    <airtime>19:00</airtime>
    <airday>Saturday</airday>
    <akas>
    <aka country="FR">Docteur Who</aka>
    <aka attr="Alternative Spelling" country="UK">Dr. Who</aka>
    <aka country="IS">T&#237;maflakk</aka>
    <aka attr="Fake Working Title" country="UK">Torchwood</aka>
    <aka country="BG">&#1044;&#1086;&#1082;&#1090;&#1086;&#1088; &#1050;&#1086;&#1081;</aka>
    <aka country="RU">&#1044;&#1086;&#1082;&#1090;&#1086;&#1088; &#1050;&#1090;&#1086;</aka>
    <aka country="IL">&#1491;&#1493;&#1511;&#1496;&#1493;&#1512; &#1492;&#1493;</aka>
    <aka country="IN">&#2337;&#2377;&#2325;&#2381;&#2335;&#2352; &#2361;&#2370;</aka>
    <aka country="CN">&#30064;&#19990;&#22855;&#20154;</aka></akas>
    </show>
        
The `showinfo` feed retrieves all meta data about one single show using the given `showid`. The result is identical to one element from the `full_search` results.

The `episode_list` feed returns all meta data about episodes of a TV show sorted by season. The optional `node` argument causes the function to return the desired XML node as ElementTree object::
    
    >>> doctor_who_eps = feeds.episode_list('3332', node='Episodelist')
    >>> print(tostring(doctor_who_eps[0]))
    <Season no="1">
    <episode>
    <epnum>1</epnum>
    <seasonnum>01</seasonnum>
    <prodnum>101</prodnum>
    <airdate>2005-03-26</airdate>
    <link>http://www.tvrage.com/DoctorWho_2005/episodes/52117</link>
    <title>Rose</title></episode>
    <episode>
    <epnum>2</epnum>
    <seasonnum>02</seasonnum>
    <prodnum>102</prodnum>
    <airdate>2005-04-02</airdate>
    <link>http://www.tvrage.com/DoctorWho_2005/episodes/52118</link>
    <title>The End of the World</title></episode>
    ...
    </Season>
    
The `full_show_info` feed combines the results of both `showinfo` and `episode_list`.

Using objects
+++++++++++++

The module `tvrage.api` provides wrapper classes for tvrage.com's data feeds. It contains the following classes: `Show`, `Season` and `Episode`.

Working with TV show objects::

    $ python
    >>> import tvrage.api
    >>> doctor_who = tvrage.api.Show('doctorwho2005')
    >>> doctor_who.country
    'UK'
    >>> doctor_who.current_season
    {1: Doctor Who (2005) 5x01 The Eleventh Hour, 2: Doctor Who (2005) 5x02 The Beast... }
    >>> doctor_who.ended
    0
    >>> doctor_who.episodes
    {1: {1: Doctor Who (2005) 1x01 Rose, 2: Doctor Who (2005) 1x02 The End of the World, ... }}
    >>> doctor_who.genres
    ['Action', 'Adventure', 'Sci-Fi']
    >>> doctor_who.latest_episode
    Doctor Who (2005) 5x04 The Time of Angels (1)
    >>> doctor_who.next_episode
    Doctor Who (2005) 5x05 Flesh and Stone (2)
    >>> doctor_who.link
    'http://www.tvrage.com/DoctorWho_2005'
    >>> doctor_who.name
    'Doctor Who (2005)'
    >>> doctor_who.pilot
    Doctor Who (2005) 1x01 Rose
    >>> doctor_who.season(2)
    {1: Doctor Who (2005) 2x01 New Earth, 2: Doctor Who (2005) 2x02 Tooth and Claw, ... }
    >>> doctor_who.seasons
    5
    >>> doctor_who.shortname
    'doctorwho2005'
    >>> doctor_who.showid
    '3332'
    >>> doctor_who.started
    2005
    >>> doctor_who.status
    'Returning Series'
    >>> doctor_who.upcoming_episodes
    <generator object upcoming_episodes at 0x152f0a8>
    
    
The `Season` object is a python dict with additional properties::
    
    >>> s4 = doctor_who.season(4)
    >>> s4.is_current
    False
    >>> s4.premiere
    Doctor Who (2005) 4x01 Partners in Crime
    >>> s4.finale
    Doctor Who (2005) 4x13 Journey's End (3)
    >>> s4.episode(3)
    Doctor Who (2005) 4x03 Planet of the Ood
    >>> s4.values()
    [Doctor Who (2005) 4x01 Partners in Crime, Doctor Who (2005) 4x02 The Fires of... ]
    >>> s4.keys()
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]

The `Episode` object contains all information related to an certain episode::

    >>> rose = doctor_who.season(1).episode(1)
    >>> rose.airdate
    datetime.date(2005, 3, 26)
    >>> rose.link
    'http://www.tvrage.com/DoctorWho_2005/episodes/52117'
    >>> rose.number
    1
    >>> rose.prodnumber
    '101'
    >>> rose.season
    1
    >>> rose.show
    'Doctor Who (2005)'
    >>> rose.title
    'Rose'

For some episodes there is detailed summary information available. This information is not provided by the XML feeds, so it has to be extracted from the episode's overview page via web scraping. Since it would be quite slow to load all those web pages for entire seasons upfront, the summary information is only loaded when the `Episode.summary` property is actually beeing read::

    >>> nextff = tvrage.api.Show('flashforward').next_episode
    >>> nextff
    FlashForward 1x18 Goodbye Yellow Brick Road
    >>> nextff.summary # spoilers alert!... you have to try this one for your self ;)
   
Using the Quickinfo Feed
++++++++++++++++++++++++

The modul `tvrage.quickinfo` provides easy access to the tvrage's `quickinfo feed`_.

.. _quickinfo feed: http://services.tvrage.com/info.php?page=quickinfo

You can fetch meta data about a tv show alone::

    >>> from tvrage import quickinfo
    >>> quickinfo.fetch('doctor who 2005')
    {'Status': 'Returning Series', 'Genres': ['Action', 'Adventure', 'Sci-Fi'], 'Network': 'BBC One (United Kingdom)', 
    'Classification': 'Scripted', 'Started': 'Mar/26/2005', 'Show Name': 'Doctor Who (2005)', 'Show URL': 
    'http://www.tvrage.com/DoctorWho_2005', 'Premiered': '2005', 'Airtime': 'Saturday at 07:00 pm', 'Ended': '', 
    'Show ID': '3332', 'Country': 'United Kingdom', 'Runtime': '50', 'Latest Episode': ['05x13', 'The Big Bang (2)', 'Jun/26/2010']} 

or you can fetch informations about an specific episode combined with the show's meta data::

    >>> epinfo = quickinfo.fetch('doctor who 2005', ep='1x01')    
    >>> epinfo
    {'Status': 'Returning Series', 'Genres': ['Action', 'Adventure', 'Sci-Fi'], ...
    >>> epinfo['Episode Info']
    ['01x01', 'Rose', '26/Mar/2005']
    >>> epinfo['Episode URL']
    'http://www.tvrage.com/DoctorWho_2005/episodes/52117'
    

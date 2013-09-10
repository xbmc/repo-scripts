# -*- coding: utf-8 -*-

import os, sys, re
from random import shuffle, random

__script__ = "Cinema Experience"
__scriptID__ = "script.cinema.experience"

slide_settings           = sys.modules["__main__"].trivia_settings
BASE_CACHE_PATH          = sys.modules["__main__"].BASE_CACHE_PATH
BASE_RESOURCE_PATH       = sys.modules["__main__"].BASE_RESOURCE_PATH
BASE_CURRENT_SOURCE_PATH = sys.modules["__main__"].BASE_CURRENT_SOURCE_PATH
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )

import xbmcgui,xbmc, xbmcaddon
from xbmcvfs import delete as delete_file
from xbmcvfs import exists as exists
from xbmcvfs import copy as file_copy
from folder import dirEntries, getFolders

def _fetch_slides( movie_mpaa ):
    # get watched list
    watched = _load_watched_trivia_file()
    # get the slides
    tmp_slides = _get_slides( [ slide_settings[ "trivia_folder" ] ], movie_mpaa )
    # shuffle and format playlist
    slide_playlist = _shuffle_slides( tmp_slides, watched )
    return slide_playlist

def _load_watched_trivia_file():
    xbmc.log( "[script.cinema.experience] - Loading Watch Slide List", level=xbmc.LOGDEBUG)
    try:
        # set base watched file path
        base_path = os.path.join( BASE_CURRENT_SOURCE_PATH, "trivia_watched.txt" ).replace("\\\\","\\")
        # open path
        usock = open( base_path, "r" )
        # read source
        watched = eval( usock.read() )
        # close socket
        usock.close()
    except:
        watched = []
    return watched

def _reset_watched():
    base_path = os.path.join( BASE_CURRENT_SOURCE_PATH, "trivia_watched.txt" ).replace("\\\\","\\")
    if exists( base_path ):
        delete_file( base_path )
        watched = []
    return watched

def _get_slides( paths, movie_mpaa ):
    # reset folders list
    tmp_slides = []
    folders = []
    # mpaa ratings
    mpaa_ratings = { "G": 0, "PG": 1, "PG-13": 2, "R": 3, "NC-17": 4, "--": 5, "": 6 }
    # enumerate thru paths and fetch slides recursively
    for path in paths:
        # get the directory listing
        entries = dirEntries( path, media_type="files", recursive="FALSE" )
        # sort in case
        entries.sort()
        # get a slides.xml if it exists
        slidesxml_exists, mpaa, question_format, clue_format, answer_format, still_format = _get_slides_xml( path )
        # check if rating is ok
        xbmc.log( "[script.cinema.experience] - Movie MPAA: %s" % movie_mpaa, level=xbmc.LOGDEBUG )
        xbmc.log( "[script.cinema.experience] - Slide MPAA: %s" % mpaa, level=xbmc.LOGDEBUG )
        if ( slidesxml_exists and mpaa_ratings.get( movie_mpaa, -1 ) < mpaa_ratings.get( mpaa, -1 ) ):
            xbmc.log( "[script.cinema.experience] - Slide Rating above movie rating - skipping whole folder", level=xbmc.LOGNOTICE)
            continue
        # initialize these to True so we add a new list item to start
        question = clue = answer = still = True
        # enumerate through our entries list and combine question, clue, answer
        for entry in entries:
            # if folder add to our folder list to recursively fetch slides
            if ( entry.endswith( "/" ) or entry.endswith( "\\" ) ):
                folders += [ entry ]
            # sliders.xml was included, so check it
            elif ( slidesxml_exists ):
                # question
                if ( question_format and re.search( question_format, os.path.basename( entry ), re.IGNORECASE ) ):
                    if ( question ):
                        tmp_slides += [ [ "", "", "" ] ]
                        clue = answer = still = False
                    tmp_slides[ -1 ][ 0 ] = "__question__" + entry
                    # clue
                elif ( clue_format and re.search( clue_format, os.path.basename( entry ), re.IGNORECASE ) ):
                    if ( clue ):
                        tmp_slides += [ [ "", "", "" ] ]
                        question = answer = still = False
                    tmp_slides[ -1 ][ 1 ] = "__clue__" + entry
                # answer
                elif ( answer_format and re.search( answer_format, os.path.basename( entry ), re.IGNORECASE ) ):
                    if ( answer ):
                        tmp_slides += [ [ "", "", "" ] ]
                        question = clue = still = False
                    tmp_slides[ -1 ][ 2 ] = "__answer__" + entry
                    # still
                elif ( still_format and re.search( still_format, os.path.basename( entry ), re.IGNORECASE ) ):
                    if ( still ):
                        tmp_slides += [ [ "", "", "" ] ]
                        clue = answer = question = False
                    tmp_slides[ -1 ][ 0 ] = "__still__" + entry
            # add the file as a question TODO: maybe check for valid picture format?
            elif ( entry and os.path.splitext( entry )[ 1 ].lower() in xbmc.getSupportedMedia( "picture" ) ):
                tmp_slides += [ [ "", "", "__still__" + entry ] ] 
    # if there are folders call again (we want recursive)
    if ( folders ):
        tmp_slides.extend( _get_slides( folders, movie_mpaa ) )
    return tmp_slides

def _get_slides_xml( path ):
    source = os.path.join( path, "slides.xml" ).replace("\\\\","\\")
    destination = os.path.join( BASE_CURRENT_SOURCE_PATH, "slides.xml" ).replace("\\\\","\\")
    # if slides.xml does not exist, try in title case
    if not exists( source ):
        source = os.path.join( path, "Slides.xml" ).replace( "\\\\", "\\" )
        # if no slides.xml exists return false
        if not exists( source ):
            return False, "", "", "", "", ""
    file_copy( source, destination )
    # fetch data
    xml = open( destination ).read()
    # parse info
    #mpaa, theme, question_format, clue_format, answer_format = re.search( "<slides?(?:.+?rating=\"([^\"]*)\")?(?:.+?theme=\"([^\"]*)\")?.*?>.+?<question.+?format=\"([^\"]*)\".*?/>.+?<clue.+?format=\"([^\"]*)\".*?/>.+?<answer.+?format=\"([^\"]*)\".*?/>", xml, re.DOTALL ).groups()
    mpaa = theme = question_format = clue_format = answer_format = still_format = ""
    mpaa_match = re.search( '''rating="([^\"]*)"''', xml, re.DOTALL )
    if mpaa_match:
        mpaa = mpaa_match.group(1)
    theme_match = re.search( '''theme="([^\"]*)"''', xml, re.DOTALL )
    if theme_match:
        theme = theme_match.group(1)
    question_match = re.search( '''<question.+?format="([^\"]*)".*?/>''', xml, re.DOTALL )
    if question_match:
        question_format = question_match.group(1)
    clue_match = re.search( '''<clue.+?format="([^\"]*)".*?/>''', xml, re.DOTALL )
    if clue_match:
        clue_format = clue_match.group(1)
    answer_match = re.search( '''<answer.+?format="([^\"]*)".*?/>''', xml, re.DOTALL )
    if answer_match:
        answer_format = answer_match.group(1)
    still_match = re.search( '''<still.+?format="([^\"]*)".*?/>''', xml, re.DOTALL )
    if still_match:
        still_format = still_match.group(1)
    #xbmc.log("[script.cinema.experience] mpaa: %s QF: %s == AF: %s == CF: %s == SF: %s" % (mpaa, question_format, answer_format, clue_format, still_format), xbmc.LOGNOTICE) 
    delete_file ( destination )
    return True, mpaa, question_format, clue_format, answer_format, still_format
    
def _shuffle_slides( tmp_slides, watched ):
    xbmc.log( "[script.cinema.experience] - Sorting Watched/Unwatched and Shuffing Slides ", level=xbmc.LOGNOTICE)
    slide_playlist = []
    # randomize the groups and create our play list
    count = 0
    while count <6:
        shuffle( tmp_slides, random )
        count += 1
    # now create our final playlist
    # loop thru slide groups and skip already watched groups
    for slides in tmp_slides:
        # has this group been watched
        if ( not slide_settings[ "trivia_unwatched_only" ] or ( slides[ 0 ] and xbmc.getCacheThumbName( slides[ 0 ] ) not in watched ) or
              ( slides[ 1 ] and xbmc.getCacheThumbName( slides[ 1 ] ) not in watched ) or
              ( slides[ 2 ] and xbmc.getCacheThumbName( slides[ 2 ] ) not in watched ) ):
            # loop thru slide group only include non blank slides
            for slide in slides:
                # only add if non blank
                if ( slide ):
                    # add slide
                    slide_playlist += [ slide ]
            xbmc.log( "[script.cinema.experience] ------------------Unwatched-------------------------     included - %s, %s, %s" % ( os.path.basename( slides[ 0 ] ), os.path.basename( slides[ 1 ] ), os.path.basename( slides[ 2 ] ), ), level=xbmc.LOGDEBUG)
            
        else:
            xbmc.log( "[script.cinema.experience] -------------------Watched--------------------------     skipped - %s, %s, %s" % ( os.path.basename( slides[ 0 ] ), os.path.basename( slides[ 1 ] ), os.path.basename( slides[ 2 ] ), ), level=xbmc.LOGDEBUG)

    xbmc.log( "[script.cinema.experience] -----------------------------------------", level=xbmc.LOGDEBUG)
    xbmc.log( "[script.cinema.experience] - total slides selected: %d" % len( slide_playlist ), level=xbmc.LOGNOTICE)

    # reset watched automatically if no slides are left
    if ( len( slide_playlist ) == 0 and slide_settings[ "trivia_unwatched_only" ] and len( watched ) > 0 ):
        watched = _reset_watched()
        #attempt to load our playlist again
        _shuffle_slides( tmp_slides, watched )
    return slide_playlist

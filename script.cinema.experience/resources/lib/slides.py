# -*- coding: utf-8 -*-

import os, sys, re
from random import shuffle, random

__script__               = sys.modules[ "__main__" ].__script__
__scriptID__             = sys.modules[ "__main__" ].__scriptID__
slide_settings           = sys.modules[ "__main__" ].trivia_settings
BASE_CACHE_PATH          = sys.modules[ "__main__" ].BASE_CACHE_PATH
BASE_RESOURCE_PATH       = sys.modules[ "__main__" ].BASE_RESOURCE_PATH
BASE_CURRENT_SOURCE_PATH = sys.modules[ "__main__" ].BASE_CURRENT_SOURCE_PATH
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )

import xbmcgui,xbmc, xbmcaddon, xbmcvfs
from folder import absolute_folder_paths, absolute_listdir
import utils

def _fetch_slides( movie_mpaa ):
    # get watched list
    watched = _load_watched_trivia_file()
    # get the slides
    tmp_slides = _get_slides( [ slide_settings[ "trivia_folder" ] ], movie_mpaa )
    # shuffle and format playlist
    slide_playlist = _shuffle_slides( tmp_slides, watched )
    return slide_playlist

def _load_watched_trivia_file():
    base_path = os.path.join( BASE_CURRENT_SOURCE_PATH, "trivia_watched.txt" ).replace("\\\\","\\")
    watched = []
    watched = utils.load_saved_list( base_path, "Watched Trivia" )
    return watched

def _reset_watched():
    base_path = os.path.join( BASE_CURRENT_SOURCE_PATH, "trivia_watched.txt" ).replace("\\\\","\\")
    if xbmcvfs.exists( base_path ):
        xbmcvfs.delete( base_path )
    watched = []
    return watched

def _get_slides( paths, movie_mpaa ):
    # reset folders list
    tmp_slides = []
    folders = []
    # mpaa ratings
    mpaa_ratings = { "": 0, "G": 1, "PG": 2, "PG-13": 3, "R": 4, "NC-17": 5, "--": 6, "NR": 7 }
    # enumerate thru paths and fetch slides recursively
    for path in paths:
        # get the directory listing
        folders, file_entries = xbmcvfs.listdir( path )
        # sort in case
        file_entries.sort()
        # get a slides.xml if it exists
        slidesxml_exists, mpaa, question_format, clue_format, answer_format, still_format = _get_slides_xml( path )
        # check if rating is ok
        utils.log( "Movie MPAA: %s" % movie_mpaa )
        utils.log( "Slide MPAA: %s" % mpaa )
        if ( slidesxml_exists and mpaa_ratings.get( movie_mpaa, -1 ) < mpaa_ratings.get( mpaa, -1 ) ):
            utils.log( "Slide Rating above movie rating - skipping whole folder", xbmc.LOGNOTICE )
            continue
        # initialize these to True so we add a new list item to start
        question = clue = answer = still = True
        # enumerate through our file_entries list and combine question, clue, answer
        for entry in file_entries:
            # slides.xml was included, so check it
            file_entry = os.path.join( path, entry )
            if ( slidesxml_exists ):
                # question
                if ( question_format and re.search( question_format, os.path.basename( file_entry ), re.IGNORECASE ) ):
                    if ( question ):
                        tmp_slides += [ [ "", "", "" ] ]
                        clue = answer = still = False
                    tmp_slides[ -1 ][ 0 ] = "__question__" + file_entry
                    # clue
                elif ( clue_format and re.search( clue_format, os.path.basename( file_entry ), re.IGNORECASE ) ):
                    if ( clue ):
                        tmp_slides += [ [ "", "", "" ] ]
                        question = answer = still = False
                    tmp_slides[ -1 ][ 1 ] = "__clue__" + file_entry
                # answer
                elif ( answer_format and re.search( answer_format, os.path.basename( file_entry ), re.IGNORECASE ) ):
                    if ( answer ):
                        tmp_slides += [ [ "", "", "" ] ]
                        question = clue = still = False
                    tmp_slides[ -1 ][ 2 ] = "__answer__" + file_entry
                    # still
                elif ( still_format and re.search( still_format, os.path.basename( file_entry ), re.IGNORECASE ) ):
                    if ( still ):
                        tmp_slides += [ [ "", "", "" ] ]
                        clue = answer = question = False
                    tmp_slides[ -1 ][ 0 ] = "__still__" + file_entry
            # add the file as a question TODO: maybe check for valid picture format?
            elif ( file_entry and os.path.splitext( file_entry )[ 1 ].lower() in xbmc.getSupportedMedia( "picture" ) ):
                tmp_slides += [ [ "", "", "__still__" + file_entry ] ] 
    # if there are folders call again (we want recursive)
    if ( folders ):
        tmp_slides.extend( _get_slides( absolute_folder_paths( folders, path ), movie_mpaa ) )
    return tmp_slides

def _get_slides_xml( path ):
    source = os.path.join( path, "slides.xml" ).replace("\\\\","\\")
    destination = os.path.join( BASE_CURRENT_SOURCE_PATH, "slides.xml" ).replace("\\\\","\\")
    slides_xml_copied = False
    # if no slides.xml exists return false
    if not xbmcvfs.exists( source ):
        # slides.xml not found, try Title case(Slides.xml)
        source = os.path.join( path, "Slides.xml" ).replace("\\\\","\\")
        if not xbmcvfs.exists( source ):
            return False, "", "", "", "", ""
    # fetch data
    try:
        xml = xbmcvfs.File( source ).read()
    except:
        try:
            xbmcvfs.copy( source, destination )
            xml = xbmcvfs.File( destination ).read()
            slides_xml_copied = True
        except:
            return False, "", "", "", "", ""
    # parse info
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
    if slides_xml_copied:
        xbmcvfs.delete( destination )
    return True, mpaa, question_format, clue_format, answer_format, still_format
    
def _shuffle_slides( tmp_slides, watched ):
    utils.log( "Sorting Watched/Unwatched and Shuffing Slides ", xbmc.LOGNOTICE )
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
            utils.log( "-------- Unwatched --------     included - %s, %s, %s" % ( os.path.basename( slides[ 0 ] ), os.path.basename( slides[ 1 ] ), os.path.basename( slides[ 2 ] ), ) )
            
        else:
            utils.log( "-------- Watched --------     skipped - %s, %s, %s" % ( os.path.basename( slides[ 0 ] ), os.path.basename( slides[ 1 ] ), os.path.basename( slides[ 2 ] ), ) )

    utils.log( "-----------------------------" )
    utils.log( "Total slides selected: %d" % len( slide_playlist ), xbmc.LOGNOTICE )

    # reset watched automatically if no slides are left
    if ( len( slide_playlist ) == 0 and slide_settings[ "trivia_unwatched_only" ] and len( watched ) > 0 ):
        watched = _reset_watched()
        #attempt to load our playlist again
        _shuffle_slides( tmp_slides, watched )
    return slide_playlist

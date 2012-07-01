#
#      Copyright (C) 2012 Tommy Winther
#      http://tommy.winther.nu
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this Program; see the file LICENSE.txt.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#

import os
import random
import datetime
import thumb
import db
import time
import re
import imdb
import game

import xbmc
import xbmcvfs

from strings import *

IMDB = imdb.Imdb()

class Answer(object):
    def __init__(self, id, text, idFile = None, sortWeight = None, correct = False):
        self.correct = correct
        self.id = id
        self.text = text
        self.idFile = idFile

        self.coverFile = None
        self.sortWeight = sortWeight


    def setCoverFile(self, path, filename = None):
        if filename is None:
            self.coverFile = path
        else:
            self.coverFile = thumb.getCachedVideoThumb(path, filename)

    def __repr__(self):
        return "<Answer(id=%s, text=%s, correct=%s)>" % (self.id, self.text, self.correct)

class Question(object):
    def __init__(self, displayType = None):
        """
        Base class for Questions

        @type displayType: DisplayType
        @param displayType:
        """
        self.answers = list()
        self.text = None
        self.fanartFile = None
        self.displayType = displayType

    def getText(self):
        return self.text

    def getAnswers(self):
        return self.answers

    def getAnswer(self, idx):
        try:
            return self.answers[idx]
        except IndexError:
            return None

    def addCorrectAnswer(self, id, text, idFile = None, path = None, filename = None, sortWeight = None):
        self.addAnswer(id, text, idFile, path, filename, sortWeight, correct = True)

    def addAnswer(self, id, text, idFile = None, path = None, filename = None, sortWeight = None, correct = False):
        a = Answer(id, text, idFile, sortWeight, correct)
        if path or filename:
            a.setCoverFile(path, filename)
        self.answers.append(a)


    def getCorrectAnswer(self):
        for answer in self.answers:
            if answer.correct:
                return answer
        return None

    def getUniqueIdentifier(self):
        return "%s-%s" % (self.__class__.__name__, str(self.getCorrectAnswer().id))

    def setFanartFile(self, path, filename = None):
        self.fanartFile = thumb.getCachedVideoFanart(path, filename)

    def getFanartFile(self):
        return self.fanartFile

    def getDisplayType(self):
        return self.displayType

    @staticmethod
    def isEnabled():
        raise

    def _getMovieIds(self):
        movieIds = list()
        for movie in self.answers:
            movieIds.append(movie.id)
        return movieIds

    def _isAnimationGenre(self, genre):
        return genre.lower().find("animation") != -1

#
# DISPLAY TYPES
#

class DisplayType(object):
    pass

class VideoDisplayType(DisplayType):
    def setVideoFile(self, path, filename):
        if filename[0:8] == 'stack://':
            self.videoFile = filename
        else:
            self.videoFile = os.path.join(path, filename)

        if not xbmcvfs.exists(self.videoFile):
            raise QuestionException('Video file not found: %s' % self.videoFile)

    def getVideoFile(self):
        return self.videoFile

class PhotoDisplayType(DisplayType):
    def setPhotoFile(self, photoFile):
        self.photoFile = photoFile

    def getPhotoFile(self):
        return self.photoFile

class ThreePhotoDisplayType(DisplayType):
    def addPhoto(self, photo, label):
        if not hasattr(self, 'photos'):
            self.photos = list()

        self.photos.append((photo, label))

    def getPhotoFile(self, index):
        return self.photos[index]

class QuoteDisplayType(DisplayType):
    def setQuoteText(self, quoteText):
        self.quoteText = quoteText

    def getQuoteText(self):
        return self.quoteText

class AudioDisplayType(DisplayType):
    def setAudioFile(self, audioFile):
        self.audioFile = audioFile

    def getAudioFile(self):
        return self.audioFile

#
# MOVIE QUESTIONS
#

class MovieQuestion(Question):
    pass

class WhatMovieIsThisQuestion(MovieQuestion):
    def __init__(self, database):
        """
        What movie is this?

        @type database: quizlib.db.Database
        @param database: Database connection instance to use
        """
        videoDisplayType = VideoDisplayType()
        super(WhatMovieIsThisQuestion, self).__init__(videoDisplayType)

        movies = database.getMovies(maxResults = 1)
        if not movies:
            raise QuestionException('No movies found')

        correctAnswer = movies[0]
        self.addCorrectAnswer(correctAnswer['idMovie'], correctAnswer['title'], correctAnswer['idFile'], correctAnswer['strPath'], correctAnswer['strFileName'])

        # Find other movies in set
        if correctAnswer['idSet'] is not None:
            otherMoviesInSet = database.getMovies(3, setId = correctAnswer['idSet'], excludeMovieIds = self._getMovieIds())
            for movie in otherMoviesInSet:
                self.addAnswer(movie['idMovie'], movie['title'], movie['idFile'], movie['strPath'], movie['strFileName'])

        # Find other movies in genre
        if len(self.answers) < 4:
            try:
                otherMoviesInGenre = database.getMovies(maxResults = 4 - len(self.answers), genres = correctAnswer['genre'], excludeMovieIds = self._getMovieIds())
                for movie in otherMoviesInGenre:
                    self.addAnswer(movie['idMovie'], movie['title'], movie['idFile'], movie['strPath'], movie['strFileName'])
            except db.DbException:
                pass # ignore in case user has no other movies in genre

        # Fill with random movies
        if len(self.answers) < 4:
            theRest = database.getMovies(maxResults = 4 - len(self.answers), excludeMovieIds = self._getMovieIds())
            for movie in theRest:
                self.addAnswer(movie['idMovie'], movie['title'], movie['idFile'], movie['strPath'], movie['strFileName'])

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_IS_THIS)
        videoDisplayType.setVideoFile(correctAnswer['strPath'], correctAnswer['strFileName'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatmovieisthis.enabled') == 'true'

class ActorNotInMovieQuestion(MovieQuestion):
    def __init__(self, database):
        """
        Actor not in movie?

        @type database: quizlib.db.Database
        @param database: Database connection instance to use
        """
        photoDisplayType = PhotoDisplayType()
        super(ActorNotInMovieQuestion, self).__init__(photoDisplayType)

        rows = database.getMovieActors(maxResults = 10, minMovieCount = 3)
        actor = None
        photoFile = None
        # try to find an actor with a cached photo (if non are found we bail out)
        for row in rows:
            photoFile = thumb.getCachedActorThumb(row['strActor'])
            if os.path.exists(photoFile):
                actor = row
                break
            else:
                print "Actor doesn't have a local photoFile"
                photoFile = None

        if actor is None:
            raise QuestionException("Didn't find any actors with photoFile")

        # Movies actor is not in
        movies = database.getMovies(maxResults = 1, actorIdNotInMovie = actor['idActor'])
        if not movies:
            raise QuestionException('No movies found')

        correctAnswer = movies[0]
        self.addCorrectAnswer(actor['idActor'], correctAnswer['title'], path = correctAnswer['strPath'], filename = correctAnswer['strFileName'])

        # Movie actor is in
        movies = database.getMovies(maxResults = 3, actorIdInMovie = actor['idActor'])
        for movie in movies:
            self.addCorrectAnswer(-1, movie['title'], path = movie['strPath'], filename = movie['strFileName'])

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_IS_ACTOR_NOT_IN, actor['strActor'])
        photoDisplayType.setPhotoFile(photoFile)

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.actornotinmovie.enabled') == 'true'


class WhatYearWasMovieReleasedQuestion(MovieQuestion):
    def __init__(self, database):
        """
        WhatYearWasMovieReleasedQuestion

        @type database: quizlib.db.Database
        @param database: Database connection instance to use
        """
        super(WhatYearWasMovieReleasedQuestion, self).__init__()

        movies = database.getMovies(maxResults = 1, minYear = 1900)
        if not movies:
            raise QuestionException('No movies found')

        row = movies[0]
        skew = random.randint(0, 10)
        minYear = int(row['year']) - skew
        maxYear = int(row['year']) + (10 - skew)

        thisYear = datetime.datetime.today().year
        if maxYear > thisYear:
            maxYear = thisYear
            minYear = thisYear - 10

        years = list()
        years.append(int(row['year']))
        while len(years) < 4:
            year = random.randint(minYear, maxYear)
            if not year in years:
                years.append(year)

        list.sort(years)

        for year in years:
            self.addAnswer(row['idFile'], str(year), row['idFile'], row['strPath'], row['strFileName'], correct = (year == int(row['year'])))

        self.text = strings(Q_WHAT_YEAR_WAS_MOVIE_RELEASED, row['title'])
        self.setFanartFile(row['strPath'], row['strFileName'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatyearwasmoviereleased.enabled') == 'true'


class WhatTagLineBelongsToMovieQuestion(MovieQuestion):
    def __init__(self, database):
        """
        WhatTagLineBelongsToMovieQuestion

        @type database: quizlib.db.Database
        @param database: Database connection instance to use
        """
        super(WhatTagLineBelongsToMovieQuestion, self).__init__()

        movies = database.getMovies(maxResults = 1, mustHaveTagline = True)
        if not movies:
            raise QuestionException('No movies found')
        row = movies[0]
        self.addCorrectAnswer(row['idMovie'], row['tagline'], row['idFile'], row['strPath'], row['strFileName'])

        otherAnswers = database.getMovies(maxResults = 3, excludeMovieIds = row['idMovie'], mustHaveTagline = True)
        for movie in otherAnswers:
            self.addAnswer(movie['idMovie'], movie['tagline'], row['idFile'], row['strPath'], row['strFileName'])

        if len(self.answers) < 3:
            raise QuestionException('Not enough taglines; got %d taglines' % len(self.answers))

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_TAGLINE_BELONGS_TO_MOVIE, row['title'])
        self.setFanartFile(row['strPath'], row['strFileName'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whattaglinebelongstomovie.enabled') == 'true'


class WhoDirectedThisMovieQuestion(MovieQuestion):
    def __init__(self, database):
        """
        WhoDirectedThisMovieQuestion

        @type database: quizlib.db.Database
        @param database: Database connection instance to use
        """
        super(WhoDirectedThisMovieQuestion, self).__init__()

        directors = database.getMovieDirectors(maxResults = 1, minMovieCount = 1)
        if not directors:
            raise QuestionException('No directors found')
        director = directors[0]

        movies = database.getMovies(maxResults = 1, directorId = director['idActor'])
        if not movies:
            raise QuestionException('No movies found')
        row = movies[0]
        self.addCorrectAnswer(director['idActor'], director['strActor'], row['idFile'], row['strPath'], row['strFileName'])

        otherAnswers = database.getMovieDirectors(maxResults = 3, excludeDirectorId = director['idActor'])
        for movie in otherAnswers:
            self.addAnswer(movie['idActor'], movie['strActor'], row['idFile'], row['strPath'], row['strFileName'])

        random.shuffle(self.answers)
        self.text = strings(Q_WHO_DIRECTED_THIS_MOVIE, row['title'])
        self.setFanartFile(row['strPath'], row['strFileName'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whodirectedthismovie.enabled') == 'true'


class WhatStudioReleasedMovieQuestion(MovieQuestion):
    def __init__(self, database):
        """
        WhatStudioReleasedMovieQuestion

        @type database: quizlib.db.Database
        @param database: Database connection instance to use
        """
        super(WhatStudioReleasedMovieQuestion, self).__init__()

        studios = database.getStudios(maxResults = 1)
        if not studios:
            raise QuestionException('No studios found')
        studio = studios[0]

        movies = database.getMovies(maxResults = 1, studioId = studio['idStudio'])
        if not movies:
            raise QuestionException('No movies found')
        row = movies[0]
        self.addCorrectAnswer(studio['idStudio'], studio['strStudio'], row['idFile'], row['strPath'], row['strFileName'])

        otherAnswers = database.getStudios(maxResults = 3, excludeStudioId = studio['idStudio'])
        for movie in otherAnswers:
            self.addAnswer(movie['idStudio'], movie['strStudio'], row['idFile'], row['strPath'], row['strFileName'])

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_STUDIO_RELEASED_MOVIE, row['title'])
        self.setFanartFile(row['strPath'], row['strFileName'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatstudioreleasedmovie.enabled') == 'true'


class WhatActorIsThisQuestion(MovieQuestion):
    def __init__(self, database):
        """
        WhatActorIsThisQuestion

        @type database: quizlib.db.Database
        @param database: Database connection instance to use
        """
        photoDisplayType = PhotoDisplayType()
        super(WhatActorIsThisQuestion, self).__init__(photoDisplayType)

        actor = None
        photoFile = None
        rows = database.getMovieActors(maxResults = 10, selectDistinct = True)
        # try to find an actor with a cached photo
        for row in rows:
            photoFile = thumb.getCachedActorThumb(row['strActor'])
            if os.path.exists(photoFile):
                actor = row
                break

        if actor is None:
            raise QuestionException("Didn't find any actors with photoFile")

        # The actor
        self.addCorrectAnswer(actor['idActor'], actor['strActor'])

        # Other actors
        actors = database.getMovieActors(maxResults = 50, excludeActorId = actor['idActor'], appendDefaultClause = False)

        # Check gender
        actorGender = IMDB.isActor(actor['strActor'])

        for actor in actors:
            if IMDB.isActor(actor['strActor']) == actorGender:
                self.addAnswer(actor['idActor'], actor['strActor'])
                if len(self.answers) == 4:
                    break

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_ACTOR_IS_THIS)
        photoDisplayType.setPhotoFile(photoFile)

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatactoristhis.enabled') == 'true'


class WhoPlayedRoleInMovieQuestion(MovieQuestion):
    def __init__(self, database):
        """
        WhoPlayedRoleInMovieQuestion

        @type database: quizlib.db.Database
        @param database: Database connection instance to use
        """
        super(WhoPlayedRoleInMovieQuestion, self).__init__()

        actors = database.getMovieActors(maxResults = 1, mustHaveRole = True)
        if not actors:
            raise QuestionException('No actors found')
        actor = actors[0]
        movies = database.getMovies(maxResults = 1, actorIdInMovie = actor['idActor'])
        if not movies:
            raise QuestionException('No movies found')
        movie = movies[0]
        role = actor['strRole']
        if re.search('[|/]', role):
            roles = re.split('[|/]', role)
            # find random role
            role = roles[random.randint(0, len(roles)-1)]

        self.addCorrectAnswer(actor['idActor'], actor['strActor'], path = thumb.getCachedActorThumb(actor['strActor']))

        actors = database.getMovieActors(maxResults = 3, excludeActorId = actor['idActor'], movieId = movie['idMovie'])
        for actor in actors:
            self.addAnswer(actor['idActor'], actor['strActor'], path = thumb.getCachedActorThumb(actor['strActor']))

        random.shuffle(self.answers)

        if self._isAnimationGenre(movie['genre']):
            self.text = strings(Q_WHO_VOICES_ROLE_IN_MOVIE) % (role, movie['title'])
        else:
            self.text = strings(Q_WHO_PLAYS_ROLE_IN_MOVIE) % (role, movie['title'])
        self.setFanartFile(movie['strPath'], movie['strFileName'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whoplayedroleinmovie.enabled') == 'true'


class WhatMovieIsThisQuoteFrom(MovieQuestion):
    def __init__(self, database):
        """
        WhatQuoteIsThisFrom

        @type database: quizlib.db.Database
        @param database: Database connection instance to use
        """
        quoteDisplayType = QuoteDisplayType()
        super(WhatMovieIsThisQuoteFrom, self).__init__(quoteDisplayType)

        rows = database.getMovies(maxResults = 10, minYear = 1900)
        quoteText = None
        row = None
        for r in rows:
            quoteText = IMDB.getRandomQuote(r['title'], maxLength = 128)

            if quoteText is not None:
                row = r
                break

        if quoteText is None:
            raise QuestionException('Did not find any quotes')

        self.addCorrectAnswer(row['idMovie'], row['title'], path = row['strPath'], filename = row['strFileName'])

        theRest = database.getMovies(maxResults = 3, excludeMovieIds = row['idMovie'])
        for movie in theRest:
            self.addAnswer(movie['idMovie'], movie['title'], path = movie['strPath'], filename = movie['strFileName'])

        random.shuffle(self.answers)
        quoteDisplayType.setQuoteText(quoteText)
        self.text = strings(Q_WHAT_MOVIE_IS_THIS_QUOTE_FROM)

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatmovieisthisquotefrom.enabled') == 'true' and IMDB.isDataPresent()


class WhatMovieIsNewestQuestion(MovieQuestion):
    def __init__(self, database):
        """
        WhatMovieIsNewestQuestion

        @type database: quizlib.db.Database
        @param database: Database connection instance to use
        """
        super(WhatMovieIsNewestQuestion, self).__init__()

        movies = database.getMovies(maxResults = 1, minYear = 1900)
        if not movies:
            raise QuestionException('No movies found')
        row = movies[0]
        self.addCorrectAnswer(row['idMovie'], row['title'], row['idFile'], row['strPath'], row['strFileName'])

        movies = database.getMovies(maxResults = 3, minYear = 1900, maxYear = row['year'])
        if len(movies) < 3:
            raise QuestionException("Less than 3 movies found; bailing out")

        for movie in movies:
            self.addAnswer(movie['idMovie'], movie['title'], path = movie['strPath'], filename = movie['strFileName'])

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_IS_THE_NEWEST)

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatmovieisnewest.enabled') == 'true'


class WhatMovieIsNotDirectedByQuestion(MovieQuestion):
    def __init__(self, database):
        """
        WhatMovieIsNotDirectedByQuestion

        @type database: quizlib.db.Database
        @param database: Database connection instance to use
        """
        photoDisplayType = PhotoDisplayType()
        super(WhatMovieIsNotDirectedByQuestion, self).__init__(photoDisplayType)

        rows = database.getMovieDirectors(maxResults = 10, minMovieCount = 3)

        director = None
        photoFile = None
        # try to find an actor with a cached photo (if non are found we bail out)
        for row in rows:
            photoFile = thumb.getCachedActorThumb(row['strActor'])
            if os.path.exists(photoFile):
                director = row
                break
            else:
                photoFile = None

        if director is None:
            raise QuestionException("Didn't find any directors with photoFile")

        # Movies not directed by director
        movies = database.getMovies(maxResults = 1, excludeDirectorId = director['idActor'])
        if not movies:
            raise QuestionException('No movies found')
        movie = movies[0]
        self.addCorrectAnswer(director['idActor'], movie['title'], path = movie['strPath'], filename = movie['strFileName'])
        
        # Movie actor is in
        movies = database.getMovies(maxResults = 3, directorId = director['idActor'])
        for movie in movies:
            self.addAnswer(-1, movie['title'], path = movie['strPath'], filename = movie['strFileName'])

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_IS_NOT_DIRECTED_BY, director['strActor'])
        photoDisplayType.setPhotoFile(photoFile)

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatmovieisnotdirectedby.enabled') == 'true'


class WhatActorIsInTheseMoviesQuestion(MovieQuestion):
    def __init__(self, database):
        """
        WhatActorIsInTheseMoviesQuestion

        @type database: quizlib.db.Database
        @param database: Database connection instance to use
        """
        threePhotoDisplayType = ThreePhotoDisplayType()
        super(WhatActorIsInTheseMoviesQuestion, self).__init__(threePhotoDisplayType)

        actors = database.getMovieActors(maxResults = 1, minMovieCount = 3)
        if not actors:
            raise QuestionException('No actors found')
        actor = actors[0]
        self.addCorrectAnswer(actor['idActor'], actor['strActor'], path = thumb.getCachedActorThumb(actor['strActor']))

        movieIds = list()
        rows = database.getMovies(maxResults = 3, actorIdInMovie = actor['idActor'])
        for row in rows:
            movieIds.append(row['idMovie'])
            photo = thumb.getCachedVideoThumb(row['strPath'], row['strFileName'])
            threePhotoDisplayType.addPhoto(photo, row['title'])

        otherActors = database.getMovieActors(maxResults = 3, excludeActorId = actor['idActor'], excludeMovieIds = movieIds)
        for other in otherActors:
            self.addAnswer(other['idActor'], other['strActor'], path = thumb.getCachedActorThumb(other['strActor']))

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_ACTOR_IS_IN_THESE_MOVIES)

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatactorisinthesemovies.enabled') == 'true'


class WhatActorIsInMovieBesidesOtherActorQuestion(MovieQuestion):
    def __init__(self, database):
        """
        WhatActorIsInMovieBesidesOtherActorQuestion

        @type database: quizlib.db.Database
        @param database: Database connection instance to use
        """
        super(WhatActorIsInMovieBesidesOtherActorQuestion, self).__init__()

        movies = database.getMovies(maxResults = 1, minActorCount = 3)
        if not movies:
            raise QuestionException('No movies found')
        movie = movies[0]
        actors = database.getMovieActors(maxResults = 2, movieId = movie['idMovie'])
        if len(actors) != 2:
            raise QuestionException('Not enough actors found')
        actorOne = actors[0]
        actorTwo = actors[1]
        self.addCorrectAnswer(actorOne['idActor'], actorOne['strActor'], path = thumb.getCachedActorThumb(actorOne['strActor']))

        otherActors = database.getMovieActors(maxResults = 3, excludeMovieIds = movie['idMovie'], excludeActorId = actorOne['idActor'])
        for actor in otherActors:
            self.addAnswer(actor['idActor'], actor['strActor'], path = thumb.getCachedActorThumb(actor['strActor']))

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_ACTOR_IS_IN_MOVIE_BESIDES_OTHER_ACTOR, (movie['title'], actorTwo['strActor']))
        self.setFanartFile(movie['strPath'], movie['strFileName'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatactorisinmoviebesidesotheractor.enabled') == 'true'

class WhatMovieHasTheLongestRuntimeQuestion(MovieQuestion):
    def __init__(self, database):
        """
        WhatMovieHasTheLongestRuntimeQuestion

        @type database: quizlib.db.Database
        @param database: Database connection instance to use
        """
        super(WhatMovieHasTheLongestRuntimeQuestion, self).__init__()

        movies = database.getMovies(maxResults = 1, mustHaveRuntime = True)
        if not movies:
            raise QuestionException('No movies found')
        correctAnswer = movies[0]
        self.addCorrectAnswer(correctAnswer['idMovie'], correctAnswer['title'], correctAnswer['idFile'], correctAnswer['strPath'], correctAnswer['strFileName'])

        movies = database.getMovies(maxResults = 3, mustHaveRuntime = True, maxRuntime = correctAnswer['runtime'])
        if len(movies) < 3:
            raise QuestionException("Less than 3 movies found; bailing out")

        for movie in movies:
            self.addAnswer(movie['idMovie'], movie['title'], path = movie['strPath'], filename = movie['strFileName'])

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_HAS_THE_LONGEST_RUNTIME)

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatmoviehaslongestruntime.enabled') == 'true'

#
# TV QUESTIONS
#

class TVQuestion(Question):
    def __init__(self, displayType = None):
        """

        @type displayType: DisplayType
        """
        super(TVQuestion, self).__init__(displayType)

    def _get_season_title(self, season):
        if not int(season):
            return strings(Q_SPECIALS)
        else:
            return strings(Q_SEASON_NO) % int(season)

    def _get_episode_title(self, season, episode, title):
        return "%dx%02d - %s" % (int(season), int(episode), title)


class WhatTVShowIsThisQuestion(TVQuestion):
    def __init__(self, database):
        """
        WhatTVShowIsThisQuestion

        @type database: quizlib.db.Database
        @param database: Database connection instance to use
        """
        videoDisplayType  = VideoDisplayType()
        super(WhatTVShowIsThisQuestion, self).__init__(videoDisplayType)

        shows = database.getTVShows(maxResults = 1)
        if not shows:
            raise QuestionException('No tvshows found')
        row = shows[0]
        self.addCorrectAnswer(row['idShow'], row['title'], row['idFile'], path = thumb.getCachedTVShowThumb(row['tvShowPath']))

        # Fill with random episodes from other shows
        shows = database.getTVShows(maxResults = 3, excludeTVShowId = row['idShow'], onlySelectTVShow = True)
        for show in shows:
            self.addAnswer(show['idShow'], show['title'], path = thumb.getCachedTVShowThumb(show['tvShowPath']))

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_TVSHOW_IS_THIS)
        videoDisplayType.setVideoFile(row['strPath'], row['strFileName'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whattvshowisthis.enabled') == 'true'


class WhatSeasonIsThisQuestion(TVQuestion):
    def __init__(self, database):
        """
        WhatSeasonIsThisQuestion

        @type database: quizlib.db.Database
        @param database: Database connection instance to use
        """
        videoDisplayType  = VideoDisplayType()
        super(WhatSeasonIsThisQuestion, self).__init__(videoDisplayType)

        rows = database.getTVShowSeasons(maxResults = 1, minSeasonCount = 3)
        if not rows:
            raise QuestionException('No tvshow seasons found')
        row = rows[0]
        cover = thumb.getCachedSeasonThumb(row['strPath'], self._get_season_title(row['season']))
        self.addCorrectAnswer("%s-%s" % (row['idShow'], row['season']), self._get_season_title(row['season']), row['idFile'], path = cover, sortWeight = row['season'])

        # Fill with random seasons from this show
        shows = database.getTVShowSeasons(maxResults = 3, onlySelectSeason = True, showId = row['idShow'], excludeSeason = row['season'])
        for show in shows:
            cover = thumb.getCachedSeasonThumb(row['strPath'], self._get_season_title(show['season']))
            self.addAnswer("%s-%s" % (row['idShow'], show['season']), self._get_season_title(show['season']), path = cover, sortWeight = show['season'])

        self.answers = sorted(self.answers, key=lambda answer: int(answer.sortWeight))

        self.text = strings(Q_WHAT_SEASON_IS_THIS) % row['title']
        videoDisplayType.setVideoFile(row['strPath'], row['strFileName'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatseasonisthis.enabled') == 'true'


class WhatEpisodeIsThisQuestion(TVQuestion):
    def __init__(self, database):
        """
        WhatEpisodeIsThisQuestion

        @type database: quizlib.db.Database
        @param database: Database connection instance to use
        """
        videoDisplayType  = VideoDisplayType()
        super(WhatEpisodeIsThisQuestion, self).__init__(videoDisplayType)

        rows = database.getTVShowEpisodes(maxResults = 1, minEpisodeCount = 3)
        if not rows:
            raise QuestionException('No tvshow episodes found')
        row = rows[0]
        answerText = self._get_episode_title(row['season'], row['episode'], row['episodeTitle'])
        id = "%s-%s-%s" % (row['idShow'], row['season'], row['episode'])
        cover = thumb.getCachedTVShowThumb(row['strPath'])
        self.addCorrectAnswer(id, answerText, row['idFile'], path = cover, sortWeight = row['episode'])

        # Fill with random episodes from this show
        episodes = database.getTVShowEpisodes(maxResults = 3, idShow = row['idShow'], season = row['season'], excludeEpisode = row['episode'])
        for episode in episodes:
            answerText = self._get_episode_title(episode['season'], episode['episode'], episode['episodeTitle'])
            id = "%s-%s-%s" % (row['idShow'], row['season'], episode['episode'])
            cover = thumb.getCachedTVShowThumb(row['strPath'])
            self.addAnswer(id, answerText, path = cover, sortWeight = episode['episode'])

        self.answers = sorted(self.answers, key=lambda answer: int(answer.sortWeight))

        self.text = strings(Q_WHAT_EPISODE_IS_THIS) % row['title']
        videoDisplayType.setVideoFile(row['strPath'], row['strFileName'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatepisodeisthis.enabled') == 'true'


class WhenWasTVShowFirstAiredQuestion(TVQuestion):
    def __init__(self, database):
        """
        WhenWasTVShowFirstAiredQuestion

        @type database: quizlib.db.Database
        @param database: Database connection instance to use
        """
        super(WhenWasTVShowFirstAiredQuestion, self).__init__()

        rows = database.getTVShows(maxResults = 1, excludeSpecials = True, episode = 1, mustHaveFirstAired = True)
        if not rows:
            raise QuestionException('no tvshows found')
        row = rows[0]
        row['year'] = time.strptime(row['firstAired'], '%Y-%m-%d').tm_year

        skew = random.randint(0, 10)
        minYear = int(row['year']) - skew
        maxYear = int(row['year']) + (10 - skew)

        thisYear = datetime.datetime.today().year
        if maxYear > thisYear:
            maxYear = thisYear
            minYear = thisYear - 10

        years = list()
        years.append(int(row['year']))
        while len(years) < 4:
            year = random.randint(minYear, maxYear)
            if not year in years:
                years.append(year)

        list.sort(years)

        for year in years:
            coverFile = thumb.getCachedTVShowThumb(row['strPath'])
            self.addAnswer(row['idFile'], str(year), row['idFile'], path = coverFile, correct = (year == int(row['year'])))

        self.text = strings(Q_WHEN_WAS_TVSHOW_FIRST_AIRED) % (row['title'] + ' - ' + self._get_season_title(row['season']))
        self.setFanartFile(row['strPath'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whenwastvshowfirstaired.enabled') == 'true'


class WhoPlayedRoleInTVShowQuestion(TVQuestion):
    def __init__(self, database):
        """
        WhoPlayedRoleInTVShowQuestion

        @type database: quizlib.db.Database
        @param database: Database connection instance to use
        """
        photoDisplayType = PhotoDisplayType()
        super(WhoPlayedRoleInTVShowQuestion, self).__init__(photoDisplayType)

        rows = database.getTVShowActors(maxResults = 1, mustHaveRole = True)
        if not rows:
            raise QuestionException('No tvshow actors found')
        row = rows[0]
        role = row['strRole']
        if re.search('[|/]', role):
            roles = re.split('[|/]', role)
            # find random role
            role = roles[random.randint(0, len(roles)-1)]

        self.addCorrectAnswer(row['idActor'], row['strActor'], path = thumb.getCachedActorThumb(row['strActor']))

        actors = database.getTVShowActors(maxResults = 3, onlySelectActor = True, showId = row['idShow'], excludeActorId = row['idActor'])
        for actor in actors:
            self.addAnswer(actor['idActor'], actor['strActor'], path = thumb.getCachedActorThumb(actor['strActor']))

        random.shuffle(self.answers)

        if self._isAnimationGenre(row['genre']):
            self.text = strings(Q_WHO_VOICES_ROLE_IN_TVSHOW) % (role, row['title'])
        else:
            self.text = strings(Q_WHO_PLAYS_ROLE_IN_TVSHOW) % (role, row['title'])
        photoDisplayType.setPhotoFile(thumb.getCachedTVShowThumb(row['strPath']))

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whoplayedroleintvshow.enabled') == 'true'

class WhatTVShowIsThisQuoteFrom(TVQuestion):
    def __init__(self, database):
        """
        WhatTVShowIsThisQuoteFrom

        @type database: quizlib.db.Database
        @param database: Database connection instance to use
        """
        quoteDisplayType = QuoteDisplayType()
        super(WhatTVShowIsThisQuoteFrom, self).__init__(quoteDisplayType)

        rows = database.getTVShows(maxResults = 1)
        if not rows:
            raise QuestionException('No tvshows found')
        row = rows[0]
        quoteText = IMDB.getRandomQuote(row['title'], season = row['season'], episode = row['episode'], maxLength = 128)
        if quoteText is None:
            raise QuestionException('Did not find any quotes')

        self.addCorrectAnswer(row['idShow'], row['title'], row['idFile'], path = thumb.getCachedTVShowThumb(row['tvShowPath']))

        # Fill with random episodes from other shows
        shows = database.getTVShows(maxResults = 3, excludeTVShowId = row['idShow'], onlySelectTVShow = True)
        for show in shows:
            self.addAnswer(show['idShow'], show['title'], path = thumb.getCachedTVShowThumb(show['tvShowPath']))

        random.shuffle(self.answers)
        quoteDisplayType.setQuoteText(quoteText)
        self.text = strings(Q_WHAT_TVSHOW_IS_THIS_QUOTE_FROM)

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whattvshowisthisquotefrom.enabled') == 'true' and IMDB.isDataPresent()

class WhatTVShowIsThisThemeFromQuestion(TVQuestion):
    def __init__(self, database):
        audioDisplayType = AudioDisplayType()
        super(WhatTVShowIsThisThemeFromQuestion, self).__init__(audioDisplayType)

        tvShow = None
        themeSong = None
        rows = database.getTVShows(maxResults = 10)
        for row in rows:
            themeSong = os.path.join(row['tvShowPath'], 'theme.mp3')
            if xbmcvfs.exists(themeSong):
                tvShow = row
                break

        if tvShow is None:
            raise QuestionException('Unable to find any tv shows with a theme.mp3 file')

        self.addCorrectAnswer(tvShow['idShow'], tvShow['title'], tvShow['idFile'], path = thumb.getCachedTVShowThumb(tvShow['tvShowPath']))

        # Fill with random episodes from other shows
        shows = database.getTVShows(maxResults = 3, excludeTVShowId = tvShow['idShow'], onlySelectTVShow = True)
        for show in shows:
            self.addAnswer(show['idShow'], show['title'], path = thumb.getCachedTVShowThumb(show['tvShowPath']))

        random.shuffle(self.answers)
        audioDisplayType.setAudioFile(themeSong)
        self.text = strings(Q_WHAT_TVSHOW_IS_THIS_THEME_FROM)

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whattvshowisthisthemefrom.enabled') == 'true'

class QuestionException(Exception):
    pass


def getRandomQuestion(gameInstance, database):
    """
        Gets random question from one of the Question subclasses.
    """
    questionCandidates = []
    if gameInstance.getType() == game.GAMETYPE_MOVIE:
        questionCandidates = MovieQuestion.__subclasses__()
    elif gameInstance.getType() == game.GAMETYPE_TVSHOW:
        questionCandidates = TVQuestion.__subclasses__()

    questionCandidates = [ candidate for candidate in questionCandidates if candidate.isEnabled() ]
    random.shuffle(questionCandidates)

    for candidate in questionCandidates:
        try:
            return candidate(database)
        except Exception, ex:
            xbmc.log("%s in %s" % (ex.__class__.__name__, candidate.__name__))
            import traceback, sys
            traceback.print_exc(file = sys.stdout)

    return None

def isAnyMovieQuestionsEnabled():
    subclasses = MovieQuestion.__subclasses__()
    subclasses  = [ subclass for subclass in subclasses if subclass.isEnabled() ]
    return subclasses

def isAnyTVShowQuestionsEnabled():
    subclasses = TVQuestion.__subclasses__()
    subclasses  = [ subclass for subclass in subclasses if subclass.isEnabled() ]
    return subclasses

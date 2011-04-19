import os
import random
import datetime
import thumb
import db
import time
import re
import imdb

from strings import *

TYPE_MOVIE = 1
TYPE_TV = 2

DISPLAY_NONE = 0
DISPLAY_VIDEO = 1
DISPLAY_PHOTO = 2
DISPLAY_QUOTE = 3
DISPLAY_THREE_PHOTOS = 4

class Answer(object):
    def __init__(self, correct, id, text, idFile = None, sortWeight = None):
        self.correct = correct
        self.id = id
        self.text = text
        self.idFile = idFile

        self.coverFile = None
        self.sortWeight = sortWeight

    def __str__(self):
        return "Answer(id=%s, text=%s, correct=%s)" % (self.id, self.text, self.correct)
        
    def setCoverFile(self, path, filename = None):
        if filename is None:
            self.coverFile = path
        else:
            self.coverFile = thumb.getCachedVideoThumb(path, filename)

class Question(object):
    ADDON = xbmcaddon.Addon(id = 'script.moviequiz')
    IMDB = imdb.Imdb(ADDON.getAddonInfo('profile'))
    
    def __init__(self, database, display, maxRating, onlyWatchedMovies):
        self.database = database
        self.answers = list()
        self.text = None
        self.videoFile = None
        self.fanartFile = None
        self.photos = list()
        self.quoteText = None

        self.display = display
        # Maximum allowed MPAA rating
        self.maxRating = maxRating
        self.onlyWatchedMovies = onlyWatchedMovies

    def getDisplay(self):
        return self.display

    def getText(self):
        return self.text

    def getAnswers(self):
        return self.answers

    def getAnswer(self, idx):
        try:
            return self.answers[idx]
        except IndexError:
            return None

    def getCorrectAnswer(self):
        for answer in self.answers:
            if answer.correct:
                return answer
        return None

    def getUniqueIdentifier(self):
        return "%s-%s" % (self.__class__.__name__, str(self.getCorrectAnswer().id))

    def setVideoFile(self, path, filename):
        if filename[0:8] == 'stack://':
            self.videoFile = filename
        else:
            self.videoFile = os.path.join(path, filename)

    def getVideoFile(self):
        return self.videoFile

    def addPhoto(self, photo):
        self.photos.append(photo)

    def getPhotoFile(self, index = 0):
        return self.photos[index]

    def setQuoteText(self, quoteText):
        self.quoteText = quoteText

    def getQuoteText(self):
        return self.quoteText

    def setFanartFile(self, path, filename = None):
        self.fanartFile = thumb.getCachedVideoFanart(path, filename)

    def getFanartFile(self):
        return self.fanartFile

    def _get_movie_ids(self):
        movieIds = list()
        for movie in self.answers:
            movieIds.append(movie.id)
        return ','.join(map(str, movieIds))

    def _isAnimated(self, genre):
        return genre.lower().find("animation") != -1

#
# MOVIE QUESTIONS
#

class MovieQuestion(Question):
    MPAA_RATINGS = ['R', 'Rated R', 'PG-13', 'Rated PG-13', 'PG', 'Rated PG', 'G', 'Rated G']

    def __init__(self, database, display, maxRating, onlyWatchedMovies):
        Question.__init__(self, database, display, maxRating, onlyWatchedMovies)

    def _get_max_rating_clause(self):
        if self.maxRating is None:
            return ''

        idx = self.MPAA_RATINGS.index(self.maxRating)
        ratings = self.MPAA_RATINGS[idx:]

        return ' AND TRIM(c12) IN (\'%s\')' % '\',\''.join(ratings)

    def _get_watched_movies_clause(self):
        if self.onlyWatchedMovies:
            return ' AND mv.playCount IS NOT NULL'
        else:
            return ''



class WhatMovieIsThisQuestion(MovieQuestion):
    """
        WhatMovieIsThisQuestion
    """

    def __init__(self, database, maxRating, onlyWatchedMovies):
        MovieQuestion.__init__(self, database, DISPLAY_VIDEO, maxRating, onlyWatchedMovies)

        row = self.database.fetchone("""
            SELECT mv.idMovie, mv.idFile, mv.c00 AS title, mv.c14 AS genre, mv.strPath, mv.strFileName, slm.idSet
            FROM movieview mv LEFT JOIN setlinkmovie slm ON mv.idMovie = slm.idMovie
            WHERE mv.strFileName NOT LIKE '%%.nfo'
            %s %s
            ORDER BY random() LIMIT 1
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()))
        a = Answer(True, row['idMovie'], row['title'], row['idFile'])
        a.setCoverFile(row['strPath'], row['strFileName'])
        self.answers.append(a)

        # Find other movies in set
        if row['idSet'] is not None:
            otherMoviesInSet = self.database.fetchall("""
                SELECT mv.idMovie, mv.idFile, mv.c00 AS title, mv.strPath, mv.strFileName
                FROM movieview mv, setlinkmovie slm
                WHERE mv.idMovie = slm.idMovie AND slm.idSet = ? AND mv.idMovie != ? AND title != ? AND mv.strFileName NOT LIKE '%%.nfo'
                %s %s
                ORDER BY random() LIMIT 3
                """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()), (row['idSet'], row['idMovie'], row['title']))
            for movie in otherMoviesInSet:
                a = Answer(False, movie['idMovie'], movie['title'], movie['idFile'])
                a.setCoverFile(movie['strPath'], movie['strFileName'])
                self.answers.append(a)

        # Find other movies in genre
        if len(self.answers) < 4:
            try:
                otherMoviesInGenre = self.database.fetchall("""
                    SELECT mv.idMovie, mv.idFile, mv.c00 AS title, mv.c14 AS genre, mv.strPath, mv.strFileName
                    FROM movieview mv
                    WHERE mv.c14 = ? AND mv.idMovie NOT IN (%s) AND mv.c00 != ? AND mv.strFileName NOT LIKE '%%.nfo'
                    %s %s
                    ORDER BY random() LIMIT %d
                    """ % (self._get_movie_ids(), self._get_max_rating_clause(), self._get_watched_movies_clause(), 4 - len(self.answers)),
                        (row['genre'], row['title'], ))
                for movie in otherMoviesInGenre:
                    a = Answer(False, movie['idMovie'], movie['title'], movie['idFile'])
                    a.setCoverFile(movie['strPath'], movie['strFileName'])
                    self.answers.append(a)
            except db.DbException:
                pass # ignore in case user has no other movies in genre

        # Fill with random movies
        if len(self.answers) < 4:
            theRest = self.database.fetchall("""
                SELECT mv.idMovie, mv.idFile, mv.c00 AS title, mv.strPath, mv.strFileName
                FROM movieview mv
                WHERE mv.idMovie NOT IN (%s) AND mv.c00 != ? AND mv.strFileName NOT LIKE '%%.nfo'
                %s %s
                ORDER BY random() LIMIT %d
                """ % (self._get_movie_ids(), self._get_max_rating_clause(), self._get_watched_movies_clause(), 4 - len(self.answers)),
                         row['title'])
            for movie in theRest:
                a = Answer(False, movie['idMovie'], movie['title'], movie['idFile'])
                a.setCoverFile(movie['strPath'], movie['strFileName'])
                self.answers.append(a)
            print self._get_movie_ids()

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_IS_THIS)
        self.setVideoFile(row['strPath'], row['strFileName'])


class ActorNotInMovieQuestion(MovieQuestion):
    """
        ActorNotInMovieQuestion
    """
    def __init__(self, database, maxRating, onlyWatchedMovies):
        MovieQuestion.__init__(self, database, DISPLAY_PHOTO, maxRating, onlyWatchedMovies)

        actor = None
        photoFile = None
        rows = self.database.fetchall("""
            SELECT a.idActor, a.strActor
            FROM movieview mv, actorlinkmovie alm, actors a
            WHERE mv.idMovie = alm.idMovie AND alm.idActor = a.idActor AND mv.strFileName NOT LIKE '%%.nfo'
            %s %s
            GROUP BY alm.idActor HAVING count(mv.idMovie) >= 3 ORDER BY random() LIMIT 10
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()))
        # try to find an actor with a cached photo (if non are found we bail out)
        for row in rows:
            photoFile = thumb.getCachedActorThumb(row['strActor'])
            if os.path.exists(photoFile):
                actor = row
                break
            else:
                print "Skipping actor: %s" % row['strActor']
                photoFile = None

        if actor is None:
            raise QuestionException("Didn't find any actors with photoFile")

        # Movies actor is not in
        row = self.database.fetchone("""
            SELECT mv.idMovie, mv.c00 AS title, mv.strPath, mv.strFileName
            FROM movieview mv WHERE mv.idMovie NOT IN (
                SELECT DISTINCT alm.idMovie FROM actorlinkmovie alm WHERE alm.idActor = ?
            ) AND mv.strFileName NOT LIKE '%%.nfo'
            %s %s
            ORDER BY random() LIMIT 1
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()), actor['idActor'])
        a = Answer(True, actor['idActor'], row['title'])
        a.setCoverFile(row['strPath'], row['strFileName'])
        self.answers.append(a)

        # Movie actor is in
        movies = self.database.fetchall("""
            SELECT mv.idMovie, mv.c00 AS title, mv.strPath, mv.strFileName
            FROM movieview mv, actorlinkmovie alm WHERE mv.idMovie = alm.idMovie AND alm.idActor = ? AND mv.strFileName NOT LIKE '%%.nfo'
            %s %s
            ORDER BY random() LIMIT 3
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()), actor['idActor'])
        for movie in movies:
            a = Answer(False, -1, movie['title'])
            a.setCoverFile(movie['strPath'], movie['strFileName'])
            self.answers.append(a)

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_IS_ACTOR_NOT_IN, actor['strActor'])
        self.addPhoto(photoFile)



class WhatYearWasMovieReleasedQuestion(MovieQuestion):
    """
        WhatYearWasMovieReleasedQuestion
    """
    def __init__(self, database, maxRating, onlyWatchedMovies):
        MovieQuestion.__init__(self, database, DISPLAY_NONE, maxRating, onlyWatchedMovies)

        row = self.database.fetchone("""
            SELECT mv.idFile, mv.c00 AS title, mv.c07 AS year, mv.strPath, mv.strFileName
            FROM movieview mv WHERE mv.c07 > 1900 AND mv.strFileName NOT LIKE '%%.nfo'
            %s %s
            ORDER BY random() LIMIT 1
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()))

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
            a = Answer(year == int(row['year']), row['idFile'], str(year), row['idFile'])
            a.setCoverFile(row['strPath'], row['strFileName'])
            self.answers.append(a)

        self.text = strings(Q_WHAT_YEAR_WAS_MOVIE_RELEASED, row['title'])
#        self.setVideoFile(row['strPath'], row['strFileName'])
        self.setFanartFile(row['strPath'], row['strFileName'])


class WhatTagLineBelongsToMovieQuestion(MovieQuestion):
    """
        WhatTagLineBelongsToMovieQuestion
    """
    def __init__(self, database, maxRating, onlyWatchedMovies):
        MovieQuestion.__init__(self, database, DISPLAY_NONE, maxRating, onlyWatchedMovies)

        row = self.database.fetchone("""
            SELECT mv.idMovie, mv.idFile, mv.c00 AS title, mv.c03 AS tagline, mv.strPath, mv.strFileName
            FROM movieview mv WHERE TRIM(mv.c03) != \'\' AND mv.strFileName NOT LIKE '%%.nfo'
            %s %s
            ORDER BY random() LIMIT 1
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()))
        a = Answer(True, row['idMovie'], row['tagline'], row['idFile'])
        a.setCoverFile(row['strPath'], row['strFileName'])
        self.answers.append(a)

        otherAnswers = self.database.fetchall("""
            SELECT mv.idMovie, mv.idFile, mv.c03 AS tagline, mv.strPath, mv.strFileName
            FROM movieview mv WHERE TRIM(mv.c03) != \'\' AND mv.idMovie != ? AND c00 != ? AND mv.strFileName NOT LIKE '%%.nfo'
            %s %s
            ORDER BY random() LIMIT 3
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()), (row['idMovie'], row['title']))
        for movie in otherAnswers:
            a = Answer(False, movie['idMovie'], movie['tagline'], row['idFile'])
            a.setCoverFile(row['strPath'], row['strFileName'])
            self.answers.append(a)

        if len(self.answers) < 3:
            raise QuestionException('Not enough taglines; got %d taglines' % len(self.answers))

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_TAGLINE_BELONGS_TO_MOVIE, row['title'])
#        self.setVideoFile(row['strPath'], row['strFileName'])
        self.setFanartFile(row['strPath'], row['strFileName'])


class WhoDirectedThisMovieQuestion(MovieQuestion):
    """
        WhoDirectedThisMovieQuestion
    """
    def __init__(self, database, maxRating, onlyWatchedMovies):
        MovieQuestion.__init__(self, database, DISPLAY_NONE, maxRating, onlyWatchedMovies)

        row = self.database.fetchone("""
            SELECT idActor, a.strActor, mv.idFile, mv.c00 AS title, mv.strPath, mv.strFileName
            FROM movieview mv, directorlinkmovie dlm, actors a
            WHERE mv.idMovie = dlm.idMovie AND dlm.idDirector = a.idActor AND mv.strFileName NOT LIKE '%%.nfo'
            %s %s
            ORDER BY random() LIMIT 1
        """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()))
        a = Answer(True, row['idActor'], row['strActor'], row['idFile'])
        a.setCoverFile(row['strPath'], row['strFileName'])
        self.answers.append(a)

        otherAnswers = self.database.fetchall("""
            SELECT a.idActor, a.strActor
            FROM actors a
            WHERE a.idActor != ?
            ORDER BY random() LIMIT 3
        """, row['idActor'])
        for movie in otherAnswers:
            a = Answer(False, movie['idActor'], movie['strActor'], row['idFile'])
            a.setCoverFile(row['strPath'], row['strFileName'])
            self.answers.append(a)

        random.shuffle(self.answers)
        self.text = strings(Q_WHO_DIRECTED_THIS_MOVIE, row['title'])
#        self.setVideoFile(row['strPath'], row['strFileName'])
        self.setFanartFile(row['strPath'], row['strFileName'])


class WhatStudioReleasedMovieQuestion(MovieQuestion):
    """
        WhatStudioReleasedMovieQuestion
    """
    def __init__(self, database, maxRating, onlyWatchedMovies):
        MovieQuestion.__init__(self, database, DISPLAY_NONE, maxRating, onlyWatchedMovies)

        row = self.database.fetchone("""
            SELECT s.idStudio, s.strStudio, mv.idFile, mv.c00 AS title, mv.strPath, mv.strFileName
            FROM movieview mv, studiolinkmovie slm, studio s
            WHERE mv.idMovie = slm.idMovie AND slm.idStudio = s.idStudio AND mv.strFileName NOT LIKE '%%.nfo'
            %s %s
            ORDER BY random() LIMIT 1
        """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()))
        a = Answer(True, row['idStudio'], row['strStudio'], row['idFile'])
        a.setCoverFile(row['strPath'], row['strFileName'])
        self.answers.append(a)

        otherAnswers = self.database.fetchall("""
            SELECT s.idStudio, s.strStudio
            FROM studio s
            WHERE s.idStudio != ?
            AND s.idStudio IN (SELECT idStudio FROM studiolinkmovie)
            ORDER BY random() LIMIT 3
        """, row['idStudio'])
        for movie in otherAnswers:
            a = Answer(False, movie['idStudio'], movie['strStudio'], row['idFile'])
            a.setCoverFile(row['strPath'], row['strFileName'])
            self.answers.append(a)

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_STUDIO_RELEASED_MOVIE, row['title'])
#        self.setVideoFile(row['strPath'], row['strFileName'])
        self.setFanartFile(row['strPath'], row['strFileName'])


class WhatActorIsThisQuestion(MovieQuestion):
    """
        WhatActorIsThisQuestion
    """
    def __init__(self, database, maxRating, onlyWatchedMovies):
        MovieQuestion.__init__(self, database, DISPLAY_PHOTO, maxRating, onlyWatchedMovies)

        actor = None
        photoFile = None
        rows = self.database.fetchall("""
            SELECT DISTINCT a.idActor, a.strActor
            FROM actors a, actorlinkmovie alm, movieview mv
            WHERE a.idActor = alm.idActor AND alm.idMovie=mv.idMovie AND mv.strFileName NOT LIKE '%%.nfo'
            %s
            ORDER BY random() LIMIT 10
            """ % self._get_watched_movies_clause())
        # try to find an actor with a cached photo (if non are found we simply use the last actor selected)
        for row in rows:
            photoFile = thumb.getCachedActorThumb(row['strActor'])
            if os.path.exists(photoFile):
                actor = row
                break
            else:
                photoFile = None

        if actor is None:
            raise QuestionException("Didn't find any actors with photoFile")

        # The actor
        a = Answer(True, actor['idActor'], actor['strActor'])
        self.answers.append(a)

        # Other actors
        actors = self.database.fetchall("""
            SELECT a.idActor, a.strActor
            FROM actors a, actorlinkmovie alm WHERE a.idActor = alm.idActor AND a.idActor != ?
            ORDER BY random() LIMIT 50
            """, actor['idActor'])

        # Check gender
        actorGender = self.IMDB.isActor(actor['strActor'])

        for actor in actors:
            if self.IMDB.isActor(actor['strActor']) == actorGender:
                self.answers.append(Answer(False, actor['idActor'], actor['strActor']))
                if len(self.answers) == 4:
                    break

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_ACTOR_IS_THIS)
        self.addPhoto(photoFile)

class WhoPlayedRoleInMovieQuestion(MovieQuestion):
    """
        WhoPlayedRoleInMovieQuestion
    """
    def __init__(self, database, maxRating, onlyWatchedMovies):
        MovieQuestion.__init__(self, database, DISPLAY_NONE, maxRating, onlyWatchedMovies)

        row = self.database.fetchone("""
            SELECT alm.idActor, a.strActor, alm.strRole, mv.idMovie, mv.c00 AS title, mv.strPath, mv.strFileName, mv.c14 AS genre
            FROM movieview mv, actorlinkmovie alm, actors a
            WHERE mv.idMovie=alm.idMovie AND alm.idActor=a.idActor AND alm.strRole != '' AND mv.strFileName NOT LIKE '%%.nfo'
            %s %s
            ORDER BY random() LIMIT 1
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()))
        role = row['strRole']
        if re.search('[|/]', role):
            roles = re.split('[|/]', role)
            # find random role
            role = roles[random.randint(0, len(roles)-1)]

        a = Answer(True, row['idActor'], row['strActor'])
        a.setCoverFile(thumb.getCachedActorThumb(row['strActor']))
        self.answers.append(a)

        shows = self.database.fetchall("""
            SELECT alm.idActor, a.strActor, alm.strRole
            FROM actorlinkmovie alm, actors a
            WHERE alm.idActor=a.idActor AND alm.idMovie = ? AND alm.idActor != ?
            ORDER BY random() LIMIT 3
            """, (row['idMovie'], row['idActor']))
        for show in shows:
            a = Answer(False, show['idActor'], show['strActor'])
            a.setCoverFile(thumb.getCachedActorThumb(show['strActor']))
            self.answers.append(a)

        random.shuffle(self.answers)

        if self._isAnimated(row['genre']):
            self.text = strings(Q_WHO_VOICES_ROLE_IN_MOVIE) % (role, row['title'])
        else:
            self.text = strings(Q_WHO_PLAYS_ROLE_IN_MOVIE) % (role, row['title'])
#        self.setVideoFile(row['strPath'], row['strFileName'])
        self.setFanartFile(row['strPath'], row['strFileName'])

        
class WhatMovieIsThisQuoteFrom(MovieQuestion):
    """
        WhatQuoteIsThisFrom
    """
    def __init__(self, database, maxRating, onlyWatchedMovies):
        MovieQuestion.__init__(self, database, DISPLAY_QUOTE, maxRating, onlyWatchedMovies)
        rows = self.database.fetchall("""
            SELECT mv.idMovie, mv.c00 AS title, mv.c07 AS year, mv.strPath, mv.strFileName
            FROM movieview mv
            WHERE mv.c07 > 1900 AND mv.strFileName NOT LIKE '%%.nfo'
            %s %s
            ORDER BY random() LIMIT 10
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()))
        quoteText = None
        row = None
        for r in rows:
            quoteText = Question.IMDB.getRandomQuote(r['title'], maxLength = 256)

            if quoteText is not None:
                row = r
                break

        if quoteText is None:
            raise QuestionException('Did not find any quotes')

        a = Answer(True, row['idMovie'], row['title'])
        a.setCoverFile(row['strPath'], row['strFileName'])
        self.answers.append(a)

        theRest = self.database.fetchall("""
            SELECT mv.idMovie, mv.c00 AS title, mv.strPath, mv.strFileName
            FROM movieview mv WHERE mv.idMovie != ? AND mv.c00 != ? AND mv.strFileName NOT LIKE '%%.nfo'
            %s %s
            ORDER BY random() LIMIT 3
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()),
                     (row['idMovie'], row['title']))
        for movie in theRest:
            a = Answer(False, movie['idMovie'], movie['title'])
            a.setCoverFile(movie['strPath'], movie['strFileName'])
            self.answers.append(a)

        random.shuffle(self.answers)
        self.setQuoteText(quoteText)
        self.text = strings(Q_WHAT_MOVIE_IS_THIS_QUOTE_FROM)


class WhatMovieIsNewestQuestion(MovieQuestion):
    """
        WhatMovieIsNewestQuestion
    """
    def __init__(self, database, maxRating, onlyWatchedMovies):
        MovieQuestion.__init__(self, database, DISPLAY_NONE, maxRating, onlyWatchedMovies)
        row = self.database.fetchone("""
            SELECT mv.idMovie, mv.idFile, mv.c00 AS title, mv.strPath, mv.strFileName, mv.c07 AS year
            FROM movieview mv
            WHERE mv.c07 > 1900 AND mv.strFileName NOT LIKE '%%.nfo'
            %s %s
            ORDER BY random() LIMIT 1
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()))
        a = Answer(True, row['idMovie'], row['title'], row['idFile'])
        a.setCoverFile(row['strPath'], row['strFileName'])
        self.answers.append(a)

        movies = self.database.fetchall("""
            SELECT mv.idMovie, mv.c00 AS title, mv.strPath, mv.strFileName, mv.c07 AS year
            FROM movieview mv
            WHERE mv.c07 > 1900 AND mv.c07 < ?
            %s %s
            ORDER BY random() LIMIT 3
        """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()), row['year'])
        if len(movies) < 3:
            raise QuestionException("Less than 3 movies found; bailing out")

        for movie in movies:
            a = Answer(False, movie['idMovie'], movie['title'])
            a.setCoverFile(movie['strPath'], movie['strFileName'])
            self.answers.append(a)

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_IS_THE_NEWEST)

class WhatMovieIsNotDirectedByQuestion(MovieQuestion):
    """
        WhatMovieIsNotDirectedByQuestion
    """
    def __init__(self, database, maxRating, onlyWatchedMovies):
        MovieQuestion.__init__(self, database, DISPLAY_PHOTO, maxRating, onlyWatchedMovies)

        director = None
        photoFile = None
        rows = self.database.fetchall("""
            SELECT a.idActor, a.strActor
            FROM movieview mv, directorlinkmovie dlm, actors a
            WHERE mv.idMovie = dlm.idMovie AND dlm.idDirector = a.idActor AND mv.strFileName NOT LIKE '%%.nfo'
            %s %s
            GROUP BY dlm.idDirector HAVING count(mv.idMovie) >= 3 ORDER BY random() LIMIT 10
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()))
        # try to find an actor with a cached photo (if non are found we bail out)
        for row in rows:
            print row['strActor']
            photoFile = thumb.getCachedActorThumb(row['strActor'])
            if os.path.exists(photoFile):
                director = row
                break
            else:
                print "Skipping actor: %s" % row['strActor']
                photoFile = None

        if director is None:
            raise QuestionException("Didn't find any directors with photoFile")

        # Movies not directed by director
        row = self.database.fetchone("""
            SELECT mv.idMovie, mv.c00 AS title, mv.strPath, mv.strFileName
            FROM movieview mv WHERE mv.idMovie NOT IN (
                SELECT DISTINCT dlm.idMovie FROM directorlinkmovie dlm WHERE dlm.idDirector = ?
            ) AND mv.strFileName NOT LIKE '%%.nfo'
            %s %s
            ORDER BY random() LIMIT 1
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()), director['idActor'])
        a = Answer(True, director['idActor'], row['title'])
        a.setCoverFile(row['strPath'], row['strFileName'])
        self.answers.append(a)

        # Movie actor is in
        movies = self.database.fetchall("""
            SELECT mv.idMovie, mv.c00 AS title, mv.strPath, mv.strFileName
            FROM movieview mv, directorlinkmovie dlm WHERE mv.idMovie = dlm.idMovie AND dlm.idDirector = ? AND mv.strFileName NOT LIKE '%%.nfo'
            %s %s
            ORDER BY random() LIMIT 3
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()), director['idActor'])
        for movie in movies:
            a = Answer(False, -1, movie['title'])
            a.setCoverFile(movie['strPath'], movie['strFileName'])
            self.answers.append(a)

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_IS_NOT_DIRECTED_BY, director['strActor'])
        self.addPhoto(photoFile)


class WhatActorIsInTheseMoviesQuestion(MovieQuestion):
    def __init__(self, database, maxRating, onlyWatchedMovies):
        MovieQuestion.__init__(self, database, DISPLAY_THREE_PHOTOS, maxRating, onlyWatchedMovies)

        actor = self.database.fetchone("""
            SELECT a.idActor, a.strActor
            FROM movieview mv, actorlinkmovie alm, actors a
            WHERE mv.idMovie = alm.idMovie AND alm.idActor = a.idActor AND mv.strFileName NOT LIKE '%%.nfo'
            %s %s
            GROUP BY alm.idActor HAVING count(mv.idMovie) >= 3 ORDER BY random() LIMIT 1
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()))
        a = Answer(True, actor['idActor'], actor['strActor'])
        a.setCoverFile(thumb.getCachedActorThumb(actor['strActor']))
        self.answers.append(a)

        rows = self.database.fetchall("""
            SELECT mv.idMovie, mv.c00 AS title, mv.strPath, mv.strFileName
            FROM movieview mv, actorlinkmovie alm
            WHERE mv.idMovie=alm.idMovie AND alm.idActor=? AND mv.strFileName NOT LIKE '%%.nfo'
            %s %s
            ORDER BY random() LIMIT 3
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()), actor['idActor'])
        for row in rows:
            self.addPhoto(thumb.getCachedVideoThumb(row['strPath'], row['strFileName']))

        otherActors = self.database.fetchall("""
            SELECT a.idActor, a.strActor
            FROM movieview mv, actorlinkmovie alm, actors a
            WHERE mv.idMovie = alm.idMovie AND alm.idActor = a.idActor AND mv.strFileName NOT LIKE '%%.nfo'
            %s %s
            GROUP BY alm.idActor HAVING count(mv.idMovie) < 3 ORDER BY random() LIMIT 3
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()))
        for other in otherActors:
            a = Answer(False, other['idActor'], other['strActor'])
            a.setCoverFile(thumb.getCachedActorThumb(other['strActor']))
            self.answers.append(a)

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_ACTOR_IS_IN_THESE_MOVIES)

#
# TV QUESTIONS
#

class TVQuestion(Question):
    CONTENT_RATINGS = ['TV-MA', 'TV-14', 'TV-PG', 'TV-G', 'TV-Y7-FV', 'TV-Y7', 'TV-Y']
    
    def __init__(self, database, display, maxRating, onlyWatchedMovies):
        Question.__init__(self, database, display, maxRating, onlyWatchedMovies)

    def _get_watched_episodes_clause(self):
        if self.onlyWatchedMovies:
            return ' AND ev.playCount IS NOT NULL'
        else:
            return ''

    def _get_max_rating_clause(self):
        if self.maxRating is None:
            return ''

        idx = self.CONTENT_RATINGS.index(self.maxRating)
        ratings = self.CONTENT_RATINGS[idx:]

        return ' AND TRIM(tv.c13) IN (\'%s\')' % '\',\''.join(ratings)

    def _get_season_title(self, season):
        if not int(season):
            return strings(Q_SPECIALS)
        else:
            return strings(Q_SEASON_NO) % int(season)

    def _get_episode_title(self, season, episode, title):
        return "%dx%02d - %s" % (int(season), int(episode), title)


class WhatTVShowIsThisQuestion(TVQuestion):
    """
        WhatTVShowIsThisQuestion
    """

    def __init__(self, database, maxRating, onlyWatchedMovies):
        TVQuestion.__init__(self, database, DISPLAY_VIDEO, maxRating, onlyWatchedMovies)

        row = self.database.fetchone("""
            SELECT ev.idFile, tv.c00 AS title, ev.idShow, ev.strPath, ev.strFileName, tv.strPath AS showPath
            FROM episodeview ev, tvshowview tv
            WHERE ev.idShow=tv.idShow AND ev.strFileName NOT LIKE '%%.nfo'
            %s %s
            ORDER BY random() LIMIT 1
            """ % (self._get_watched_episodes_clause(), self._get_max_rating_clause()))
        a = Answer(True, row['idShow'], row['title'], row['idFile'])
        a.setCoverFile(thumb.getCachedTVShowThumb(row['showPath']))
        self.answers.append(a)

        # Fill with random episodes from other shows
        shows = self.database.fetchall("""
            SELECT tv.idShow, tv.c00 AS title, tv.strPath
            FROM tvshowview tv
            WHERE tv.idShow != ?
            ORDER BY random() LIMIT 3
            """, row['idShow'])
        for show in shows:
            a = Answer(False, show['idShow'], show['title'])
            a.setCoverFile(thumb.getCachedTVShowThumb(show['strPath']))
            self.answers.append(a)

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_TVSHOW_IS_THIS)
        self.setVideoFile(row['strPath'], row['strFileName'])
#        self.setFanartFile(row['strPath'], row['strFileName'])


class WhatSeasonIsThisQuestion(TVQuestion):
    """
        WhatSeasonIsThisQuestion
    """

    def __init__(self, database, maxRating, onlyWatchedMovies):
        TVQuestion.__init__(self, database, DISPLAY_VIDEO, maxRating, onlyWatchedMovies)

        row = self.database.fetchone("""
            SELECT ev.idFile, ev.c12 AS season, tv.c00 AS title, ev.idShow, ev.strPath, ev.strFileName, tv.strPath AS showPath,
                (SELECT COUNT(DISTINCT c12) FROM episodeview WHERE idShow=ev.idShow) AS seasons
            FROM episodeview ev, tvshowview tv
            WHERE ev.idShow=tv.idShow AND seasons > 2 AND ev.strFileName NOT LIKE '%%.nfo'
            %s %s
            ORDER BY random() LIMIT 1
            """ % (self._get_watched_episodes_clause(), self._get_max_rating_clause()))
        a = Answer(True, "%s-%s" % (row['idShow'], row['season']), self._get_season_title(row['season']), row['idFile'], sortWeight = row['season'])
        a.setCoverFile(thumb.getCachedSeasonThumb(row['strPath'], self._get_season_title(row['season'])))
        self.answers.append(a)

        # Fill with random seasons from this show
        shows = self.database.fetchall("""
            SELECT DISTINCT ev.c12 AS season
            FROM episodeview ev
            WHERE ev.idShow = ? AND ev.c12 != ? AND ev.strFileName NOT LIKE '%%.nfo'
            ORDER BY random() LIMIT 3
            """, (row['idShow'], row['season']))
        for show in shows:
            a = Answer(False, "%s-%s" % (row['idShow'], show['season']), self._get_season_title(show['season']), sortWeight = show['season'])
            a.setCoverFile(thumb.getCachedSeasonThumb(row['strPath'], self._get_season_title(show['season'])))
            self.answers.append(a)

        self.answers = sorted(self.answers, key=lambda answer: int(answer.sortWeight))

        self.text = strings(Q_WHAT_SEASON_IS_THIS) % row['title']
        self.setVideoFile(row['strPath'], row['strFileName'])
#        self.setFanartFile(row['strPath'], row['strFileName'])


class WhatEpisodeIsThisQuestion(TVQuestion):
    """
        WhatEpisodeIsThisQuestion
    """

    def __init__(self, database, maxRating, onlyWatchedMovies):
        TVQuestion.__init__(self, database, DISPLAY_VIDEO, maxRating, onlyWatchedMovies)

        row = self.database.fetchone("""
            SELECT ev.idFile, ev.c00 AS episodeTitle, ev.c12 AS season, ev.c13 AS episode, tv.c00 AS title, ev.idShow, ev.strPath, ev.strFileName,
                (SELECT COUNT(DISTINCT c13) FROM episodeview WHERE idShow=ev.idShow) AS episodes
            FROM episodeview ev, tvshowview tv
            WHERE ev.idShow=tv.idShow AND episodes > 2 AND ev.strFileName NOT LIKE '%%.nfo'
            %s %s
            ORDER BY random() LIMIT 1
            """ % (self._get_watched_episodes_clause(), self._get_max_rating_clause()))
        answerText = self._get_episode_title(row['season'], row['episode'], row['episodeTitle'])
        id = "%s-%s-%s" % (row['idShow'], row['season'], row['episode'])
        a = Answer(True, id, answerText, row['idFile'], sortWeight = row['episode'])
        a.setCoverFile(thumb.getCachedTVShowThumb(row['strPath']))
        self.answers.append(a)

        # Fill with random episodes from this show
        shows = self.database.fetchall("""
            SELECT ev.c00 AS episodeTitle, ev.c12 AS season, ev.c13 AS episode
            FROM episodeview ev
            WHERE ev.idShow = ? AND ev.c12 = ? AND ev.c13 != ? AND ev.strFileName NOT LIKE '%%.nfo'
            ORDER BY random() LIMIT 3
            """, (row['idShow'], row['season'], row['episode']))
        for show in shows:
            answerText = self._get_episode_title(show['season'], show['episode'], show['episodeTitle'])
            id = "%s-%s-%s" % (row['idShow'], row['season'], show['episode'])
            a = Answer(False, id, answerText, sortWeight = show['episode'])
            a.setCoverFile(thumb.getCachedTVShowThumb(row['strPath']))
            self.answers.append(a)

        self.answers = sorted(self.answers, key=lambda answer: int(answer.sortWeight))

        self.text = strings(Q_WHAT_EPISODE_IS_THIS) % row['title']
        self.setVideoFile(row['strPath'], row['strFileName'])
#        self.setFanartFile(row['strPath'], row['strFileName'])

class WhenWasTVShowFirstAiredQuestion(TVQuestion):
    """
        WhenWasEpisodeFirstAiredQuestion
    """

    def __init__(self, database, maxRating, onlyWatchedMovies):
        TVQuestion.__init__(self, database, DISPLAY_NONE, maxRating, onlyWatchedMovies)

        row = self.database.fetchone("""
            SELECT ev.idFile, ev.c12 AS season, ev.c13 AS episode, ev.c05 AS firstAired, tv.c00 AS title, ev.idShow, ev.strPath, ev.strFileName
            FROM episodeview ev, tvshowview tv
            WHERE ev.idShow=tv.idShow AND ev.c12 != 0 AND ev.c13 = 1 AND ev.c05 != '' AND ev.strFileName NOT LIKE '%%.nfo'
            %s %s
            ORDER BY random() LIMIT 1
            """ % (self._get_watched_episodes_clause(), self._get_max_rating_clause()))

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
            a = Answer(year == int(row['year']), row['idFile'], str(year), row['idFile'])
            a.setCoverFile(thumb.getCachedTVShowThumb(row['strPath']))
            self.answers.append(a)

        self.text = strings(Q_WHEN_WAS_TVSHOW_FIRST_AIRED) % (row['title'] + ' - ' + self._get_season_title(row['season']))
#        self.setVideoFile(row['strPath'], row['strFileName'])
        self.setFanartFile(row['strPath'])


class WhoPlayedRoleInTVShowQuestion(TVQuestion):
    """
        WhoPlayedRoleInTVShowQuestion
    """

    def __init__(self, database, maxRating, onlyWatchedMovies):
        TVQuestion.__init__(self, database, DISPLAY_PHOTO, maxRating, onlyWatchedMovies)

        row = self.database.fetchone("""
            SELECT DISTINCT alt.idActor, a.strActor, alt.strRole, tv.idShow, tv.c00 AS title, tv.strPath, tv.c08 AS genre
            FROM tvshowview tv, actorlinktvshow alt, actors a, episodeview ev
            WHERE tv.idShow = alt.idShow AND alt.idActor=a.idActor AND tv.idShow=ev.idShow AND alt.strRole != '' AND ev.strFileName NOT LIKE '%%.nfo'
            %s
            ORDER BY random() LIMIT 1
            """ % self._get_watched_episodes_clause())
        role = row['strRole']
        if re.search('[|/]', role):
            roles = re.split('[|/]', role)
            # find random role
            role = roles[random.randint(0, len(roles)-1)]

        a = Answer(True, row['idActor'], row['strActor'])
        a.setCoverFile(thumb.getCachedActorThumb(row['strActor']))
        self.answers.append(a)

        shows = self.database.fetchall("""
            SELECT alt.idActor, a.strActor, alt.strRole
            FROM actorlinktvshow alt, actors a
            WHERE alt.idActor=a.idActor AND alt.idShow = ?  AND alt.idActor != ?
            ORDER BY random() LIMIT 3
            """, (row['idShow'], row['idActor']))
        for show in shows:
            a = Answer(False, show['idActor'], show['strActor'])
            a.setCoverFile(thumb.getCachedActorThumb(show['strActor']))
            self.answers.append(a)

        random.shuffle(self.answers)

        if self._isAnimated(row['genre']):
            self.text = strings(Q_WHO_VOICES_ROLE_IN_TVSHOW) % (role, row['title'])
        else:
            self.text = strings(Q_WHO_PLAYS_ROLE_IN_TVSHOW) % (role, row['title'])
        self.addPhoto(thumb.getCachedTVShowThumb(row['strPath']))

class QuestionException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

def getRandomQuestion(type, database, maxRating, onlyWatchedMovies):
    """
        Gets random question from one of the Question subclasses.
    """
    subclasses = []
    if type == TYPE_MOVIE:
        #noinspection PyUnresolvedReferences
        subclasses = MovieQuestion.__subclasses__()
    elif type == TYPE_TV:
        #noinspection PyUnresolvedReferences
        subclasses = TVQuestion.__subclasses__()
    random.shuffle(subclasses)

    for subclass in subclasses:
        try:
            return subclass(database, maxRating, onlyWatchedMovies)
        except QuestionException, ex:
            print "QuestionException in %s: %s" % (subclass, ex)
        except db.DbException, ex:
            print "DbException in %s: %s" % (subclass, ex)

    return None

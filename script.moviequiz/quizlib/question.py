#
#      Copyright (C) 2013 Tommy Winther
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
import re
import imdb
import game
import library

import xbmcvfs

from strings import *

IMDB = imdb.Imdb()


class Answer(object):
    def __init__(self, id, text, image=None, sortWeight=None, correct=False):
        self.correct = correct
        self.id = id
        self.text = text
        self.coverFile = image
        self.sortWeight = sortWeight

    def setCoverFile(self, coverFile):
        self.coverFile = coverFile

    def __repr__(self):
        return "<Answer(id=%s, text=%s, correct=%s)>" % (self.id, self.text, self.correct)


class Question(object):
    def __init__(self, displayType=None):
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

    def addCorrectAnswer(self, id, text, image=None, sortWeight=None):
        self.addAnswer(id, text, image, sortWeight, correct=True)

    def addAnswer(self, id, text, image=None, sortWeight=None, correct=False):
        a = Answer(id, text, image, sortWeight, correct)
        self.answers.append(a)

    def getCorrectAnswer(self):
        for answer in self.answers:
            if answer.correct:
                return answer
        return None

    def getUniqueIdentifier(self):
        return "%s-%s" % (self.__class__.__name__, unicode(self.getCorrectAnswer().id))

    def setFanartFile(self, fanartFile):
        self.fanartFile = fanartFile

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
            movieIds.append(str(movie.id))
        return movieIds

    def getAnswerTexts(self):
        texts = list()
        for answer in self.answers:
            texts.append(answer.text)
        return texts

    def _isAnimationGenre(self, genre):
        return "Animation" in genre  # todo case insensitive

#
# DISPLAY TYPES
#


class DisplayType(object):
    pass


class VideoDisplayType(DisplayType):
    def setVideoFile(self, videoFile, resumePoint):
        self.videoFile = videoFile
        self.resumePoint = resumePoint
        if not xbmcvfs.exists(self.videoFile):
            raise QuestionException('Video file not found: %s' % self.videoFile.encode('utf-8', 'ignore'))

    def getVideoFile(self):
        return self.videoFile

    def getResumePoint(self):
        return self.resumePoint


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
    def __init__(self, defaultFilters):
        """
        What movie is this?
        """
        videoDisplayType = VideoDisplayType()
        super(WhatMovieIsThisQuestion, self).__init__(videoDisplayType)

        correctAnswer = library.getMovies(['title', 'set', 'genre', 'file', 'resume', 'art']).withFilters(
            defaultFilters).limitTo(1).asItem()
        if not correctAnswer:
            raise QuestionException('No movies found')

        self.addCorrectAnswer(id=correctAnswer['movieid'], text=correctAnswer['title'],
                              image=correctAnswer['art']['poster'])

        # Find other movies in set
        if correctAnswer['set'] is not None:
            otherMoviesInSet = library.getMovies(['title', 'art']).withFilters(defaultFilters).inSet(
                correctAnswer['set']).excludeTitles(self.getAnswerTexts()).limitTo(3).asList()
            for movie in otherMoviesInSet:
                self.addAnswer(id=movie['movieid'], text=movie['title'], image=movie['art']['poster'])

        # Find other movies in genre
        if len(self.answers) < 4:
            otherMoviesInGenre = library.getMovies(['title', 'art']).withFilters(defaultFilters).inGenre(
                correctAnswer['genre']).excludeTitles(self.getAnswerTexts()).limitTo(4 - len(self.answers)).asList()
            for movie in otherMoviesInGenre:
                self.addAnswer(id=movie['movieid'], text=movie['title'], image=movie['art']['poster'])

        # Fill with random movies
        if len(self.answers) < 4:
            theRest = library.getMovies(['title', 'art']).withFilters(defaultFilters).excludeTitles(
                self.getAnswerTexts()).limitTo(4 - len(self.answers)).asList()
            for movie in theRest:
                self.addAnswer(id=movie['movieid'], text=movie['title'], image=movie['art']['poster'])

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_IS_THIS)
        videoDisplayType.setVideoFile(correctAnswer['file'], correctAnswer['resume']['position'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatmovieisthis.enabled') == 'true'


class WhatActorIsThisQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        WhatActorIsThisQuestion
        """
        photoDisplayType = PhotoDisplayType()
        super(WhatActorIsThisQuestion, self).__init__(photoDisplayType)

        # Find a bunch of actors with thumbnails
        actors = list()
        names = list()
        for movie in library.getMovies(['cast']).withFilters(defaultFilters).limitTo(10).asList():
            for actor in movie['cast']:
                if 'thumbnail' in actor and actor['name'] not in names:
                    actors.append(actor)
                    names.append(actor['name'])

        if not actors:
            raise QuestionException("Didn't find any actors with thumbnail")

        random.shuffle(actors)
        actor = actors.pop()

        # The actor
        self.addCorrectAnswer(id=actor['name'], text=actor['name'])

        # Check gender
        actorGender = IMDB.isActor(actor['name'])

        for otherActor in actors:
            if IMDB.isActor(otherActor['name']) == actorGender:
                self.addAnswer(otherActor['name'].encode('utf-8', 'ignore'), otherActor['name'])
                if len(self.answers) == 4:
                    break

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_ACTOR_IS_THIS)
        photoDisplayType.setPhotoFile(actor['thumbnail'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatactoristhis.enabled') == 'true'


class ActorNotInMovieQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        Actor not in movie?
        """
        photoDisplayType = PhotoDisplayType()
        super(ActorNotInMovieQuestion, self).__init__(photoDisplayType)

        actors = list()
        for movie in library.getMovies(['cast']).withFilters(defaultFilters).limitTo(10).asList():
            for actor in movie['cast']:
                if 'thubmnail' in actor:
                    actors.append(actor)

        if not actors:
            raise QuestionException("Didn't find any actors with thumbnail")

        random.shuffle(actors)

        actor = None
        for actor in actors:
            # Movie actor is in
            movies = library.getMovies(['title', 'art']).withFilters(defaultFilters).withActor(actor['name']).limitTo(3).asList()
            if len(movies) < 3:
                continue

            for movie in movies:
                self.addAnswer(-1, movie['title'], image=movie['art']['poster'])

            # Movies actor is not in
            correctAnswer = library.getMovies(['title', 'art']).withFilters(defaultFilters).withoutActor(
                actor['name']).limitTo(1).asItem()
            if not correctAnswer:
                raise QuestionException('No movies found')
            self.addCorrectAnswer(actor['name'], correctAnswer['title'], image=correctAnswer['art']['poster'])

            break

        if not self.answers:
            raise QuestionException("Didn't find any actors with at least three movies")

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_IS_ACTOR_NOT_IN, actor['name'])
        photoDisplayType.setPhotoFile(actor['thumbnail'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.actornotinmovie.enabled') == 'true'


class WhatYearWasMovieReleasedQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        WhatYearWasMovieReleasedQuestion
        """
        super(WhatYearWasMovieReleasedQuestion, self).__init__()

        movie = library.getMovies(['title', 'year', 'art']).withFilters(defaultFilters).fromYear(1900).limitTo(
            1).asItem()
        if not movie:
            raise QuestionException('No movies found')

        skew = random.randint(0, 10)
        minYear = int(movie['year']) - skew
        maxYear = int(movie['year']) + (10 - skew)

        thisYear = datetime.datetime.today().year
        if maxYear > thisYear:
            maxYear = thisYear
            minYear = thisYear - 10

        years = list()
        years.append(int(movie['year']))
        while len(years) < 4:
            year = random.randint(minYear, maxYear)
            if not year in years:
                years.append(year)

        list.sort(years)

        for year in years:
            self.addAnswer(id=movie['movieid'], text=str(year), correct=(year == int(movie['year'])))

        self.text = strings(Q_WHAT_YEAR_WAS_MOVIE_RELEASED, movie['title'])
        self.setFanartFile(movie['art']['fanart'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatyearwasmoviereleased.enabled') == 'true'


class WhatTagLineBelongsToMovieQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        WhatTagLineBelongsToMovieQuestion
        """
        super(WhatTagLineBelongsToMovieQuestion, self).__init__()

        movie = None
        items = library.getMovies(['title', 'tagline', 'art']).withFilters(defaultFilters).limitTo(10).asList()
        for item in items:
            if not item['tagline']:
                continue

            movie = item
            break

        if not movie:
            raise QuestionException('No movies found')
        self.addCorrectAnswer(id=movie['movieid'], text=movie['tagline'])

        otherMovies = library.getMovies(['tagline']).withFilters(defaultFilters).excludeTitles(movie['title']).limitTo(
            10).asList()
        for otherMovie in otherMovies:
            if not otherMovie['tagline']:
                continue

            self.addAnswer(id=otherMovie['movieid'], text=otherMovie['tagline'])
            if len(self.answers) == 4:
                break

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_TAGLINE_BELONGS_TO_MOVIE, movie['title'])
        self.setFanartFile(movie['art']['fanart'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whattaglinebelongstomovie.enabled') == 'true'


class WhatStudioReleasedMovieQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        WhatStudioReleasedMovieQuestion
        """
        super(WhatStudioReleasedMovieQuestion, self).__init__()

        movie = None
        items = library.getMovies(['title', 'studio', 'art']).withFilters(defaultFilters).limitTo(10).asList()
        for item in items:
            if not item['studio']:
                continue

            movie = item
            break

        if not movie:
            raise QuestionException('No movies found')

        studio = random.choice(movie['studio'])
        self.addCorrectAnswer(id=movie['movieid'], text=studio)

        otherMovies = library.getMovies(['studio']).withFilters(defaultFilters).excludeTitles(movie['title']).limitTo(
            10).asList()
        for otherMovie in otherMovies:
            if not otherMovie['studio']:
                continue

            studioFound = False
            for otherStudio in otherMovie['studio']:
                if otherStudio in self.getAnswerTexts():
                    studioFound = True
                    break

            if studioFound:
                continue

            self.addAnswer(id=otherMovie['movieid'], text=random.choice(otherMovie['studio']))
            if len(self.answers) == 4:
                break

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_STUDIO_RELEASED_MOVIE, movie['title'])
        self.setFanartFile(movie['art']['fanart'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatstudioreleasedmovie.enabled') == 'true'


class WhoPlayedRoleInMovieQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        WhoPlayedRoleInMovieQuestion
        """
        super(WhoPlayedRoleInMovieQuestion, self).__init__()

        movie = None
        items = library.getMovies(['title', 'cast', 'genre', 'art']).withFilters(defaultFilters).limitTo(10).asList()
        for item in items:
            if len(item['cast']) < 4:
                continue

            movie = item
            break

        if not movie:
            raise QuestionException('No applicable movie found')

        actor = random.choice(movie['cast'])
        role = actor['role']
        if re.search('[|/,]', role):
            roles = re.split('[|/,]', role)
            # find random role
            role = roles[random.randint(0, len(roles) - 1)]

        self.addCorrectAnswer(actor['name'], actor['name'], image=actor['thumbnail'])

        for otherActor in movie['cast']:
            if otherActor['name'] == actor['name']:
                continue

            self.addAnswer(otherActor['name'].encode('utf-8', 'ignore'), otherActor['name'], image=otherActor['thumbnail'])

            if len(self.answers) == 4:
                break

        random.shuffle(self.answers)

        if self._isAnimationGenre(movie['genre']):
            self.text = strings(Q_WHO_VOICES_ROLE_IN_MOVIE) % (role, movie['title'])
        else:
            self.text = strings(Q_WHO_PLAYS_ROLE_IN_MOVIE) % (role, movie['title'])
        self.setFanartFile(movie['art']['fanart'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whoplayedroleinmovie.enabled') == 'true'


class WhatMovieIsThisQuoteFrom(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        WhatQuoteIsThisFrom
        """
        quoteDisplayType = QuoteDisplayType()
        super(WhatMovieIsThisQuoteFrom, self).__init__(quoteDisplayType)

        quoteText = None
        row = None
        for item in library.getMovies(['title', 'art']).withFilters(defaultFilters).limitTo(10).asList():
            quoteText = IMDB.getRandomQuote(item['title'], maxLength=128)

            if quoteText is not None:
                row = item
                break

        if quoteText is None:
            raise QuestionException('Did not find any quotes')

        self.addCorrectAnswer(row['movieid'], row['title'], image=row['art']['poster'])

        theRest = library.getMovies(['title', 'art']).withFilters(defaultFilters).excludeTitles(
            self.getAnswerTexts()).limitTo(3).asList()
        for movie in theRest:
            self.addAnswer(movie['movieid'], movie['title'], image=movie['art']['poster'])

        random.shuffle(self.answers)
        quoteDisplayType.setQuoteText(quoteText)
        self.text = strings(Q_WHAT_MOVIE_IS_THIS_QUOTE_FROM)

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatmovieisthisquotefrom.enabled') == 'true' and IMDB.isDataPresent()


class WhatMovieIsNewestQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        WhatMovieIsNewestQuestion
        """
        super(WhatMovieIsNewestQuestion, self).__init__()

        movie = library.getMovies(['title', 'year', 'art']).withFilters(defaultFilters).fromYear(1900).limitTo(
            1).asItem()
        if not movie:
            raise QuestionException('No movies found')

        self.addCorrectAnswer(id=movie['movieid'], text=movie['title'], image=movie['art']['poster'])

        otherMovies = library.getMovies(['title', 'art']).withFilters(defaultFilters).fromYear(1900).toYear(
            movie['year']).limitTo(3).asList()
        if len(otherMovies) < 3:
            raise QuestionException("Less than 3 movies found; bailing out")

        for otherMovie in otherMovies:
            self.addAnswer(otherMovie['movieid'], otherMovie['title'], image=otherMovie['art']['poster'])

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_IS_THE_NEWEST)

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatmovieisnewest.enabled') == 'true'


class WhoDirectedThisMovieQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        WhoDirectedThisMovieQuestion
        """
        super(WhoDirectedThisMovieQuestion, self).__init__()

        movie = None
        items = library.getMovies(['title', 'director', 'art']).withFilters(defaultFilters).limitTo(10).asList()
        for item in items:
            if not item['director']:
                continue

            movie = item
            break

        if not movie:
            raise QuestionException('No movies found')

        director = random.choice(movie['director'])
        self.addCorrectAnswer(id=movie['movieid'], text=director)

        otherMovies = library.getMovies(['director']).withFilters(defaultFilters).excludeTitles(movie['title']).limitTo(
            10).asList()
        for otherMovie in otherMovies:
            if not otherMovie['director']:
                continue

            directorFound = False
            for otherDirector in otherMovie['director']:
                if otherDirector in self.getAnswerTexts():
                    directorFound = True
                    break

            if directorFound:
                continue

            self.addAnswer(id=otherMovie['movieid'], text=random.choice(otherMovie['director']))
            if len(self.answers) == 4:
                break

        random.shuffle(self.answers)
        self.text = strings(Q_WHO_DIRECTED_THIS_MOVIE, movie['title'])
        self.setFanartFile(movie['art']['fanart'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whodirectedthismovie.enabled') == 'true'


class WhatMovieIsNotDirectedByQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        WhatMovieIsNotDirectedByQuestion
        """
        super(WhatMovieIsNotDirectedByQuestion, self).__init__()

        # Find a bunch of directors
        directors = list()
        items = library.getMovies(['title', 'director']).withFilters(defaultFilters).limitTo(10).asList()
        for item in items:
            directors.extend(iter(item['director']))

        # Find one that has at least three movies
        movies = None
        director = None
        for director in directors:
        #            if not director['thumbnail']:
        #                continue
            movies = library.getMovies(['title', 'art']).withFilters(defaultFilters).directedBy(director).limitTo(
                3).asList()

            if len(movies) >= 3:
                break

        if len(movies) < 3:
            raise QuestionException("Didn't find a director with at least three movies")

        # Find movie not directed by director
        otherMovie = library.getMovies(['title', 'art']).withFilters(defaultFilters).notDirectedBy(director).limitTo(
            1).asItem()
        if not otherMovie:
            raise QuestionException('No movie found')
        self.addCorrectAnswer(director, otherMovie['title'], image=otherMovie['art']['poster'])

        for movie in movies:
            self.addAnswer(-1, movie['title'], image=movie['art']['poster'])

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_IS_NOT_DIRECTED_BY, director)
        # todo perhaps set fanart instead?

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatmovieisnotdirectedby.enabled') == 'true'


class WhatActorIsInTheseMoviesQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        WhatActorIsInTheseMoviesQuestion
        """
        threePhotoDisplayType = ThreePhotoDisplayType()
        super(WhatActorIsInTheseMoviesQuestion, self).__init__(threePhotoDisplayType)

        # Find a bunch of actors
        actors = list()
        items = library.getMovies(['title', 'cast']).withFilters(defaultFilters).limitTo(10).asList()
        for item in items:
            actors.extend(iter(item['cast']))

        # Find one that has at least three movies
        movies = None
        actor = None
        for actor in actors:
            if not 'thumbnail' in actor:
                continue
            movies = library.getMovies(['title', 'art']).withFilters(defaultFilters).withActor(actor['name']).limitTo(
                3).asList()

            if len(movies) >= 3:
                break

        if len(movies) < 3:
            raise QuestionException("Didn't find an actor with at least three movies")

        # Setup the display with three movies
        for movie in movies:
            threePhotoDisplayType.addPhoto(movie['art']['poster'], movie['title'])

        # Find movie without actor
        otherMovie = library.getMovies(['title', 'art']).withFilters(defaultFilters).withoutActor(
            actor['name']).limitTo(1).asItem()
        if not otherMovie:
            raise QuestionException('No movie found')
        self.addCorrectAnswer(actor['name'], actor['title'], image=actor['thumbnail'])

        # Find another bunch of actors
        actors = list()
        items = library.getMovies(['title', 'cast']).withFilters(defaultFilters).withoutActor(actor['name']).limitTo(
            10).asList()
        for item in items:
            actors.extend(iter(item['cast']))

        random.shuffle(actors)
        for actor in actors:
            if not 'thumbnail' in actor:
                continue
            self.addAnswer(-1, actor['name'], image=actor['thumbnail'])
            if len(self.answers) == 4:
                break

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_ACTOR_IS_IN_THESE_MOVIES)

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatactorisinthesemovies.enabled') == 'true'


class WhatActorIsInMovieBesidesOtherActorQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        WhatActorIsInMovieBesidesOtherActorQuestion
        """
        super(WhatActorIsInMovieBesidesOtherActorQuestion, self).__init__()

        # Find a bunch of movies
        items = library.getMovies(['title', 'cast', 'art']).withFilters(defaultFilters).limitTo(10).asList()
        movie = None
        for item in items:
            if len(item['cast']) >= 2:
                movie = item
                break

        if not movie:
            raise QuestionException('No movies with two actors found')

        actors = movie['cast']
        random.shuffle(actors)
        actorOne = actors[0]
        actorTwo = actors[1]
        self.addCorrectAnswer(actorOne['name'], actorOne['name'], image=actorOne['thumbnail'])

        # Find another bunch of actors
        otherActors = list()
        items = library.getMovies(['title', 'cast']).withFilters(defaultFilters).withoutActor(
            actorOne['name']).withoutActor(actorTwo['name']).limitTo(10).asList()
        for item in items:
            otherActors.extend(iter(item['cast']))
        random.shuffle(otherActors)

        for otherActor in otherActors:
            if not 'thumbnail' in otherActor:
                continue
            self.addAnswer(otherActor['name'].encode('utf-8', 'ignore'), otherActor['name'], image=otherActor['thumbnail'])
            if len(self.answers) == 4:
                break

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_ACTOR_IS_IN_MOVIE_BESIDES_OTHER_ACTOR, (movie['title'], actorTwo['name']))
        self.setFanartFile(movie['art']['fanart'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatactorisinmoviebesidesotheractor.enabled') == 'true'


class WhatMovieHasTheLongestRuntimeQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        WhatMovieHasTheLongestRuntimeQuestion
        """
        super(WhatMovieHasTheLongestRuntimeQuestion, self).__init__()

        # Find a bunch of movies
        items = library.getMovies(['title', 'runtime', 'art']).withFilters(defaultFilters).limitTo(10).asList()
        movie = None
        otherMovies = list()
        for item in items:
            if movie is None or movie['runtime'] < item['runtime']:
                movie = item
            else:
                otherMovies.append(item)

        if not movie or len(otherMovies) < 3:
            raise QuestionException('Not enough movies found')

        self.addCorrectAnswer(id=movie['movieid'], text=movie['title'], image=movie['art']['poster'])

        for otherMovie in otherMovies:
            self.addAnswer(id=otherMovie['movieid'], text=otherMovie['title'], image=otherMovie['art']['poster'])
            if len(self.answers) == 4:
                break

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_HAS_THE_LONGEST_RUNTIME)

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatmoviehaslongestruntime.enabled') == 'true'

#
# TV QUESTIONS
#


class TVQuestion(Question):
    def __init__(self, displayType=None):
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
    def __init__(self, defaultFilters):
        """
        WhatTVShowIsThisQuestion
        """
        videoDisplayType = VideoDisplayType()
        super(WhatTVShowIsThisQuestion, self).__init__(videoDisplayType)

        show = library.getTVShows(['title', 'art']).withFilters(defaultFilters).limitTo(1).asItem()
        if not show:
            raise QuestionException('No tvshows found')
        self.addCorrectAnswer(id=show['tvshowid'], text=show['title'], image=show['art']['poster'])

        episode = library.getEpisodes(['file', 'resume']).withFilters(defaultFilters).fromShow(show['title']).limitTo(
            1).asItem()
        if not episode:
            raise QuestionException('TVshow has no episodes')

        otherShows = library.getTVShows(['title', 'art']).withFilters(defaultFilters).excludeTitles(
            [show['title']]).limitTo(3).asList()
        for otherShow in otherShows:
            self.addAnswer(id=otherShow['tvshowid'], text=otherShow['title'], image=otherShow['art']['poster'])

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_TVSHOW_IS_THIS)
        videoDisplayType.setVideoFile(episode['file'], episode['resume']['position'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whattvshowisthis.enabled') == 'true'


class WhatSeasonIsThisQuestion(TVQuestion):
    def __init__(self, defaultFilters):
        """
        WhatSeasonIsThisQuestion
        """
        videoDisplayType = VideoDisplayType()
        super(WhatSeasonIsThisQuestion, self).__init__(videoDisplayType)

        show = library.getTVShows(['title', 'art']).withFilters(defaultFilters).limitTo(1).asItem()
        if not show:
            raise QuestionException('No tvshows found')

        seasons = library.getSeasons(show['tvshowid'], ['season', 'art']).limitTo(4).asList()
        correctIdx = random.randint(0, len(seasons) - 1)

        episode = library.getEpisodes(['file', 'resume']).withFilters(defaultFilters).fromShow(
            show['title']).fromSeason(seasons[correctIdx]['season']).limitTo(1).asItem()
        if not episode:
            raise QuestionException('TVshow has no episodes')

        for idx, season in enumerate(seasons):
            self.addAnswer("%s-%s" % (show['tvshowid'], season['season']), season['label'],
                           image=season['art']['poster'], sortWeight=season['season'], correct=(idx == correctIdx))

        self.answers = sorted(self.answers, key=lambda answer: int(answer.sortWeight))

        self.text = strings(Q_WHAT_SEASON_IS_THIS) % show['title']
        videoDisplayType.setVideoFile(episode['file'], episode['resume']['position'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatseasonisthis.enabled') == 'true'


class WhatEpisodeIsThisQuestion(TVQuestion):
    def __init__(self, defaultFilters):
        """
        WhatEpisodeIsThisQuestion
        """
        videoDisplayType = VideoDisplayType()
        super(WhatEpisodeIsThisQuestion, self).__init__(videoDisplayType)

        show = library.getTVShows(['title', 'art']).withFilters(defaultFilters).limitTo(1).asItem()
        if not show:
            raise QuestionException('No tvshows found')

        season = library.getSeasons(show['tvshowid'], ['season', 'art']).limitTo(14).asItem()
        if not season:
            raise QuestionException('No seasons found')

        episodes = library.getEpisodes(['episode', 'title', 'file', 'resume']).fromShow(show['title']).fromSeason(
            season['season']).limitTo(4).asList()
        correctIdx = random.randint(0, len(episodes) - 1)

        for idx, episode in enumerate(episodes):
            id = "%s-%s-%s" % (show['tvshowid'], season['season'], episode['episode'])
            self.addAnswer(id=id, text=episode['label'], image=season['art']['poster'], sortWeight=episode['episode'],
                           correct=(idx == correctIdx))

        self.answers = sorted(self.answers, key=lambda answer: int(answer.sortWeight))

        self.text = strings(Q_WHAT_EPISODE_IS_THIS) % show['title']
        videoDisplayType.setVideoFile(episodes[correctIdx]['file'], episodes[correctIdx]['resume']['position'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatepisodeisthis.enabled') == 'true'


class WhenWasTVShowFirstAiredQuestion(TVQuestion):
    def __init__(self, defaultFilters):
        """
        WhenWasTVShowFirstAiredQuestion
        """
        super(WhenWasTVShowFirstAiredQuestion, self).__init__()

        show = library.getTVShows(['title', 'art']).withFilters(defaultFilters).limitTo(1).asItem()
        if not show:
            raise QuestionException('No shows found')

        season = library.getSeasons(show['tvshowid'], ['season']).limitTo(1).asItem()
        if not season:
            raise QuestionException('No seasons found')

        episode = library.getEpisodes(['firstaired']).withFilters(defaultFilters).episode(1).fromShow(
            show['title']).fromSeason(season['season']).limitTo(1).asItem()
        if not episode:
            raise QuestionException('No episodes found')

        episodeYear = int(episode['firstaired'][0:4])

        skew = random.randint(0, 10)
        minYear = episodeYear - skew
        maxYear = episodeYear + (10 - skew)

        thisYear = datetime.datetime.today().year
        if maxYear > thisYear:
            maxYear = thisYear
            minYear = thisYear - 10

        years = list()
        years.append(episodeYear)
        while len(years) < 4:
            year = random.randint(minYear, maxYear)
            if not year in years:
                years.append(year)

        list.sort(years)

        for year in years:
            self.addAnswer(id="%s-%s" % (show['tvshowid'], season['season']), text=str(year),
                           correct=(year == episodeYear))

        self.text = strings(Q_WHEN_WAS_TVSHOW_FIRST_AIRED) % (show['title'] + ' - ' + season['label'])
        self.setFanartFile(show['art']['fanart'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whenwastvshowfirstaired.enabled') == 'true'


class WhoPlayedRoleInTVShowQuestion(TVQuestion):
    def __init__(self, defaultFilters):
        """
        WhoPlayedRoleInTVShowQuestion
        """
        super(WhoPlayedRoleInTVShowQuestion, self).__init__()

        show = library.getTVShows(['title', 'genre', 'cast', 'art']).withFilters(defaultFilters).limitTo(1).asItem()
        if not show or len(show['cast']) < 4:
            raise QuestionException('No tvshows found')

        otherActors = show['cast']
        actor = otherActors.pop(random.randint(0, len(otherActors) - 1))

        role = actor['role']
        if re.search('[|/,]', role):
            roles = re.split('[|/,]', role)
            # find random role
            role = roles[random.randint(0, len(roles) - 1)]

        self.addCorrectAnswer(id=actor['name'], text=actor['name'], image=actor.get('thumbnail'))

        for otherActor in otherActors:
            self.addAnswer(id=otherActor['name'].encode('utf-8', 'ignore'), text=otherActor['name'], image=otherActor.get('thumbnail'))

            if len(self.answers) == 4:
                break

        random.shuffle(self.answers)

        if self._isAnimationGenre(show['genre']):
            self.text = strings(Q_WHO_VOICES_ROLE_IN_TVSHOW) % (role, show['title'])
        else:
            self.text = strings(Q_WHO_PLAYS_ROLE_IN_TVSHOW) % (role, show['title'])
        self.setFanartFile(show['art']['fanart'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whoplayedroleintvshow.enabled') == 'true'


class WhatTVShowIsThisQuoteFrom(TVQuestion):
    def __init__(self, defaultFilters):
        """
        WhatTVShowIsThisQuoteFrom
        """
        quoteDisplayType = QuoteDisplayType()
        super(WhatTVShowIsThisQuoteFrom, self).__init__(quoteDisplayType)

        episode = library.getEpisodes(['showtitle', 'season', 'episode', 'art']).withFilters(defaultFilters).limitTo(
            1).asItem()
        if not episode:
            raise QuestionException('No episodes found')

        quoteText = IMDB.getRandomQuote(episode['showtitle'], season=episode['season'], episode=episode['episode'],
                                        maxLength=128)
        if quoteText is None:
            raise QuestionException('Did not find any quotes')

        self.addCorrectAnswer(id=episode['showtitle'], text=episode['showtitle'], image=episode['art']['tvshow.poster'])

        otherShows = library.getTVShows(['title', 'art']).withFilters(defaultFilters).excludeTitles(
            [episode['showtitle']]).limitTo(3).asList()
        for otherShow in otherShows:
            self.addAnswer(id=otherShow['title'].encode('utf-8', 'ignore'), text=otherShow['title'], image=otherShow['art']['poster'])

        random.shuffle(self.answers)
        quoteDisplayType.setQuoteText(quoteText)
        self.text = strings(Q_WHAT_TVSHOW_IS_THIS_QUOTE_FROM)

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whattvshowisthisquotefrom.enabled') == 'true' and IMDB.isDataPresent()


class WhatTVShowIsThisThemeFromQuestion(TVQuestion):
    def __init__(self, defaultFilters):
        audioDisplayType = AudioDisplayType()
        super(WhatTVShowIsThisThemeFromQuestion, self).__init__(audioDisplayType)

        items = library.getTVShows(['title', 'file', 'art']).withFilters(defaultFilters).limitTo(4).asList()
        show = None
        otherShows = list()
        for item in items:
            themeSong = os.path.join(item['file'], 'theme.mp3')
            if show is None and xbmcvfs.exists(themeSong):
                show = item
            else:
                otherShows.append(item)

        if show is None:
            raise QuestionException('Unable to find any tv shows with a theme.mp3 file')

        self.addCorrectAnswer(id=show['tvshowid'], text=show['title'], image=show['art']['poster'])

        # Fill with random episodes from other shows
        for otherShow in otherShows:
            self.addAnswer(id=otherShow['tvshowid'], text=otherShow['title'], image=otherShow['art']['poster'])

        random.shuffle(self.answers)
        audioDisplayType.setAudioFile(os.path.join(show['file'], 'theme.mp3'))
        self.text = strings(Q_WHAT_TVSHOW_IS_THIS_THEME_FROM)

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whattvshowisthisthemefrom.enabled') == 'true'


class QuestionException(Exception):
    pass


def getEnabledQuestionCandidates(gameInstance):
    """
        Gets random question from one of the Question subclasses.
    """
    questionCandidates = []
    if gameInstance.getType() == game.GAMETYPE_MOVIE:
        questionCandidates = MovieQuestion.__subclasses__()
    elif gameInstance.getType() == game.GAMETYPE_TVSHOW:
        questionCandidates = TVQuestion.__subclasses__()

    questionCandidates = [candidate for candidate in questionCandidates if candidate.isEnabled()]

    return questionCandidates


def isAnyMovieQuestionsEnabled():
    subclasses = MovieQuestion.__subclasses__()
    subclasses = [subclass for subclass in subclasses if subclass.isEnabled()]
    return subclasses


def isAnyTVShowQuestionsEnabled():
    subclasses = TVQuestion.__subclasses__()
    subclasses = [subclass for subclass in subclasses if subclass.isEnabled()]
    return subclasses

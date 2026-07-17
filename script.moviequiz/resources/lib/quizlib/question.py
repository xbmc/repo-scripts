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

import datetime, random, re

import xbmcvfs

from . import game, imdb, library
from .strings import *


IMDB = imdb.Imdb()


class DisplayType:
    pass


class VideoDisplayType(DisplayType):
    def setVideoFile(self, videoFile):
        self.videoFile = videoFile
        if not xbmcvfs.exists(self.videoFile):
            raise QuestionException(f'Video file not found: {self.videoFile.encode('utf-8', 'ignore')}')

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


class Answer:
    def __init__(self, id, text, image=None, sortWeight=None, correct=False):
        self.correct = correct
        self.id = id
        self.text = text
        self.coverFile = image
        self.sortWeight = sortWeight

    def setCoverFile(self, coverFile):
        self.coverFile = coverFile

    def __repr__(self):
        return f"<Answer(id={self.id}, text={self.text}, correct={self.correct})>"


class Question:
    def __init__(self, displayType: DisplayType = None):
        """
        Base class for Questions
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
        return f"{self.__class__.__name__}-{str(self.getCorrectAnswer().id)}"

    def setFanartFile(self, fanartFile):
        self.fanartFile = fanartFile

    def getFanartFile(self):
        return self.fanartFile

    def getDisplayType(self):
        return self.displayType

    @staticmethod
    def isEnabled():
        raise NotImplementedError("subclasses must implement 'isenabled()'")

    def getAnswerTexts(self):
        return [answer.text for answer in self.answers]

    def _isAnimationGenre(self, genre):
        return library.GENRE_ANIMATION in genre


#
# MOVIE QUESTIONS
#


class MovieQuestion(Question):
    pass


class WhatMovieIsThisQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        videoDisplayType = VideoDisplayType()
        super().__init__(videoDisplayType)

        correctAnswer = (library.getMovies([library.KEY_TITLE, library.KEY_SET, library.KEY_GENRE, library.KEY_FILE, library.KEY_ART])
                                .withFilters(defaultFilters).limitTo(1).asItem())
        if not correctAnswer:
            raise QuestionException('No movies found')

        self.addCorrectAnswer(id=correctAnswer[library.KEY_MOVIE_ID], text=correctAnswer[library.KEY_TITLE],
                              image=correctAnswer[library.KEY_ART].get(library.KEY_POSTER))

        # Find other movies in set
        if correctAnswer[library.KEY_SET]:
            otherMoviesInSet = (library.getMovies([library.KEY_TITLE, library.KEY_ART]).withFilters(defaultFilters)
                                       .inSet(correctAnswer[library.KEY_SET]).excludeTitles(self.getAnswerTexts()).limitTo(3).asList())
            for movie in otherMoviesInSet:
                self.addAnswer(id=movie[library.KEY_MOVIE_ID], text=movie[library.KEY_TITLE], image=movie[library.KEY_ART].get(library.KEY_POSTER))

        # Find other movies in genre
        if len(self.answers) < 4:
            otherMoviesInGenre = (library.getMovies([library.KEY_TITLE, library.KEY_ART]).withFilters(defaultFilters)
                                         .inGenre(correctAnswer[library.KEY_GENRE]).excludeTitles(self.getAnswerTexts())
                                         .limitTo(4 - len(self.answers)).asList())
            for movie in otherMoviesInGenre:
                self.addAnswer(id=movie[library.KEY_MOVIE_ID], text=movie[library.KEY_TITLE], image=movie[library.KEY_ART].get(library.KEY_POSTER))

        # Fill with random movies
        if len(self.answers) < 4:
            theRest = library.getMovies([library.KEY_TITLE, library.KEY_ART]).withFilters(defaultFilters).excludeTitles(
                self.getAnswerTexts()).limitTo(4 - len(self.answers)).asList()
            for movie in theRest:
                self.addAnswer(id=movie[library.KEY_MOVIE_ID], text=movie[library.KEY_TITLE], image=movie[library.KEY_ART].get(library.KEY_POSTER))

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_IS_THIS)
        videoDisplayType.setVideoFile(correctAnswer[library.KEY_FILE])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatmovieisthis.enabled') == 'true'


class WhatActorIsThisQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        photoDisplayType = PhotoDisplayType()
        super().__init__(photoDisplayType)

        # Find a bunch of actors with thumbnails
        actors = list()
        names = list()
        for movie in library.getMovies([library.KEY_CAST]).withFilters(defaultFilters).limitTo(10).asList():
            for actor in movie[library.KEY_CAST]:
                if library.KEY_THUMBNAIL in actor and actor[library.KEY_NAME] not in names:
                    actors.append(actor)
                    names.append(actor[library.KEY_NAME])

        if not actors:
            raise QuestionException("Didn't find any actors with thumbnail")

        random.shuffle(actors)
        actor = actors.pop()

        # The actor
        self.addCorrectAnswer(id=actor[library.KEY_NAME], text=actor[library.KEY_NAME])

        for otherActor in actors:
            self.addAnswer(otherActor[library.KEY_NAME].encode('utf-8', 'ignore'), otherActor[library.KEY_NAME])
            if len(self.answers) == 4:
                break

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_ACTOR_IS_THIS)
        photoDisplayType.setPhotoFile(actor.get(library.KEY_THUMBNAIL))

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatactoristhis.enabled') == 'true'


class ActorNotInMovieQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        photoDisplayType = PhotoDisplayType()
        super().__init__(photoDisplayType)

        actors = list()
        for movie in library.getMovies([library.KEY_CAST]).withFilters(defaultFilters).limitTo(10).asList():
            for actor in movie[library.KEY_CAST]:
                if library.KEY_THUMBNAIL in actor:
                    actors.append(actor)

        if not actors:
            raise QuestionException("Didn't find any actors with thumbnail")

        random.shuffle(actors)

        actor = None
        for actor in actors:
            # Movie actor is in
            movies = library.getMovies([library.KEY_TITLE, library.KEY_ART]).withFilters(defaultFilters).withActor(actor[library.KEY_NAME]).limitTo(3).asList()
            if len(movies) < 3:
                continue

            for movie in movies:
                self.addAnswer(-1, movie[library.KEY_TITLE], image=movie[library.KEY_ART].get(library.KEY_POSTER))

            # Movies actor is not in
            correctAnswer = (library.getMovies([library.KEY_TITLE, library.KEY_ART]).withFilters(defaultFilters)
                                    .withoutActor(actor[library.KEY_NAME]).limitTo(1).asItem())
            if not correctAnswer:
                raise QuestionException('No movies found')
            self.addCorrectAnswer(actor[library.KEY_NAME], correctAnswer[library.KEY_TITLE], image=correctAnswer[library.KEY_ART].get(library.KEY_POSTER))
            break

        if not self.answers:
            raise QuestionException("Didn't find any actors with at least three movies")

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_IS_ACTOR_NOT_IN) % actor[library.KEY_NAME]
        photoDisplayType.setPhotoFile(actor.get(library.KEY_THUMBNAIL))

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.actornotinmovie.enabled') == 'true'


class WhatYearWasMovieReleasedQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        super().__init__()

        movie = (library.getMovies([library.KEY_TITLE, library.KEY_YEAR, library.KEY_ART])
                        .withFilters(defaultFilters).fromYear(1900).limitTo(1).asItem())
        if not movie:
            raise QuestionException('No movies found')

        skew = random.randint(0, 10)
        minYear = int(movie[library.KEY_YEAR]) - skew
        maxYear = int(movie[library.KEY_YEAR]) + (10 - skew)

        thisYear = datetime.datetime.today().year
        if maxYear > thisYear:
            maxYear = thisYear
            minYear = thisYear - 10

        years = list()
        years.append(int(movie[library.KEY_YEAR]))
        while len(years) < 4:
            year = random.randint(minYear, maxYear)
            if not year in years:
                years.append(year)

        list.sort(years)

        for year in years:
            self.addAnswer(id=movie[library.KEY_MOVIE_ID], text=str(year), correct=(year == int(movie[library.KEY_YEAR])))

        self.text = strings(Q_WHAT_YEAR_WAS_MOVIE_RELEASED) % movie[library.KEY_TITLE]
        self.setFanartFile(movie[library.KEY_ART].get(library.KEY_FANART))

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatyearwasmoviereleased.enabled') == 'true'


class WhatTagLineBelongsToMovieQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        super().__init__()

        movie = None
        items = library.getMovies([library.KEY_TITLE, library.KEY_TAGLINE, library.KEY_ART]).withFilters(defaultFilters).limitTo(10).asList()
        for item in items:
            if not item[library.KEY_TAGLINE]:
                continue

            movie = item
            break

        if not movie:
            raise QuestionException('No movies found')
        self.addCorrectAnswer(id=movie[library.KEY_MOVIE_ID], text=movie[library.KEY_TAGLINE])

        otherMovies = (library.getMovies([library.KEY_TAGLINE]).withFilters(defaultFilters)
                              .excludeTitles(movie[library.KEY_TITLE]).limitTo(10).asList())
        for otherMovie in otherMovies:
            if not otherMovie[library.KEY_TAGLINE]:
                continue

            self.addAnswer(id=otherMovie[library.KEY_MOVIE_ID], text=otherMovie[library.KEY_TAGLINE])
            if len(self.answers) == 4:
                break

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_TAGLINE_BELONGS_TO_MOVIE) % movie[library.KEY_TITLE]
        self.setFanartFile(movie[library.KEY_ART].get(library.KEY_FANART))

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whattaglinebelongstomovie.enabled') == 'true'


class WhatStudioReleasedMovieQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        super().__init__()

        movie = None
        items = library.getMovies([library.KEY_TITLE, library.KEY_STUDIO, library.KEY_ART]).withFilters(defaultFilters).limitTo(10).asList()
        for item in items:
            if not item[library.KEY_STUDIO]:
                continue

            movie = item
            break

        if not movie:
            raise QuestionException('No movies found')

        studio = random.choice(movie[library.KEY_STUDIO])
        self.addCorrectAnswer(id=movie[library.KEY_MOVIE_ID], text=studio)

        otherMovies = (library.getMovies([library.KEY_STUDIO]).withFilters(defaultFilters)
                              .excludeTitles(movie[library.KEY_TITLE]).limitTo(10).asList())
        for otherMovie in otherMovies:
            if not otherMovie[library.KEY_STUDIO]:
                continue

            studioFound = False
            for otherStudio in otherMovie[library.KEY_STUDIO]:
                if otherStudio in self.getAnswerTexts():
                    studioFound = True
                    break

            if studioFound:
                continue

            self.addAnswer(id=otherMovie[library.KEY_MOVIE_ID], text=random.choice(otherMovie[library.KEY_STUDIO]))
            if len(self.answers) == 4:
                break

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_STUDIO_RELEASED_MOVIE) % movie[library.KEY_TITLE]
        self.setFanartFile(movie[library.KEY_ART].get(library.KEY_FANART))

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatstudioreleasedmovie.enabled') == 'true'


class WhoPlayedRoleInMovieQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        super().__init__()

        movie = None
        items = library.getMovies([library.KEY_TITLE, library.KEY_CAST, library.KEY_GENRE, library.KEY_ART]).withFilters(defaultFilters).limitTo(10).asList()
        for item in items:
            if len(item[library.KEY_CAST]) < 4:
                continue

            movie = item
            break

        if not movie:
            raise QuestionException('No applicable movie found')

        actor = random.choice(movie[library.KEY_CAST])
        role = actor[library.KEY_ROLE]
        if re.search(r'[|/,]', role):
            roles = re.split(r'[|/,]', role)
            # find random role
            role = roles[random.randint(0, len(roles) - 1)]

        self.addCorrectAnswer(actor[library.KEY_NAME], actor[library.KEY_NAME], image=actor.get(library.KEY_THUMBNAIL))

        for otherActor in movie[library.KEY_CAST]:
            if otherActor[library.KEY_NAME] == actor[library.KEY_NAME]:
                continue

            self.addAnswer(otherActor[library.KEY_NAME].encode('utf-8', 'ignore'), otherActor[library.KEY_NAME], image=otherActor.get(library.KEY_THUMBNAIL))

            if len(self.answers) == 4:
                break

        random.shuffle(self.answers)

        baseText = strings(Q_WHO_VOICES_ROLE_IN_MOVIE) if self._isAnimationGenre(movie[library.KEY_GENRE]) else strings(Q_WHO_PLAYS_ROLE_IN_MOVIE)
        self.text = baseText % (role, movie[library.KEY_TITLE])
        self.setFanartFile(movie[library.KEY_ART].get(library.KEY_FANART))

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whoplayedroleinmovie.enabled') == 'true'


class WhatMovieIsThisQuoteFrom(MovieQuestion):
    def __init__(self, defaultFilters):
        quoteDisplayType = QuoteDisplayType()
        super().__init__(quoteDisplayType)

        quoteText = None
        row = None
        for item in library.getMovies([library.KEY_TITLE, library.KEY_ART, library.KEY_YEAR]).withFilters(defaultFilters).limitTo(10).asList():
            quoteText = IMDB.getRandomQuote(item[library.KEY_TITLE], year=item[library.KEY_YEAR], maxLength=128)

            if quoteText is not None:
                row = item
                break

        if quoteText is None:
            raise QuestionException('Did not find any quotes')

        self.addCorrectAnswer(row[library.KEY_MOVIE_ID], row[library.KEY_TITLE], image=row[library.KEY_ART].get(library.KEY_POSTER))

        theRest = (library.getMovies([library.KEY_TITLE, library.KEY_ART]).withFilters(defaultFilters)
                          .excludeTitles(self.getAnswerTexts()).limitTo(3).asList())
        for movie in theRest:
            self.addAnswer(movie[library.KEY_MOVIE_ID], movie[library.KEY_TITLE], image=movie[library.KEY_ART].get(library.KEY_POSTER))

        random.shuffle(self.answers)
        quoteDisplayType.setQuoteText(quoteText)
        self.text = strings(Q_WHAT_MOVIE_IS_THIS_QUOTE_FROM)

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatmovieisthisquotefrom.enabled') == 'true' and IMDB.isDataPresent()


class WhatMovieIsNewestQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        super().__init__()

        movie = (library.getMovies([library.KEY_TITLE, library.KEY_YEAR, library.KEY_ART])
                        .withFilters(defaultFilters).fromYear(1900).limitTo(1).asItem())
        if not movie:
            raise QuestionException('No movies found')

        self.addCorrectAnswer(id=movie[library.KEY_MOVIE_ID], text=movie[library.KEY_TITLE], image=movie[library.KEY_ART].get(library.KEY_POSTER))

        otherMovies = (library.getMovies([library.KEY_TITLE, library.KEY_ART]).withFilters(defaultFilters)
                              .fromYear(1900).toYear(movie[library.KEY_YEAR]).limitTo(3).asList())
        if len(otherMovies) < 3:
            raise QuestionException("Less than 3 movies found; bailing out")

        for otherMovie in otherMovies:
            self.addAnswer(otherMovie[library.KEY_MOVIE_ID], otherMovie[library.KEY_TITLE], image=otherMovie[library.KEY_ART].get(library.KEY_POSTER))

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_IS_THE_NEWEST)

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatmovieisnewest.enabled') == 'true'


class WhoDirectedThisMovieQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        super().__init__()

        movie = None
        items = library.getMovies([library.KEY_TITLE, library.KEY_DIRECTOR, library.KEY_ART]).withFilters(defaultFilters).limitTo(10).asList()
        for item in items:
            if not item[library.KEY_DIRECTOR]:
                continue

            movie = item
            break

        if not movie:
            raise QuestionException('No movies found')

        director = random.choice(movie[library.KEY_DIRECTOR])
        self.addCorrectAnswer(id=movie[library.KEY_MOVIE_ID], text=director)

        otherMovies = (library.getMovies([library.KEY_DIRECTOR]).withFilters(defaultFilters)
                              .excludeTitles(movie[library.KEY_TITLE]).limitTo(10).asList())
        for otherMovie in otherMovies:
            if not otherMovie[library.KEY_DIRECTOR]:
                continue

            directorFound = False
            for otherDirector in otherMovie[library.KEY_DIRECTOR]:
                if otherDirector in self.getAnswerTexts():
                    directorFound = True
                    break

            if directorFound:
                continue

            self.addAnswer(id=otherMovie[library.KEY_MOVIE_ID], text=random.choice(otherMovie[library.KEY_DIRECTOR]))
            if len(self.answers) == 4:
                break

        random.shuffle(self.answers)
        self.text = strings(Q_WHO_DIRECTED_THIS_MOVIE) % movie[library.KEY_TITLE]
        self.setFanartFile(movie[library.KEY_ART].get(library.KEY_FANART))

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whodirectedthismovie.enabled') == 'true'


class WhatMovieIsNotDirectedByQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        super().__init__()

        # Find a bunch of directors
        directors = list()
        items = library.getMovies([library.KEY_TITLE, library.KEY_DIRECTOR]).withFilters(defaultFilters).limitTo(10).asList()
        for item in items:
            directors.extend(iter(item[library.KEY_DIRECTOR]))

        # Find one that has at least three movies
        movies = None
        director = None
        for director in directors:
            movies = (library.getMovies([library.KEY_TITLE, library.KEY_ART]).withFilters(defaultFilters)
                             .directedBy(director).limitTo(3).asList())

            if len(movies) >= 3:
                break

        if len(movies) < 3:
            raise QuestionException("Didn't find a director with at least three movies")

        # Find movie not directed by director
        otherMovie = (library.getMovies([library.KEY_TITLE, library.KEY_ART]).withFilters(defaultFilters)
                             .notDirectedBy(director).limitTo(1).asItem())
        if not otherMovie:
            raise QuestionException('No movie found')

        self.addCorrectAnswer(director, otherMovie[library.KEY_TITLE], image=otherMovie[library.KEY_ART].get(library.KEY_POSTER))

        for movie in movies:
            self.addAnswer(-1, movie[library.KEY_TITLE], image=movie[library.KEY_ART].get(library.KEY_POSTER))

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_IS_NOT_DIRECTED_BY) % director

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatmovieisnotdirectedby.enabled') == 'true'


class WhatActorIsInTheseMoviesQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        threePhotoDisplayType = ThreePhotoDisplayType()
        super().__init__(threePhotoDisplayType)

        # Find a bunch of actors
        actors = list()
        items = library.getMovies([library.KEY_TITLE, library.KEY_CAST]).withFilters(defaultFilters).limitTo(10).asList()
        for item in items:
            actors.extend(iter(item[library.KEY_CAST]))

        # Find one that has at least three movies
        movies = None
        actor = None
        for actor in actors:
            if not library.KEY_THUMBNAIL in actor:
                continue
            movies = (library.getMovies([library.KEY_TITLE, library.KEY_ART]).withFilters(defaultFilters)
                             .withActor(actor[library.KEY_NAME]).limitTo(3).asList())

            if len(movies) >= 3:
                break

        if len(movies) < 3:
            raise QuestionException("Didn't find an actor with at least three movies")

        # Setup the display with three movies
        for movie in movies:
            threePhotoDisplayType.addPhoto(movie[library.KEY_ART].get(library.KEY_POSTER), movie[library.KEY_TITLE])

        # Find movie without actor
        otherMovie = (library.getMovies([library.KEY_TITLE, library.KEY_ART]).withFilters(defaultFilters)
                             .withoutActor(actor[library.KEY_NAME]).limitTo(1).asItem())
        if not otherMovie:
            raise QuestionException('No movie found')
        self.addCorrectAnswer(actor[library.KEY_NAME], actor[library.KEY_NAME], image=actor.get(library.KEY_THUMBNAIL))

        # Find another bunch of actors
        actors = list()
        items = (library.getMovies([library.KEY_TITLE, library.KEY_CAST]).withFilters(defaultFilters)
                        .withoutActor(actor[library.KEY_NAME]).limitTo(10).asList())
        for item in items:
            actors.extend(iter(item[library.KEY_CAST]))

        random.shuffle(actors)
        for actor in actors:
            if not library.KEY_THUMBNAIL in actor:
                continue
            self.addAnswer(-1, actor[library.KEY_NAME], image=actor.get(library.KEY_THUMBNAIL))
            if len(self.answers) == 4:
                break

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_ACTOR_IS_IN_THESE_MOVIES)

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatactorisinthesemovies.enabled') == 'true'


class WhatMovieHasTheLongestRuntimeQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        super().__init__()

        # Find a bunch of movies
        items = library.getMovies([library.KEY_TITLE, library.KEY_RUNTIME, library.KEY_ART]).withFilters(defaultFilters).limitTo(10).asList()
        movie = None
        otherMovies = list()
        for item in items:
            if movie is None or movie[library.KEY_RUNTIME] < item[library.KEY_RUNTIME]:
                movie = item
            else:
                otherMovies.append(item)

        if not movie or len(otherMovies) < 3:
            raise QuestionException('Not enough movies found')

        self.addCorrectAnswer(id=movie[library.KEY_MOVIE_ID], text=movie[library.KEY_TITLE], image=movie[library.KEY_ART].get(library.KEY_POSTER))

        for otherMovie in otherMovies:
            self.addAnswer(id=otherMovie[library.KEY_MOVIE_ID], text=otherMovie[library.KEY_TITLE], image=otherMovie[library.KEY_ART].get(library.KEY_POSTER))
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
    def __init__(self, displayType: DisplayType = None):
        super().__init__(displayType)


class WhatTVShowIsThisQuestion(TVQuestion):
    def __init__(self, defaultFilters):
        videoDisplayType = VideoDisplayType()
        super().__init__(videoDisplayType)

        show = library.getTVShows([library.KEY_TITLE, library.KEY_ART]).withFilters(defaultFilters).limitTo(1).asItem()
        if not show:
            raise QuestionException('No tvshows found')
        self.addCorrectAnswer(id=show[library.KEY_TVSHOW_ID], text=show[library.KEY_TITLE], image=show[library.KEY_ART].get(library.KEY_POSTER))

        episode = (library.getEpisodes([library.KEY_FILE]).withFilters(defaultFilters)
                          .fromShow(show[library.KEY_TITLE]).limitTo(1).asItem())
        if not episode:
            raise QuestionException('TVshow has no episodes')

        otherShows = (library.getTVShows([library.KEY_TITLE, library.KEY_ART]).withFilters(defaultFilters)
                             .excludeTitles([show[library.KEY_TITLE]]).limitTo(3).asList())
        for otherShow in otherShows:
            self.addAnswer(id=otherShow[library.KEY_TVSHOW_ID], text=otherShow[library.KEY_TITLE], image=otherShow[library.KEY_ART].get(library.KEY_POSTER))

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_TVSHOW_IS_THIS)
        videoDisplayType.setVideoFile(episode[library.KEY_FILE])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whattvshowisthis.enabled') == 'true'


class WhatSeasonIsThisQuestion(TVQuestion):
    def __init__(self, defaultFilters):
        videoDisplayType = VideoDisplayType()
        super().__init__(videoDisplayType)

        show = library.getTVShows([library.KEY_TITLE, library.KEY_ART]).withFilters(defaultFilters).limitTo(1).asItem()
        if not show:
            raise QuestionException('No tvshows found')

        seasons = library.getSeasons(show[library.KEY_TVSHOW_ID], [library.KEY_SEASON, library.KEY_ART]).limitTo(4).asList()
        correctIdx = random.randint(0, len(seasons) - 1)

        episode = (library.getEpisodes([library.KEY_FILE]).withFilters(defaultFilters).fromShow(show[library.KEY_TITLE])
                          .fromSeason(seasons[correctIdx][library.KEY_SEASON]).limitTo(1).asItem())
        if not episode:
            raise QuestionException('TVshow has no episodes')

        for idx, season in enumerate(seasons):
            self.addAnswer(f"{show[library.KEY_TVSHOW_ID]}-{season[library.KEY_SEASON]}", season[library.KEY_LABEL],
                           image=season[library.KEY_ART].get(library.KEY_POSTER), sortWeight=season[library.KEY_SEASON], correct=(idx == correctIdx))

        self.answers = sorted(self.answers, key=lambda answer: int(answer.sortWeight))

        self.text = strings(Q_WHAT_SEASON_IS_THIS) % show[library.KEY_TITLE]
        videoDisplayType.setVideoFile(episode[library.KEY_FILE])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatseasonisthis.enabled') == 'true'


class WhatEpisodeIsThisQuestion(TVQuestion):
    def __init__(self, defaultFilters):
        videoDisplayType = VideoDisplayType()
        super().__init__(videoDisplayType)

        show = library.getTVShows([library.KEY_TITLE, library.KEY_ART]).withFilters(defaultFilters).limitTo(1).asItem()
        if not show:
            raise QuestionException('No tvshows found')

        season = library.getSeasons(show[library.KEY_TVSHOW_ID], [library.KEY_SEASON, library.KEY_ART]).limitTo(14).asItem()
        if not season:
            raise QuestionException('No seasons found')

        episodes = (library.getEpisodes([library.KEY_EPISODE, library.KEY_TITLE, library.KEY_FILE]).fromShow(show[library.KEY_TITLE])
                           .fromSeason(season[library.KEY_SEASON]).limitTo(4).asList())
        correctIdx = random.randint(0, len(episodes) - 1)

        for idx, episode in enumerate(episodes):
            id = f"{show[library.KEY_TVSHOW_ID]}-{season[library.KEY_SEASON]}-{episode[library.KEY_EPISODE]}"
            self.addAnswer(id=id, text=episode[library.KEY_LABEL], image=season[library.KEY_ART].get(library.KEY_POSTER),
                           sortWeight=episode[library.KEY_EPISODE], correct=(idx == correctIdx))

        self.answers = sorted(self.answers, key=lambda answer: int(answer.sortWeight))

        self.text = strings(Q_WHAT_EPISODE_IS_THIS) % show[library.KEY_TITLE]
        videoDisplayType.setVideoFile(episodes[correctIdx][library.KEY_FILE])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatepisodeisthis.enabled') == 'true'


class WhenWasTVShowFirstAiredQuestion(TVQuestion):
    def __init__(self, defaultFilters):
        super().__init__()

        show = library.getTVShows([library.KEY_TITLE, library.KEY_ART]).withFilters(defaultFilters).limitTo(1).asItem()
        if not show:
            raise QuestionException('No shows found')

        season = library.getSeasons(show[library.KEY_TVSHOW_ID], [library.KEY_SEASON]).limitTo(1).asItem()
        if not season:
            raise QuestionException('No seasons found')

        episode = (library.getEpisodes([library.KEY_FIRST_AIRED]).withFilters(defaultFilters).episode(1)
                          .fromShow(show[library.KEY_TITLE]).fromSeason(season[library.KEY_SEASON]).limitTo(1).asItem())
        if not episode or len(episode[library.KEY_FIRST_AIRED]) < 4:
            raise QuestionException('No episodes found')

        episodeYear = int(episode[library.KEY_FIRST_AIRED][0:4])

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
            self.addAnswer(id=f"{show[library.KEY_TVSHOW_ID]}-{season[library.KEY_SEASON]}", text=str(year),
                           correct=(year == episodeYear))

        self.text = strings(Q_WHEN_WAS_TVSHOW_FIRST_AIRED) % f'{show[library.KEY_TITLE]} - {season[library.KEY_LABEL]}'
        self.setFanartFile(show[library.KEY_ART].get(library.KEY_FANART))

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whenwastvshowfirstaired.enabled') == 'true'


class WhoPlayedRoleInTVShowQuestion(TVQuestion):
    def __init__(self, defaultFilters):
        super().__init__()

        show = library.getTVShows([library.KEY_TITLE, library.KEY_GENRE, library.KEY_CAST, library.KEY_ART]).withFilters(defaultFilters).limitTo(1).asItem()
        if not show or len(show[library.KEY_CAST]) < 4:
            raise QuestionException('No tvshows found')

        otherActors = show[library.KEY_CAST]
        actor = otherActors.pop(random.randint(0, len(otherActors) - 1))

        role = actor[library.KEY_ROLE]
        if re.search('[|/,]', role):
            roles = re.split('[|/,]', role)
            # find random role
            role = roles[random.randint(0, len(roles) - 1)]

        self.addCorrectAnswer(id=actor[library.KEY_NAME], text=actor[library.KEY_NAME], image=actor.get(library.KEY_THUMBNAIL))

        for otherActor in otherActors:
            self.addAnswer(id=otherActor[library.KEY_NAME].encode('utf-8', 'ignore'), text=otherActor[library.KEY_NAME], image=otherActor.get(library.KEY_THUMBNAIL))

            if len(self.answers) == 4:
                break

        random.shuffle(self.answers)

        baseText = strings(Q_WHO_VOICES_ROLE_IN_TVSHOW) if self._isAnimationGenre(show[library.KEY_GENRE]) else strings(Q_WHO_PLAYS_ROLE_IN_TVSHOW)
        self.text = baseText % (role, show[library.KEY_TITLE])
        self.setFanartFile(show[library.KEY_ART].get(library.KEY_FANART))

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whoplayedroleintvshow.enabled') == 'true'


class WhatTVShowIsThisQuoteFrom(TVQuestion):
    def __init__(self, defaultFilters):
        quoteDisplayType = QuoteDisplayType()
        super().__init__(quoteDisplayType)

        episode = (library.getEpisodes([library.KEY_SHOW_TITLE, library.KEY_SEASON, library.KEY_EPISODE, library.KEY_ART])
                          .withFilters(defaultFilters).limitTo(1).asItem())
        if not episode:
            raise QuestionException('No episodes found')

        quoteText = IMDB.getRandomQuote(episode[library.KEY_SHOW_TITLE], season=episode[library.KEY_SEASON], episode=episode[library.KEY_EPISODE],
                                        maxLength=128)
        if quoteText is None:
            raise QuestionException('Did not find any quotes')

        self.addCorrectAnswer(id=episode[library.KEY_SHOW_TITLE], text=episode[library.KEY_SHOW_TITLE], image=episode[library.KEY_ART].get(library.KEY_TVSHOW_POSTER))

        otherShows = (library.getTVShows([library.KEY_TITLE, library.KEY_ART]).withFilters(defaultFilters)
                             .excludeTitles([episode[library.KEY_SHOW_TITLE]]).limitTo(3).asList())
        for otherShow in otherShows:
            self.addAnswer(id=otherShow[library.KEY_TITLE].encode('utf-8', 'ignore'), text=otherShow[library.KEY_TITLE], image=otherShow[library.KEY_ART].get(library.KEY_POSTER))

        random.shuffle(self.answers)
        quoteDisplayType.setQuoteText(quoteText)
        self.text = strings(Q_WHAT_TVSHOW_IS_THIS_QUOTE_FROM)

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whattvshowisthisquotefrom.enabled') == 'true' and IMDB.isDataPresent()


#
# Music Questions
#


class MusicQuestion(Question):
    pass

class WhatSongIsThisQuestion(MusicQuestion):
    def __init__(self, defaultFilters):
        audioDisplayType = AudioDisplayType()
        super().__init__(audioDisplayType)

        correctAnswer = (library.getSongs([library.KEY_TITLE, library.KEY_ARTIST, library.KEY_ARTIST_ID, library.KEY_FILE, library.KEY_THUMBNAIL])
                                .withFilters(defaultFilters).limitTo(1).asItem())
        if not correctAnswer:
            raise QuestionException('No songs found')

        self.addCorrectAnswer(id=correctAnswer[library.KEY_FILE], text=correctAnswer[library.KEY_TITLE], image=correctAnswer.get(library.KEY_THUMBNAIL))

        # Fill with random songs
        theRest = (library.getSongs([library.KEY_TITLE, library.KEY_ARTIST, library.KEY_THUMBNAIL]).withFilters(defaultFilters)
                          .excludeTitles(self.getAnswerTexts()).withArtist(correctAnswer[library.KEY_ARTIST][0]).limitTo(4 - len(self.answers)).asList())
        for song in theRest:
            self.addAnswer(id=-1, text=song[library.KEY_TITLE], image=song.get(library.KEY_THUMBNAIL))

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_SONG_IS_THIS) % correctAnswer[library.KEY_ARTIST][0]
        audioDisplayType.setAudioFile(correctAnswer[library.KEY_FILE])

        artist = library.getArtistDetails(correctAnswer[library.KEY_ARTIST_ID][0], [library.KEY_FANART]).asItem()
        self.setFanartFile(artist.get(library.KEY_FANART))

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatsongisthis.enabled') == 'true'


class WhoMadeThisSongQuestion(MusicQuestion):
    def __init__(self, defaultFilters):
        audioDisplayType = AudioDisplayType()
        super().__init__(audioDisplayType)

        correctAnswer = library.getArtists().withFilters(defaultFilters).limitTo(1).asItem()
        artist = library.getArtistDetails(correctAnswer[library.KEY_ARTIST_ID], [library.KEY_THUMBNAIL]).asItem()
        song = library.getSongs([library.KEY_TITLE, library.KEY_FILE]).withFilters(defaultFilters).withArtist(correctAnswer[library.KEY_ARTIST]).limitTo(1).asItem()
        if not correctAnswer or not song:
            raise QuestionException('No artist or song found')

        self.addCorrectAnswer(id=correctAnswer[library.KEY_ARTIST_ID], text=correctAnswer[library.KEY_ARTIST], image=artist.get(library.KEY_THUMBNAIL))

        # Fill with random artists
        theRest = library.getArtists().withFilters(defaultFilters).withoutArtist(correctAnswer[library.KEY_ARTIST]).limitTo(4 - len(self.answers)).asList()
        for item in theRest:
            artist = library.getArtistDetails(item[library.KEY_ARTIST_ID], [library.KEY_THUMBNAIL]).asItem()
            self.addAnswer(id=item[library.KEY_ARTIST], text=item[library.KEY_ARTIST], image=artist.get(library.KEY_THUMBNAIL))

        random.shuffle(self.answers)
        self.text = strings(Q_WHO_MADE_THE_SONG) % song[library.KEY_TITLE]
        audioDisplayType.setAudioFile(song[library.KEY_FILE])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whomadethissong.enabled') == 'true'


class WhoMadeThisAlbumQuestion(MusicQuestion):
    def __init__(self, defaultFilters):
        photoDisplayType = PhotoDisplayType()
        super().__init__(photoDisplayType)

        correctAnswer = library.getArtists().withFilters(defaultFilters).limitTo(1).asItem()
        artist = library.getArtistDetails(correctAnswer[library.KEY_ARTIST_ID], [library.KEY_THUMBNAIL]).asItem()
        album = (library.getAlbums([library.KEY_TITLE, library.KEY_FANART, library.KEY_THUMBNAIL]).withFilters(defaultFilters)
                        .withArtist(correctAnswer[library.KEY_ARTIST]).limitTo(1).asItem())
        if not correctAnswer or not album:
            raise QuestionException('No artist or album found')

        self.addCorrectAnswer(id=correctAnswer[library.KEY_ARTIST_ID], text=correctAnswer[library.KEY_ARTIST], image=artist.get(library.KEY_THUMBNAIL))

        # Fill with random artists
        theRest = library.getArtists().withFilters(defaultFilters).withoutArtist(correctAnswer[library.KEY_ARTIST]).limitTo(4 - len(self.answers)).asList()
        for item in theRest:
            artist = library.getArtistDetails(item[library.KEY_ARTIST_ID], [library.KEY_THUMBNAIL]).asItem()
            self.addAnswer(id=item[library.KEY_ARTIST], text=item[library.KEY_ARTIST], image=artist.get(library.KEY_THUMBNAIL))

        random.shuffle(self.answers)
        self.text = strings(Q_WHO_MADE_THE_ALBUM) % album[library.KEY_TITLE]
        photoDisplayType.setPhotoFile(album.get(library.KEY_THUMBNAIL))
        self.setFanartFile(album.get(library.KEY_FANART))

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whomadethisalbum.enabled') == 'true'


class QuestionException(Exception):
    pass


def getEnabledQuestionCandidates(gameInstance: game.UnlimitedGame):
    """
    Gets all enabled question types for the game
    """
    if gameInstance.getType() == game.GAMETYPE_MOVIE:
        questionCandidates = MovieQuestion.__subclasses__()
    elif gameInstance.getType() == game.GAMETYPE_TVSHOW:
        questionCandidates = TVQuestion.__subclasses__()
    elif gameInstance.getType() == game.GAMETYPE_MUSIC:
        questionCandidates = MusicQuestion.__subclasses__()

    return [candidate for candidate in questionCandidates if candidate.isEnabled()]


def isAnyMovieQuestionsEnabled():
    return [subclass for subclass in MovieQuestion.__subclasses__() if subclass.isEnabled()]


def isAnyTVShowQuestionsEnabled():
    return [subclass for subclass in TVQuestion.__subclasses__() if subclass.isEnabled()]


def isAnyMusicQuestionsEnabled():
    return [subclass for subclass in MusicQuestion.__subclasses__() if subclass.isEnabled()]

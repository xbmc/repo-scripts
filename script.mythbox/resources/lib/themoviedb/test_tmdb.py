#!/usr/bin/env python2.5
#encoding:utf-8
#author:dbr/Ben
#project:themoviedb

import unittest

import tmdb

class test_search(unittest.TestCase):
    def setUp(self):
        self.m = tmdb.MovieDb()

    def test_simple_search(self):
        """Simple test search
        """
        self.assertEquals(
            type(
                self.m.search("Fight Club")
            ),
            tmdb.SearchResults
        )

    def test_search_results(self):
        """Check SearchResults are usable
        """
        results = self.m.search("Fight Club")
        first_result = results[0]

        self.assertEquals(
            type(first_result),
            tmdb.MovieResult
        )

        self.assertEquals(
            first_result['name'],
            'Fight Club'
        )

        self.assertEquals(
            first_result['released'],
            '1999-09-16'
        )

        self.assertEquals(
            first_result['imdb_id'],
            'tt0137523'
        )

class test_getmovieinfo(unittest.TestCase):
    def test_search_to_info(self):
        """Gets a movie ID via search, then calls getMovieInfo using this
        """
        sr = tmdb.search("fight club")[0]
        movie = tmdb.getMovieInfo(sr['id'])
        self.assertEquals(
            sr['name'],
            movie['name']
        )
    
    def test_get_director(self):
        """Checks you can get the director of a film
        """
        mid = tmdb.search("Inglourious Basterds")[0]['id']
        movie = tmdb.getMovieInfo(mid)

        self.assertTrue(len(movie['cast']['director']) == 1)
        self.assertEquals(
            movie['cast']['director'][0]['name'],
            "Quentin Tarantino"
        )

class test_wrappers(unittest.TestCase):
    def test_search_wrapper(self):
        """Tests tmdb.search() wrapper works correctly
        """
        r = tmdb.search("The Matrix")
        self.assertEquals(
            type(r),
            tmdb.SearchResults
        )

    def test_getmovieinfo_wrapper(self):
        """Tests tmdb.getMovieInfo() wrapper works correctly
        """
        r = tmdb.getMovieInfo(550)
        self.assertEquals(
            type(r),
            tmdb.Movie
        )

class test_artwork(unittest.TestCase):
    def setUp(self):
        filmId = tmdb.MovieDb().search("Fight Club")[0]['id']
        self.film = tmdb.MovieDb().getMovieInfo(filmId)

    def test_poster_urls(self):
        """Checks posters are valid looking URLs
        """
        for _id in self.film['images']['poster']:
            for size in self.film['images']['poster'][_id]:
                url = self.film['images']['poster'][_id][size]
                self.assertTrue(
                    url.startswith("http://")
                )

    def test_backdrop_urls(self):
        """Checks backdrop images are valid looking URLs
        """
        for _id in self.film['images']['backdrop']:
            for size in self.film['images']['backdrop'][_id]:
                url = self.film['images']['backdrop'][_id][size]
                self.assertTrue(
                    url.startswith("http://")
                )

    def test_artwork_repr(self):
        """Checks artwork repr looks sensible
        """
        self.assertTrue(
            repr(self.film['images']).startswith(
                "<Images with "
            )
        )


if __name__ == '__main__':
    unittest.main()
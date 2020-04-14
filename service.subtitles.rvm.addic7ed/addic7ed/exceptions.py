# coding: utf-8
# Created on: 06.04.2016
# Author: Roman Miroshnychenko aka Roman V.M. (roman1972@gmail.com)


class Add7Exception(Exception):
    pass


class ParseError(Add7Exception):
    pass


class SubsSearchError(Add7Exception):
    pass


class Add7ConnectionError(Add7Exception):
    pass


class DailyLimitError(Add7Exception):
    pass

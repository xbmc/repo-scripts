import sys

from lib import weather
from lib import config

if (__name__ == '__main__'):
	config.init(cache=True)
	weather.Main(sys.argv[1])


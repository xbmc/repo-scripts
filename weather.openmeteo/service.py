from lib import service
from lib import config

if (__name__ == '__main__'):
	config.init(cache=True)
	service.Main()


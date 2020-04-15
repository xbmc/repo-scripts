import sys
from lib import maps


if ( __name__ == "__main__" ):
    try:
        params = dict(arg.split('=') for arg in sys.argv[1].split('&'))
    except:
        params = {}
    maps.Main(params=params)

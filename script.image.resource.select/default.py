import sys
from lib import select

if (__name__ == '__main__'):
    try:
        params = dict(arg.split('=') for arg in sys.argv[ 1 ].split('&'))
    except:
        params = {}
    select.Main(params=params)

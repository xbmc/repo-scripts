import sys

from conf import Conf
from pair import ask_user_if_repair
from utils import debug


debug('main_pair.py sys.argv = ' + str(sys.argv))


if __name__ == '__main__':
    conf = Conf()

    if conf.is_paired:
        should_repair = ask_user_if_repair()
        debug('User asked to pair again')
    else:
        should_repair = True

    if should_repair:
        debug('Asking for re-pair')
        conf.ask_repair()

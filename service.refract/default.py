"""Actions from the add-on settings: connect or disconnect the Refract account."""
import sys

from resources.lib import account

account.main(sys.argv[1:])

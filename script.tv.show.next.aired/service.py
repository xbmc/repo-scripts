from default import NextAired

# This will startup the Next-Aired script as a background updater.  If the skin is
# also starting one up, the skin's version notices that we're running and exits.
sys.argv = [ 'default.py', 'service=true' ]
NextAired()

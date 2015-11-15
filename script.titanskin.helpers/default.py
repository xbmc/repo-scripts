from migration import *


# get arguments
action = ""
try:
    action = str(sys.argv[1])
except: 
    pass

if action =="migrate":
    fullMigration()
	
elif action =="migratecolors":
    migrateColorSettings()

elif action =="migratethemes":
    migrateColorThemes()

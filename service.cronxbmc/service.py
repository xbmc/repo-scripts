from resources.lib.cron import utils, CronService

# run the program
utils.log("Cron for Kodi service starting....")
CronService().runProgram()

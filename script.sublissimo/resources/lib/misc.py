def decimal_timeline_with_checker(timestring):
    try:
        decimal_timestring = (3600000 * int(timestring[:2]) + 60000
                    * int(timestring[3:5]) + 1000 * int(timestring[6:8]) + int(timestring[9:12]))
        return decimal_timestring
    except ValueError:
        return False

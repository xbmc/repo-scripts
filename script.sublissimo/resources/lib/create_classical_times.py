def create_classical_times(decimal):
    hours = int(decimal / 3600000)
    restminutes = decimal % 3600000
    minutes = int(restminutes / 60000)
    restseconds = restminutes % 60000
    seconds = int(restseconds / 1000)
    milliseconds = int(restseconds % 1000)
    output = (str(hours).zfill(2) + ":" + str(minutes).zfill(2) + ":" +
              str(seconds).zfill(2) + "," + str(milliseconds).zfill(3))
    return output

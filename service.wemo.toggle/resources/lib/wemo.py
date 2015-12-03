import urllib2

class wemo():
    def __init__(self, ip_address, debug=False):
        self.debug = debug
        self._url = 'http://{0}:{1}/upnp/control/basicevent1'
        self.ip_address = ip_address
        self._port = None
        self._get_header = {'Content-type': 'text/xml; charset="utf-8"', 'SOAPACTION': '"urn:Belkin:service:basicevent:1#GetBinaryState"'}
        self._get_data = '''
                        <?xml version="1.0" encoding="utf-8"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
                        <s:Body><u:GetBinaryState xmlns:u="urn:Belkin:service:basicevent:1"><BinaryState>1</BinaryState></u:GetBinaryState></s:Body></s:Envelope>
                        '''
        self._set_header = {'Content-type': 'text/xml; charset="utf-8"', 'SOAPACTION': '"urn:Belkin:service:basicevent:1#SetBinaryState"'}
        self._set_data = '''
                    <?xml version="1.0" encoding="utf-8"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
                    s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body><u:SetBinaryState xmlns:u="urn:Belkin:service:basicevent:1"><BinaryState>{0}</BinaryState>
                    </u:SetBinaryState></s:Body></s:Envelope>
                    '''
        self.get_port()

    def log(self, msg):
        if self.debug:
            print(msg)

    def get_port(self):
        for port in ['49152', '49153', '49154', '49155']:
            try:
                current_state = urllib2.urlopen(urllib2.Request(self._url.format(self.ip_address, port), self._get_data, self._get_header), timeout = 3).read()[216]
                if current_state in ['0', '1']:
                    self._port = port
                    self.log('INFO - {0}:{1}'.format(self.ip_address, self._port))
                    return True
            except Exception, e:
                self.port = False
                self.log('ERROR - {0}:{1} - {2}'.format(self.ip_address, port, e))
        raise ValueError('Unable to access WeMo Switch: {0}'.format(self.ip_address))

    def get_state(self):
        try:
            return urllib2.urlopen(urllib2.Request(self._url.format(self.ip_address, self._port), self._get_data, self._get_header), timeout = 3).read()[216]
        except Exception, e:
            if self.get_port():
                self.get_state()
            else:
                self.log('ERROR - Unable to access the current state of WeMo Switch: {0}:{1} - {2}'.format(self.ip_address, self._port, e))
                return False

    def on(self):
        try:
            urllib2.urlopen(urllib2.Request(self._url.format(self.ip_address, self._port), self._set_data.format(1), self._set_header))
            self.log('INFO - On - {0}:{1}'.format(self.ip_address, self._port))
        except Exception, e:
            if self.get_port():
                self.on()
            self.log('ERROR - On - {0}:{1} - {2}'.format(self.ip_address, self._port, e))

    def off(self):
        try:
            urllib2.urlopen(urllib2.Request(self._url.format(self.ip_address, self._port), self._set_data.format(0), self._set_header))
            self.log('INFO - Off - {0}:{1}'.format(self.ip_address, self._port))
        except Exception, e:
            if self.get_port():
                self.off()
            self.log('ERROR - Off - {0}:{1} - {2}'.format(self.ip_address, self._port, e))

    def toggle(self):
        if self.get_state() in ['0', '1', '8']:
            if self.get_state() == '0':
                try:
                    urllib2.urlopen(urllib2.Request(self._url.format(self.ip_address, self._port), self._set_data.format(1), self._set_header))
                except Exception, e:
                    if self.get_port():
                        self.toggle()
                    self.log('ERROR - Toggle On - {0}:{1} - {2}'.format(self.ip_address, self._port, e))
            elif self.get_state() in ['1', '8']:
                try:
                    urllib2.urlopen(urllib2.Request(self._url.format(self.ip_address, self._port), self._set_data.format(0), self._set_header))
                except Exception, e:
                    if self.get_port():
                        self.toggle()
                    self.log('ERROR - Toggle Off - {0}:{1} - {2}'.format(self.ip_address, self._port, e))
        else:
            self.log('ERROR - Toggle - Unable to access WeMo Switch: {0}'.format(self.ip_address))

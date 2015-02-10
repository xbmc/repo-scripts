from service import RadioDNS_Service
import re


class RadioDNS_IPService(RadioDNS_Service):

    def __init__(self, fqdn, si):
        self._fqdn = fqdn
		

    def resolveAuthorativeFQDN(self):
        return self._fqdn
		


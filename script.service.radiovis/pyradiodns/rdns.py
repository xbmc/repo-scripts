from radiodns.am_service import RadioDNS_AMService
from radiodns.dab_service import RadioDNS_DABService
from radiodns.fm_service import RadioDNS_FMService
from radiodns.hd_service import RadioDNS_HDService
from radiodns.ip_service import RadioDNS_IPService

class RadioDNS:

    KNOWN_APPLICATIONS = [
        ('radioepg', 'TCP'),
        ('radiotag', 'TCP'),
        ('radiovis', 'TCP'),
    ]

    def lookup_am(self, type=None, sid=None):
        service = RadioDNS_AMService(type, sid)
        return self.__lookup(service)

    def lookup_dab(self, ecc=None, eid=None, sid=None, scids=None, data=None):
        service = RadioDNS_DABService(ecc, eid, sid, scids, data)
        return self.__lookup(service)

    def lookup_fm(self, country=None, pi=None, frequency=None):
        service = RadioDNS_FMService(country, pi, frequency)
        return self.__lookup(service)

    def lookup_hd(self, tx=None, cc=None):
        service = RadioDNS_HDService(tx, cc)
        return self.__lookup(service)
		
    def lookup_ip(self, fqdn=None, si=None):
	   service = RadioDNS_IPService(fqdn, si)
	   return self.__lookup(service)

    def __lookup(self, service):
        results = {}
        results['authorative_fqdn'] = service.resolveAuthorativeFQDN()
        if not (results['authorative_fqdn']):
            return False
        results['applications'] = {}
        for application in self.KNOWN_APPLICATIONS:
            (app_id, transport) = application
            result = service.resolve(app_id, transport)
            results['applications'][app_id] = {}
            supported = True if result != False else False
            results['applications'][app_id]['supported'] = supported
            if (result):
                results['applications'][app_id]['servers'] = result
        return results

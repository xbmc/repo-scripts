from service import RadioDNS_Service
import re


class RadioDNS_FMService(RadioDNS_Service):

    def __init__(self, country, pi, frequency):
        country_pattern = re.compile('^[0-9A-Fa-f]{3}$')
        pi_pattern = re.compile('^[0-9A-Fa-f]{4}$')

        # Country
        if len(country) == 2:
            self.rds_cc_ecc = None
            self.iso3166_country_code = country
        elif country_pattern.match(country):
            self.rds_cc_ecc = country
            self.iso3166_country_code = None
        else:
            raise ValueError('Invalid country')

        # TODO Tidy this up
        # Must be a valid hexadecimal RDS Programme Identifier (PI) code
        # and the first character must match the first character of the
        # combined RDS Country Code and RDS Extended Country Code (ECC)
        # value (if supplied).
        if pi_pattern.match(pi):
            self.pi = pi
        else:
            raise ValueError('Invalid PI value')

        if isinstance(frequency, float) or isinstance(frequency, int):
            if frequency > 108:
                raise ValueError('Frequency can not be above 108.0 Mhz')
            elif frequency < 76:
                raise ValueError('Frequency can not be below 76.0 Mhz')
            self.frequency = frequency
        else:
            raise ValueError('Frequency must be a number')

    def fqdn(self):
        country = self.rds_cc_ecc or self.iso3166_country_code
        fqdn = "%05d.%s.%s.fm.radiodns.org" %\
            (self.frequency * 100, self.pi, country)
        return fqdn.lower()

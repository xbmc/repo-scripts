from service import RadioDNS_Service
import re

class RadioDNS_HDService(RadioDNS_Service):
  
  def __init__(self, type, sid):
    # Compile regex patterns
    sid_pattern = re.compile('^[0-9A-F]{6}$')
    
    # Type
    if type == 'drm' or type == 'amss':
      self.type = type
    else:
      print 'Invalid type value. Must be either \'drm\' (Digital Radio Mondiale) or \'amss\' (AM Signalling System).'
      return None
    
    # SID
    if sid_pattern.match(sid):
      self.sid = sid
    else:
      print('Invalid Service Identifier (SId) value. Must be a valid 6-character hexadecimal.');
      return None
      
      
  def fqdn(self):
    fqdn = "%s.%s.radiodns.org" % (self.sid, self.type)
    fqdn = fqdn.lower()
    return fqdn

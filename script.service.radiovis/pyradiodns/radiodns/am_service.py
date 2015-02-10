from service import RadioDNS_Service
import re

class RadioDNS_AMService(RadioDNS_Service):
  
  def __init__(self, type, sid):
    type = type.lower()
    if type == 'drm' or type == 'amss':
      self.type = type
    else:
      raise ValueError("Type value must be either 'drm' or 'amss'")
    
    if re.compile('^[0-9A-Fa-f]{6}$').match(sid):
      self.sid = sid.lower()
    else:
      raise ValueError('Service Identifier (SId) must be a valid 6-character hexadecimal.');
      
  def fqdn(self):
    fqdn = "%s.%s.radiodns.org" % (self.sid, self.type)
    return fqdn.lower()

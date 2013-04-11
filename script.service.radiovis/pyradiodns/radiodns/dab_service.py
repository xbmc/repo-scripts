from service import RadioDNS_Service
import re

class RadioDNS_DABService(RadioDNS_Service):
  
  def __init__(self, ecc, eid, sid, scids, data=None):
    # Compile regex patterns
    ecc_pattern = re.compile('^[0-9A-F]{3}$')
    eid_pattern = re.compile('^[0-9A-F]{4}$')
    sid_pattern = re.compile('^[0-9A-F]{4}$|^[0-9A-F]{8}$')
    scids_pattern = re.compile('^[0-9A-F]{1}$|^[0-9A-F]{3}$')
    data_pattern = re.compile('^[0-9A-F]{2}-[0-9A-F]{3}$')
    
    # ECC
    if ecc_pattern.match(ecc):
      self.ecc = ecc
    else:
      print('Invalid Extended Country Code (ECC) value. Must be a valid 3-character hexadecimal.');
      return None
      
    # EID
    if eid_pattern.match(eid):
      self.eid = eid
    else:
      print('Invalid Ensembled Identifier (EId) value. Must be a valid 4-character hexadecimal.');
      return None
      
    # SID
    if sid_pattern.match(sid):
      self.sid = sid
    else:
      print('Invalid Service Identifier (SId) value. Must be a valid 4 or 8-character hexadecimal.');
      return None
      
    # SCIDS
    if scids_pattern.match(str(scids)):
      self.scids = scids
    else:
      print('Invalid Service Component Identifer within the Service (SCIdS) value. Must be a valid 3-character hexadecimal.');
      return None
      
    # AppTy/UAtype
    if data:
      self.data = data
      if xpad_pattern.match(data):
        self.xpad = self.data
        self.pa = None
      elif isinstance(data, int) and 0 >= self.data <= 1023:
        self.xpad = None
        self.pa = self.data
      else:
        print 'Invalid data value. Must be either a valid X-PAD Applicaton Type (AppTy) and User Applicaton type (UAtype) hexadecimal or Packet Address integer.'
        return None
    else:
      self.data = None  
      
      
  def fqdn(self):
    fqdn = "%s.%s.%s.%s.dab.radiodns.org" % (self.scids, self.sid, self.eid, self.ecc)
    if self.data:
      if self.xpad:
        fqdn = sprintf('%s.%s', self.xpad, fqdn)
      elif self.pa:
        fqdn = sprintf('%s.%s', self.pa, fqdn)
    fqdn = fqdn.lower()
    return fqdn

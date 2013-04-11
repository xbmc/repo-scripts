import dns.resolver

class RadioDNS_Service:
  
  dns_resolver = None
  cached_authorative_fqdn = None
  
  def __init__(self):
    pass
    
  def setupDNSResolver(self):
    self.dns_resolver = dns.resolver
    
  def resolveAuthorativeFQDN(self):
    if not self.dns_resolver:
      self.setupDNSResolver()
    r = self.dns_resolver.query(self.fqdn(), 'CNAME')
    if not r:
      return False
    if not r.response.answer[0].items:
      return False
    self.cached_authorative_fqdn = r.response.answer[0].items[0].to_text()
    return self.cached_authorative_fqdn
    
  def resolve(self, application_id, transport_protocol='TCP'):
    if self.cached_authorative_fqdn:
      authorative_fqdn = self.cached_authorative_fqdn
    else:
      authorative_fqdn = self.resolveAuthorativeFQDN()
    if not authorative_fqdn:
      return False
    application_fqdn = "_%s._%s.%s" % (application_id.lower(), transport_protocol.lower(), authorative_fqdn)
    if not self.dns_resolver:
      self.setupDNSResolver()
    try:
      r = self.dns_resolver.query(application_fqdn, 'SRV')
      if len(r.response.answer) == 0:
        return False
      results = []
      for answer in r.response.answer:
        results.append({
          'target': r.response.answer[0].items[0].target.to_text(),
          'port': r.response.answer[0].items[0].port,
          'priority': r.response.answer[0].items[0].priority,
          'weight': r.response.answer[0].items[0].weight,
        })
      return results
    except dns.resolver.NXDOMAIN:
      # Non-existent domain
      return False